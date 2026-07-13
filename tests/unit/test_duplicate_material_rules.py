from __future__ import annotations

from pathlib import Path

from pipeline_inspector.core import (
    ConnectionSnapshot,
    FileDependencySnapshot,
    GraphSnapshot,
    MaterialSnapshot,
    NodeSnapshot,
    RuleDefinition,
    ValidationEngine,
    load_rule_file,
)
from pipeline_inspector.core.graph_fingerprint import (
    material_graph_content_fingerprint,
    material_graph_fingerprint,
)
from pipeline_inspector.maya.snapshot_enrichment import _material_texture_paths, enrich_snapshot

ROOT = Path(__file__).resolve().parents[2]
RULE_PATH = ROOT / "src" / "pipeline_inspector" / "rules" / "common" / "duplicate_materials.json"


def load_duplicate_material_rules() -> dict[str, RuleDefinition]:
    return {rule.id: rule for rule in load_rule_file(RULE_PATH)}


def twin_material_snapshot() -> GraphSnapshot:
    shared_nodes = [
        NodeSnapshot(
            id="node:file_albedo_a",
            name="file_albedo_a",
            type_name="file",
            attrs={"colorSpace": "Raw", "fileTextureName": "albedo.exr"},
        ),
        NodeSnapshot(
            id="node:file_albedo_b",
            name="file_albedo_b",
            type_name="file",
            attrs={"colorSpace": "Raw", "fileTextureName": "albedo.exr"},
        ),
        NodeSnapshot(
            id="node:hero_mtl",
            name="hero_mtl",
            type_name="VRayMtl",
            attrs={"color": [1.0, 1.0, 1.0]},
        ),
        NodeSnapshot(
            id="node:hero_mtl_copy",
            name="hero_mtl_copy",
            type_name="VRayMtl",
            attrs={"color": [1.0, 1.0, 1.0]},
        ),
    ]
    connections = [
        ConnectionSnapshot(
            src_node="node:file_albedo_a",
            src_attr="outColor",
            dst_node="node:hero_mtl",
            dst_attr="color",
        ),
        ConnectionSnapshot(
            src_node="node:file_albedo_b",
            src_attr="outColor",
            dst_node="node:hero_mtl_copy",
            dst_attr="color",
        ),
    ]
    materials = [
        MaterialSnapshot(
            node_id="node:hero_mtl",
            name="hero_mtl",
            type_name="VRayMtl",
            texture_nodes=["node:file_albedo_a"],
            assigned_shapes=["shape:hero"],
        ),
        MaterialSnapshot(
            node_id="node:hero_mtl_copy",
            name="hero_mtl_copy",
            type_name="VRayMtl",
            texture_nodes=["node:file_albedo_b"],
            assigned_shapes=["shape:prop"],
        ),
    ]
    file_dependencies = [
        FileDependencySnapshot(
            node_id="node:file_albedo_a",
            attr="fileTextureName",
            raw_path="albedo.exr",
            resolved_path="P:/asset/albedo.exr",
            exists=True,
        ),
        FileDependencySnapshot(
            node_id="node:file_albedo_b",
            attr="fileTextureName",
            raw_path="albedo.exr",
            resolved_path="P:/asset/albedo.exr",
            exists=True,
        ),
    ]
    return GraphSnapshot(
        scene_path="demo.ma",
        renderer="vray",
        nodes=shared_nodes,
        connections=connections,
        materials=materials,
        file_dependencies=file_dependencies,
    )


def test_duplicate_material_rule_pack_has_production_defaults():
    rules = load_duplicate_material_rules()

    fingerprint = rules["common.shader_network.duplicate.fingerprint"]
    assert fingerprint.scope == "graph"
    assert fingerprint.severity == "warning"
    assert fingerprint.check.type == "duplicate_material_fingerprints"
    assert fingerprint.check.params["max_materials"] == 250
    assert fingerprint.check.params["min_group_size"] == 2

    scan_cap = rules["common.shader_network.duplicate.scan_cap"]
    assert scan_cap.check.type == "duplicate_scan_budget"
    assert scan_cap.check.params["max_materials"] == 250
    assert scan_cap.check.params["max_file_dependencies"] == 2000


def test_content_fingerprint_ignores_material_and_node_names():
    snapshot = twin_material_snapshot()
    enriched = enrich_snapshot(snapshot)
    first, second = enriched.materials

    assert first.graph_fingerprint != second.graph_fingerprint
    assert first.graph_content_fingerprint == second.graph_content_fingerprint
    assert first.graph_content_fingerprint.startswith("sha256:")


