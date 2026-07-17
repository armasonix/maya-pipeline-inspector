"""Route fix application between Maya scene edits and USD stage edits."""
from __future__ import annotations

from collections.abc import Sequence
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
        for path in _collect_usd_proxy_paths(cmds):
            usd_records.extend(
                apply_usd_fix_actions(
                    path,
                    list(usd_actions),
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
    if str(action.target_id).startswith("prim:"):
        return True
    if not has_usd_proxy:
        return False
    if action.fix_type not in USD_STAGE_FIX_TYPES:
        return False
    return action.target_kind in {"scene", "graph"}


def _usd_only_report(records: list[Any]) -> Any:
    from types import SimpleNamespace

    applied_count = sum(1 for record in records if record.succeeded)
    failed_count = sum(
        1 for record in records if not record.succeeded and record.message != "blocked"
    )
    blocked_count = sum(1 for record in records if record.message == "blocked")
    return SimpleNamespace(
        applied_count=applied_count,
        failed_count=failed_count,
        blocked_count=blocked_count,
        records=records,
    )


def _merge_reports(maya_report: Any, usd_records: list[Any]) -> Any:
    from types import SimpleNamespace

    applied_count = int(getattr(maya_report, "applied_count", 0))
    failed_count = int(getattr(maya_report, "failed_count", 0))
    blocked_count = int(getattr(maya_report, "blocked_count", 0))
    records = list(getattr(maya_report, "records", []) or [])
    applied_count += sum(1 for record in usd_records if record.succeeded)
    failed_count += sum(
        1 for record in usd_records if not record.succeeded and record.message != "blocked"
    )
    blocked_count += sum(1 for record in usd_records if record.message == "blocked")
    records.extend(usd_records)
    return SimpleNamespace(
        applied_count=applied_count,
        failed_count=failed_count,
        blocked_count=blocked_count,
        records=records,
    )
