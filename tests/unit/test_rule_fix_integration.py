from __future__ import annotations

from pathlib import Path

from shader_health.core import GraphSnapshot, ValidationEngine, build_fix_plan, load_rule_stack

ROOT = Path(__file__).resolve().parents[2]
RULE_ROOT = ROOT / "src" / "shader_health" / "rules"
FIXTURES_ROOT = ROOT / "tests" / "fixtures" / "snapshots"


def test_packaged_rules_emit_medium_and_high_fix_actions():
    snapshot = GraphSnapshot.from_json(
        (FIXTURES_ROOT / "texture_freshness_outdated.json").read_text(encoding="utf-8")
    )
    rules = load_rule_stack(rule_root=RULE_ROOT, renderer_ids=(snapshot.renderer or "common",))
    results = ValidationEngine().validate(snapshot, rules)
    failed = [result for result in results if result.status == "failed"]
    plan = build_fix_plan(failed, rules, snapshot)

    fix_types = {action.fix_type for action in plan.actions}
    risks = {action.risk for action in plan.actions}

    assert "relink_path" in fix_types
    assert "medium" in risks


def test_swap_texture_version_in_path_replaces_version_token():
    from shader_health.core.fix_plan import swap_texture_version_in_path

    updated = swap_texture_version_in_path(
        "D:/show/tex/albedo_v001.<UDIM>.exr",
        "001",
        "003",
    )

    assert updated == "D:/show/tex/albedo_v003.<UDIM>.exr"


def test_local_drive_rule_fix_is_normalize_path_medium():
    rules = load_rule_stack(rule_root=RULE_ROOT, renderer_ids=("common",))
    rule = next(item for item in rules if item.id == "common.texture.path.local_drive")

    assert rule.fix is not None
    assert rule.fix.type == "normalize_path"
    assert rule.fix.risk == "medium"
    assert rule.fix.params.get("replace_to") == "${ASSET_ROOT}"
    assert rule.policy.auto_fix_allowed is True


def test_displacement_amount_rule_fix_is_disable_feature_high():
    rules = load_rule_stack(rule_root=RULE_ROOT, renderer_ids=("common",))
    rule = next(item for item in rules if item.id == "common.displacement.amount.max")

    assert rule.fix is not None
    assert rule.fix.type == "disable_feature"
    assert rule.fix.risk == "high"
    assert rule.policy.auto_fix_allowed is True
