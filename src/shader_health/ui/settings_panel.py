"""Settings screen for the Maya Shader Health Inspector panel."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Optional

from shader_health.connectors_registry import (
    iter_connectors,
    update_connector_views,
)
from shader_health.connectors_registry import (
    read_connectors_from_settings_view as _read_connectors_from_registry,
)
from shader_health.studio_config import ConnectorSettings, StudioConfig
from shader_health.ui.basic_settings_section import (
    build_basic_settings_section,
    read_basic_user_preferences_from_view,
    update_basic_settings_view,
)
from shader_health.ui.settings_tabs import (
    SETTINGS_BASIC_TAB_OBJECT_NAME,
    SETTINGS_CONNECTORS_TAB_OBJECT_NAME,
    SETTINGS_STUDIO_TAB_OBJECT_NAME,
    SETTINGS_TAB_SPECS,
    build_placeholder_tab,
    get_settings_tab_spec,
)
from shader_health.ui.settings_widgets import (
    apply_toggle_style,
    build_settings_toggle,
    find_child,
    toggle_label,
    wire_button,
)
from shader_health.user_config import UserPreferences

SETTINGS_VIEW_OBJECT_NAME = "shaderHealthInspectorSettingsView"
SETTINGS_TAB_WIDGET_OBJECT_NAME = "shaderHealthInspectorSettingsTabWidget"
SETTINGS_BACK_BUTTON_OBJECT_NAME = "shaderHealthInspectorSettingsBackButton"
SETTINGS_STATUS_LABEL_OBJECT_NAME = "shaderHealthInspectorSettingsStatusLabel"
SETTINGS_SAVE_STUDIO_BUTTON_OBJECT_NAME = "shaderHealthInspectorSettingsSaveStudioButton"
SETTINGS_LOAD_STUDIO_BUTTON_OBJECT_NAME = "shaderHealthInspectorSettingsLoadStudioButton"
SETTINGS_SAVE_USER_BUTTON_OBJECT_NAME = "shaderHealthInspectorSettingsSaveUserButton"
SETTINGS_LOAD_USER_BUTTON_OBJECT_NAME = "shaderHealthInspectorSettingsLoadUserButton"
SETTINGS_STUDIO_CONFIG_PATH_LABEL_OBJECT_NAME = "shaderHealthInspectorSettingsStudioConfigPathLabel"
SETTINGS_USER_CONFIG_PATH_LABEL_OBJECT_NAME = "shaderHealthInspectorSettingsUserConfigPathLabel"

# Backward-compatible aliases for older tests and integrations.
SETTINGS_SAVE_BUTTON_OBJECT_NAME = SETTINGS_SAVE_STUDIO_BUTTON_OBJECT_NAME
SETTINGS_LOAD_BUTTON_OBJECT_NAME = SETTINGS_LOAD_STUDIO_BUTTON_OBJECT_NAME
SETTINGS_CONFIG_PATH_LABEL_OBJECT_NAME = SETTINGS_STUDIO_CONFIG_PATH_LABEL_OBJECT_NAME

SETTINGS_PIPELINE_SECTION_OBJECT_NAME = "shaderHealthInspectorSettingsPipelineSection"
SETTINGS_REQUIRE_TX_TOGGLE_OBJECT_NAME = "shaderHealthInspectorSettingsRequireTxToggle"


@dataclass(frozen=True)
class SettingsActionCallbacks:
    """Callbacks for the settings screen."""

    on_back: Optional[Callable[[], None]] = None
    on_require_tx_changed: Optional[Callable[[bool], None]] = None
    on_deadline_enabled_changed: Optional[Callable[[bool], None]] = None
    on_deadline_settings_changed: Optional[Callable[[], None]] = None
    on_save_studio_settings: Optional[Callable[[], None]] = None
    on_load_studio_settings: Optional[Callable[[], None]] = None
    on_save_user_preferences: Optional[Callable[[], None]] = None
    on_load_user_preferences: Optional[Callable[[], None]] = None
    on_user_preferences_changed: Optional[Callable[[], None]] = None


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

    status_label = qt_widgets.QLabel(
        "Save studio policy and connectors separately from per-user preferences."
    )
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


def build_require_tx_toggle(
    qt_widgets: Any,
    *,
    enabled: bool,
    on_changed: Optional[Callable[[bool], None]] = None,
) -> Any:
    """Build a green/gray toggle button for the .tx pipeline policy."""

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

    return _read_connectors_from_registry(view, qt_widgets, base=base)


def update_settings_view(
    view: Any,
    qt_widgets: Any,
    *,
    config: StudioConfig,
    user_config: UserPreferences | None = None,
    status_message: str = "",
) -> None:
    """Refresh settings controls from the active studio and user config."""

    toggle = find_child(view, qt_widgets.QWidget, SETTINGS_REQUIRE_TX_TOGGLE_OBJECT_NAME)
    if toggle is not None:
        set_checked = getattr(toggle, "setChecked", None)
        if set_checked is not None:
            set_checked(config.pipeline.require_tx_derivatives)
        toggle.setText(toggle_label(config.pipeline.require_tx_derivatives))
        apply_toggle_style(toggle, config.pipeline.require_tx_derivatives)

    update_connector_views(view, qt_widgets, config.connectors)

    if user_config is not None:
        update_basic_settings_view(view, qt_widgets, user_config)

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


def read_user_preferences_from_settings_view(
    view: Any,
    qt_widgets: Any,
    *,
    base: UserPreferences | None = None,
) -> UserPreferences:
    """Read user preference fields currently shown in the settings UI."""

    return read_basic_user_preferences_from_view(view, qt_widgets, base=base)


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

    intro = qt_widgets.QLabel(
        "Studio-wide pipeline policy from shader_health_studio.json. "
        "Network paths live under Studio Environment; integrations under Connectors."
    )
    intro.setWordWrap(True)
    layout.addWidget(intro)

    pipeline_section = qt_widgets.QWidget()
    pipeline_section.setObjectName(SETTINGS_PIPELINE_SECTION_OBJECT_NAME)
    pipeline_layout = qt_widgets.QVBoxLayout(pipeline_section)
    pipeline_layout.setContentsMargins(0, 0, 0, 0)
    pipeline_layout.setSpacing(4)

    title = qt_widgets.QLabel("Pipeline Policy")
    set_style = getattr(title, "setStyleSheet", None)
    if set_style is not None:
        set_style("font-weight: bold;")
    pipeline_layout.addWidget(title)

    row = qt_widgets.QHBoxLayout()
    row.addWidget(
        qt_widgets.QLabel("Require .tx optimized texture derivatives")
    )
    row.addStretch(1)
    row.addWidget(
        build_require_tx_toggle(
            qt_widgets,
            enabled=config.pipeline.require_tx_derivatives,
            on_changed=callbacks.on_require_tx_changed,
        )
    )
    pipeline_layout.addLayout(row)

    hint = qt_widgets.QLabel(
        "When enabled, validation checks that raster textures have matching .tx files. "
        "Disable for studios that do not bake or use OpenImageIO derivatives."
    )
    hint.setWordWrap(True)
    pipeline_layout.addWidget(hint)
    layout.addWidget(pipeline_section)
    layout.addStretch(1)
    return tab


def _studio_config_path_text(config: StudioConfig) -> str:
    if config.config_path is None:
        return "Studio config: in-session defaults (no file loaded)."
    return f"Studio config: {config.config_path}"


def _user_config_path_text(config: UserPreferences) -> str:
    if config.config_path is None:
        return "User preferences: in-session defaults (no file loaded)."
    return f"User preferences: {config.config_path}"
