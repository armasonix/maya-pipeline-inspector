"""Maya-side execution for planned safe actions."""

from __future__ import annotations

import contextlib
import glob
import importlib
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from pipeline_inspector.core.fix_plan import FixAction
from pipeline_inspector.core.fix_plan import (
    HIGH_RISK_BLOCK_REASON,
    NAMING_FIX_TYPE,
    resolve_normalize_path_value,
)
from pipeline_inspector.core.naming_fix import texture_tile_filename_from_paths
from pipeline_inspector.studio_config import StudioEnvironmentSettings
from pipeline_inspector.util.paths import (
    author_maya_texture_path_for_fix,
    sync_studio_environment_to_os,
)

SUPPORTED_FIX_TYPES = frozenset(
    {
        "set_attr",
        "relink_path",
        "normalize_path",
        "disable_feature",
        "rename_node",
        "rename_texture_file",
    }
)
DEFAULT_UNDO_CHUNK_NAME = "Pipeline Inspector Apply Fixes"
DEFAULT_TEXTURE_PATH_ATTR = "fileTextureName"
REFERENCED_BLOCK_REASON = "target_referenced"
LOCKED_BLOCK_REASON = "target_locked"
READ_ONLY_NODE_REASON = "target_read_only"
UNSUPPORTED_FIX_REASON = "unsupported_fix_type"
MISSING_TARGET_REASON = "target_node_missing"
MISSING_ATTR_REASON = "target_attr_missing"
INVALID_RELINK_PATH_REASON = "invalid_relink_path"
INVALID_NORMALIZE_PATH_REASON = "invalid_normalize_path"
INVALID_RENAME_NAME_REASON = "invalid_rename_name"
RENAME_FAILED_REASON = "rename_failed"
REFERENCE_RENAME_NOT_PERSISTED_REASON = "reference_rename_not_persisted"
INVALID_TEXTURE_FILE_RENAME_REASON = "invalid_texture_file_rename"
TEXTURE_FILE_MISSING_REASON = "texture_file_missing"
METADATA_PLUG_NAMES = frozenset({"version"})


@dataclass(frozen=True)
class AppliedFixRecord:
    fix_id: str
    rule_id: str
    fix_type: str
    target_node: str
    target_attr: Optional[str]
    before_value: Any = None
    after_value: Any = None
    applied: bool = False
    blocked: bool = False
    message: str = ""
    block_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fix_id": self.fix_id,
            "rule_id": self.rule_id,
            "fix_type": self.fix_type,
            "target_node": self.target_node,
            "target_attr": self.target_attr,
            "before_value": self.before_value,
            "after_value": self.after_value,
            "applied": self.applied,
            "blocked": self.blocked,
            "message": self.message,
            "block_reasons": list(self.block_reasons),
        }


@dataclass(frozen=True)
class ApplyFixReport:
    records: tuple[AppliedFixRecord, ...]
    undo_chunk_name: str = DEFAULT_UNDO_CHUNK_NAME

    @property
    def total(self) -> int:
        return len(self.records)

    @property
    def applied_count(self) -> int:
        return sum(1 for record in self.records if record.applied)

    @property
    def blocked_count(self) -> int:
        return sum(1 for record in self.records if record.blocked)

    @property
    def failed_count(self) -> int:
        return sum(1 for record in self.records if not record.applied and (not record.blocked))

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "total": self.total,
            "applied_count": self.applied_count,
            "blocked_count": self.blocked_count,
            "failed_count": self.failed_count,
            "undo_chunk_name": self.undo_chunk_name,
            "records": [record.to_dict() for record in self.records],
        }
        return payload


def apply_fix_actions(
    actions: Iterable[FixAction],
    *,
    cmds: Optional[Any] = None,
    allow_referenced: bool = False,
    allow_locked: bool = False,
    allow_high_risk: bool = False,
    undo_chunk_name: str = DEFAULT_UNDO_CHUNK_NAME,
) -> ApplyFixReport:
    maya_cmds = cmds or _maya_cmds()
    queued = tuple(actions)
    if not queued:
        return ApplyFixReport(records=(), undo_chunk_name=undo_chunk_name)
    records: list[AppliedFixRecord] = []
    maya_cmds.undoInfo(openChunk=True, chunkName=undo_chunk_name)
    try:
        for action in queued:
            records.append(
                _apply_one(action, maya_cmds, allow_referenced, allow_locked, allow_high_risk)
            )
    finally:
        maya_cmds.undoInfo(closeChunk=True)
    return ApplyFixReport(records=tuple(records), undo_chunk_name=undo_chunk_name)


def _apply_one(
    action: FixAction, cmds: Any, allow_referenced: bool, allow_locked: bool, allow_high_risk: bool
) -> AppliedFixRecord:
    reasons = _reasons(action, allow_referenced, allow_locked, allow_high_risk)
    if reasons:
        return _blocked(action, reasons)
    if action.fix_type not in SUPPORTED_FIX_TYPES:
        return _blocked(action, [UNSUPPORTED_FIX_REASON])
    exists_target = action.target_node
    if action.fix_type == "rename_node":
        exists_target = _resolve_existing_dag_path(
            cmds,
            action.target_node,
            prefer_referenced=bool(action.referenced or action.requires_reference_edit),
        )
    if not exists_target or not _node_exists(cmds, exists_target):
        return _blocked(action, [MISSING_TARGET_REASON])
    if action.fix_type == "set_attr":
        return _apply_set_attr(action, cmds)
    if action.fix_type == "relink_path":
        return _apply_relink_path(action, cmds)
    if action.fix_type == "normalize_path":
        return _apply_normalize_path(action, cmds)
    if action.fix_type == "disable_feature":
        return _apply_disable_feature(action, cmds)
    if action.fix_type == "rename_node":
        return _apply_rename_node(
            action, cmds, allow_referenced=allow_referenced, allow_locked=allow_locked
        )
    if action.fix_type == "rename_texture_file":
        return _apply_rename_texture_file(action, cmds)
    return _blocked(action, [UNSUPPORTED_FIX_REASON])


