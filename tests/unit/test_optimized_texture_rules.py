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
RULE_PATH = ROOT / "src" / "shader_health" / "rules" / "common" / "optimized_textures.json"


def load_optimized_rule(rule_id: str) -> RuleDefinition:
    rules = {rule.id: rule for rule in load_rule_file(RULE_PATH)}
    return rules[rule_id]


def snapshot_for_optimized_texture(
    *,
    optimized_exists: bool | None = True,
    optimized_is_stale: bool | None = False,
) -> GraphSnapshot:
    return GraphSnapshot(
        scene_path="demo.ma",
        renderer="arnold",
        file_dependencies=[
            FileDependencySnapshot(
                node_id="node:file_albedo",
                attr="fileTextureName",
                raw_path="$ASSET_ROOT/tex/albedo_v003.exr",
                resolved_path="D:/show/assets/tex/albedo_v003.exr",
                exists=True,
                extension=".exr",
                mtime_utc="2026-06-30T11:00:00Z",
                optimized_path="D:/show/assets/tex/albedo_v003.tx",
                optimized_exists=optimized_exists,
                optimized_mtime_utc="2026-06-30T11:05:00Z",
                optimized_is_stale=optimized_is_stale,
            )
        ],
    )


def test_file_dependency_snapshot_round_trips_optimized_texture_metadata():
    snapshot = snapshot_for_optimized_texture(
        optimized_exists=True,
        optimized_is_stale=False,
    )

    data = snapshot.to_dict()
    restored = GraphSnapshot.from_dict(data)

    dependency = data["file_dependencies"][0]
    assert restored == snapshot
    assert dependency["optimized_path"] == "D:/show/assets/tex/albedo_v003.tx"
    assert dependency["optimized_exists"] is True
    assert dependency["optimized_mtime_utc"] == "2026-06-30T11:05:00Z"
    assert dependency["optimized_is_stale"] is False


def test_optimized_exists_rule_pack_has_production_defaults():
    rule = load_optimized_rule("common.texture.optimized.exists")

    assert rule.scope == "file_dependency"
    assert rule.severity == "warning"
    assert rule.match.criteria == {
        "dependency_kind": "texture",
        "optimized_exists": [True, False],
    }
    assert rule.check.type == "attribute_equals"
    assert rule.check.params["attribute"] == "optimized_exists"
    assert rule.check.params["expected"] is True
    assert rule.policy.block_publish is False
    assert rule.policy.block_deadline is False
    assert rule.policy.auto_fix_allowed is False


def test_optimized_exists_rule_fails_when_derivative_is_missing():
    rule = load_optimized_rule("common.texture.optimized.exists")
    snapshot = snapshot_for_optimized_texture(optimized_exists=False)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.target_kind == "file_dependency"
    assert result.target_id == "node:file_albedo"
    assert result.plug == "optimized_exists"
    assert result.current_value is False
    assert result.expected_value is True
    assert result.block_publish is False
    assert result.block_deadline is False


def test_optimized_exists_rule_passes_when_derivative_exists():
    rule = load_optimized_rule("common.texture.optimized.exists")
    snapshot = snapshot_for_optimized_texture(optimized_exists=True)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.current_value is True
    assert result.expected_value is True


def test_optimized_exists_rule_skips_when_metadata_is_absent():
    rule = load_optimized_rule("common.texture.optimized.exists")
    snapshot = snapshot_for_optimized_texture(optimized_exists=None)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "skipped"
    assert result.evidence["reason"] == "no_matching_targets"


def test_optimized_fresh_rule_pack_has_production_defaults():
    rule = load_optimized_rule("common.texture.optimized.fresh")

    assert rule.scope == "file_dependency"
    assert rule.severity == "warning"
    assert rule.match.criteria == {
        "dependency_kind": "texture",
        "optimized_is_stale": [True, False],
    }
    assert rule.check.type == "attribute_equals"
    assert rule.check.params["attribute"] == "optimized_is_stale"
    assert rule.check.params["expected"] is False
    assert rule.policy.block_publish is False
    assert rule.policy.block_deadline is False
    assert rule.policy.auto_fix_allowed is False


def test_optimized_fresh_rule_fails_when_derivative_is_stale():
    rule = load_optimized_rule("common.texture.optimized.fresh")
    snapshot = snapshot_for_optimized_texture(optimized_is_stale=True)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.target_kind == "file_dependency"
    assert result.target_id == "node:file_albedo"
    assert result.plug == "optimized_is_stale"
    assert result.current_value is True
    assert result.expected_value is False


def test_optimized_fresh_rule_passes_when_derivative_is_fresh():
    rule = load_optimized_rule("common.texture.optimized.fresh")
    snapshot = snapshot_for_optimized_texture(optimized_is_stale=False)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.current_value is False
    assert result.expected_value is False


def test_optimized_fresh_rule_skips_when_metadata_is_absent():
    rule = load_optimized_rule("common.texture.optimized.fresh")
    snapshot = snapshot_for_optimized_texture(optimized_is_stale=None)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "skipped"
    assert result.evidence["reason"] == "no_matching_targets"
