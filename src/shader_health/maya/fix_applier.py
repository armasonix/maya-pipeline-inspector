"""Maya-side execution for planned safe actions."""
from __future__ import annotations

import importlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from shader_health.core.fix_plan import FixAction

from shader_health.core.fix_plan import resolve_normalize_path_value

SUPPORTED_FIX_TYPES = frozenset({"set_attr", "relink_path", "normalize_path"})
DEFAULT_UNDO_CHUNK_NAME = "Shader Health Apply Fixes"
DEFAULT_TEXTURE_PATH_ATTR = "fileTextureName"
REFERENCED_BLOCK_REASON = "target_referenced"
LOCKED_BLOCK_REASON = "target_locked"
UNSUPPORTED_FIX_REASON = "unsupported_fix_type"
MISSING_TARGET_REASON = "target_node_missing"
MISSING_ATTR_REASON = "target_attr_missing"
INVALID_RELINK_PATH_REASON = "invalid_relink_path"
INVALID_NORMALIZE_PATH_REASON = "invalid_normalize_path"
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
        return {
            "total": self.total,
            "applied_count": self.applied_count,
            "blocked_count": self.blocked_count,
            "failed_count": self.failed_count,
            "records": [record.to_dict() for record in self.records],
        }


def apply_fix_actions(
    actions: Iterable[FixAction],
    *,
    cmds: Optional[Any] = None,
    allow_referenced: bool = False,
    allow_locked: bool = False,
    undo_chunk_name: str = DEFAULT_UNDO_CHUNK_NAME,
) -> ApplyFixReport:
    maya_cmds = cmds or _maya_cmds()
    queued = tuple(actions)
    if not queued:
        return ApplyFixReport(records=())

    records: list[AppliedFixRecord] = []
    maya_cmds.undoInfo(openChunk=True, chunkName=undo_chunk_name)
    try:
        for action in queued:
            records.append(_apply_one(action, maya_cmds, allow_referenced, allow_locked))
    finally:
        maya_cmds.undoInfo(closeChunk=True)
    return ApplyFixReport(records=tuple(records))


def _apply_one(
    action: FixAction,
    cmds: Any,
    allow_referenced: bool,
    allow_locked: bool,
) -> AppliedFixRecord:
    reasons = _reasons(action, allow_referenced, allow_locked)
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
    return _blocked(action, [UNSUPPORTED_FIX_REASON])


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
        planned_after=action.after_value,
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


def _reasons(action: FixAction, allow_referenced: bool, allow_locked: bool) -> list[str]:
    reasons: list[str] = []
    for reason in action.block_reasons:
        if reason == REFERENCED_BLOCK_REASON and allow_referenced:
            continue
        if reason == LOCKED_BLOCK_REASON and allow_locked:
            continue
        _append_unique(reasons, reason)
    if action.referenced and not allow_referenced:
        _append_unique(reasons, REFERENCED_BLOCK_REASON)
    if action.locked and not allow_locked:
        _append_unique(reasons, LOCKED_BLOCK_REASON)
    return reasons


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
