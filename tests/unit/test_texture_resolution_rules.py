from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from shader_health.core import (
    FileDependencySnapshot,
    GraphSnapshot,
    RuleDefinition,
    ValidationEngine,
    load_rule_file,
    load_rule_stack,
)

ROOT = Path(__file__).resolve().parents[2]
RULE_PATH = ROOT / "src" / "shader_health" / "rules" / "common" / "texture_resolution.json"
RULE_ROOT = ROOT / "src" / "shader_health" / "rules"
HERO_PROFILE = RULE_ROOT / "profiles" / "asset_class_hero.json"
PROP_PROFILE = RULE_ROOT / "profiles" / "asset_class_prop.json"
BACKGROUND_PROFILE = RULE_ROOT / "profiles" / "asset_class_background.json"


def load_resolution_rule(rule_id: str) -> RuleDefinition:
    rules = {rule.id: rule for rule in load_rule_file(RULE_PATH)}
    return rules[rule_id]


def enabled_resolution_rule(rule_id: str) -> RuleDefinition:
    return replace(load_resolution_rule(rule_id), enabled=True)


def snapshot_for_texture_dimension(
    *,
    max_dimension: object,
    exists: bool = True,
) -> GraphSnapshot:
    return GraphSnapshot(
        scene_path="demo.ma",
        renderer="vray",
        file_dependencies=[
            FileDependencySnapshot(
                node_id="node:file_albedo",
                attr="fileTextureName",
                raw_path="$ASSET_ROOT/tex/albedo_v001.exr",
                resolved_path="D:/show/asset/tex/albedo_v001.exr",
                exists=exists,
                extension=".exr",
                max_dimension=max_dimension if isinstance(max_dimension, int) else None,
            )
        ],
    )


def test_texture_resolution_rule_pack_has_production_defaults():
    hero = load_resolution_rule("common.texture.resolution.hero.max")
    prop = load_resolution_rule("common.texture.resolution.prop.max")
    background = load_resolution_rule("common.texture.resolution.background.max")

    for rule in (hero, prop, background):
        assert rule.scope == "file_dependency"
        assert rule.severity == "warning"
        assert rule.enabled is False
        assert rule.match.criteria == {"dependency_kind": "texture", "exists": True}
        assert rule.check.type == "numeric_max"
        assert rule.check.params["attribute"] == "max_dimension"
        assert rule.policy.auto_fix_allowed is False

    assert hero.check.params["max"] == 4096
    assert prop.check.params["max"] == 2048
    assert background.check.params["max"] == 1024
    assert hero.policy.block_publish is True
    assert prop.policy.block_publish is True
    assert background.policy.block_publish is False


def test_hero_resolution_rule_is_disabled_until_profile_enables_it():
    rules = load_rule_stack(renderer_ids=["vray"])
    rules_by_id = {rule.id: rule for rule in rules}

    assert rules_by_id["common.texture.resolution.hero.max"].enabled is False

    enabled_rules = load_rule_stack(renderer_ids=["vray"], profile_path=HERO_PROFILE)
    enabled_by_id = {rule.id: rule for rule in enabled_rules}

    assert enabled_by_id["common.texture.resolution.hero.max"].enabled is True
    assert enabled_by_id["common.texture.resolution.prop.max"].enabled is False
    assert enabled_by_id["common.texture.resolution.background.max"].enabled is False


def test_asset_class_profiles_enable_only_matching_tier():
    prop_rules = {
        rule.id: rule
        for rule in load_rule_stack(renderer_ids=["vray"], profile_path=PROP_PROFILE)
    }
    background_rules = {
        rule.id: rule
        for rule in load_rule_stack(renderer_ids=["vray"], profile_path=BACKGROUND_PROFILE)
    }

    assert prop_rules["common.texture.resolution.prop.max"].enabled is True
    assert prop_rules["common.texture.resolution.hero.max"].enabled is False
    assert background_rules["common.texture.resolution.background.max"].enabled is True
    assert background_rules["common.texture.resolution.prop.max"].enabled is False


def test_hero_resolution_rule_fails_above_threshold():
    rule = enabled_resolution_rule("common.texture.resolution.hero.max")
    snapshot = snapshot_for_texture_dimension(max_dimension=5000)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.target_kind == "file_dependency"
    assert result.target_id == "node:file_albedo"
    assert result.current_value == 5000
    assert result.expected_value == 4096
    assert result.block_publish is True


def test_hero_resolution_rule_passes_at_threshold():
    rule = enabled_resolution_rule("common.texture.resolution.hero.max")
    snapshot = snapshot_for_texture_dimension(max_dimension=4096)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.block_publish is False


def test_prop_profile_rule_fails_above_prop_threshold():
    rules = [
        rule
        for rule in load_rule_stack(renderer_ids=["vray"], profile_path=PROP_PROFILE)
        if rule.id == "common.texture.resolution.prop.max"
    ]
    snapshot = snapshot_for_texture_dimension(max_dimension=3000)

    result = ValidationEngine().validate(snapshot, rules)[0]

    assert result.status == "failed"
    assert result.expected_value == 2048
    assert result.block_publish is True


def test_resolution_rule_skips_missing_dimension_metadata():
    rule = enabled_resolution_rule("common.texture.resolution.hero.max")
    snapshot = snapshot_for_texture_dimension(max_dimension=None)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "skipped"
    assert result.evidence["reason"] == "numeric_max_requires_numeric_values"


def test_resolution_rule_skips_missing_files():
    rule = enabled_resolution_rule("common.texture.resolution.hero.max")
    snapshot = snapshot_for_texture_dimension(max_dimension=9000, exists=False)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "skipped"
    assert result.evidence["reason"] == "no_matching_targets"
