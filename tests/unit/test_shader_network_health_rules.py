from __future__ import annotations

from pathlib import Path

from shader_health.core import (
    GraphSnapshot,
    MaterialSnapshot,
    RuleDefinition,
    ShadingEngineSnapshot,
    ValidationEngine,
    load_rule_file,
)

ROOT = Path(__file__).resolve().parents[2]
RULE_PATH = ROOT / "src" / "shader_health" / "rules" / "common" / "shader_network_health.json"


def load_shader_network_rule(rule_id: str) -> RuleDefinition:
    rules = {rule.id: rule for rule in load_rule_file(RULE_PATH)}
    return rules[rule_id]


def material_snapshot(*, assigned_shapes: list[str]) -> GraphSnapshot:
    return GraphSnapshot(
        scene_path="demo.ma",
        renderer="vray",
        materials=[
            MaterialSnapshot(
                node_id="node:hero_material",
                name="hero_material",
                type_name="VRayMtl",
                renderer_family="vray",
                assigned_shapes=assigned_shapes,
                graph_node_count=4,
                graph_depth=2,
            )
        ],
    )


def shading_engine_snapshot(
    *,
    node_id: str = "node:hero_sg",
    name: str = "hero_sg",
    surface_shader: str | None = "node:hero_material",
    members: list[str],
) -> GraphSnapshot:
    return GraphSnapshot(
        scene_path="demo.ma",
        renderer="vray",
        shading_engines=[
            ShadingEngineSnapshot(
                node_id=node_id,
                name=name,
                surface_shader=surface_shader,
                members=members,
            )
        ],
    )


def test_shader_network_rule_pack_has_acceptance_criteria_rules():
    unassigned = load_shader_network_rule("common.shader_network.material.unassigned")
    empty_engine = load_shader_network_rule("common.shader_network.shading_engine.empty")
    default_material = load_shader_network_rule(
        "common.shader_network.default_material.assigned"
    )

    assert unassigned.scope == "material"
    assert unassigned.check.type == "list_length_min"
    assert unassigned.check.params["attribute"] == "assigned_shapes"
    assert unassigned.check.params["min"] == 1

    assert empty_engine.scope == "shading_engine"
    assert empty_engine.check.type == "list_length_min"
    assert empty_engine.check.params["attribute"] == "members"
    assert empty_engine.check.params["min"] == 1

    assert default_material.scope == "graph"
    assert default_material.severity == "error"
    assert default_material.check.type == "default_material_assignment"
    assert default_material.policy.block_publish is True
    assert default_material.policy.block_deadline is False


def test_unassigned_material_rule_reports_material_without_assignments():
    rule = load_shader_network_rule("common.shader_network.material.unassigned")
    snapshot = material_snapshot(assigned_shapes=[])

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.target_kind == "material"
    assert result.target_id == "node:hero_material"
    assert result.node == "hero_material"
    assert result.plug == "assigned_shapes"
    assert result.current_value == 0
    assert result.expected_value == 1
    assert result.evidence["min"] == 1.0


def test_unassigned_material_rule_passes_assigned_material():
    rule = load_shader_network_rule("common.shader_network.material.unassigned")
    snapshot = material_snapshot(assigned_shapes=["mesh:hero_body"])

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.current_value == 1
    assert result.expected_value == 1


def test_empty_shading_engine_rule_reports_empty_shading_engine():
    rule = load_shader_network_rule("common.shader_network.shading_engine.empty")
    snapshot = shading_engine_snapshot(members=[])

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.target_kind == "shading_engine"
    assert result.target_id == "node:hero_sg"
    assert result.node == "hero_sg"
    assert result.plug == "members"
    assert result.current_value == 0
    assert result.expected_value == 1
    assert result.evidence["min"] == 1.0


def test_empty_shading_engine_rule_passes_shading_engine_with_members():
    rule = load_shader_network_rule("common.shader_network.shading_engine.empty")
    snapshot = shading_engine_snapshot(members=["mesh:hero_body"])

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.current_value == 1
    assert result.expected_value == 1


def test_default_material_rule_reports_default_material_on_production_geometry():
    rule = load_shader_network_rule("common.shader_network.default_material.assigned")
    snapshot = shading_engine_snapshot(
        node_id="node:initialShadingGroup",
        name="initialShadingGroup",
        surface_shader="node:lambert1",
        members=["mesh:hero_body"],
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.target_kind == "graph"
    assert result.plug == "shading_engines"
    assert result.current_value == 1
    assert result.expected_value == 0
    assert result.block_publish is True
    assert result.block_deadline is False
    assert result.evidence["assignments"] == [
        {
            "shading_engine": "node:initialShadingGroup",
            "surface_shader": "node:lambert1",
            "members": ["mesh:hero_body"],
            "count": 1,
        }
    ]


def test_default_material_rule_passes_empty_default_shading_engine():
    rule = load_shader_network_rule("common.shader_network.default_material.assigned")
    snapshot = shading_engine_snapshot(
        node_id="node:initialShadingGroup",
        name="initialShadingGroup",
        surface_shader="node:lambert1",
        members=[],
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.current_value == 0
    assert result.expected_value == 0


def test_default_material_rule_passes_non_default_material_assignment():
    rule = load_shader_network_rule("common.shader_network.default_material.assigned")
    snapshot = shading_engine_snapshot(
        node_id="node:hero_sg",
        name="hero_sg",
        surface_shader="node:hero_material",
        members=["mesh:hero_body"],
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.current_value == 0
    assert result.expected_value == 0
