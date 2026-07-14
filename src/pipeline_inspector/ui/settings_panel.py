"""Settings screen for the Maya Pipeline Inspector panel."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Optional

from pipeline_inspector.connectors_registry import (
    iter_connectors,
    update_connector_views,
)
from pipeline_inspector.connectors_registry import (
    read_connectors_from_settings_view as _read_connectors_from_registry,
)
from pipeline_inspector.studio_config import ConnectorSettings, StudioConfig
from pipeline_inspector.trackers_registry import (
    iter_trackers,
    update_tracker_views,
)
from pipeline_inspector.trackers_registry import (
    read_trackers_from_settings_view as _read_trackers_from_registry,
)
from pipeline_inspector.ui.advanced_settings_section import (
    build_advanced_settings_section,
    read_advanced_user_preferences_from_view,
    update_advanced_settings_view,
)
from pipeline_inspector.ui.basic_settings_section import (
    build_basic_settings_section,
    prepare_basic_settings_interactions,
    read_basic_user_preferences_from_view,
    update_basic_settings_view,
)
from pipeline_inspector.ui.bug_report_section import (
    build_bug_report_section,
    update_bug_report_view,
)
from pipeline_inspector.ui.settings_dirty_state import (
    DEFAULT_SETTINGS_STATUS_MESSAGE,
    SETTINGS_DIRTY_BANNER_OBJECT_NAME,
    SettingsDirtyState,
    dirty_indicator_text,
)
from pipeline_inspector.ui.settings_tabs import (
    SETTINGS_ADVANCED_TAB_OBJECT_NAME,
    SETTINGS_BASIC_TAB_OBJECT_NAME,
    SETTINGS_BUG_REPORT_TAB_OBJECT_NAME,
    SETTINGS_CONNECTORS_TAB_OBJECT_NAME,
    SETTINGS_STUDIO_ENVIRONMENT_TAB_OBJECT_NAME,
    SETTINGS_STUDIO_TAB_OBJECT_NAME,
    SETTINGS_TAB_SPECS,
    build_placeholder_tab,
    get_settings_tab_spec,
)
from pipeline_inspector.ui.settings_widgets import find_child, wire_button
from pipeline_inspector.ui.studio_environment_section import (
    build_studio_environment_section,
    update_studio_environment_view,
)
from pipeline_inspector.ui.studio_policy_section import (
    SETTINGS_REQUIRE_TX_TOGGLE_OBJECT_NAME,
    build_studio_policy_section,
    update_studio_policy_view,
)
from pipeline_inspector.ui.support_section import (
    build_support_and_roles_section,
    update_support_and_roles_view,
)
from pipeline_inspector.user_config import UserPreferences

SETTINGS_VIEW_OBJECT_NAME = "pipelineInspectorSettingsView"
SETTINGS_TAB_WIDGET_OBJECT_NAME = "pipelineInspectorSettingsTabWidget"
SETTINGS_BACK_BUTTON_OBJECT_NAME = "pipelineInspectorSettingsBackButton"
SETTINGS_STATUS_LABEL_OBJECT_NAME = "pipelineInspectorSettingsStatusLabel"
SETTINGS_SAVE_STUDIO_BUTTON_OBJECT_NAME = "pipelineInspectorSettingsSaveStudioButton"
SETTINGS_LOAD_STUDIO_BUTTON_OBJECT_NAME = "pipelineInspectorSettingsLoadStudioButton"
SETTINGS_SAVE_USER_BUTTON_OBJECT_NAME = "pipelineInspectorSettingsSaveUserButton"
SETTINGS_LOAD_USER_BUTTON_OBJECT_NAME = "pipelineInspectorSettingsLoadUserButton"
SETTINGS_STUDIO_CONFIG_PATH_LABEL_OBJECT_NAME = "pipelineInspectorSettingsStudioConfigPathLabel"
SETTINGS_USER_CONFIG_PATH_LABEL_OBJECT_NAME = "pipelineInspectorSettingsUserConfigPathLabel"

# Backward-compatible aliases for older tests and integrations.
SETTINGS_SAVE_BUTTON_OBJECT_NAME = SETTINGS_SAVE_STUDIO_BUTTON_OBJECT_NAME
SETTINGS_LOAD_BUTTON_OBJECT_NAME = SETTINGS_LOAD_STUDIO_BUTTON_OBJECT_NAME
SETTINGS_CONFIG_PATH_LABEL_OBJECT_NAME = SETTINGS_STUDIO_CONFIG_PATH_LABEL_OBJECT_NAME

SETTINGS_PIPELINE_SECTION_OBJECT_NAME = "pipelineInspectorSettingsPipelineSection"


@dataclass(frozen=True)
class SettingsActionCallbacks:
    """Callbacks for the settings screen."""

    on_back: Optional[Callable[[], None]] = None
    on_require_tx_changed: Optional[Callable[[bool], None]] = None
    on_deadline_enabled_changed: Optional[Callable[[bool], None]] = None
    on_deadline_settings_changed: Optional[Callable[[], None]] = None
    on_telegram_enabled_changed: Optional[Callable[[bool], None]] = None
    on_telegram_settings_changed: Optional[Callable[[], None]] = None
    on_discord_enabled_changed: Optional[Callable[[bool], None]] = None
    on_discord_settings_changed: Optional[Callable[[], None]] = None
    on_slack_enabled_changed: Optional[Callable[[bool], None]] = None
    on_slack_settings_changed: Optional[Callable[[], None]] = None
    on_ftrack_enabled_changed: Optional[Callable[[bool], None]] = None
    on_ftrack_settings_changed: Optional[Callable[[], None]] = None
    on_shotgrid_enabled_changed: Optional[Callable[[bool], None]] = None
    on_shotgrid_settings_changed: Optional[Callable[[], None]] = None
    on_cerebro_enabled_changed: Optional[Callable[[bool], None]] = None
    on_cerebro_settings_changed: Optional[Callable[[], None]] = None
    on_studio_environment_changed: Optional[Callable[[], None]] = None
    on_studio_policy_changed: Optional[Callable[[], None]] = None
    on_readiness_settings_changed: Optional[Callable[[], None]] = None
    on_bug_report_settings_changed: Optional[Callable[[], None]] = None
    on_bug_report_enabled_changed: Optional[Callable[[bool], None]] = None
    on_save_studio_settings: Optional[Callable[[], None]] = None
    on_load_studio_settings: Optional[Callable[[], None]] = None
    on_save_user_preferences: Optional[Callable[[], None]] = None
    on_load_user_preferences: Optional[Callable[[], None]] = None
    on_user_preferences_changed: Optional[Callable[[], None]] = None
    on_theme_changed: Optional[Callable[[], None]] = None
    on_open_rule_editor: Optional[Callable[[], None]] = None
    on_open_new_rule_wizard: Optional[Callable[[], None]] = None
    on_open_rule_browser: Optional[Callable[[], None]] = None


def build_settings_view(
    qt_widgets: Any,
    *,
    config: Optional[StudioConfig] = None,
    user_config: Optional[UserPreferences] = None,
    callbacks: Optional[SettingsActionCallbacks] = None,
) -> Any:
    """Build the settings screen with category tabs and studio pipeline controls."""

    studio_config = config or StudioConfig.default()
    active_user_config = user_config or UserPreferences.default()
    settings_callbacks = callbacks or SettingsActionCallbacks()

    view = qt_widgets.QWidget()
    view.setObjectName(SETTINGS_VIEW_OBJECT_NAME)

    layout = qt_widgets.QVBoxLayout(view)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)

    top_row = qt_widgets.QHBoxLayout()
    back_button = qt_widgets.QPushButton("Back")
    back_button.setObjectName(SETTINGS_BACK_BUTTON_OBJECT_NAME)
    wire_button(back_button, settings_callbacks.on_back)
    top_row.addWidget(back_button)
    top_row.addStretch(1)
    layout.addLayout(top_row)

    tabs = qt_widgets.QTabWidget()
    tabs.setObjectName(SETTINGS_TAB_WIDGET_OBJECT_NAME)
    for spec in SETTINGS_TAB_SPECS:
        tab_widget = _build_settings_tab(
            qt_widgets,
            spec.tab_id,
            studio_config,
            active_user_config,
            settings_callbacks,
        )
        tabs.addTab(tab_widget, spec.title)
    layout.addWidget(tabs)

    studio_path_label = qt_widgets.QLabel(_studio_config_path_text(studio_config))
    studio_path_label.setObjectName(SETTINGS_STUDIO_CONFIG_PATH_LABEL_OBJECT_NAME)
    studio_path_label.setWordWrap(True)
    layout.addWidget(studio_path_label)

    user_path_label = qt_widgets.QLabel(_user_config_path_text(active_user_config))
    user_path_label.setObjectName(SETTINGS_USER_CONFIG_PATH_LABEL_OBJECT_NAME)
    user_path_label.setWordWrap(True)
    layout.addWidget(user_path_label)

    dirty_banner = qt_widgets.QLabel("")
    dirty_banner.setObjectName(SETTINGS_DIRTY_BANNER_OBJECT_NAME)
    dirty_banner.setWordWrap(True)
    set_visible = getattr(dirty_banner, "setVisible", None)
    if set_visible is not None:
        set_visible(False)
    layout.addWidget(dirty_banner)

    status_label = qt_widgets.QLabel(DEFAULT_SETTINGS_STATUS_MESSAGE)
    status_label.setObjectName(SETTINGS_STATUS_LABEL_OBJECT_NAME)
    status_label.setWordWrap(True)
    layout.addWidget(status_label)

    studio_actions_row = qt_widgets.QHBoxLayout()
    save_studio_button = qt_widgets.QPushButton("Save Studio Config")
    save_studio_button.setObjectName(SETTINGS_SAVE_STUDIO_BUTTON_OBJECT_NAME)
    wire_button(save_studio_button, settings_callbacks.on_save_studio_settings)
    studio_actions_row.addWidget(save_studio_button)

    load_studio_button = qt_widgets.QPushButton("Load Studio Config")
    load_studio_button.setObjectName(SETTINGS_LOAD_STUDIO_BUTTON_OBJECT_NAME)
    wire_button(load_studio_button, settings_callbacks.on_load_studio_settings)
    studio_actions_row.addWidget(load_studio_button)
    studio_actions_row.addStretch(1)
    layout.addLayout(studio_actions_row)

    user_actions_row = qt_widgets.QHBoxLayout()
    save_user_button = qt_widgets.QPushButton("Save User Preferences")
    save_user_button.setObjectName(SETTINGS_SAVE_USER_BUTTON_OBJECT_NAME)
    wire_button(save_user_button, settings_callbacks.on_save_user_preferences)
    user_actions_row.addWidget(save_user_button)

    load_user_button = qt_widgets.QPushButton("Load User Preferences")
    load_user_button.setObjectName(SETTINGS_LOAD_USER_BUTTON_OBJECT_NAME)
    wire_button(load_user_button, settings_callbacks.on_load_user_preferences)
    user_actions_row.addWidget(load_user_button)
    user_actions_row.addStretch(1)
    layout.addLayout(user_actions_row)

    return view


def prepare_settings_interactive_state(
    view: Any,
    qt_widgets: Any,
    user_config: UserPreferences,
    *,
    on_preferences_changed: Optional[Callable[[], None]] = None,
    on_theme_changed: Optional[Callable[[], None]] = None,
) -> None:
    """Wire Basic settings interactions when the settings screen is opened."""

    prepare_basic_settings_interactions(
        view,
        qt_widgets,
        user_config,
        on_preferences_changed=on_preferences_changed,
        on_theme_changed=on_theme_changed,
    )


def build_require_tx_toggle(
    qt_widgets: Any,
    *,
    enabled: bool,
    on_changed: Optional[Callable[[bool], None]] = None,
) -> Any:
    """Build a green/gray toggle button for the .tx pipeline policy."""

    from pipeline_inspector.ui.settings_widgets import build_settings_toggle

    return build_settings_toggle(
        qt_widgets,
        object_name=SETTINGS_REQUIRE_TX_TOGGLE_OBJECT_NAME,
        enabled=enabled,
        on_changed=on_changed,
    )


def read_connectors_from_settings_view(
    view: Any,
    qt_widgets: Any,
    *,
    base: ConnectorSettings | None = None,
) -> ConnectorSettings:
    """Read connector settings currently shown in the settings UI."""

    return _read_trackers_from_registry(
        view,
        qt_widgets,
        base=_read_connectors_from_registry(view, qt_widgets, base=base),
    )


def update_settings_view(
    view: Any,
    qt_widgets: Any,
    *,
    config: StudioConfig,
    user_config: UserPreferences | None = None,
    status_message: str = "",
    dirty_state: SettingsDirtyState | None = None,
) -> None:
    """Refresh settings controls from the active studio and user config."""

    update_studio_policy_view(view, qt_widgets, config)
    update_support_and_roles_view(view, qt_widgets, config.readiness)
    update_connector_views(view, qt_widgets, config.connectors)
    update_tracker_views(view, qt_widgets, config.connectors)
    update_studio_environment_view(view, qt_widgets, config.studio_environment)
    update_bug_report_view(view, qt_widgets, config.bug_report)

    if user_config is not None:
        update_basic_settings_view(view, qt_widgets, user_config)
        update_advanced_settings_view(view, qt_widgets, user_config)

    studio_path_label = find_child(
        view,
        qt_widgets.QLabel,
        SETTINGS_STUDIO_CONFIG_PATH_LABEL_OBJECT_NAME,
    )
    if studio_path_label is not None:
        studio_path_label.setText(_studio_config_path_text(config))

    if user_config is not None:
        user_path_label = find_child(
            view,
            qt_widgets.QLabel,
            SETTINGS_USER_CONFIG_PATH_LABEL_OBJECT_NAME,
        )
        if user_path_label is not None:
            user_path_label.setText(_user_config_path_text(user_config))

    if status_message:
        status_label = find_child(view, qt_widgets.QLabel, SETTINGS_STATUS_LABEL_OBJECT_NAME)
        if status_label is not None:
            status_label.setText(status_message)
    else:
        status_label = find_child(view, qt_widgets.QLabel, SETTINGS_STATUS_LABEL_OBJECT_NAME)
        if status_label is not None:
            status_label.setText(DEFAULT_SETTINGS_STATUS_MESSAGE)

    if dirty_state is not None:
        dirty_banner = find_child(view, qt_widgets.QLabel, SETTINGS_DIRTY_BANNER_OBJECT_NAME)
        if dirty_banner is not None:
            banner_text = dirty_indicator_text(dirty_state)
            dirty_banner.setText(banner_text)
            set_visible = getattr(dirty_banner, "setVisible", None)
            if set_visible is not None:
                set_visible(bool(banner_text))


def read_user_preferences_from_settings_view(
    view: Any,
    qt_widgets: Any,
    *,
    base: UserPreferences | None = None,
) -> UserPreferences:
    """Read user preference fields currently shown in the settings UI."""

    base = base or UserPreferences.default()
    merged = read_basic_user_preferences_from_view(view, qt_widgets, base=base)
    return read_advanced_user_preferences_from_view(view, qt_widgets, base=merged)


def _build_settings_tab(
    qt_widgets: Any,
    tab_id: str,
    config: StudioConfig,
    user_config: UserPreferences,
    callbacks: SettingsActionCallbacks,
) -> Any:
    spec = get_settings_tab_spec(tab_id)
    if spec is None:
        raise ValueError(f"Unknown settings tab id: {tab_id}")

    if tab_id == "basic":
        return _build_basic_tab(qt_widgets, user_config, callbacks)
    if tab_id == "advanced":
        return _build_advanced_tab(qt_widgets, user_config, callbacks)
    if tab_id == "connectors":
        return build_placeholder_tab(
            qt_widgets,
            spec,
            builder=lambda widgets: _build_connectors_tab(widgets, config, callbacks),
        )
    if tab_id == "studio":
        return build_placeholder_tab(
            qt_widgets,
            spec,
            builder=lambda widgets: _build_studio_tab(widgets, config, callbacks),
        )
    if tab_id == "studio_environment":
        return _build_studio_environment_tab(qt_widgets, config, callbacks)
    if tab_id == "bug_report":
        return _build_bug_report_tab(qt_widgets, config, callbacks)
    return build_placeholder_tab(qt_widgets, spec)


def _build_basic_tab(
    qt_widgets: Any,
    user_config: UserPreferences,
    callbacks: SettingsActionCallbacks,
) -> Any:
    tab = qt_widgets.QWidget()
    tab.setObjectName(SETTINGS_BASIC_TAB_OBJECT_NAME)
    layout = qt_widgets.QVBoxLayout(tab)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(8)
    layout.addWidget(
        build_basic_settings_section(
            qt_widgets,
            user_config,
            on_preferences_changed=callbacks.on_user_preferences_changed,
            on_theme_changed=callbacks.on_theme_changed,
        )
    )
    layout.addStretch(1)
    return tab


def _build_advanced_tab(
    qt_widgets: Any,
    user_config: UserPreferences,
    callbacks: SettingsActionCallbacks,
) -> Any:
    tab = qt_widgets.QWidget()
    tab.setObjectName(SETTINGS_ADVANCED_TAB_OBJECT_NAME)
    layout = qt_widgets.QVBoxLayout(tab)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(8)
    layout.addWidget(
        build_advanced_settings_section(
            qt_widgets,
            user_config,
            on_preferences_changed=callbacks.on_user_preferences_changed,
            on_open_rule_editor=callbacks.on_open_rule_editor or callbacks.on_open_rule_browser,
            on_open_new_rule_wizard=callbacks.on_open_new_rule_wizard,
        )
    )
    layout.addStretch(1)
    return tab


def _build_connectors_tab(
    qt_widgets: Any,
    config: StudioConfig,
    callbacks: SettingsActionCallbacks,
) -> Any:
    tab = qt_widgets.QWidget()
    tab.setObjectName(SETTINGS_CONNECTORS_TAB_OBJECT_NAME)
    layout = qt_widgets.QVBoxLayout(tab)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(8)

    for connector in iter_connectors():
        section = connector.build_section(qt_widgets, config, callbacks)
        layout.addWidget(section)

    for tracker in iter_trackers():
        if tracker.build_section is None:
            continue
        section = tracker.build_section(qt_widgets, config, callbacks)
        layout.addWidget(section)

    layout.addStretch(1)
    return tab


def _build_studio_environment_tab(
    qt_widgets: Any,
    config: StudioConfig,
    callbacks: SettingsActionCallbacks,
) -> Any:
    tab = qt_widgets.QWidget()
    tab.setObjectName(SETTINGS_STUDIO_ENVIRONMENT_TAB_OBJECT_NAME)
    layout = qt_widgets.QVBoxLayout(tab)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(8)
    layout.addWidget(
        build_studio_environment_section(
            qt_widgets,
            config,
            on_settings_changed=callbacks.on_studio_environment_changed,
        )
    )
    layout.addStretch(1)
    return tab


def _build_bug_report_tab(
    qt_widgets: Any,
    config: StudioConfig,
    callbacks: SettingsActionCallbacks,
) -> Any:
    tab = qt_widgets.QWidget()
    tab.setObjectName(SETTINGS_BUG_REPORT_TAB_OBJECT_NAME)
    layout = qt_widgets.QVBoxLayout(tab)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(8)
    layout.addWidget(
        build_bug_report_section(
            qt_widgets,
            config,
            on_enabled_changed=callbacks.on_bug_report_enabled_changed,
            on_settings_changed=callbacks.on_bug_report_settings_changed,
        )
    )
    layout.addStretch(1)
    return tab


def _build_studio_tab(
    qt_widgets: Any,
    config: StudioConfig,
    callbacks: SettingsActionCallbacks,
) -> Any:
    tab = qt_widgets.QWidget()
    tab.setObjectName(SETTINGS_STUDIO_TAB_OBJECT_NAME)
    layout = qt_widgets.QVBoxLayout(tab)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(8)
    layout.addWidget(
        build_studio_policy_section(
            qt_widgets,
            config,
            on_require_tx_changed=callbacks.on_require_tx_changed,
            on_settings_changed=callbacks.on_studio_policy_changed,
        )
    )
    layout.addWidget(
        build_support_and_roles_section(
            qt_widgets,
            config,
            on_settings_changed=callbacks.on_readiness_settings_changed,
        )
    )
    layout.addStretch(1)
    return tab


def _studio_config_path_text(config: StudioConfig) -> str:
    studio_name = str(config.studio_name or "").strip()
    name_prefix = f'Studio "{studio_name}" — ' if studio_name else ""
    if config.config_path is None:
        return (
            f"{name_prefix}pipeline_inspector_studio.json not saved yet "
            "(in-session defaults)."
        )
    return f"{name_prefix}pipeline_inspector_studio.json: {config.config_path}"


def _user_config_path_text(config: UserPreferences) -> str:
    if config.config_path is None:
        return "User preferences: in-session defaults (no file loaded)."
    return f"User preferences: {config.config_path}"