def _apply_rename_texture_file(action: FixAction, cmds: Any) -> AppliedFixRecord:
    raw_before = action.before_value
    raw_after = action.after_value
    if not _is_path_string_value(raw_before) or not _is_path_string_value(raw_after):
        return _blocked(action, [INVALID_TEXTURE_FILE_RENAME_REASON])
    target_attr = _path_target_attr(action)
    if not target_attr:
        return _blocked(action, [MISSING_ATTR_REASON])
    resolved_before = str(action.params.get("resolved_before") or raw_before)
    is_udim = bool(action.params.get("is_udim"))
    rename_error = _rename_texture_files_on_disk(
        resolved_before, str(raw_before), str(raw_after), is_udim=is_udim
    )
    if rename_error:
        return _blocked(action, [rename_error])
    path_record = _apply_path_value(
        action, cmds, target_attr, str(raw_after).strip().replace("\\", "/"), str(raw_before)
    )
    if path_record.blocked:
        return path_record
    node_after = action.params.get("node_name_after")
    if isinstance(node_after, str) and node_after.strip() and cmds.objExists(action.target_node):
        if _is_read_only_node(cmds, action.target_node):
            return _blocked(action, [READ_ONLY_NODE_REASON])
        try:
            cmds.rename(action.target_node, node_after.strip())
        except RuntimeError as exc:
            if _is_read_only_rename_error(exc):
                return _blocked(action, [READ_ONLY_NODE_REASON])
            raise
    return path_record


def _rename_texture_files_on_disk(
    resolved_before: str, raw_before: str, raw_after: str, *, is_udim: bool
) -> Optional[str]:
    if is_udim or "<UDIM>" in resolved_before or "<udim>" in resolved_before:
        return _rename_udim_texture_files(resolved_before, raw_before, raw_after)
    source = Path(os.path.expandvars(os.path.expanduser(resolved_before.replace("/", os.sep))))
    destination = _resolved_destination_path(source, raw_before, raw_after)
    if destination is None:
        destination = Path(
            os.path.expandvars(os.path.expanduser(str(raw_after).replace("/", os.sep)))
        )
    if not source.is_file():
        if _texture_destination_ready(destination, raw_after, is_udim=False):
            return None
        return TEXTURE_FILE_MISSING_REASON
    if destination.exists():
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.rename(source, destination)
    return None


def _rename_udim_texture_files(
    resolved_before: str, raw_before: str, raw_after: str
) -> Optional[str]:
    glob_pattern = resolved_before.replace("<UDIM>", "[0-9][0-9][0-9][0-9]").replace(
        "<udim>", "[0-9][0-9][0-9][0-9]"
    )
    matched_files = sorted(glob.glob(glob_pattern))
    if not matched_files:
        if _texture_destination_ready(
            Path(str(raw_after).replace("\\", "/")), raw_after, is_udim=True
        ):
            return None
        return TEXTURE_FILE_MISSING_REASON
    for old_file in matched_files:
        old_path = Path(old_file)
        new_name = texture_tile_filename_from_paths(
            old_path.name, raw_before=raw_before, raw_after=raw_after
        )
        if not new_name:
            return INVALID_TEXTURE_FILE_RENAME_REASON
        new_path = old_path.with_name(new_name)
        if new_path.exists():
            continue
        os.rename(old_path, new_path)
    return None


def _texture_destination_ready(path: Path, raw_after: str, *, is_udim: bool) -> bool:
    from pipeline_inspector.core.fix_plan import texture_path_resolves_on_disk

    return texture_path_resolves_on_disk(
        str(raw_after or path),
        is_udim=is_udim or "<UDIM>" in str(raw_after) or "<udim>" in str(raw_after),
    )


def _resolved_destination_path(source: Path, raw_before: str, raw_after: str) -> Optional[Path]:
    before_name = Path(str(raw_before).replace("\\", "/")).name
    after_name = Path(str(raw_after).replace("\\", "/")).name
    if not before_name or not after_name:
        return None
    if source.name != before_name:
        return source.with_name(after_name)
    return source.with_name(after_name)


