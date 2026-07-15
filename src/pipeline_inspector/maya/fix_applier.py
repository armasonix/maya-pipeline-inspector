"""Maya-side execution for planned safe actions."""
from __future__ import annotations

import glob
import importlib
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from pipeline_inspector.core.fix_plan import FixAction

from pipeline_inspector.core.fix_plan import HIGH_RISK_BLOCK_REASON, resolve_normalize_path_value
from pipeline_inspector.core.naming_fix import texture_tile_filename_from_paths
from pipeline_inspector.studio_config import StudioEnvironmentSettings

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
        return sum(1 for record in self.records if not record.applied and not record.blocked)

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
                _apply_one(
                    action,
                    maya_cmds,
                    allow_referenced,
                    allow_locked,
                    allow_high_risk,
                )
            )
    finally:
        maya_cmds.undoInfo(closeChunk=True)
    return ApplyFixReport(records=tuple(records), undo_chunk_name=undo_chunk_name)

def _apply_one(
    action: FixAction,
    cmds: Any,
    allow_referenced: bool,
    allow_locked: bool,
    allow_high_risk: bool,
) -> AppliedFixRecord:
    reasons = _reasons(action, allow_referenced, allow_locked, allow_high_risk)
    if reasons:
        return _blocked(action, reasons)
    if action.fix_type not in SUPPORTED_FIX_TYPES:
        return _blocked(action, [UNSUPPORTED_FIX_REASON])
    if not cmds.objExists(action.target_node):
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
        return _apply_rename_node(action, cmds)
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
        resolved_before,
        str(raw_before),
        str(raw_after),
        is_udim=is_udim,
    )
    if rename_error:
        return _blocked(action, [rename_error])

    path_record = _apply_path_value(
        action,
        cmds,
        target_attr,
        str(raw_after).strip(),
        str(raw_before),
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
    resolved_before: str,
    raw_before: str,
    raw_after: str,
    *,
    is_udim: bool,
) -> Optional[str]:
    if is_udim or "<UDIM>" in resolved_before or "<udim>" in resolved_before:
        return _rename_udim_texture_files(resolved_before, raw_before, raw_after)

    source = Path(os.path.expandvars(os.path.expanduser(resolved_before.replace("/", os.sep))))
    if not source.is_file():
        return TEXTURE_FILE_MISSING_REASON

    destination = _resolved_destination_path(source, raw_before, raw_after)
    if destination is None:
        return INVALID_TEXTURE_FILE_RENAME_REASON
    if destination.exists():
        return INVALID_TEXTURE_FILE_RENAME_REASON

    destination.parent.mkdir(parents=True, exist_ok=True)
    os.rename(source, destination)
    return None


def _rename_udim_texture_files(
    resolved_before: str,
    raw_before: str,
    raw_after: str,
) -> Optional[str]:
    glob_pattern = (
        resolved_before.replace("<UDIM>", "[0-9][0-9][0-9][0-9]")
        .replace("<udim>", "[0-9][0-9][0-9][0-9]")
    )
    matched_files = sorted(glob.glob(glob_pattern))
    if not matched_files:
        return TEXTURE_FILE_MISSING_REASON

    for old_file in matched_files:
        old_path = Path(old_file)
        new_name = texture_tile_filename_from_paths(
            old_path.name,
            raw_before=raw_before,
            raw_after=raw_after,
        )
        if not new_name:
            return INVALID_TEXTURE_FILE_RENAME_REASON
        new_path = old_path.with_name(new_name)
        if new_path.exists():
            return INVALID_TEXTURE_FILE_RENAME_REASON
        os.rename(old_path, new_path)
    return None


def _resolved_destination_path(
    source: Path,
    raw_before: str,
    raw_after: str,
) -> Optional[Path]:
    before_name = Path(str(raw_before).replace("\\", "/")).name
    after_name = Path(str(raw_after).replace("\\", "/")).name
    if not before_name or not after_name:
        return None
    if source.name != before_name:
        return source.with_name(after_name)
    return source.with_name(after_name)


