from __future__ import annotations

from pipeline_inspector.core.models import FileDependencySnapshot, GraphSnapshot
from pipeline_inspector.core.rule_schema import ValidationEngine
from pipeline_inspector.maya.snapshot_enrichment import build_material_index, enrich_rule_results
from pipeline_inspector.core import RuleResult
from pipeline_inspector.usd.enrichment import usd_material_name_from_prim_path
from pipeline_inspector.usd.scanner import _dedupe_texture_file_dependencies


def test_usd_material_name_from_prim_path() -> None:
    assert (
        usd_material_name_from_prim_path(
            "/Base/mtl/Base_MTLSG/VRay/Base_MTL/demo_albedo_v002_1_bitmap"
        )
        == "Base_MTLSG"
    )


def test_dedupe_texture_file_dependencies_prefers_bitmap() -> None:
    preview = FileDependencySnapshot(
        node_id="prim:/Base/mtl/Base_MTLSG/UsdPreviewSurface/demo_albedo_v002_1",
        attr="file",
        raw_path="D:/textures/demo_albedo_v002.1001.exr",
        resolved_path="D:/textures/demo_albedo_v002.1001.exr",
        exists=False,
    )
    bitmap = FileDependencySnapshot(
        node_id="prim:/Base/mtl/Base_MTLSG/VRay/Base_MTL/demo_albedo_v002_1_bitmap",
        attr="file",
        raw_path="D:/textures/demo_albedo_v002.1001.exr",
        resolved_path="D:/textures/demo_albedo_v002.1001.exr",
        exists=False,
    )
    deduped = _dedupe_texture_file_dependencies([preview, bitmap])
    assert len(deduped) == 1
    assert deduped[0].node_id == bitmap.node_id


def test_usd_texture_missing_skips_maya_file_dependency() -> None:
    from pipeline_inspector.core.rule_loader import load_rule_stack

    snapshot = GraphSnapshot(
        scene_path="shot.ma",
        renderer="vray",
        file_dependencies=[
            FileDependencySnapshot(
                node_id="node:file1",
                attr="fileTextureName",
                raw_path="D:/missing/file.exr",
                resolved_path="D:/missing/file.exr",
                exists=False,
            ),
            FileDependencySnapshot(
                node_id="prim:/Base/mtl/Base_MTLSG/VRay/Base_MTL/demo_albedo_v002_1_bitmap",
                attr="file",
                raw_path="D:/missing/usd.exr",
                resolved_path="D:/missing/usd.exr",
                exists=False,
            ),
        ],
    )
    rules = load_rule_stack(renderer_ids=("vray", "usd"))
    results = ValidationEngine().validate(snapshot, rules)
    usd_missing = [
        item
        for item in results
        if item.rule_id == "usd.texture.missing" and item.status == "failed"
    ]
    assert len(usd_missing) == 1
    assert usd_missing[0].target_id == (
        "prim:/Base/mtl/Base_MTLSG/VRay/Base_MTL/demo_albedo_v002_1_bitmap"
    )
    assert all(item.target_id.startswith("prim:") for item in usd_missing)


def test_enrich_rule_results_sets_usd_material_from_prim_path() -> None:
    snapshot = GraphSnapshot(
        scene_path="hero.usda",
        renderer="usd",
        materials=[],
        file_dependencies=[
            FileDependencySnapshot(
                node_id="prim:/Base/mtl/Base_MTLSG/VRay/Base_MTL/demo_albedo_v002_1_bitmap",
                attr="file",
                raw_path="D:/missing/file.exr",
                resolved_path="D:/missing/file.exr",
                exists=False,
            )
        ],
    )
    result = RuleResult(
        rule_id="usd.texture.missing",
        severity="critical",
        status="failed",
        title="missing",
        message="missing",
        why="missing",
        owner="shader_td",
        target_kind="file_dependency",
        target_id="prim:/Base/mtl/Base_MTLSG/VRay/Base_MTL/demo_albedo_v002_1_bitmap",
        node="/Base/mtl/Base_MTLSG/VRay/Base_MTL/demo_albedo_v002_1_bitmap",
    )
    enriched = enrich_rule_results(snapshot, [result])[0]
    assert enriched.material == "Base_MTLSG"
    assert build_material_index(snapshot)[
        "prim:/Base/mtl/Base_MTLSG/VRay/Base_MTL/demo_albedo_v002_1_bitmap"
    ] == "Base_MTLSG"
