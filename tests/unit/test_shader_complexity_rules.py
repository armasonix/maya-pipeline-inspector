from __future__ import annotations

from pathlib import Path

from pipeline_inspector.core import (
    GraphSnapshot,
    MaterialSnapshot,
    RuleDefinition,
    ShaderComplexityMetadata,
    ValidationEngine,
    apply_profile_overrides,
    load_profile,
    load_rule_file,
)

ROOT = Path(__file__).resolve().parents[2]
RULE_PATH = ROOT / "src" / "pipeline_inspector" / "rules" / "common" / "shader_complexity.json"
DEADLINE_PROFILE = (
    ROOT / "src" / "pipeline_inspector" / "rules" / "profiles" / "deadline_critical.json"
)
PUBLISH_PROFILE = ROOT / "src" / "pipeline_inspector" / "rules" / "profiles" / "publish_strict.json"


def load_complexity_rule(rule_id: str) -> RuleDefinition:
    rules = {rule.id: rule for rule in load_rule_file(RULE_PATH)}
    return rules[rule_id]


def snapshot_for_material_complexity(
    *,
    graph_node_count: object = 10,
    texture_count: int = 4,
    graph_depth: object = 3,
    expensive_node_count: int = 1,
    farm_cost_score: float = 8.0,
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
                complexity_metadata=ShaderComplexityMetadata(
                    expensive_node_count=expensive_node_count,
                    farm_cost_score=farm_cost_score,
                ),
            )
        ],
    )


def test_shader_complexity_rule_pack_has_production_defaults():
    graph_nodes = load_complexity_rule("common.shader_complexity.graph_nodes.max")
    textures = load_complexity_rule("common.shader_complexity.texture_count.max")
    depth = load_complexity_rule("common.shader_complexity.graph_depth.max")
    expensive = load_complexity_rule("common.shader_complexity.expensive_nodes.max")
    farm_cost = load_complexity_rule("common.shader_complexity.farm_cost_score.max")

    assert graph_nodes.scope == "material"
    assert graph_nodes.check.type == "numeric_max"
    assert graph_nodes.check.params["attribute"] == "graph_node_count"
    assert graph_nodes.check.params["max"] == 64

    assert textures.scope == "material"
    assert textures.check.type == "list_length_max"
    assert textures.check.params["attribute"] == "texture_nodes"
    assert textures.check.params["max"] == 24

    assert depth.scope == "material"
    assert depth.check.type == "numeric_max"
    assert depth.check.params["attribute"] == "graph_depth"
    assert depth.check.params["max"] == 10

    assert expensive.check.params["attribute"] == "complexity_metadata.expensive_node_count"
    assert expensive.check.params["max"] == 3
    assert farm_cost.check.params["attribute"] == "complexity_metadata.farm_cost_score"
    assert farm_cost.check.params["max"] == 16

    for rule in (graph_nodes, textures, depth, expensive, farm_cost):
        assert rule.severity == "warning"
        assert rule.policy.block_publish is False
        assert rule.policy.block_deadline is False
        assert rule.policy.auto_fix_allowed is False


def test_graph_node_budget_rule_fails_above_threshold():
    rule = load_complexity_rule("common.shader_complexity.graph_nodes.max")
    snapshot = snapshot_for_material_complexity(graph_node_count=65)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.target_kind == "material"
    assert result.target_id == "node:hero_material"
    assert result.node == "hero_material"
    assert result.plug == "graph_node_count"
    assert result.current_value == 65
    assert result.expected_value == 64
    assert result.evidence["max"] == 64.0


def test_graph_node_budget_rule_passes_at_threshold():
    rule = load_complexity_rule("common.shader_complexity.graph_nodes.max")
    snapshot = snapshot_for_material_complexity(graph_node_count=64)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.block_publish is False
    assert result.block_deadline is False


