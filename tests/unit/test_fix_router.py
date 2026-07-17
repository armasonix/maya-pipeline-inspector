from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pathlib import Path

from pipeline_inspector.core.fix_plan import FixAction
from pipeline_inspector.maya.fix_router import _is_usd_stage_action, apply_fix_actions


def test_is_usd_stage_action_detects_scene_default_prim_fix() -> None:
    action = FixAction(
        fix_id="usd.stage.default_prim.required:scene:set_default_prim",
        rule_id="usd.stage.default_prim.required",
        title="default prim",
        fix_type="set_default_prim",
        risk="low",
        target_kind="scene",
        target_id="D:/shots/hero.ma",
        target_node="D:/shots/hero.ma",
        before_value=False,
        after_value="/Base",
    )
    assert _is_usd_stage_action(action, has_usd_proxy=True) is True
    assert _is_usd_stage_action(action, has_usd_proxy=False) is False


def test_apply_fix_actions_routes_scene_usd_fix_to_usd_applier() -> None:
    action = FixAction(
        fix_id="usd.stage.default_prim.required:scene:set_default_prim",
        rule_id="usd.stage.default_prim.required",
        title="default prim",
        fix_type="set_default_prim",
        risk="low",
        target_kind="scene",
        target_id="D:/shots/hero.ma",
        target_node="D:/shots/hero.ma",
        before_value=False,
        after_value="/Base",
    )
    cmds = MagicMock()

    with patch(
        "pipeline_inspector.maya.usd_scene_scan._collect_usd_proxy_paths",
        return_value=[Path("D:/assets/hero.usda")],
    ), patch(
        "pipeline_inspector.usd.fix_applier.apply_usd_fix_actions",
        return_value=[
            SimpleNamespace(
                fix_id=action.fix_id,
                succeeded=True,
                message="",
            )
        ],
    ) as apply_usd:
        report = apply_fix_actions([action], cmds=cmds)

    apply_usd.assert_called_once()
    assert report.applied_count == 1
