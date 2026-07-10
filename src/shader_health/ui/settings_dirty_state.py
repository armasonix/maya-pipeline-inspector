"""Dirty-state tracking for the Settings screen."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shader_health.connectors_registry import (
    read_connectors_from_settings_view,
)
from shader_health.studio_config import ConnectorSettings, StudioConfig
from shader_health.ui.bug_report_section import read_bug_report_from_view
from shader_health.ui.studio_environment_section import read_studio_environment_from_view
from shader_health.ui.studio_policy_section import read_studio_policy_from_view
from shader_health.user_config import UserPreferences

SETTINGS_DIRTY_BANNER_OBJECT_NAME = "shaderHealthInspectorSettingsDirtyBanner"
DEFAULT_SETTINGS_STATUS_MESSAGE = (
    "Save studio policy and connectors separately from per-user preferences."
)


@dataclass(frozen=True)
class SettingsDirtyState:
    """Tracks whether studio or user settings differ from the last saved baseline."""

    studio_dirty: bool = False
    user_dirty: bool = False

    @property
    def any_dirty(self) -> bool:
        return self.studio_dirty or self.user_dirty


def dirty_indicator_text(state: SettingsDirtyState) -> str:
    """Return banner text for unsaved settings, or an empty string when clean."""

    if not state.any_dirty:
        return ""
    parts: list[str] = []
    if state.studio_dirty:
        parts.append("studio policy")
    if state.user_dirty:
        parts.append("user preferences")
    if len(parts) == 1:
        return f"Unsaved changes: {parts[0]}."
    return f"Unsaved changes: {parts[0]} and {parts[1]}."


def studio_config_content_equal(left: StudioConfig, right: StudioConfig) -> bool:
    """Compare studio settings ignoring the loaded file path metadata."""

    return left.to_dict() == right.to_dict()


def user_preferences_content_equal(left: UserPreferences, right: UserPreferences) -> bool:
    """Compare user preference fields ignoring config path metadata."""

    return left.normalized().to_dict() == right.normalized().to_dict()


def studio_config_from_settings_view(
    view: Any,
    qt_widgets: Any,
    *,
    base: StudioConfig,
) -> StudioConfig:
    """Read the studio config currently represented in the settings UI."""

    connectors = read_connectors_from_settings_view(
        view,
        qt_widgets,
        base=base.connectors,
    )
    studio_environment = read_studio_environment_from_view(
        view,
        qt_widgets,
        base=base.studio_environment,
    )
    return read_bug_report_from_view(
        view,
        qt_widgets,
        base=read_studio_policy_from_view(
            view,
            qt_widgets,
            base=base.with_updates(
                connectors=connectors,
                studio_environment=studio_environment,
            ),
        ),
    )


def evaluate_settings_dirty_state(
    *,
    current_studio: StudioConfig,
    saved_studio: StudioConfig,
    current_user: UserPreferences,
    saved_user: UserPreferences,
) -> SettingsDirtyState:
    """Return which settings layers differ from their saved baselines."""

    return SettingsDirtyState(
        studio_dirty=not studio_config_content_equal(current_studio, saved_studio),
        user_dirty=not user_preferences_content_equal(current_user, saved_user),
    )


def evaluate_settings_dirty_state_from_view(
    view: Any,
    qt_widgets: Any,
    *,
    current_studio: StudioConfig,
    saved_studio: StudioConfig,
    current_user: UserPreferences,
    saved_user: UserPreferences,
) -> SettingsDirtyState:
    """Evaluate dirty state using connector fields read from the settings view."""

    effective_studio = studio_config_from_settings_view(
        view,
        qt_widgets,
        base=current_studio,
    )
    return evaluate_settings_dirty_state(
        current_studio=effective_studio,
        saved_studio=saved_studio,
        current_user=current_user,
        saved_user=saved_user,
    )


def connectors_match_saved(
    current: ConnectorSettings,
    saved: ConnectorSettings,
) -> bool:
    """Helper for tests comparing connector settings payloads."""

    return current.to_dict() == saved.to_dict()
