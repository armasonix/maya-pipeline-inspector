from __future__ import annotations

from pathlib import Path

from shader_health.runtime_preferences import (
    resolved_profile_id,
    resolved_scan_scope,
    user_extra_rule_paths,
    user_validation_preferences,
)
from shader_health.user_config import UserPreferences


def test_resolved_profile_id_falls_back_to_default_when_blank():
    assert resolved_profile_id(UserPreferences(default_profile_id="")) == "artist_relaxed"
    assert resolved_profile_id(UserPreferences(default_profile_id="publish_strict")) == (
        "publish_strict"
    )
    assert resolved_profile_id(UserPreferences(), override="deadline_critical") == (
        "deadline_critical"
    )


def test_resolved_scan_scope_normalizes_invalid_values():
    assert resolved_scan_scope(UserPreferences(default_scan_scope="selection")) == "selection"
    assert resolved_scan_scope(UserPreferences(default_scan_scope="everything")) == "scene"
    assert resolved_scan_scope(UserPreferences(), override="selection") == "selection"


def test_user_validation_preferences_merges_user_defaults_and_overrides():
    prefs = user_validation_preferences(
        UserPreferences(
            default_profile_id="publish_strict",
            default_asset_class_id="asset_class_hero",
            default_scan_scope="selection",
            extra_rule_paths=("/show/rules",),
        ),
        profile_id="deadline_critical",
        asset_class_id="asset_class_prop",
        scan_scope="scene",
    )

    assert prefs.profile_id == "deadline_critical"
    assert prefs.asset_class_id == "asset_class_prop"
    assert prefs.scan_scope == "scene"
    assert prefs.extra_rule_paths == (Path("/show/rules"),)


def test_user_extra_rule_paths_skips_blank_entries():
    paths = user_extra_rule_paths(
        UserPreferences(extra_rule_paths=("/a", "", "  ", "/b")),
    )

    assert paths == (Path("/a"), Path("/b"))