def _apply_rename_node(
    action: FixAction, cmds: Any, *, allow_referenced: bool = False, allow_locked: bool = False
) -> AppliedFixRecord:
    proposed_name = action.after_value
    if not isinstance(proposed_name, str) or not proposed_name.strip():
        return _blocked(action, [INVALID_RENAME_NAME_REASON])
    rename_target = _resolve_rename_target_node(cmds, action)
    before_name = _node_short_name(cmds, rename_target)
    if before_name is None:
        return _blocked(action, [MISSING_TARGET_REASON])
    runtime_referenced = _node_is_referenced(cmds, rename_target)
    allow_reference_edit = allow_referenced and (
        action.requires_reference_edit or action.referenced or runtime_referenced
    )
    rename_target = _canonical_dag_node(cmds, rename_target) or rename_target
    target_node_locked = _query_lock_node(cmds, rename_target)
    target_name_locked = _query_lock_node_name(cmds, rename_target)
    if allow_reference_edit:
        prep = _prepare_reference_edit(cmds, rename_target)
        updated_target = prep.get("node_name")
        if isinstance(updated_target, str) and updated_target.strip():
            rename_target = updated_target
    elif not allow_locked and target_node_locked:
        return _blocked(action, [READ_ONLY_NODE_REASON])
    renamed_node, rename_error = _rename_dag_node(
        cmds,
        rename_target,
        str(proposed_name).strip(),
        allow_reference_edit=allow_reference_edit,
        allow_unlock=target_node_locked or target_name_locked,
    )
    if renamed_node is None:
        if rename_error and _is_read_only_rename_error(RuntimeError(rename_error)):
            return _blocked(action, [READ_ONLY_NODE_REASON])
        return _blocked(action, [RENAME_FAILED_REASON])
    if runtime_referenced:
        after_name = _resolved_transform_short_name_after_rename(
            cmds, rename_target, str(proposed_name).strip(), before_name, str(renamed_node)
        )
        persisted = after_name == str(proposed_name).strip() and after_name != before_name
        if not persisted:
            return _blocked(action, [REFERENCE_RENAME_NOT_PERSISTED_REASON])
    else:
        after_name = _node_short_name(cmds, renamed_node) or str(proposed_name).strip()
    return _applied(action, None, before_name, after_name)


def _resolve_rename_target_node(cmds: Any, action: FixAction) -> str:
    """Resolve the DAG node that should be renamed for Outliner-visible naming."""
    target_node = str(action.target_node or "").strip()
    if not target_node:
        return target_node
    prefer_referenced = bool(action.referenced or action.requires_reference_edit)
    target_node = _resolve_existing_dag_path(cmds, target_node, prefer_referenced=prefer_referenced)
    if not target_node or not _node_exists(cmds, target_node):
        return str(action.target_node or "").strip()
    object_type = str(action.params.get("object_type") or "").strip()
    if object_type != "mesh":
        return target_node
    try:
        node_type = str(cmds.nodeType(target_node))
    except RuntimeError:
        return target_node
    if node_type == "transform":
        return target_node
    parents = cmds.listRelatives(target_node, parent=True, fullPath=True) or []
    if parents:
        return str(parents[0])
    return target_node


def _dag_path_candidates(node_hint: str) -> list[str]:
    normalized = str(node_hint or "").strip()
    if not normalized:
        return []
    candidates: list[str] = []
    for token in (normalized, normalized.lstrip("|"), f"|{normalized.lstrip('|')}"):
        short = token.split("|")[-1].split(":")[-1]
        for value in (token, short):
            if value and value not in candidates:
                candidates.append(value)
    return candidates


def _resolve_existing_dag_path(
    cmds: Any, node_hint: str, *, prefer_referenced: bool = False
) -> str:
    candidates = _dag_path_candidates(node_hint)
    if not candidates:
        return node_hint
    resolved: list[str] = []
    for candidate in candidates:
        if not cmds.objExists(candidate):
            continue
        long_names = cmds.ls(candidate, long=True) or []
        if long_names:
            resolved.extend(str(name) for name in long_names)
        else:
            resolved.append(candidate)
    if not resolved:
        return node_hint
    unique: list[str] = []
    for path in resolved:
        if path not in unique:
            unique.append(path)
    if len(unique) == 1:
        chosen = unique[0]
    elif prefer_referenced:
        chosen = unique[0]
        for name in unique:
            if _node_is_referenced(cmds, name):
                chosen = name
                break
    else:
        chosen = unique[0]
    if prefer_referenced:
        for path in unique:
            if _node_is_referenced(cmds, path):
                return path
        for candidate in candidates:
            if not cmds.objExists(candidate):
                continue
            long_names = cmds.ls(candidate, long=True) or []
            for path in long_names:
                token = str(path)
                if _node_is_referenced(cmds, token):
                    return token
    if cmds.objExists(chosen):
        long_names = cmds.ls(chosen, long=True) or []
        if long_names:
            return str(long_names[0])
        return chosen
    for candidate in _dag_path_candidates(node_hint):
        if cmds.objExists(candidate):
            long_names = cmds.ls(candidate, long=True) or []
            if long_names:
                return str(long_names[0])
            return candidate
    return chosen


def _node_exists(cmds: Any, node_hint: str) -> bool:
    return any(cmds.objExists(candidate) for candidate in _dag_path_candidates(node_hint))


def _node_is_referenced(cmds: Any, node_name: str) -> bool:
    try:
        return bool(cmds.referenceQuery(node_name, isNodeReferenced=True))
    except (RuntimeError, TypeError):
        return False


def _node_short_name(cmds: Any, node_name: str) -> Optional[str]:
    resolved = _resolve_existing_dag_path(cmds, node_name)
    if not resolved or not _node_exists(cmds, resolved):
        return None
    short_names = cmds.ls(resolved, shortNames=True) or cmds.ls(resolved) or []
    token = str(short_names[0]) if short_names else resolved
    short = token.split("|")[-1].split(":")[-1].strip()
    return short or None


def _is_read_only_node(cmds: Any, node_name: str) -> bool:
    return _query_lock_node(cmds, node_name)


def _query_lock_node(cmds: Any, node_name: str) -> bool:
    try:
        value = cmds.lockNode(node_name, q=True, lock=True)
    except RuntimeError:
        return False
    if isinstance(value, list):
        return bool(value[0]) if value else False
    return bool(value)