def _apply_rename_node(action: FixAction, cmds: Any) -> AppliedFixRecord:
    proposed_name = action.after_value
    if not isinstance(proposed_name, str) or not proposed_name.strip():
        return _blocked(action, [INVALID_RENAME_NAME_REASON])

    rename_target = _resolve_rename_target_node(cmds, action)
    before_name = _node_short_name(cmds, rename_target)
    if before_name is None:
        return _blocked(action, [MISSING_TARGET_REASON])

    if _is_read_only_node(cmds, rename_target):
        # #region agent log
        _agent_debug_log(
            "fix_applier.py:_apply_rename_node",
            "rename_blocked_read_only",
            {
                "target_node": action.target_node,
                "rename_target": rename_target,
                "proposed_name": proposed_name,
                "before_name": before_name,
            },
            hypothesis_id="D",
        )
        # #endregion
        return _blocked(action, [READ_ONLY_NODE_REASON])

    try:
        renamed_node = cmds.rename(rename_target, proposed_name.strip())
    except RuntimeError as exc:
        if _is_read_only_rename_error(exc):
            return _blocked(action, [READ_ONLY_NODE_REASON])
        raise
    after_name = _node_short_name(cmds, renamed_node) or str(proposed_name).strip()
    # #region agent log
    _agent_debug_log(
        "fix_applier.py:_apply_rename_node",
        "rename_applied",
        {
            "target_node": action.target_node,
            "rename_target": rename_target,
            "proposed_name": proposed_name,
            "before_name": before_name,
            "after_name": after_name,
            "renamed_node": renamed_node,
        },
        hypothesis_id="E",
    )
    # #endregion
    return _applied(action, None, before_name, after_name)


def _resolve_rename_target_node(cmds: Any, action: FixAction) -> str:
    """Resolve the DAG node that should be renamed for Outliner-visible naming."""

    target_node = str(action.target_node or "").strip()
    if not target_node or not cmds.objExists(target_node):
        return target_node

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


def _agent_debug_log(
    location: str,
    message: str,
    data: dict[str, Any],
    *,
    hypothesis_id: str,
) -> None:
    try:
        import json
        import time
        from pathlib import Path

        payload = {
            "sessionId": "618f4f",
            "timestamp": int(time.time() * 1000),
            "location": location,
            "message": message,
            "data": data,
            "hypothesisId": hypothesis_id,
        }
        log_path = Path(__file__).resolve().parents[2] / "debug-618f4f.log"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
    except OSError:
        return


def _node_short_name(cmds: Any, node_name: str) -> Optional[str]:
    if not cmds.objExists(node_name):
        return None
    short_names = cmds.ls(node_name, shortNames=True) or []
    if not short_names:
        return None
    return str(short_names[0]).split("|")[-1].split(":")[-1]


def _is_read_only_node(cmds: Any, node_name: str) -> bool:
    locked = _query_lock_node(cmds, node_name)
    referenced = False
    read_only_reference = False
    try:
        referenced = bool(cmds.referenceQuery(node_name, isNodeReferenced=True))
        if referenced:
            read_only_reference = bool(cmds.referenceQuery(node_name, isReadOnly=True))
    except RuntimeError:
        pass
    # #region agent log
    _agent_debug_log(
        "fix_applier.py:_is_read_only_node",
        "read_only_probe",
        {
            "node_name": node_name,
            "locked": locked,
            "referenced": referenced,
            "read_only_reference": read_only_reference,
        },
        hypothesis_id="D",
    )
    # #endregion
    if locked:
        return True
    return referenced and read_only_reference


def _query_lock_node(cmds: Any, node_name: str) -> bool:
    try:
        value = cmds.lockNode(node_name, q=True, lock=True)
    except RuntimeError:
        return False
    if isinstance(value, list):
        return bool(value[0]) if value else False
    return bool(value)


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

    return _apply_path_value(action, cmds, target_attr, str(action.after_value).strip())

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

    normalized_path = resolve_normalize_path_value(
        before_value,
        action.params,
        scene_path=str(action.params.get("scene_path") or ""),
        studio_environment=_studio_environment_from_params(action.params),
    )
    if not _is_path_string_value(normalized_path) or normalized_path == before_value:
        return _blocked(action, [INVALID_NORMALIZE_PATH_REASON])

    return _apply_path_value(action, cmds, target_attr, str(normalized_path).strip(), before_value)

def _apply_path_value(
    action: FixAction,
    cmds: Any,
    target_attr: str,
    path_value: str,
    before_value: Any = None,
) -> AppliedFixRecord:
    plug = f"{action.target_node}.{target_attr}"
    if not _plug_exists(cmds, plug):
        return _blocked(action, [MISSING_ATTR_REASON])

    current_value = before_value if before_value is not None else cmds.getAttr(plug)
    _set_attr(cmds, plug, path_value)
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
    action: FixAction,
    target_attr: Optional[str],
    before_value: Any,
    after_value: Any,
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
    action: FixAction,
    allow_referenced: bool,
    allow_locked: bool,
    allow_high_risk: bool,
) -> list[str]:
    reasons: list[str] = []
    for reason in action.block_reasons:
        if reason == REFERENCED_BLOCK_REASON and allow_referenced:
            continue
        if reason == LOCKED_BLOCK_REASON and allow_locked:
            continue
        if reason == HIGH_RISK_BLOCK_REASON and allow_high_risk:
            continue
        _append_unique(reasons, reason)
    if action.referenced and not allow_referenced:
        _append_unique(reasons, REFERENCED_BLOCK_REASON)
    if action.locked and not allow_locked:
        _append_unique(reasons, LOCKED_BLOCK_REASON)
    return reasons

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
