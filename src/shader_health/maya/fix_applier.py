"""Maya-side execution for planned safe actions."""
from __future__ import annotations

import importlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from shader_health.core.fix_plan import FixAction

SUPPORTED_FIX_TYPES = frozenset({"set_attr"})
DEFAULT_UNDO_CHUNK_NAME = "Shader Health Apply Fixes"
REFERENCED_BLOCK_REASON = "target_referenced"
LOCKED_BLOCK_REASON = "target_locked"
UNSUPPORTED_FIX_REASON = "unsupported_fix_type"
MISSING_TARGET_REASON = "target_node_missing"
MISSING_ATTR_REASON = "target_attr_missing"


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
    if not action.target_attr:
        return _blocked(action, [MISSING_ATTR_REASON])

    plug = f"{action.target_node}.{action.target_attr}"
    before_value = cmds.getAttr(plug)
    _set_attr(cmds, plug, action.after_value)
    after_value = cmds.getAttr(plug)
    return AppliedFixRecord(
        action.fix_id,
        action.rule_id,
        action.fix_type,
        action.target_node,
        action.target_attr,
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