def _query_lock_node_name(cmds: Any, node_name: str) -> bool:
    try:
        value = cmds.lockNode(node_name, q=True, lockName=True)
    except RuntimeError:
        return False
    if isinstance(value, list):
        return bool(value[0]) if value else False
    return bool(value)


def _canonical_dag_node(cmds: Any, node_hint: str) -> str:
    normalized = str(node_hint or "").strip()
    if not normalized:
        return normalized
    try:
        long_names = cmds.ls(normalized, long=True) or []
        if long_names:
            return str(long_names[0])
        short_names = cmds.ls(normalized) or []
        if short_names:
            return str(short_names[0])
    except (RuntimeError, TypeError):
        pass
    return normalized


def _rename_unlock_targets(cmds: Any, node_hint: str) -> list[str]:
    """Return DAG nodes that may need unlock before rename (transform only)."""
    resolved = _canonical_dag_node(cmds, node_hint)
    if not resolved or not _node_exists(cmds, resolved):
        return []
    return [resolved]


def _node_has_rename_lock(cmds: Any, node_name: str) -> bool:
    return _query_lock_node(cmds, node_name) or _query_lock_node_name(cmds, node_name)


def _mel_unlock_node(mel_module: Any, node_name: str) -> None:
    """MEL unlock without -lp (invalid on reference nodes in Maya 2024)."""
    for script in (
        f'lockNode -l 0 -ln 0 "{node_name}";',
        f'lockNode -lock 0 -lockName 0 "{node_name}";',
    ):
        with contextlib.suppress(RuntimeError, TypeError):
            mel_module.eval(script)


def _reference_namespace(cmds: Any, ref_node: str) -> Optional[str]:
    try:
        return str(cmds.referenceQuery(ref_node, namespace=True))
    except (RuntimeError, TypeError):
        return None


def _is_root_reference_namespace(namespace: Optional[str]) -> bool:
    if namespace is None:
        return False
    token = str(namespace).strip()
    return token in ("", ":")


def _sanitize_reference_namespace(token: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in token)
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"ref_{cleaned}"
    return cleaned


def _reference_allows_namespace_edit(cmds: Any, ref_node: str) -> bool:
    try:
        return bool(cmds.referenceQuery(ref_node, isTopLevelReference=True))
    except (RuntimeError, TypeError):
        try:
            parent = cmds.referenceQuery(ref_node, parent=True)
        except (RuntimeError, TypeError):
            return False
        return parent in (None, "")


def _ensure_reference_namespace_for_edit(cmds: Any, ref_node: str) -> tuple[str, Optional[str]]:
    """Root-ns references block DAG rename; assign a named namespace when allowed."""
    current = _reference_namespace(cmds, ref_node)
    if not _is_root_reference_namespace(current):
        return ("skipped", current)
    if not _reference_allows_namespace_edit(cmds, ref_node):
        return ("skipped:not_top_level", current)
    base = ref_node[:-2] if ref_node.endswith("RN") else ref_node
    temp_ns = _sanitize_reference_namespace(base)
    try:
        cmds.file(edit=True, namespace=temp_ns, referenceNode=ref_node)
        return ("ok", temp_ns)
    except (RuntimeError, TypeError) as exc:
        return (f"failed:{exc}", current)


def _resolve_namespaced_dag_path(cmds: Any, ref_node: str, node_name: str) -> str:
    namespace = _reference_namespace(cmds, ref_node)
    if _is_root_reference_namespace(namespace):
        return node_name
    short = node_name.split("|")[-1].split(":")[-1]
    ns_token = str(namespace or "").strip().strip(":")
    if not ns_token:
        return node_name
    for candidate in (f"{ns_token}:{short}", f"|{ns_token}:{short}"):
        if not cmds.objExists(candidate):
            continue
        long_names = cmds.ls(candidate, long=True) or []
        if long_names:
            return str(long_names[0])
        return candidate
    return node_name


def _force_unlock_node(cmds: Any, target: str) -> dict[str, Any]:
    before = {
        "lock": _query_lock_node(cmds, target),
        "lockName": _query_lock_node_name(cmds, target),
    }
    if not before["lock"] and (not before["lockName"]):
        return {"before": before, "after": before, "skipped": True}
    for kwargs in (
        {"lock": False, "lockName": False},
        {"lock": False, "lockName": False, "ignoreComponents": True},
        {"lock": False, "lockName": False, "lockUnpublished": False},
    ):
        with contextlib.suppress(RuntimeError, TypeError):
            cmds.lockNode(target, **kwargs)
        after_lock = _query_lock_node(cmds, target)
        after_name = _query_lock_node_name(cmds, target)
        if not after_lock and (not after_name):
            return {
                "before": before,
                "after": {"lock": after_lock, "lockName": after_name},
                "skipped": False,
            }
    mel = getattr(cmds, "mel", None)
    if mel is not None:
        _mel_unlock_node(mel, target)
    else:
        try:
            import maya.mel as mel_module

            _mel_unlock_node(mel_module, target)
        except (ImportError, RuntimeError, TypeError):
            pass
    after = {
        "lock": _query_lock_node(cmds, target),
        "lockName": _query_lock_node_name(cmds, target),
    }
    return {"before": before, "after": after, "skipped": False}


