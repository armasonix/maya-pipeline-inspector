"""Route fix application between Maya scene edits and USD stage edits."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any, Optional

from pipeline_inspector.core.fix_plan import FixAction

USD_STAGE_FIX_TYPES = frozenset(
    {
        "set_default_prim",
        "set_attr",
        "normalize_path",
        "relink_path",
    }
)
USD_PRIM_FIX_TYPES = frozenset(
    {
        "set_attr",
        "normalize_path",
        "relink_path",
        "rename_node",
        "rename_texture_file",
    }
)


def apply_fix_actions(
    actions: Sequence[FixAction],
    *,
    cmds: Optional[Any] = None,
    allow_referenced: bool = False,
    allow_locked: bool = False,
    allow_high_risk: bool = False,
    studio_environment: Optional[Any] = None,
) -> Any:
    """Apply fixes to Maya nodes and USD proxy stages in the current scene."""

    from pipeline_inspector.maya import fix_applier as maya_fix_applier
    from pipeline_inspector.maya.usd_scene_scan import _collect_usd_proxy_paths
    from pipeline_inspector.usd.fix_applier import apply_usd_fix_actions

    if cmds is None:
        from pipeline_inspector.maya.commands import _maya_cmds

        cmds = _maya_cmds()

    usd_actions, maya_actions = _partition_fix_actions(actions, cmds)

    maya_report = None
    if maya_actions:
        maya_report = maya_fix_applier.apply_fix_actions(
            maya_actions,
            cmds=cmds,
            allow_referenced=allow_referenced,
            allow_locked=allow_locked,
            allow_high_risk=allow_high_risk,
        )

    usd_records = []
    if usd_actions:
        resolved_usd_actions = _resolve_usd_prim_fix_actions(usd_actions, cmds)
        for path in _collect_usd_proxy_paths(cmds):
            proxy_stage = _proxy_stage_for_path(cmds, path)
            usd_records.extend(
                apply_usd_fix_actions(
                    path,
                    list(resolved_usd_actions),
                    stage=proxy_stage,
                    studio_environment=studio_environment,
                )
            )

    if maya_report is not None and not usd_records:
        return maya_report
    if maya_report is None and usd_records:
        return _usd_only_report(usd_records)
    return _merge_reports(maya_report, usd_records)


def _partition_fix_actions(
    actions: Sequence[FixAction],
    cmds: Any,
) -> tuple[list[FixAction], list[FixAction]]:
    """Split planned fixes between Maya DAG edits and on-disk USD stage edits."""

    from pipeline_inspector.maya.usd_scene_scan import _collect_usd_proxy_paths

    has_usd_proxy = bool(_collect_usd_proxy_paths(cmds))
    usd_actions: list[FixAction] = []
    maya_actions: list[FixAction] = []
    for action in actions:
        if _is_usd_stage_action(action, has_usd_proxy=has_usd_proxy):
            usd_actions.append(action)
        else:
            maya_actions.append(action)
    return usd_actions, maya_actions


def _is_usd_stage_action(action: FixAction, *, has_usd_proxy: bool) -> bool:
    if action.fix_type == "set_default_prim" and action.target_kind in {"scene", "graph"}:
        return has_usd_proxy
    if str(action.target_id).startswith("prim:"):
        return has_usd_proxy and action.fix_type in USD_PRIM_FIX_TYPES
    if not has_usd_proxy:
        return False
    if action.fix_type not in USD_STAGE_FIX_TYPES:
        return False
    return action.target_kind in {"scene", "graph"}


def _resolve_usd_prim_fix_actions(
    actions: Sequence[FixAction],
    cmds: Any,
) -> list[FixAction]:
    """Resolve short Maya-style prim identifiers to full USD prim paths."""

    from pipeline_inspector.maya.usd_navigation import find_usd_prim_for_issue

    resolved: list[FixAction] = []
    for action in actions:
        if not str(action.target_id).startswith("prim:"):
            resolved.append(action)
            continue
        prim_path = str(action.params.get("resolved_prim_path") or "").strip()
        if not prim_path:
            prim_path = find_usd_prim_for_issue(
                target_id=action.target_id,
                node_name=str(action.target_node or ""),
                material_name=str(action.params.get("material_name") or ""),
                cmds=cmds,
            )
        if not prim_path:
            resolved.append(action)
            continue
        normalized = prim_path if prim_path.startswith("/") else f"/{prim_path.lstrip('/')}"
        resolved.append(
            replace(
                action,
                target_id=f"prim:{normalized}",
                target_node=normalized,
                params={
                    **action.params,
                    "resolved_prim_path": normalized,
                },
            )
        )
    return resolved


def _proxy_stage_for_path(cmds: Any, usd_path: Path) -> Any:
    from pipeline_inspector.maya.usd_navigation import _get_proxy_stage

    target = str(Path(usd_path).resolve())
    shapes = cmds.ls(type="mayaUsdProxyShape", long=True) or []
    for shape in shapes:
        for attr in ("filePath", "fp"):
            try:
                raw_path = str(cmds.getAttr(f"{shape}.{attr}") or "").strip()
            except Exception:  # noqa: BLE001
                continue
            if not raw_path:
                continue
            if str(Path(raw_path).resolve()) != target:
                continue
            return _get_proxy_stage(shape, cmds)
    return None


def _usd_only_report(records: list[Any]) -> Any:
    from pipeline_inspector.maya.fix_applier import ApplyFixReport, DEFAULT_UNDO_CHUNK_NAME

    return ApplyFixReport(
        records=tuple(_coerce_apply_records(records)),
        undo_chunk_name=DEFAULT_UNDO_CHUNK_NAME,
    )


def _merge_reports(maya_report: Any, usd_records: list[Any]) -> Any:
    from pipeline_inspector.maya.fix_applier import ApplyFixReport, DEFAULT_UNDO_CHUNK_NAME

    undo_chunk_name = str(
        getattr(maya_report, "undo_chunk_name", DEFAULT_UNDO_CHUNK_NAME)
        or DEFAULT_UNDO_CHUNK_NAME
    )
    records = list(getattr(maya_report, "records", []) or ())
    records.extend(_coerce_apply_records(usd_records))
    return ApplyFixReport(records=tuple(records), undo_chunk_name=undo_chunk_name)


def _coerce_apply_records(records: list[Any]) -> list[Any]:
    from pipeline_inspector.maya.fix_applier import AppliedFixRecord
    from pipeline_inspector.usd.fix_applier import AppliedUsdFixRecord

    coerced: list[Any] = []
    for record in records:
        if isinstance(record, AppliedFixRecord):
            coerced.append(record)
            continue
        if isinstance(record, AppliedUsdFixRecord):
            coerced.append(_usd_record_as_applied(record))
            continue
        to_dict = getattr(record, "to_dict", None)
        if callable(to_dict):
            payload = dict(to_dict())
            coerced.append(
                AppliedFixRecord(
                    fix_id=str(payload.get("fix_id", "")),
                    rule_id=str(payload.get("rule_id", "")),
                    fix_type=str(payload.get("fix_type", "")),
                    target_node=str(payload.get("target_node", "")),
                    target_attr=payload.get("target_attr"),
                    before_value=payload.get("before_value"),
                    after_value=payload.get("after_value"),
                    applied=bool(payload.get("applied", False)),
                    blocked=bool(payload.get("blocked", False)),
                    message=str(payload.get("message", "")),
                    block_reasons=list(payload.get("block_reasons") or ()),
                )
            )
            continue
        coerced.append(record)
    return coerced


def _usd_record_as_applied(record: Any) -> Any:
    from pipeline_inspector.maya.fix_applier import AppliedFixRecord
    from pipeline_inspector.usd.fix_applier import AppliedUsdFixRecord

    if isinstance(record, AppliedFixRecord):
        return record
    if not isinstance(record, AppliedUsdFixRecord):
        payload = dict(record.to_dict()) if callable(getattr(record, "to_dict", None)) else {}
        return AppliedFixRecord(
            fix_id=str(payload.get("fix_id", "")),
            rule_id=str(payload.get("rule_id", "")),
            fix_type=str(payload.get("fix_type", "")),
            target_node=str(payload.get("target_node", "")),
            target_attr=payload.get("target_attr"),
            before_value=payload.get("before_value"),
            after_value=payload.get("after_value"),
            applied=bool(payload.get("applied", False)),
            blocked=bool(payload.get("blocked", False)),
            message=str(payload.get("message", "")),
            block_reasons=list(payload.get("block_reasons") or ()),
        )

    payload = record.to_dict()
    return AppliedFixRecord(
        fix_id=str(payload["fix_id"]),
        rule_id=str(payload.get("rule_id", "")),
        fix_type=str(payload["fix_type"]),
        target_node=str(payload["target_node"]),
        target_attr=payload.get("target_attr"),
        before_value=payload.get("before_value"),
        after_value=payload.get("after_value"),
        applied=bool(payload.get("applied", False)),
        blocked=bool(payload.get("blocked", False)),
        message=str(payload.get("message", "")),
        block_reasons=list(payload.get("block_reasons") or ()),
    )
