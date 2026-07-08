from __future__ import annotations

from shader_health.ui.settings_tabs import (
    SETTINGS_TAB_SPECS,
    get_settings_tab_spec,
    settings_tab_titles,
)


def test_settings_tab_specs_include_v05_tabs():
    assert settings_tab_titles() == (
        "Basic",
        "Advanced",
        "Connectors",
        "Studio",
        "Studio Environment",
        "Bug Report",
    )


def test_settings_tab_object_names_follow_shader_health_pattern():
    for spec in SETTINGS_TAB_SPECS:
        assert spec.object_name.startswith("shaderHealthInspectorSettings")
        assert spec.object_name.endswith("Tab")


def test_get_settings_tab_spec_returns_known_tabs():
    assert get_settings_tab_spec("studio_environment") is not None
    assert get_settings_tab_spec("bug_report") is not None
    assert get_settings_tab_spec("missing") is None