def _unlock_rename_name_lock(cmds: Any, node_name: str) -> dict[str, Any]:
    """Unlock transform name locks only when Maya reports the node is locked."""
    results: dict[str, Any] = {}
    for target in _rename_unlock_targets(cmds, node_name):
        results[target] = _force_unlock_node(cmds, target)
    return results


def _rename_dag_node(
    cmds: Any,
    rename_target: str,
    proposed_name: str,
    *,
    allow_reference_edit: bool,
    allow_unlock: bool,
) -> tuple[Optional[str], Optional[str]]:
    canonical_target = _canonical_dag_node(cmds, rename_target) or rename_target
    if allow_unlock and _node_has_rename_lock(cmds, canonical_target):
        _unlock_rename_name_lock(cmds, canonical_target)
    if allow_reference_edit:
        ref_node = _reference_node_for_dag(cmds, canonical_target)
        if ref_node:
            ref_locked = _query_reference_locked(cmds, ref_node)
            ref_node_locked = _query_lock_node(cmds, ref_node)
            if ref_locked or ref_node_locked:
                with contextlib.suppress(RuntimeError, TypeError):
                    cmds.file(lockReference=False, referenceNode=ref_node)
                _force_unlock_reference_node(cmds, ref_node)
            _unlock_referenced_shape_nodes(cmds, canonical_target)
            _clear_failed_rename_reference_edits(cmds, ref_node)
    ref_namespace = None
    if allow_reference_edit:
        ref_node = _reference_node_for_dag(cmds, canonical_target)
        if ref_node:
            ref_namespace = _reference_namespace(cmds, ref_node)
    last_error: Optional[str] = None
    rename_targets = (
        _dag_rename_candidates(cmds, canonical_target)
        if allow_reference_edit
        else [canonical_target]
    )
    for attempt in range(2):
        renamed_node, rename_error = _attempt_rename(
            cmds,
            rename_targets,
            proposed_name,
            namespace=ref_namespace,
            allow_api_fallback=allow_reference_edit,
        )
        if renamed_node is not None:
            return (renamed_node, None)
        last_error = rename_error
        if (
            attempt == 0
            and rename_error
            and (
                _is_rename_lock_error(RuntimeError(rename_error))
                or _is_read_only_rename_error(RuntimeError(rename_error))
            )
        ):
            if allow_reference_edit:
                ref_node = _reference_node_for_dag(cmds, canonical_target)
                if ref_node:
                    _reload_reference_for_edit(cmds, ref_node)
                prep = _prepare_reference_edit(cmds, canonical_target)
                updated_target = prep.get("node_name")
                if isinstance(updated_target, str) and updated_target.strip():
                    canonical_target = updated_target
            if _is_rename_lock_error(RuntimeError(rename_error)) or _node_has_rename_lock(
                cmds, canonical_target
            ):
                _unlock_rename_name_lock(cmds, canonical_target)
            canonical_target = _canonical_dag_node(cmds, canonical_target) or canonical_target
            rename_targets = (
                _dag_rename_candidates(cmds, canonical_target)
                if allow_reference_edit
                else [canonical_target]
            )
            continue
        return (None, last_error)
    return (None, last_error)


def _reference_node_for_dag(cmds: Any, node_name: str) -> Optional[str]:
    try:
        ref_node = cmds.referenceQuery(node_name, referenceNode=True)
    except (RuntimeError, TypeError):
        return None
    return str(ref_node) if ref_node else None


def _query_reference_locked(cmds: Any, ref_node: str) -> Optional[bool]:
    try:
        return bool(cmds.file(referenceNode=ref_node, query=True, lockReference=True))
    except (RuntimeError, TypeError):
        return None


def _query_node_read_only(cmds: Any, node_name: str) -> Optional[bool]:
    try:
        return bool(cmds.referenceQuery(node_name, isReadOnly=True))
    except (RuntimeError, TypeError):
        return None


def _reference_is_deferred(cmds: Any, ref_node: str) -> Optional[bool]:
    try:
        return bool(cmds.file(referenceNode=ref_node, query=True, deferReference=True))
    except (RuntimeError, TypeError):
        return None


def _force_unlock_reference_node(cmds: Any, ref_node: str) -> dict[str, Any]:
    """Fully unlock a reference container node (safe; never touches DAG meshes)."""
    before = {
        "lock": _query_lock_node(cmds, ref_node),
        "lockName": _query_lock_node_name(cmds, ref_node),
    }
    for kwargs in (
        {"lock": False, "lockName": False},
        {"lock": False, "lockName": False, "lockUnpublished": False},
        {"lock": False, "lockName": False, "ignoreComponents": True},
    ):
        with contextlib.suppress(RuntimeError, TypeError):
            cmds.lockNode(ref_node, **kwargs)
    try:
        import maya.mel as mel_module

        _mel_unlock_node(mel_module, ref_node)
    except (ImportError, RuntimeError, TypeError):
        pass
    after = {
        "lock": _query_lock_node(cmds, ref_node),
        "lockName": _query_lock_node_name(cmds, ref_node),
    }
    return {"before": before, "after": after}


def _reload_reference_for_edit(cmds: Any, ref_node: str) -> str:
    try:
        cmds.file(unloadReference=True, referenceNode=ref_node)
        cmds.file(loadReference=True, loadReferenceDepth="all", referenceNode=ref_node)
        cmds.file(lockReference=False, referenceNode=ref_node)
        _force_unlock_reference_node(cmds, ref_node)
        return "ok"
    except (RuntimeError, TypeError) as exc:
        return f"failed:{exc}"


