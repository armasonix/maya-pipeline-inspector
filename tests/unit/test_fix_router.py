from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pathlib import Path

from pipeline_inspector.core.fix_plan import FixAction
from pipeline_inspector.maya.fix_applier import ApplyFixReport
from pipeline_inspector.maya.fix_router import _is_usd_stage_action, apply_fix_actions
from pipeline_inspector.usd.fix_applier import AppliedUsdFixRecord


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


def test_is_usd_stage_action_detects_prim_rename_fix() -> None:
    action = FixAction(
        fix_id="studio.naming.texture.pattern:prim:/Base/mtl/albedo:rename_texture_file",
        rule_id="studio.naming.texture.pattern",
        title="rename texture file",
        fix_type="rename_texture_file",
        risk="medium",
        target_kind="node",
        target_id="prim:/Base/mtl/albedo",
        target_node="/Base/mtl/albedo",
        before_value="demo_albedo_v002_1.exr",
        after_value="t_demo_albedo_v002_1.exr",
    )
    assert _is_usd_stage_action(action, has_usd_proxy=True) is True
    assert _is_usd_stage_action(action, has_usd_proxy=False) is False


def test_is_usd_stage_action_routes_colorspace_set_attr_to_usd() -> None:
    action = FixAction(
        fix_id="common.texture.colorspace.color_managed:node:aiImage1:set_attr",
        rule_id="common.texture.colorspace.color_managed",
        title="colorspace",
        fix_type="set_attr",
        risk="low",
        target_kind="node",
        target_id="node:demo_albedo_v002_1",
        target_node="demo_albedo_v002_1",
        target_attr="colorSpace",
        before_value="Raw",
        after_value="sRGB",
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
            AppliedUsdFixRecord(
                fix_id=action.fix_id,
                fix_type=action.fix_type,
                target_id=action.target_id,
                target_attr=None,
                before_value=action.before_value,
                after_value=action.after_value,
                succeeded=True,
            )
        ],
    ) as apply_usd:
        report = apply_fix_actions([action], cmds=cmds)

    apply_usd.assert_called_once()
    assert isinstance(report, ApplyFixReport)
    assert report.applied_count == 1
