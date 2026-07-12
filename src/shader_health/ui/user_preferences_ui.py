"""Apply persisted user preferences to the Maya panel shell."""
from __future__ import annotations

import logging
from typing import Any

from shader_health.runtime_preferences import (
    resolved_profile_id,
    user_validation_preferences,
)
from shader_health.ui import main_window
from shader_health.ui.settings_widgets import find_child
from shader_health.ui.theme_loader import apply_panel_theme
from shader_health.user_config import UserPreferences

_SHADER_HEALTH_LOGGER = logging.getLogger("shader_health")

_UI_DENSITY_MARGINS = {
    "comfortable": (8, 8, 8, 8),
    "compact": (4, 4, 4, 4),
}
_UI_DENSITY_SPACING = {
    "comfortable": 4,
    "compact": 2,
}


def summary_header_state_from_user_config(user_config: UserPreferences) -> Any:
    """Build initial Validate tab header defaults from user preferences."""

    from shader_health.ui.main_window import ASSET_CLASS_NONE_ID, SummaryHeaderState

    prefs = user_validation_preferences(user_config)
    return SummaryHeaderState(
        profile_id=prefs.profile_id,
        asset_class_id=prefs.asset_class_id or ASSET_CLASS_NONE_ID,
        scan_scope=prefs.scan_scope,
    )


def apply_user_preferences_to_panel(
    content: Any,
    qt_widgets: Any,
    user_config: UserPreferences,
) -> None:
    """Apply saved user defaults to the Validate tab and panel chrome."""

    profile_dropdown = find_child(
        content,
        qt_widgets.QComboBox,
        main_window.PROFILE_DROPDOWN_OBJECT_NAME,
    )
    main_window.select_workflow_profile(
        profile_dropdown,
        resolved_profile_id(user_config),
    )

    asset_class_dropdown = find_child(
        content,
        qt_widgets.QComboBox,
        main_window.ASSET_CLASS_DROPDOWN_OBJECT_NAME,
    )
    main_window.select_asset_class_profile(
        asset_class_dropdown,
        user_config.default_asset_class_id,
    )

    content._shader_health_scan_scope = user_validation_preferences(user_config).scan_scope
    content._shader_health_ui_density = user_config.ui_density
    content._shader_health_extra_rule_paths = user_config.extra_rule_paths
    content._shader_health_max_issues_displayed = user_config.max_issues_displayed
    content._shader_health_mayapy_path = user_config.mayapy_path
    _apply_ui_density(content, qt_widgets, user_config.ui_density)
    apply_panel_theme(
        content,
        user_config.theme,
        dock=getattr(content, "_shader_health_dock", None),
    )
    _apply_debug_logging(user_config.debug_logging)


def _apply_debug_logging(enabled: bool) -> None:
    level = logging.DEBUG if enabled else logging.INFO
    _SHADER_HEALTH_LOGGER.setLevel(level)
    if enabled:
        if not logging.getLogger().handlers:
            logging.basicConfig(level=logging.DEBUG)
        return
    root = logging.getLogger()
    if root.level == logging.DEBUG:
        root.setLevel(logging.INFO)


def _widget_layout(widget: Any) -> Any | None:
    layout_attr = getattr(widget, "layout", None)
    if layout_attr is None:
        return None
    if callable(layout_attr):
        return layout_attr()
    return layout_attr


def _apply_ui_density(content: Any, qt_widgets: Any, density: str) -> None:
    normalized = density if density in _UI_DENSITY_MARGINS else "comfortable"
    margins = _UI_DENSITY_MARGINS[normalized]
    spacing = _UI_DENSITY_SPACING[normalized]

    layout = _widget_layout(content)
    if layout is not None:
        set_margins = getattr(layout, "setContentsMargins", None)
        if set_margins is not None:
            set_margins(*margins)
        set_spacing = getattr(layout, "setSpacing", None)
        if set_spacing is not None:
            set_spacing(spacing)

    validate_tab = _validate_tab_widget(content, qt_widgets)
    if validate_tab is None:
        return
    tab_layout = _widget_layout(validate_tab)
    if tab_layout is None:
        return
    set_margins = getattr(tab_layout, "setContentsMargins", None)
    if set_margins is not None:
        set_margins(*margins)
    set_spacing = getattr(tab_layout, "setSpacing", None)
    if set_spacing is not None:
        set_spacing(spacing)


def _validate_tab_widget(content: Any, qt_widgets: Any) -> Any | None:
    tabs = find_child(content, qt_widgets.QTabWidget, main_window.TAB_WIDGET_OBJECT_NAME)
    if tabs is None:
        return None
    tab_widget = getattr(tabs, "widget", None)
    if tab_widget is not None:
        widget = tab_widget(0)
        if widget is not None:
            return widget
    stored_tabs = getattr(tabs, "tabs", None)
    if not stored_tabs:
        return None
    first = stored_tabs[0]
    if isinstance(first, tuple):
        return first[1]
    return first
