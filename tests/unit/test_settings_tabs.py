from __future__ import annotations

from pipeline_inspector.ui.settings_tabs import (
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
        "Render",
        "Bug Report",
    )


def test_settings_tab_object_names_follow_pipeline_inspector_pattern():
    for spec in SETTINGS_TAB_SPECS:
        assert spec.object_name.startswith("pipelineInspectorSettings")
        assert spec.object_name.endswith("Tab")


def test_get_settings_tab_spec_returns_known_tabs():
    assert get_settings_tab_spec("studio_environment") is not None
    assert get_settings_tab_spec("bug_report") is not None
    assert get_settings_tab_spec("missing") is None
