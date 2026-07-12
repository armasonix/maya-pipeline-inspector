from __future__ import annotations

from pathlib import Path

from pipeline_inspector.core import (
    ConnectionSnapshot,
    FileDependencySnapshot,
    GraphSnapshot,
    MaterialSnapshot,
    NodeSnapshot,
    RuleResult,
    ValidationEngine,
    load_rule_file,
)
from pipeline_inspector.maya.snapshot_enrichment import (
    build_material_index,
    enrich_rule_results,
    prepare_snapshot_for_validation,
)
from pipeline_inspector.studio_config import StudioEnvironmentSettings

ROOT = Path(__file__).resolve().parents[2]
COLOR_SPACE_RULE = ROOT / "src" / "pipeline_inspector" / "rules" / "common" / "color_space.json"
UDIM_RULE = ROOT / "src" / "pipeline_inspector" / "rules" / "common" / "udim_integrity.json"
DISPLACEMENT_RULE = (
    ROOT / "src" / "pipeline_inspector" / "rules" / "common" / "displacement_common.json"
)


def _broken_scene_like_snapshot(tmp_path: Path) -> GraphSnapshot:
    tile_1001 = tmp_path / "demo_roughness_v001.1001.exr"
    tile_1003 = tmp_path / "demo_roughness_v001.1003.exr"
    tile_1001.write_bytes(b"tile")
    tile_1003.write_bytes(b"tile")
    udim_path = str(tmp_path / "demo_roughness_v001.1001.exr").replace("\\", "/")

    return GraphSnapshot(
        scene_path=str(tmp_path / "demo.ma"),
        renderer="vray",
        nodes=[
            NodeSnapshot(
                id="node:demo_roughness_v001_1",
                name="demo_roughness_v001_1",
                type_name="file",
                attrs={"colorSpace": "sRGB"},
            ),
            NodeSnapshot(
                id="node:demo_roughness_v001_2",
                name="demo_roughness_v001_2",
                type_name="file",
                attrs={
                    "colorSpace": "Raw",
                    "uvTilingMode": 3,
                    "fileTextureName": udim_path,
                },
            ),
            NodeSnapshot(
                id="node:demo_wrong_colorspace_MTL",
                name="demo_wrong_colorspace_MTL",
                type_name="VRayMtl",
            ),
            NodeSnapshot(
                id="node:displacementShader1",
                name="displacementShader1",
                type_name="displacementShader",
                attrs={"scale": 18},
            ),
        ],
        connections=[
            ConnectionSnapshot(
                src_node="node:demo_roughness_v001_1",
                src_attr="outAlpha",
                dst_node="node:demo_wrong_colorspace_MTL",
                dst_attr="rlg",
            ),
            ConnectionSnapshot(
                src_node="node:demo_displacement_v001_1",
                src_attr="outAlpha",
                dst_node="node:displacementShader1",
                dst_attr="d",
            ),
        ],
        materials=[
            MaterialSnapshot(
                node_id="node:demo_wrong_colorspace_MTL",
                name="demo_wrong_colorspace_MTL",
                type_name="VRayMtl",
                texture_nodes=["node:demo_roughness_v001_1"],
            )
        ],
        file_dependencies=[
            FileDependencySnapshot(
                node_id="node:demo_roughness_v001_2",
                attr="fileTextureName",
                raw_path=udim_path,
                resolved_path=udim_path,
                exists=True,
                is_udim=False,
            )
        ],
    )


def test_prepare_snapshot_propagates_semantics_and_udim_metadata(tmp_path: Path):
    snapshot = prepare_snapshot_for_validation(_broken_scene_like_snapshot(tmp_path))

    roughness_node = next(
        node for node in snapshot.nodes if node.id == "node:demo_roughness_v001_1"
    )
    assert roughness_node.attrs["semantic_slot"] == "roughness"

    udim_dependency = next(
        item for item in snapshot.file_dependencies if item.node_id == "node:demo_roughness_v001_2"
    )
    assert udim_dependency.is_udim is True
    assert udim_dependency.missing_udim_tiles == [1002]

    displacement_node = next(
        node for node in snapshot.nodes if node.id == "node:displacementShader1"
    )
    assert displacement_node.attrs["amount"] == 18


