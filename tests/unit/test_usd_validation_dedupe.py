from __future__ import annotations

from pipeline_inspector.core import RuleResult
from pipeline_inspector.core.models import GraphSnapshot, NodeSnapshot
from pipeline_inspector.maya.usd_validation_dedupe import dedupe_validation_results


def _colorspace_result(*, target_id: str, node: str) -> RuleResult:
    return RuleResult(
        rule_id="common.texture.colorspace.color_managed",
        severity="error",
        status="failed",
        title="Color texture is configured as non-color data.",
        message="Color texture is configured as non-color data.",
        why="why",
        owner="shader_td",
        target_kind="node",
        target_id=target_id,
        node=node,
    )


def test_dedupe_colorspace_keeps_usdpreview_surface_only() -> None:
    snapshot = GraphSnapshot(
        scene_path="shot.ma",
        renderer="vray",
        nodes=[
            NodeSnapshot(
                id="node:char_usd_asset:_Base_mtl_Base_MTLSG_VRay_Base_MTL_demo_albedo_v002_1_place2dTexture1_tex",
                name="_Base_mtl_Base_MTLSG_VRay_Base_MTL_demo_albedo_v002_1_place2dTexture1_tex",
                type_name="Shader",
                attrs={"semantic_slot": "base_color", "colorSpace": "Raw"},
            ),
            NodeSnapshot(
                id="prim:/Base/mtl/Base_MTLSG/UsdPreviewSurface/demo_albedo_v002_1",
                name="demo_albedo_v002_1",
                full_name="/Base/mtl/Base_MTLSG/UsdPreviewSurface/demo_albedo_v002_1",
                type_name="Shader",
                attrs={"semantic_slot": "base_color", "colorSpace": "Raw"},
            ),
            NodeSnapshot(
                id="prim:/Base/mtl/Base_MTLSG/VRay/Base_MTL/demo_albedo_v002_1_place2dTexture1",
                name="demo_albedo_v002_1_place2dTexture1",
                full_name="/Base/mtl/Base_MTLSG/VRay/Base_MTL/demo_albedo_v002_1_place2dTexture1",
                type_name="Shader",
                attrs={"semantic_slot": "base_color", "colorSpace": "Raw"},
            ),
            NodeSnapshot(
                id="prim:/Base/mtl/Base_MTLSG/VRay/Base_MTL/demo_albedo_v002_1_bitmap",
                name="demo_albedo_v002_1_bitmap",
                full_name="/Base/mtl/Base_MTLSG/VRay/Base_MTL/demo_albedo_v002_1_bitmap",
                type_name="Shader",
                attrs={"semantic_slot": "base_color", "colorSpace": "Raw"},
            ),
        ],
        usd_stage_metadata=__import__(
            "pipeline_inspector.core.models",
            fromlist=["UsdStageMetadata"],
        ).UsdStageMetadata(has_default_prim=True),
    )
    results = [
        _colorspace_result(
            target_id="node:char_usd_asset:_Base_mtl_Base_MTLSG_VRay_Base_MTL_demo_albedo_v002_1_place2dTexture1_tex",
            node="_Base_mtl_Base_MTLSG_VRay_Base_MTL_demo_albedo_v002_1_place2dTexture1_tex",
        ),
        _colorspace_result(
            target_id="prim:/Base/mtl/Base_MTLSG/UsdPreviewSurface/demo_albedo_v002_1",
            node="/Base/mtl/Base_MTLSG/UsdPreviewSurface/demo_albedo_v002_1",
        ),
        _colorspace_result(
            target_id="prim:/Base/mtl/Base_MTLSG/VRay/Base_MTL/demo_albedo_v002_1_place2dTexture1",
            node="/Base/mtl/Base_MTLSG/VRay/Base_MTL/demo_albedo_v002_1_place2dTexture1",
        ),
        _colorspace_result(
            target_id="prim:/Base/mtl/Base_MTLSG/VRay/Base_MTL/demo_albedo_v002_1_bitmap",
            node="/Base/mtl/Base_MTLSG/VRay/Base_MTL/demo_albedo_v002_1_bitmap",
        ),
    ]
    deduped = dedupe_validation_results(snapshot, results)
    failed = [item for item in deduped if item.status == "failed"]
    assert len(failed) == 1
    assert failed[0].target_id == "prim:/Base/mtl/Base_MTLSG/UsdPreviewSurface/demo_albedo_v002_1"


def test_dedupe_colorspace_groups_place2d_without_semantic_slot() -> None:
    snapshot = GraphSnapshot(
        scene_path="shot.ma",
        renderer="vray",
        nodes=[
            NodeSnapshot(
                id="prim:/Base/mtl/Base_MTLSG/UsdPreviewSurface/demo_albedo_v002_1",
                name="demo_albedo_v002_1",
                full_name="/Base/mtl/Base_MTLSG/UsdPreviewSurface/demo_albedo_v002_1",
                type_name="Shader",
                attrs={"semantic_slot": "base_color", "colorSpace": "Raw"},
            ),
            NodeSnapshot(
                id="prim:/Base/mtl/Base_MTLSG/VRay/Base_MTL/demo_albedo_v002_1_place2dTexture1",
                name="demo_albedo_v002_1_place2dTexture1",
                full_name="/Base/mtl/Base_MTLSG/VRay/Base_MTL/demo_albedo_v002_1_place2dTexture1",
                type_name="Shader",
                attrs={"colorSpace": "Raw"},
            ),
        ],
        usd_stage_metadata=__import__(
            "pipeline_inspector.core.models",
            fromlist=["UsdStageMetadata"],
        ).UsdStageMetadata(has_default_prim=True),
    )
    results = [
        _colorspace_result(
            target_id="prim:/Base/mtl/Base_MTLSG/UsdPreviewSurface/demo_albedo_v002_1",
            node="/Base/mtl/Base_MTLSG/UsdPreviewSurface/demo_albedo_v002_1",
        ),
        _colorspace_result(
            target_id="prim:/Base/mtl/Base_MTLSG/VRay/Base_MTL/demo_albedo_v002_1_place2dTexture1",
            node="/Base/mtl/Base_MTLSG/VRay/Base_MTL/demo_albedo_v002_1_place2dTexture1",
        ),
    ]
    deduped = dedupe_validation_results(snapshot, results)
    failed = [item for item in deduped if item.status == "failed"]
    assert len(failed) == 1
    assert failed[0].target_id == "prim:/Base/mtl/Base_MTLSG/UsdPreviewSurface/demo_albedo_v002_1"