def _dag_rename_candidates(cmds: Any, node_hint: str) -> list[str]:
    candidates: list[str] = []
    canonical = _canonical_dag_node(cmds, node_hint) or node_hint
    short = canonical.split("|")[-1].split(":")[-1]
    for token in (
        canonical,
        canonical.lstrip("|"),
        f"|{canonical.lstrip('|')}",
        short,
        f":{short}",
    ):
        normalized = str(token or "").strip()
        if normalized and normalized not in candidates:
            candidates.append(normalized)
    if short:
        try:
            for path in cmds.ls(short, long=True) or []:
                token = str(path)
                if token not in candidates:
                    candidates.append(token)
        except (RuntimeError, TypeError):
            pass
    return candidates


def _proposed_rename_variants(proposed_name: str, namespace: Optional[str]) -> list[str]:
    short = str(proposed_name or "").strip().split("|")[-1].split(":")[-1]
    if not short:
        return []
    variants = [short]
    if _is_root_reference_namespace(namespace):
        colon_name = f":{short}"
        if colon_name not in variants:
            variants.append(colon_name)
    return variants


def _unlock_referenced_shape_nodes(cmds: Any, transform: str) -> dict[str, Any]:
    results: dict[str, Any] = {}
    try:
        shapes = cmds.listRelatives(transform, shapes=True, fullPath=True) or []
    except (RuntimeError, TypeError):
        return results
    for shape in shapes:
        shape_name = str(shape)
        if _node_has_rename_lock(cmds, shape_name):
            results[shape_name] = _force_unlock_node(cmds, shape_name)
    return results


def _clear_failed_rename_reference_edits(cmds: Any, ref_node: str) -> str:
    try:
        failed = cmds.referenceEdit(ref_node, query=True, failedEdits=True, editCommand="rename")
        if failed:
            cmds.referenceEdit(ref_node, removeEdits=True, failedEdits=True, editCommand="rename")
            return "cleared"
        return "none"
    except (RuntimeError, TypeError) as exc:
        return f"failed:{exc}"


def _rename_via_dag_modifier(
    target: str, proposed_name: str
) -> tuple[Optional[str], Optional[str]]:
    try:
        import maya.api.OpenMaya as om
    except ImportError:
        return (None, "openmaya_unavailable")
    short_new = str(proposed_name or "").strip().split("|")[-1].split(":")[-1]
    if not short_new:
        return (None, "invalid_proposed_name")
    try:
        selection = om.MSelectionList()
        selection.add(target)
        dag_path = selection.getDagPath(0)
        modifier = om.MDagModifier()
        modifier.renameNode(dag_path.node(), short_new)
        modifier.doIt()
        renamed_path = dag_path.fullPathName()
        return (str(renamed_path), None)
    except (RuntimeError, TypeError, ValueError) as exc:
        return (None, str(exc))


def _resolve_renamed_dag_path(cmds: Any, proposed_name: str) -> Optional[str]:
    short = str(proposed_name or "").strip().split("|")[-1].split(":")[-1]
    for candidate in _dag_path_candidates(short):
        if not candidate or not cmds.objExists(candidate):
            continue
        long_names = cmds.ls(candidate, long=True) or []
        if long_names:
            return str(long_names[0])
        return candidate
    return None


def _attempt_rename(
    cmds: Any,
    targets: list[str],
    proposed_name: str,
    *,
    namespace: Optional[str] = None,
    allow_api_fallback: bool = False,
) -> tuple[Optional[str], Optional[str]]:
    last_error: Optional[str] = None
    proposed_variants = _proposed_rename_variants(proposed_name, namespace)
    for target in targets:
        for variant in proposed_variants:
            try:
                renamed_node = cmds.rename(target, variant)
                return (str(renamed_node), None)
            except RuntimeError as exc:
                last_error = str(exc)
        if allow_api_fallback:
            for variant in proposed_variants:
                renamed_node, api_error = _rename_via_dag_modifier(target, variant)
                if renamed_node:
                    resolved = _resolve_renamed_dag_path(cmds, renamed_node) or renamed_node
                    return (resolved, None)
                last_error = api_error
    return (None, last_error)


def _ensure_reference_loaded_for_edit(cmds: Any, ref_node: str) -> str:
    try:
        cmds.file(loadReference=True, loadReferenceDepth="all", referenceNode=ref_node)
        return "ok"
    except (RuntimeError, TypeError) as exc:
        return f"failed:{exc}"


def _unlock_reference_file(cmds: Any, ref_node: str) -> str:
    try:
        cmds.file(lockReference=False, referenceNode=ref_node)
        return "ok"
    except (RuntimeError, TypeError) as exc:
        return f"failed:{exc}"


def _unlock_reference_node_after_load(cmds: Any, ref_node: str) -> tuple[str, dict[str, Any]]:
    """Unlock reference RN after loadReference; load can re-apply lockNode -l 1."""
    unlock_result = _force_unlock_reference_node(cmds, ref_node)
    status = (
        "ok"
        if not unlock_result.get("after", {}).get("lock")
        and (not unlock_result.get("after", {}).get("lockName"))
        else "partial"
    )
    return (status, unlock_result)