def test_enrich_rule_results_sets_material_for_displacement_texture(tmp_path: Path):
    snapshot = GraphSnapshot(
        scene_path=str(tmp_path / "demo.ma"),
        renderer="vray",
        nodes=[
            NodeSnapshot(
                id="node:demo_displacement_v001_1",
                name="demo_displacement_v001_1",
                type_name="file",
                attrs={"colorSpace": "Raw"},
            ),
            NodeSnapshot(
                id="node:displacementShader1",
                name="displacementShader1",
                type_name="displacementShader",
                attrs={"scale": 18},
            ),
            NodeSnapshot(
                id="node:hero_mtl",
                name="hero_mtl",
                type_name="VRayMtl",
            ),
        ],
        connections=[
            ConnectionSnapshot(
                src_node="node:demo_displacement_v001_1",
                src_attr="outAlpha",
                dst_node="node:displacementShader1",
                dst_attr="displacement",
            ),
        ],
        materials=[
            MaterialSnapshot(
                node_id="node:hero_mtl",
                name="hero_mtl",
                type_name="VRayMtl",
                displacement_nodes=["node:displacementShader1"],
            )
        ],
    )
    result = RuleResult(
        rule_id="common.displacement.amount.max",
        severity="warning",
        status="failed",
        title="High displacement",
        message="High displacement",
        why="Why",
        owner="shader_td",
        target_kind="node",
        target_id="node:displacementShader1",
        node="node:displacementShader1",
    )

    enriched = enrich_rule_results(snapshot, [result])[0]

    assert enriched.material == "hero_mtl"


def test_enrich_rule_results_sets_material_for_texture_dependency(tmp_path: Path):
    snapshot = _broken_scene_like_snapshot(tmp_path)
    result = RuleResult(
        rule_id="common.texture.path.local_drive",
        severity="critical",
        status="failed",
        title="Local path",
        message="Local path",
        why="Why",
        owner="pipeline_td",
        target_kind="file_dependency",
        target_id="node:demo_roughness_v001_1",
        node="node:demo_roughness_v001_1",
    )

    enriched = enrich_rule_results(snapshot, [result])[0]

    assert enriched.material == "demo_wrong_colorspace_MTL"


def test_prepared_snapshot_activates_colorspace_and_udim_rules(tmp_path: Path):
    snapshot = prepare_snapshot_for_validation(_broken_scene_like_snapshot(tmp_path))
    rules = {
        rule.id: rule
        for rule in (
            *load_rule_file(COLOR_SPACE_RULE),
            *load_rule_file(UDIM_RULE),
            *load_rule_file(DISPLACEMENT_RULE),
        )
    }
    selected = [
        rules["common.texture.colorspace.data_raw"],
        rules["common.texture.udim.missing_tiles"],
        rules["common.displacement.amount.max"],
    ]

    results = ValidationEngine().validate(snapshot, selected)
    by_id = {item.rule_id: item for item in results}

    assert by_id["common.texture.colorspace.data_raw"].status == "failed"
    assert by_id["common.texture.udim.missing_tiles"].status == "failed"
    assert by_id["common.displacement.amount.max"].status == "failed"


def test_build_material_index_maps_texture_nodes(tmp_path: Path):
    index = build_material_index(_broken_scene_like_snapshot(tmp_path))

    assert index["node:demo_roughness_v001_1"] == "demo_wrong_colorspace_MTL"


def test_prepare_snapshot_for_validation_resolves_studio_texture_root_tokens(tmp_path: Path):
    texture = tmp_path / "demo.exr"
    texture.write_bytes(b"demo")
    environment = StudioEnvironmentSettings(
        texture_root=str(tmp_path).replace("\\", "/"),
    )
    snapshot = GraphSnapshot(
        scene_path=str(tmp_path / "demo.ma"),
        file_dependencies=[
            FileDependencySnapshot(
                node_id="node:file1",
                attr="fileTextureName",
                raw_path="${STUDIO_TEXTURE_ROOT}/demo.exr",
            )
        ],
    )

    enriched = prepare_snapshot_for_validation(snapshot, studio_environment=environment)
    dependency = enriched.file_dependencies[0]

    assert dependency.resolved_path.endswith("/demo.exr")
    assert dependency.exists is True
