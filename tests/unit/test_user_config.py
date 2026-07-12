from __future__ import annotations

import json
from pathlib import Path

import pytest

from shader_health.studio_config import StudioConfig
from shader_health.user_config import (
    USER_CONFIG_FILENAME,
    UserPreferences,
    UserUpdatesSettings,
    default_user_config_path,
    discover_user_config_path,
    load_user_config,
    merge_runtime_config,
    save_user_config,
)


def test_user_preferences_round_trips_through_json_file(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    path = tmp_path / ".shader_health" / USER_CONFIG_FILENAME
    original = UserPreferences(
        default_profile_id="lookdev",
        default_asset_class_id="character",
        default_scan_scope="selection",
        theme="dark",
        ui_density="compact",
        extra_rule_paths=("/studio/rules",),
        debug_logging=True,
        max_issues_displayed=250,
        mayapy_path="C:/mayapy.exe",
        docs_url="https://example.test/docs",
        updates=UserUpdatesSettings(check_on_startup=True),
    )

    save_user_config(path, original)
    loaded = load_user_config(path)

    assert loaded.default_profile_id == "lookdev"
    assert loaded.theme == "dark"
    assert loaded.extra_rule_paths == ("/studio/rules",)
    assert loaded.updates.check_on_startup is True
    assert loaded.config_path == path.resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"
    assert payload["theme"] == "dark"


def test_enrich_user_preferences_infers_mayapy_from_executable(
    monkeypatch: pytest.MonkeyPatch,
):
    import sys

    from shader_health.user_config import enrich_user_preferences, infer_local_mayapy_path

    monkeypatch.setattr(
        sys,
        "executable",
        r"C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe",
    )
    assert infer_local_mayapy_path().endswith("mayapy.exe")

    enriched = enrich_user_preferences(UserPreferences())
    assert enriched.mayapy_path.endswith("mayapy.exe")

    preserved = enrich_user_preferences(UserPreferences(mayapy_path="D:/custom/mayapy.exe"))
    assert preserved.mayapy_path == "D:/custom/mayapy.exe"


def test_user_preferences_default_uses_default_path_when_missing(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("SHADER_HEALTH_USER_CONFIG", raising=False)

    config = UserPreferences.default()

    assert config.config_path == default_user_config_path()
    assert discover_user_config_path() is None


def test_discover_user_config_path_honors_env_var(tmp_path: Path, monkeypatch):
    path = tmp_path / "custom_user.json"
    path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("SHADER_HEALTH_USER_CONFIG", str(path))

    assert discover_user_config_path() == path


def test_merge_runtime_config_pairs_studio_and_user_layers():
    merged = merge_runtime_config(StudioConfig(studio_name="Demo"), UserPreferences(theme="dark"))

    assert merged.studio.studio_name == "Demo"
    assert merged.user.theme == "dark"


def test_user_preferences_normalizes_invalid_enum_values():
    config = UserPreferences.from_dict(
        {
            "theme": "neon",
            "ui_density": "huge",
            "default_scan_scope": "everything",
        }
    )

    assert config.theme == "classic"
    assert config.ui_density == "comfortable"
    assert config.default_scan_scope == "scene"
