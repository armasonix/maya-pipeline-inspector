from __future__ import annotations

from shader_health.studio_config import (
    ConnectorSettings,
    DeadlineConnectorSettings,
    PipelineSettings,
    StudioConfig,
)
from shader_health.ui.settings_dirty_state import (
    SettingsDirtyState,
    dirty_indicator_text,
    evaluate_settings_dirty_state,
    user_preferences_content_equal,
)
from shader_health.user_config import UserPreferences


def test_dirty_indicator_text_describes_single_and_dual_layers():
    assert dirty_indicator_text(SettingsDirtyState()) == ""
    assert dirty_indicator_text(SettingsDirtyState(studio_dirty=True)) == (
        "Unsaved changes: studio policy."
    )
    assert dirty_indicator_text(SettingsDirtyState(user_dirty=True)) == (
        "Unsaved changes: user preferences."
    )
    assert dirty_indicator_text(SettingsDirtyState(studio_dirty=True, user_dirty=True)) == (
        "Unsaved changes: studio policy and user preferences."
    )


def test_evaluate_settings_dirty_state_detects_studio_and_user_differences():
    saved_studio = StudioConfig(pipeline=PipelineSettings(require_tx_derivatives=False))
    current_studio = StudioConfig(pipeline=PipelineSettings(require_tx_derivatives=True))
    saved_user = UserPreferences(default_profile_id="artist_relaxed")
    current_user = UserPreferences(default_profile_id="publish_strict")

    assert evaluate_settings_dirty_state(
        current_studio=current_studio,
        saved_studio=saved_studio,
        current_user=saved_user,
        saved_user=saved_user,
    ) == SettingsDirtyState(studio_dirty=True, user_dirty=False)

    assert evaluate_settings_dirty_state(
        current_studio=saved_studio,
        saved_studio=saved_studio,
        current_user=current_user,
        saved_user=saved_user,
    ) == SettingsDirtyState(studio_dirty=False, user_dirty=True)


def test_user_preferences_content_equal_ignores_config_path():
    left = UserPreferences(
        default_profile_id="deadline_critical",
        config_path=None,
    )
    right = UserPreferences(
        default_profile_id="deadline_critical",
        config_path=__import__("pathlib").Path("C:/Users/me/.shader_health/user.json"),
    )

    assert user_preferences_content_equal(left, right) is True


def test_evaluate_settings_dirty_state_detects_connector_changes():
    saved = StudioConfig(
        connectors=ConnectorSettings(
            deadline=DeadlineConnectorSettings(enabled=False, web_service_host=""),
        )
    )
    current = StudioConfig(
        connectors=ConnectorSettings(
            deadline=DeadlineConnectorSettings(enabled=True, web_service_host="farm-host"),
        )
    )

    state = evaluate_settings_dirty_state(
        current_studio=current,
        saved_studio=saved,
        current_user=UserPreferences(),
        saved_user=UserPreferences(),
    )

    assert state == SettingsDirtyState(studio_dirty=True, user_dirty=False)