def test_material_graph_content_fingerprint_matches_enrichment():
    snapshot = twin_material_snapshot()
    enriched = enrich_snapshot(snapshot)
    material = enriched.materials[0]
    nodes_by_id = {node.id: node for node in enriched.nodes}
    texture_paths = _material_texture_paths(material, tuple(enriched.file_dependencies))

    expected = material_graph_content_fingerprint(
        material,
        nodes_by_id=nodes_by_id,
        connections=enriched.connections,
        texture_paths=texture_paths,
    )

    assert material.graph_content_fingerprint == expected


def test_duplicate_material_fingerprint_rule_fails_for_twin_networks():
    rule = load_duplicate_material_rules()["common.shader_network.duplicate.fingerprint"]
    snapshot = enrich_snapshot(twin_material_snapshot())

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.current_value == 1
    assert result.evidence["duplicate_groups"] == [
        {
            "fingerprint": snapshot.materials[0].graph_content_fingerprint,
            "material_ids": ["node:hero_mtl", "node:hero_mtl_copy"],
            "material_names": ["hero_mtl", "hero_mtl_copy"],
            "count": 2,
        }
    ]


def test_duplicate_material_fingerprint_rule_passes_for_unique_networks():
    rule = load_duplicate_material_rules()["common.shader_network.duplicate.fingerprint"]
    snapshot = enrich_snapshot(twin_material_snapshot())
    unique_material = MaterialSnapshot(
        node_id="node:prop_mtl",
        name="prop_mtl",
        type_name="VRayMtl",
        texture_nodes=[],
        assigned_shapes=["shape:extra"],
        graph_content_fingerprint="sha256:unique",
    )
    snapshot = GraphSnapshot(
        scene_path=snapshot.scene_path,
        renderer=snapshot.renderer,
        nodes=list(snapshot.nodes),
        connections=list(snapshot.connections),
        materials=[snapshot.materials[0], unique_material],
        file_dependencies=list(snapshot.file_dependencies),
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.current_value == 0


def test_duplicate_material_fingerprint_rule_truncates_large_scenes():
    rule = load_duplicate_material_rules()["common.shader_network.duplicate.fingerprint"]
    rule = RuleDefinition.from_dict(
        {
            **rule.to_dict(),
            "check": {
                **rule.check.to_dict(),
                "max_materials": 1,
            },
        }
    )
    snapshot = enrich_snapshot(twin_material_snapshot())

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.evidence["material_scan_truncated"] is True
    assert result.evidence["material_count"] == 2
    assert result.evidence["scanned_material_count"] == 1


def test_duplicate_scan_budget_rule_fails_when_material_cap_exceeded():
    rule = load_duplicate_material_rules()["common.shader_network.duplicate.scan_cap"]
    materials = [
        MaterialSnapshot(
            node_id=f"node:mtl_{index}",
            name=f"mtl_{index}",
            type_name="VRayMtl",
        )
        for index in range(3)
    ]
    snapshot = GraphSnapshot(scene_path="demo.ma", renderer="vray", materials=materials)
    rule = RuleDefinition.from_dict(
        {
            **rule.to_dict(),
            "check": {
                **rule.check.to_dict(),
                "max_materials": 2,
                "max_file_dependencies": 2000,
            },
        }
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.evidence["material_scan_truncated"] is True
    assert result.evidence["material_count"] == 3


def test_duplicate_scan_budget_rule_fails_when_texture_cap_exceeded():
    rule = load_duplicate_material_rules()["common.shader_network.duplicate.scan_cap"]
    dependencies = [
        FileDependencySnapshot(
            node_id=f"node:file_{index}",
            attr="fileTextureName",
            raw_path=f"tex_{index}.exr",
            resolved_path=f"P:/asset/tex_{index}.exr",
            exists=True,
        )
        for index in range(3)
    ]
    snapshot = GraphSnapshot(scene_path="demo.ma", renderer="vray", file_dependencies=dependencies)
    rule = RuleDefinition.from_dict(
        {
            **rule.to_dict(),
            "check": {
                **rule.check.to_dict(),
                "max_materials": 250,
                "max_file_dependencies": 2,
            },
        }
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.evidence["file_dependency_scan_truncated"] is True
    assert result.evidence["file_dependency_count"] == 3


def test_passport_fingerprint_still_includes_material_id():
    snapshot = twin_material_snapshot()
    material = snapshot.materials[0]
    nodes_by_id = {node.id: node for node in snapshot.nodes}
    passport = material_graph_fingerprint(
        material,
        nodes_by_id=nodes_by_id,
        connections=snapshot.connections,
        texture_paths=("P:/asset/albedo.exr",),
    )
    content = material_graph_content_fingerprint(
        material,
        nodes_by_id=nodes_by_id,
        connections=snapshot.connections,
        texture_paths=("P:/asset/albedo.exr",),
    )

    assert passport != content
