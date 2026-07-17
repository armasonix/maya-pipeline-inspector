from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pipeline_inspector.core.models import GraphSnapshot, NodeSnapshot
from pipeline_inspector.maya import commands
from pipeline_inspector.maya.navigation import NavigationActionResult
from pipeline_inspector.maya.usd_navigation import (
    find_usd_prim_for_issue,
    is_usd_prim_target,
    open_usd_shader_view,
    resolve_usd_material_scope_prim,
    resolve_usd_prim_path,
    select_usd_prim,
)
from pipeline_inspector.usd.scanner import _read_opening_errors


def test_is_usd_prim_target_detects_prim_prefix() -> None:
    assert is_usd_prim_target(target_id="prim:/Base/mtl/albedo")
    assert is_usd_prim_target(node_name="prim:/Base/mtl/albedo")
    assert is_usd_prim_target(node_name="/Base/mtl/albedo")
    assert not is_usd_prim_target(target_id="file1", node_name="file1")


def test_resolve_usd_prim_path_from_target_id() -> None:
    assert (
        resolve_usd_prim_path(target_id="prim:/Base/mtl/albedo")
        == "/Base/mtl/albedo"
    )


def test_resolve_usd_prim_path_from_snapshot_node_name() -> None:
    snapshot = GraphSnapshot(
        scene_path="shot.ma",
        renderer="vray",
        nodes=[
            NodeSnapshot(
                id="prim:/Base/mtl/albedo",
                name="demo_albedo_v002_1",
                full_name="/Base/mtl/albedo",
                type_name="Shader",
            )
        ],
    )
    assert (
        resolve_usd_prim_path(node_name="demo_albedo_v002_1", snapshot=snapshot)
        == "/Base/mtl/albedo"
    )


def test_select_usd_prim_uses_cmds_select_with_ufe_path() -> None:
    cmds = MagicMock()
    stage = MagicMock()
    stage.GetPrimAtPath.return_value.IsValid.return_value = True

    def ls_side_effect(*_args: object, **kwargs: object) -> list[str]:
        if kwargs.get("type") == "mayaUsdProxyShape":
            return ["|hero|heroShape"]
        if kwargs.get("ufe"):
            return ["|hero|heroShape,/Base/mtl/albedo"]
        return []

    cmds.ls.side_effect = ls_side_effect

    with patch(
        "pipeline_inspector.maya.usd_navigation._get_proxy_stage",
        return_value=stage,
    ):
        result = select_usd_prim("/Base/mtl/albedo", cmds=cmds)

    assert result.succeeded is True
    cmds.select.assert_called_once_with("|hero|heroShape,/Base/mtl/albedo", replace=True)


def test_is_usd_prim_target_detects_maya_usd_reference_node_id() -> None:
    assert is_usd_prim_target(target_id="node:char_usd_asset:SphereMTLSG")


def test_find_usd_prim_for_issue_matches_material_name_on_proxy_stage() -> None:
    stage = MagicMock()
    material_prim = MagicMock()
    material_prim.GetPath.return_value = "/Sphere/mtl/SphereMTLSG"
    material_prim.GetName.return_value = "SphereMTLSG"
    stage.Traverse.return_value = [material_prim]

    cmds = MagicMock()
    cmds.ls.return_value = ["|hero|heroShape"]

    with patch(
        "pipeline_inspector.maya.usd_navigation._get_proxy_stage",
        return_value=stage,
    ):
        prim_path = find_usd_prim_for_issue(
            target_id="node:char_usd_asset:SphereMTLSG",
            node_name="SphereMTLSG",
            material_name="SphereMTLSG",
            cmds=cmds,
        )

    assert prim_path == "/Sphere/mtl/SphereMTLSG"


def test_read_opening_errors_returns_empty_when_api_missing() -> None:
    class _Stage:
        pass

    assert _read_opening_errors(_Stage()) == []


def test_select_node_action_routes_maya_usd_reference_target() -> None:
    with patch(
        "pipeline_inspector.maya.commands._maya_cmds",
        return_value=MagicMock(objExists=lambda *_a, **_k: False),
    ), patch(
        "pipeline_inspector.maya.usd_navigation.resolve_usd_prim_path",
        return_value="/Sphere/mtl/SphereMTLSG",
    ), patch(
        "pipeline_inspector.maya.usd_navigation.select_usd_prim",
        return_value=NavigationActionResult(
            action="select_node",
            target="/Sphere/mtl/SphereMTLSG",
            succeeded=True,
            message="ok",
        ),
    ) as select_usd:
        result = commands.select_node_action(
            "SphereMTLSG",
            target_id="node:char_usd_asset:SphereMTLSG",
            material_name="SphereMTLSG",
        )

    assert result.succeeded is True
    select_usd.assert_called_once()


