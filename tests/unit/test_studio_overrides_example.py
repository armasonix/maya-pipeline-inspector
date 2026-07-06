from __future__ import annotations

from pathlib import Path

from shader_health.core.rule_loader import load_profile, load_rule_stack

ROOT = Path(__file__).resolve().parents[2]
STUDIO_RULES = ROOT / "examples" / "studio" / "rules"
STUDIO_PROFILE = ROOT / "examples" / "studio" / "profiles" / "show_publish_strict.json"


def test_studio_example_extra_rules_and_profile_load():
    rules = load_rule_stack(
        renderer_ids=["vray"],
        profile_path=STUDIO_PROFILE,
        extra_rule_paths=[STUDIO_RULES],
    )
    rules_by_id = {rule.id: rule for rule in rules}

    assert "studio.texture.path.no_user_home" in rules_by_id
    assert rules_by_id["common.texture.version.latest"].enabled is False
    assert rules_by_id["common.texture.path.local_drive"].policy.block_publish is True
    assert rules_by_id["common.texture.path.local_drive"].policy.block_deadline is True

    studio_rule = rules_by_id["studio.texture.path.no_user_home"]
    assert studio_rule.enabled is True
    assert studio_rule.severity == "critical"
    assert studio_rule.policy.block_publish is True
    assert studio_rule.policy.block_deadline is True


def test_studio_example_profile_metadata():
    profile = load_profile(STUDIO_PROFILE)

    assert profile.id == "show_publish_strict"
    assert profile.display_name == "Show Publish Strict"
    assert "studio.texture.path.no_user_home" in profile.rule_overrides
    assert profile.rule_overrides["common.texture.version.latest"].enabled is False