def _resolved_transform_short_name_after_rename(
    cmds: Any, rename_target: str, proposed_name: str, before_name: str, renamed_node: str
) -> str:
    if rename_target and cmds.objExists(rename_target):
        current = _node_short_name(cmds, rename_target)
        if current:
            return current
    for candidate in _dag_path_candidates(proposed_name):
        if cmds.objExists(candidate):
            current = _node_short_name(cmds, candidate)
            if current:
                return current
    for candidate in _dag_path_candidates(renamed_node):
        if cmds.objExists(candidate):
            current = _node_short_name(cmds, candidate)
            if current:
                return current
    return before_name


def _reference_is_loaded(cmds: Any, ref_node: str) -> bool:
    try:
        return bool(cmds.referenceQuery(ref_node, isLoaded=True))
    except (RuntimeError, TypeError):
        return True


def _prepare_reference_edit(cmds: Any, node_name: str) -> dict[str, Any]:
    """Prepare a referenced DAG node for rename per Maya file/lockNode API."""
    canonical = _canonical_dag_node(cmds, node_name) or node_name
    ref_node = _reference_node_for_dag(cmds, canonical)
    if not ref_node:
        return {"ref_node": None, "node_name": canonical}
    lock_before = _query_reference_locked(cmds, ref_node)
    ref_loaded_before = _reference_is_loaded(cmds, ref_node)
    ref_deferred_before = _reference_is_deferred(cmds, ref_node)
    target_read_only_before = _query_node_read_only(cmds, canonical)
    ref_node_lock_before = _query_lock_node(cmds, ref_node)
    steps: dict[str, str] = {}
    steps["unlock_reference"] = _unlock_reference_file(cmds, ref_node)
    steps["load_reference_depth"] = _ensure_reference_loaded_for_edit(cmds, ref_node)
    unlock_status, unlock_result = _unlock_reference_node_after_load(cmds, ref_node)
    steps["unlock_reference_node_force"] = unlock_status
    ns_status, assigned_ns = _ensure_reference_namespace_for_edit(cmds, ref_node)
    steps["assign_reference_namespace"] = ns_status
    canonical = _resolve_namespaced_dag_path(cmds, ref_node, canonical)
    shape_unlock_targets = _unlock_referenced_shape_nodes(cmds, canonical)
    steps["clear_failed_rename_edits"] = _clear_failed_rename_reference_edits(cmds, ref_node)
    unlock_targets = {}
    if _node_has_rename_lock(cmds, canonical):
        unlock_targets = _unlock_rename_name_lock(cmds, canonical)
    state = {
        "node_name": canonical,
        "ref_node": ref_node,
        "steps": steps,
        "ref_loaded_before": ref_loaded_before,
        "ref_deferred_before": ref_deferred_before,
        "ref_locked_before": lock_before,
        "ref_node_lock_before": ref_node_lock_before,
        "ref_node_lock_after": _query_lock_node(cmds, ref_node),
        "ref_locked_after": _query_reference_locked(cmds, ref_node),
        "target_read_only_before": target_read_only_before,
        "target_read_only_after": _query_node_read_only(cmds, canonical),
        "target_lock_after": _query_lock_node(cmds, canonical),
        "target_lock_name_after": _query_lock_node_name(cmds, canonical),
        "unlock_targets": unlock_targets,
        "shape_unlock_targets": shape_unlock_targets,
    }
    return state


def _is_rename_lock_error(exc: RuntimeError) -> bool:
    message = str(exc).casefold()
    return "locked name" in message or "locked node" in message


def _is_read_only_rename_error(exc: RuntimeError) -> bool:
    message = str(exc).casefold()
    return "read only" in message or "read-only" in message


def _apply_disable_feature(action: FixAction, cmds: Any) -> AppliedFixRecord:
    if action.after_value is None:
        return _blocked(action, [MISSING_ATTR_REASON])
    return _apply_set_attr(action, cmds)


def _apply_set_attr(action: FixAction, cmds: Any) -> AppliedFixRecord:
    if not action.target_attr:
        return _blocked(action, [MISSING_ATTR_REASON])
    plug = f"{action.target_node}.{action.target_attr}"
    if not _plug_exists(cmds, plug):
        return _blocked(action, [MISSING_ATTR_REASON])
    before_value = cmds.getAttr(plug)
    _set_attr(cmds, plug, action.after_value)
    after_value = cmds.getAttr(plug)
    return _applied(action, action.target_attr, before_value, after_value)


def _apply_relink_path(action: FixAction, cmds: Any) -> AppliedFixRecord:
    target_attr = _path_target_attr(action)
    if not target_attr:
        return _blocked(action, [MISSING_ATTR_REASON])
    if not _is_path_string_value(action.after_value):
        return _blocked(action, [INVALID_RELINK_PATH_REASON])
    return _apply_path_value(
        action,
        cmds,
        target_attr,
        _author_maya_path_for_action(
            action,
            str(action.after_value).strip(),
            str(action.params.get("resolved_before") or action.before_value or ""),
        ),
    )