def test_select_node_action_routes_prim_target() -> None:
    with patch(
        "pipeline_inspector.maya.commands._maya_cmds",
        return_value=MagicMock(objExists=lambda *_a, **_k: False),
    ), patch(
        "pipeline_inspector.maya.usd_navigation.resolve_usd_prim_path",
        return_value="/Base/mtl/albedo",
    ), patch(
        "pipeline_inspector.maya.usd_navigation.select_usd_prim",
        return_value=NavigationActionResult(
            action="select_node",
            target="/Base/mtl/albedo",
            succeeded=True,
            message="ok",
        ),
    ) as select_usd:
        result = commands.select_node_action(
            "demo_albedo_v002_1",
            target_id="prim:/Base/mtl/albedo",
        )

    assert result.succeeded is True
    select_usd.assert_called_once()


def test_open_in_hypershade_action_routes_prim_target() -> None:
    with patch(
        "pipeline_inspector.maya.commands._maya_cmds",
        return_value=MagicMock(objExists=lambda *_a, **_k: False),
    ), patch(
        "pipeline_inspector.maya.usd_navigation.resolve_usd_prim_path",
        return_value="/Base/mtl/albedo",
    ), patch(
        "pipeline_inspector.maya.usd_navigation.open_usd_shader_view",
        return_value=NavigationActionResult(
            action="open_in_hypershade",
            target="/Base/mtl/albedo",
            succeeded=True,
            message="ok",
        ),
    ) as open_usd:
        result = commands.open_in_hypershade_action(
            "demo_albedo_v002_1",
            target_id="prim:/Base/mtl/albedo",
        )

    assert result.succeeded is True
    open_usd.assert_called_once()
    assert open_usd.call_args.args[0] == "/Base/mtl/albedo"


def test_resolve_usd_material_scope_prim_from_texture_path() -> None:
    assert (
        resolve_usd_material_scope_prim(
            "/Base/mtl/Base_MTLSG/VRay/Base_MTL/demo_albedo_v002_1_bitmap",
            material_name="Base_MTLSG",
        )
        == "/Base/mtl/Base_MTLSG"
    )


def test_open_usd_shader_view_opens_hypershade_and_attribute_editor() -> None:
    mel = MagicMock()
    cmds = MagicMock()
    cmds.HypershadeWindow = MagicMock()
    cmds.evalDeferred = MagicMock(side_effect=lambda callback: callback())
    shader_prim = "/Base/mtl/Base_MTLSG/UsdPreviewSurface/demo_albedo_v002_1"
    with patch(
        "pipeline_inspector.maya.usd_navigation.select_usd_prim",
        return_value=NavigationActionResult(
            action="select_node",
            target=shader_prim,
            succeeded=True,
            message="ok",
        ),
    ) as select_usd, patch(
        "pipeline_inspector.maya.usd_navigation._hypershade_panel_name",
        return_value="hyperShadePanel1",
    ):
        result = open_usd_shader_view(
            shader_prim,
            material_name="Base_MTLSG",
            cmds=cmds,
            mel=mel,
        )

    assert result.succeeded is True
    assert result.target == shader_prim
    select_usd.assert_called_once_with(shader_prim, cmds=cmds)
    cmds.HypershadeWindow.assert_called_once()
    mel.eval.assert_any_call("openAEWindow")
    mel.eval.assert_any_call(
        'hyperShadePanelGraphCommand("hyperShadePanel1", "showUpAndDownstream")'
    )
    assert not any(
        call.args == ("updateAE",) for call in mel.eval.call_args_list
    )


def test_open_in_hypershade_action_prefers_maya_node_from_prim_path() -> None:
    maya_cmds = MagicMock()
    maya_cmds.objExists.side_effect = lambda name: name == "demo_albedo_v002_1"
    with patch(
        "pipeline_inspector.maya.commands._maya_cmds",
        return_value=maya_cmds,
    ), patch(
        "pipeline_inspector.maya.commands.open_in_hypershade",
        return_value=NavigationActionResult(
            action="open_in_hypershade",
            target="demo_albedo_v002_1",
            succeeded=True,
            message="ok",
        ),
    ) as open_maya, patch(
        "pipeline_inspector.maya.usd_navigation.open_usd_shader_view",
    ) as open_usd:
        result = commands.open_in_hypershade_action(
            "/Base/mtl/Base_MTLSG/demo_albedo_v002_1",
            target_id="prim:/Base/mtl/Base_MTLSG/demo_albedo_v002_1",
        )

    assert result.succeeded is True
    open_maya.assert_called_once_with("demo_albedo_v002_1", cmds=maya_cmds)
    open_usd.assert_not_called()
