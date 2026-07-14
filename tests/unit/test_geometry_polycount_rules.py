from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from pipeline_inspector.core import (
    GraphSnapshot,
    RuleDefinition,
    ShapeSnapshot,
    ValidationEngine,
    load_rule_file,
    load_rule_stack,
)

ROOT = Path(__file__).resolve().parents[2]
RULE_PATH = ROOT / "src" / "pipeline_inspector" / "rules" / "common" / "geometry_polycount.json"
RULE_ROOT = ROOT / "src" / "pipeline_inspector" / "rules"
HERO_PROFILE = RULE_ROOT / "profiles" / "asset_class_hero.json"
PROP_PROFILE = RULE_ROOT / "profiles" / "asset_class_prop.json"
BACKGROUND_PROFILE = RULE_ROOT / "profiles" / "asset_class_background.json"
PASS_FIXTURE = ROOT / "tests" / "fixtures" / "snapshots" / "geometry_polycount_pass.json"
OVER_FIXTURE = ROOT / "tests" / "fixtures" / "snapshots" / "geometry_polycount_over_budget.json"


def load_polycount_rule(rule_id: str) -> RuleDefinition:
    rules = {rule.id: rule for rule in load_rule_file(RULE_PATH)}
    return rules[rule_id]


def enabled_polycount_rule(rule_id: str) -> RuleDefinition:
    return replace(load_polycount_rule(rule_id), enabled=True)


def load_fixture(path: Path) -> GraphSnapshot:
    return GraphSnapshot.from_dict(json.loads(path.read_text(encoding="utf-8")))


def snapshot_for_polygon_count(polygon_count: object) -> GraphSnapshot:
    return GraphSnapshot(
        scene_path="demo.ma",
        renderer="common",
        shapes=[
            ShapeSnapshot(
                node_id="mesh:hero_body",
                name="hero_body",
                type_name="mesh",
                polygon_count=int(polygon_count) if isinstance(polygon_count, int) else 0,
            )
        ],
    )


def test_geometry_polycount_rule_pack_has_production_defaults():
    hero = load_polycount_rule("common.geometry.polycount.hero.max")
    prop = load_polycount_rule("common.geometry.polycount.prop.max")
    background = load_polycount_rule("common.geometry.polycount.background.max")

    for rule in (hero, prop, background):
        assert rule.scope == "geometry"
        assert rule.severity == "warning"
        assert rule.enabled is False
        assert rule.owner == "modeling_td"
        assert rule.match.criteria == {"type_name": "mesh", "referenced": False}
        assert rule.check.type == "numeric_max"
        assert rule.check.params["attribute"] == "polygon_count"
        assert rule.policy.auto_fix_allowed is False

    assert hero.check.params["max"] == 500000
    assert prop.check.params["max"] == 100000
    assert background.check.params["max"] == 25000
    assert hero.policy.block_publish is True
    assert prop.policy.block_publish is True
    assert background.policy.block_publish is False


def test_hero_polycount_rule_is_disabled_until_profile_enables_it():
    rules_by_id = {rule.id: rule for rule in load_rule_stack(renderer_ids=["common"])}
    enabled_by_id = {
        rule.id: rule
        for rule in load_rule_stack(renderer_ids=["common"], profile_path=HERO_PROFILE)
    }

    assert rules_by_id["common.geometry.polycount.hero.max"].enabled is False
    assert enabled_by_id["common.geometry.polycount.hero.max"].enabled is True
    assert enabled_by_id["common.geometry.polycount.prop.max"].enabled is False
    assert enabled_by_id["common.geometry.polycount.background.max"].enabled is False


def test_asset_class_profiles_enable_only_matching_polycount_tier():
    prop_rules = {
        rule.id: rule
        for rule in load_rule_stack(renderer_ids=["common"], profile_path=PROP_PROFILE)
    }
    background_rules = {
        rule.id: rule
        for rule in load_rule_stack(renderer_ids=["common"], profile_path=BACKGROUND_PROFILE)
    }

    assert prop_rules["common.geometry.polycount.prop.max"].enabled is True
    assert prop_rules["common.geometry.polycount.hero.max"].enabled is False
    assert background_rules["common.geometry.polycount.background.max"].enabled is True
    assert background_rules["common.geometry.polycount.prop.max"].enabled is False


def test_hero_polycount_rule_fails_above_threshold():
    rule = enabled_polycount_rule("common.geometry.polycount.hero.max")
    snapshot = snapshot_for_polygon_count(600000)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.target_kind == "shape"
    assert result.target_id == "mesh:hero_body"
    assert result.current_value == 600000
    assert result.expected_value == 500000
    assert result.block_publish is True


def test_hero_polycount_rule_passes_at_threshold():
    rule = enabled_polycount_rule("common.geometry.polycount.hero.max")
    snapshot = snapshot_for_polygon_count(500000)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.block_publish is False


def test_prop_profile_rule_fails_above_prop_threshold():
    rules = [
        rule
        for rule in load_rule_stack(renderer_ids=["common"], profile_path=PROP_PROFILE)
        if rule.id == "common.geometry.polycount.prop.max"
    ]
    snapshot = snapshot_for_polygon_count(120000)

    result = ValidationEngine().validate(snapshot, rules)[0]

    assert result.status == "failed"
    assert result.expected_value == 100000
    assert result.block_publish is True


def test_polycount_rule_skips_non_mesh_shapes():
    rule = enabled_polycount_rule("common.geometry.polycount.hero.max")
    snapshot = GraphSnapshot(
        scene_path="demo.ma",
        renderer="common",
        shapes=[
            ShapeSnapshot(
                node_id="shape:ctrl_curve",
                name="ctrl_curve",
                type_name="nurbsCurve",
                polygon_count=900000,
            )
        ],
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "skipped"
    assert result.evidence["reason"] == "no_matching_targets"


def test_polycount_rule_skips_referenced_meshes():
    rule = enabled_polycount_rule("common.geometry.polycount.hero.max")
    snapshot = GraphSnapshot(
        scene_path="demo.ma",
        renderer="common",
        shapes=[
            ShapeSnapshot(
                node_id="mesh:ref_body",
                name="ref_body",
                type_name="mesh",
                polygon_count=900000,
                referenced=True,
            )
        ],
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "skipped"
    assert result.evidence["reason"] == "no_matching_targets"


def test_geometry_polycount_pass_fixture_stays_within_prop_budget():
    snapshot = load_fixture(PASS_FIXTURE)
    rules = [
        rule
        for rule in load_rule_stack(renderer_ids=["common"], profile_path=PROP_PROFILE)
        if rule.id == "common.geometry.polycount.prop.max"
    ]

    result = ValidationEngine().validate(snapshot, rules)[0]

    assert result.status == "passed"
    assert result.current_value == 48000


def test_geometry_polycount_over_budget_fixture_fails_prop_budget():
    snapshot = load_fixture(OVER_FIXTURE)
    rules = [
        rule
        for rule in load_rule_stack(renderer_ids=["common"], profile_path=PROP_PROFILE)
        if rule.id == "common.geometry.polycount.prop.max"
    ]

    result = ValidationEngine().validate(snapshot, rules)[0]

    assert result.status == "failed"
    assert result.current_value == 150000
    assert result.expected_value == 100000
