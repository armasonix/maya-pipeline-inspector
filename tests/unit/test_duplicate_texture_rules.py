from __future__ import annotations

from pathlib import Path

from shader_health.core import (
    FileDependencySnapshot,
    GraphSnapshot,
    RuleDefinition,
    ValidationEngine,
    load_rule_file,
)

ROOT = Path(__file__).resolve().parents[2]
RULE_PATH = ROOT / "src" / "shader_health" / "rules" / "common" / "duplicate_textures.json"


def load_duplicate_texture_rule() -> RuleDefinition:
    rules = load_rule_file(RULE_PATH)
    assert len(rules) == 1
    return rules[0]


def make_dependency(node_id: str, resolved_path: str) -> FileDependencySnapshot:
    return FileDependencySnapshot(
        node_id=node_id,
        attr="fileTextureName",
        raw_path=resolved_path,
        resolved_path=resolved_path,
        exists=True,
        extension=".exr",
    )


def snapshot_with(*dependencies: FileDependencySnapshot) -> GraphSnapshot:
    return GraphSnapshot(
        scene_path="demo.ma",
        renderer="vray",
        file_dependencies=list(dependencies),
    )


def test_duplicate_texture_rule_pack_has_production_defaults():
    rule = load_duplicate_texture_rule()

    assert rule.id == "common.texture.duplicates.same_path"
    assert rule.scope == "graph"
    assert rule.severity == "warning"
    assert rule.match.criteria == {}
    assert rule.check.type == "duplicate_file_dependencies"
    assert rule.policy.block_publish is False
    assert rule.policy.block_deadline is False
    assert rule.policy.auto_fix_allowed is False


def test_duplicate_texture_rule_fails_for_same_texture_on_multiple_nodes():
    rule = load_duplicate_texture_rule()
    snapshot = snapshot_with(
        make_dependency("node:file_a", "P:/asset/tex/albedo.exr"),
        make_dependency("node:file_b", "p:/asset/tex/albedo.exr"),
        make_dependency("node:file_c", "P:/asset/tex/roughness.exr"),
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.target_kind == "graph"
    assert result.plug == "file_dependencies"
    assert result.current_value == 1
    assert result.expected_value == 0
    assert result.block_publish is False
    assert result.block_deadline is False
    assert result.evidence["duplicate_groups"] == [
        {
            "path": "p:/asset/tex/albedo.exr",
            "node_ids": ["node:file_a", "node:file_b"],
            "count": 2,
        }
    ]


def test_duplicate_texture_rule_passes_for_unique_texture_dependencies():
    rule = load_duplicate_texture_rule()
    snapshot = snapshot_with(
        make_dependency("node:file_a", "P:/asset/tex/albedo.exr"),
        make_dependency("node:file_b", "P:/asset/tex/roughness.exr"),
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.current_value == 0
    assert result.expected_value == 0
    assert result.evidence == {}


def test_duplicate_texture_rule_ignores_repeated_records_for_same_node():
    rule = load_duplicate_texture_rule()
    snapshot = snapshot_with(
        make_dependency("node:file_a", "P:/asset/tex/albedo.exr"),
        make_dependency("node:file_a", "P:/asset/tex/albedo.exr"),
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.current_value == 0
    assert result.expected_value == 0


def test_duplicate_texture_rule_passes_empty_graph():
    rule = load_duplicate_texture_rule()
    snapshot = snapshot_with()

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.current_value == 0
    assert result.expected_value == 0