def _apply_normalize_path(action: FixAction, cmds: Any) -> AppliedFixRecord:
    target_attr = _path_target_attr(action)
    if not target_attr:
        return _blocked(action, [MISSING_ATTR_REASON])
    plug = f"{action.target_node}.{target_attr}"
    if not _plug_exists(cmds, plug):
        return _blocked(action, [MISSING_ATTR_REASON])
    before_value = cmds.getAttr(plug)
    if not isinstance(before_value, str):
        return _blocked(action, [INVALID_NORMALIZE_PATH_REASON])
    before_normalized = str(before_value).replace("\\", "/")
    planned_after = str(action.after_value or "").strip().replace("\\", "/")
    if planned_after and planned_after != before_normalized:
        normalized_path = planned_after
    else:
        resolve_source = before_normalized
        if action.params.get("is_udim"):
            from pipeline_inspector.util.paths import normalize_udim_tile_token_in_path

            resolve_source = normalize_udim_tile_token_in_path(resolve_source)
        resolved = resolve_normalize_path_value(
            resolve_source,
            action.params,
            scene_path=str(action.params.get("scene_path") or ""),
            studio_environment=_studio_environment_from_params(action.params),
        )
        if not resolved:
            return _blocked(action, [INVALID_NORMALIZE_PATH_REASON])
        normalized_path = resolved
    if not _is_path_string_value(normalized_path):
        return _blocked(action, [INVALID_NORMALIZE_PATH_REASON])
    studio_environment = _studio_environment_from_params(action.params)
    if studio_environment is not None:
        sync_studio_environment_to_os(studio_environment)
    authored_path = _author_maya_path_for_action(
        action,
        str(normalized_path).strip(),
        str(action.params.get("resolved_before") or before_value),
    )
    authored_path = authored_path.replace("\\", "/")
    before_normalized = str(before_value).replace("\\", "/")
    authored_normalized = authored_path.replace("\\", "/")
    planned_normalized = str(normalized_path).strip().replace("\\", "/")
    if planned_normalized == before_normalized and authored_normalized == before_normalized:
        return _applied(action, target_attr, before_value, before_value)
    return _apply_path_value(action, cmds, target_attr, authored_path, before_value)


def _author_maya_path_for_action(
    action: FixAction, planned_path: str, fallback_absolute: str
) -> str:
    return author_maya_texture_path_for_fix(
        planned_path,
        scene_path=str(action.params.get("scene_path") or ""),
        studio_environment=_studio_environment_from_params(action.params),
        fallback_absolute=fallback_absolute,
    ).replace("\\", "/")


def _apply_path_value(
    action: FixAction, cmds: Any, target_attr: str, path_value: str, before_value: Any = None
) -> AppliedFixRecord:
    plug = f"{action.target_node}.{target_attr}"
    if not _plug_exists(cmds, plug):
        return _blocked(action, [MISSING_ATTR_REASON])
    current_value = before_value if before_value is not None else cmds.getAttr(plug)
    _set_attr(cmds, plug, str(path_value).replace("\\", "/"))
    after_value = cmds.getAttr(plug)
    return _applied(action, target_attr, current_value, after_value)


def _path_target_attr(action: FixAction) -> Optional[str]:
    if action.target_attr and action.target_attr not in METADATA_PLUG_NAMES:
        return action.target_attr
    param_attr = action.params.get("attribute")
    if param_attr:
        return str(param_attr)
    return DEFAULT_TEXTURE_PATH_ATTR


def _is_path_string_value(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _plug_exists(cmds: Any, plug: str) -> bool:
    try:
        cmds.getAttr(plug)
    except (KeyError, RuntimeError, TypeError, ValueError):
        return False
    return True


def _applied(
    action: FixAction, target_attr: Optional[str], before_value: Any, after_value: Any
) -> AppliedFixRecord:
    return AppliedFixRecord(
        action.fix_id,
        action.rule_id,
        action.fix_type,
        action.target_node,
        target_attr,
        before_value,
        after_value,
        True,
        False,
        "Fix applied.",
        [],
    )


def _reasons(
    action: FixAction, allow_referenced: bool, allow_locked: bool, allow_high_risk: bool
) -> list[str]:
    reasons: list[str] = []
    skip_locked = _allows_reference_naming_edit(action)
    for reason in action.block_reasons:
        if reason == REFERENCED_BLOCK_REASON and allow_referenced:
            continue
        if reason == LOCKED_BLOCK_REASON and (allow_locked or skip_locked):
            continue
        if reason == HIGH_RISK_BLOCK_REASON and allow_high_risk:
            continue
        _append_unique(reasons, reason)
    if action.referenced and (not allow_referenced):
        _append_unique(reasons, REFERENCED_BLOCK_REASON)
    if action.locked and (not allow_locked) and (not skip_locked):
        _append_unique(reasons, LOCKED_BLOCK_REASON)
    return reasons


def _allows_reference_naming_edit(action: FixAction) -> bool:
    return action.fix_type == NAMING_FIX_TYPE and (
        action.referenced or action.requires_reference_edit
    )


def _studio_environment_from_params(
    params: Mapping[str, Any],
) -> Optional[StudioEnvironmentSettings]:
    raw = params.get("studio_environment")
    if isinstance(raw, Mapping):
        return StudioEnvironmentSettings.from_mapping(raw)
    return None


def _append_unique(items: list[str], item: str) -> None:
    if item not in items:
        items.append(item)


def _blocked(action: FixAction, reasons: list[str]) -> AppliedFixRecord:
    return AppliedFixRecord(
        action.fix_id,
        action.rule_id,
        action.fix_type,
        action.target_node,
        action.target_attr,
        action.before_value,
        action.after_value,
        False,
        True,
        "Fix blocked.",
        reasons,
    )


def _set_attr(cmds: Any, plug: str, value: Any) -> None:
    if isinstance(value, str):
        cmds.setAttr(plug, value, type="string")
        return
    cmds.setAttr(plug, value)


def _maya_cmds() -> Any:
    try:
        return importlib.import_module("maya.cmds")
    except ImportError as exc:
        raise RuntimeError("Maya fix applier can only run inside Autodesk Maya.") from exc
