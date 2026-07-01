from __future__ import annotations

from pathlib import Path

from shader_health.core import (
    GraphSnapshot,
    MaterialSnapshot,
    RuleDefinition,
    ValidationEngine,
    load_rule_file,
)

ROOT = Path(__file__).resolve().parents[2]
RULE_PATH = ROOT / "src" / "shader_health" / "rules" / "common" / "shader_complexity.json"


def load_complexity_rule(rule_id: str) -> RuleDefinition:
    rules = {rule.id: rule for rule in load_rule_file(RULE_PATH)}
    return rules[rule_id]


def snapshot_for_material_complexity(
    *,
    graph_node_count: object = 10,
    texture_count: int = 4,
    graph_depth: object = 3,
) -> GraphSnapshot:
    return GraphSnapshot(
        scene_path="demo.ma",
        renderer="vray",
        materials=[
            MaterialSnapshot(
                node_id="node:hero_material",
                name="hero_material",
                type_name="VRayMtl",
                renderer_family="vray",
                texture_nodes=[
                    f"node:file_{index}"
                    for index in range(texture_count)
                ],
                graph_node_count=graph_node_count,
                graph_depth=graph_depth,
                graph_fingerprint="sha256:demo",
            )
        ],
    )


def test_shader_complexity_rule_pack_has_production_defaults():
    graph_nodes = load_complexity_rule("common.shader_complexity.graph_nodes.max")
    textures = load_complexity_rule("common.shader_complexity.texture_count.max")
    depth = load_complexity_rule("common.shader_complexity.graph_depth.max")

    assert graph_nodes.scope == "material"
    assert graph_nodes.check.type == "numeric_max"
    assert graph_nodes.check.params["attribute"] == "graph_node_count"
    assert graph_nodes.check.params["max"] == 80

    assert textures.scope == "material"
    assert textures.check.type == "list_length_max"
    assert textures.check.params["attribute"] == "texture_nodes"
    assert textures.check.params["max"] == 32

    assert depth.scope == "material"
    assert depth.check.type == "numeric_max"
    assert depth.check.params["attribute"] == "graph_depth"
    assert depth.check.params["max"] == 12

    for rule in (graph_nodes, textures, depth):
        assert rule.severity == "warning"
        assert rule.policy.block_publish is False
        assert rule.policy.block_deadline is False
        assert rule.policy.auto_fix_allowed is False


def test_graph_node_budget_rule_fails_above_threshold():
    rule = load_complexity_rule("common.shader_complexity.graph_nodes.max")
    snapshot = snapshot_for_material_complexity(graph_node_count=81)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.target_kind == "material"
    assert result.target_id == "node:hero_material"
    assert result.node == "hero_material"
    assert result.plug == "graph_node_count"
    assert result.current_value == 81
    assert result.expected_value == 80
    assert result.evidence["max"] == 80.0


def test_graph_node_budget_rule_passes_at_threshold():
    rule = load_complexity_rule("common.shader_complexity.graph_nodes.max")
    snapshot = snapshot_for_material_complexity(graph_node_count=80)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.block_publish is False
    assert result.block_deadline is False


def test_texture_count_budget_rule_fails_above_threshold():
    rule = load_complexity_rule("common.shader_complexity.texture_count.max")
    snapshot = snapshot_for_material_complexity(texture_count=33)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.target_kind == "material"
    assert result.target_id == "node:hero_material"
    assert result.node == "hero_material"
    assert result.plug == "texture_nodes"
    assert result.current_value == 33
    assert result.expected_value == 32
    assert result.evidence["max"] == 32.0


def test_texture_count_budget_rule_passes_at_threshold():
    rule = load_complexity_rule("common.shader_complexity.texture_count.max")
    snapshot = snapshot_for_material_complexity(texture_count=32)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.current_value == 32
    assert result.expected_value == 32


def test_graph_depth_budget_rule_fails_above_threshold():
    rule = load_complexity_rule("common.shader_complexity.graph_depth.max")
    snapshot = snapshot_for_material_complexity(graph_depth=13)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.target_kind == "material"
    assert result.target_id == "node:hero_material"
    assert result.node == "hero_material"
    assert result.plug == "graph_depth"
    assert result.current_value == 13
    assert result.expected_value == 12
    assert result.evidence["max"] == 12.0


def test_graph_depth_budget_rule_passes_at_threshold():
    rule = load_complexity_rule("common.shader_complexity.graph_depth.max")
    snapshot = snapshot_for_material_complexity(graph_depth=12)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.current_value == 12
    assert result.expected_value == 12


def test_graph_node_budget_rule_skips_missing_numeric_metadata():
    rule = load_complexity_rule("common.shader_complexity.graph_nodes.max")
    snapshot = snapshot_for_material_complexity(graph_node_count="not-a-number")

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "skipped"
    assert result.evidence["reason"] == "numeric_max_requires_numeric_values"