def test_texture_count_budget_rule_fails_above_threshold():
    rule = load_complexity_rule("common.shader_complexity.texture_count.max")
    snapshot = snapshot_for_material_complexity(texture_count=25)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.target_kind == "material"
    assert result.target_id == "node:hero_material"
    assert result.node == "hero_material"
    assert result.plug == "texture_nodes"
    assert result.current_value == 25
    assert result.expected_value == 24
    assert result.evidence["max"] == 24.0


def test_texture_count_budget_rule_passes_at_threshold():
    rule = load_complexity_rule("common.shader_complexity.texture_count.max")
    snapshot = snapshot_for_material_complexity(texture_count=24)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.current_value == 24
    assert result.expected_value == 24


def test_graph_depth_budget_rule_fails_above_threshold():
    rule = load_complexity_rule("common.shader_complexity.graph_depth.max")
    snapshot = snapshot_for_material_complexity(graph_depth=11)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.target_kind == "material"
    assert result.target_id == "node:hero_material"
    assert result.node == "hero_material"
    assert result.plug == "graph_depth"
    assert result.current_value == 11
    assert result.expected_value == 10
    assert result.evidence["max"] == 10.0


def test_graph_depth_budget_rule_passes_at_threshold():
    rule = load_complexity_rule("common.shader_complexity.graph_depth.max")
    snapshot = snapshot_for_material_complexity(graph_depth=10)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.current_value == 10
    assert result.expected_value == 10


def test_expensive_node_budget_rule_fails_above_threshold():
    rule = load_complexity_rule("common.shader_complexity.expensive_nodes.max")
    snapshot = snapshot_for_material_complexity(expensive_node_count=4)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.plug == "complexity_metadata.expensive_node_count"
    assert result.current_value == 4
    assert result.expected_value == 3


def test_farm_cost_score_budget_rule_fails_above_threshold():
    rule = load_complexity_rule("common.shader_complexity.farm_cost_score.max")
    snapshot = snapshot_for_material_complexity(farm_cost_score=16.5)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.plug == "complexity_metadata.farm_cost_score"
    assert result.current_value == 16.5
    assert result.expected_value == 16


def test_graph_node_budget_rule_skips_missing_numeric_metadata():
    rule = load_complexity_rule("common.shader_complexity.graph_nodes.max")
    snapshot = snapshot_for_material_complexity(graph_node_count="not-a-number")

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "skipped"
    assert result.evidence["reason"] == "numeric_max_requires_numeric_values"


def test_deadline_critical_profile_tightens_complexity_thresholds():
    rules = load_rule_file(RULE_PATH)
    profile = load_profile(DEADLINE_PROFILE)
    resolved = {rule.id: rule for rule in apply_profile_overrides(rules, profile)}

    graph_nodes = resolved["common.shader_complexity.graph_nodes.max"]
    textures = resolved["common.shader_complexity.texture_count.max"]
    depth = resolved["common.shader_complexity.graph_depth.max"]
    expensive = resolved["common.shader_complexity.expensive_nodes.max"]
    farm_cost = resolved["common.shader_complexity.farm_cost_score.max"]

    assert graph_nodes.enabled is True
    assert graph_nodes.severity == "error"
    assert graph_nodes.policy.block_deadline is True
    assert graph_nodes.check.params["max"] == 40
    assert textures.check.params["max"] == 12
    assert depth.check.params["max"] == 6
    assert expensive.check.params["max"] == 2
    assert farm_cost.check.params["max"] == 14


def test_publish_strict_profile_blocks_publish_on_complexity_failures():
    rules = load_rule_file(RULE_PATH)
    profile = load_profile(PUBLISH_PROFILE)
    resolved = {rule.id: rule for rule in apply_profile_overrides(rules, profile)}

    graph_nodes = resolved["common.shader_complexity.graph_nodes.max"]
    farm_cost = resolved["common.shader_complexity.farm_cost_score.max"]

    assert graph_nodes.policy.block_publish is True
    assert graph_nodes.check.params["max"] == 48
    assert farm_cost.policy.block_publish is True
    assert farm_cost.check.params["max"] == 16
