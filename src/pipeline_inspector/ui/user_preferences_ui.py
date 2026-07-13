"""Apply persisted user preferences to the Maya panel shell."""
from __future__ import annotations

import logging
from typing import Any

from pipeline_inspector.runtime_preferences import (
    resolved_profile_id,
    user_validation_preferences,
)
from pipeline_inspector.ui import main_window
from pipeline_inspector.ui.settings_widgets import find_child
from pipeline_inspector.ui.theme_loader import apply_panel_theme
from pipeline_inspector.ui.ui_density_tokens import density_tokens, normalize_density
from pipeline_inspector.user_config import UserPreferences

_PIPELINE_INSPECTOR_LOGGER = logging.getLogger("pipeline_inspector")


def summary_header_state_from_user_config(user_config: UserPreferences) -> Any:
    """Build initial Validate tab header defaults from user preferences."""

    from pipeline_inspector.ui.main_window import ASSET_CLASS_NONE_ID, SummaryHeaderState

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

    content._pipeline_inspector_scan_scope = user_validation_preferences(user_config).scan_scope
    content._pipeline_inspector_ui_density = user_config.ui_density
    content._pipeline_inspector_extra_rule_paths = user_config.extra_rule_paths
    content._pipeline_inspector_max_issues_displayed = user_config.max_issues_displayed
    content._pipeline_inspector_mayapy_path = user_config.mayapy_path
    _apply_ui_density(content, qt_widgets, user_config.ui_density)
    apply_panel_theme(
        content,
        user_config.theme,
        dock=getattr(content, "_pipeline_inspector_dock", None),
    )
    _apply_debug_logging(user_config.debug_logging)


def _apply_debug_logging(enabled: bool) -> None:
    level = logging.DEBUG if enabled else logging.INFO
    _PIPELINE_INSPECTOR_LOGGER.setLevel(level)
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
    normalized = normalize_density(density)
    tokens = density_tokens(normalized)

    layout = _widget_layout(content)
    if layout is not None:
        set_margins = getattr(layout, "setContentsMargins", None)
        if set_margins is not None:
            set_margins(*tokens.content_margins)
        set_spacing = getattr(layout, "setSpacing", None)
        if set_spacing is not None:
            set_spacing(tokens.content_spacing)

    validate_tab = _validate_tab_widget(content, qt_widgets)
    if validate_tab is not None:
        tab_layout = _widget_layout(validate_tab)
        if tab_layout is not None:
            set_margins = getattr(tab_layout, "setContentsMargins", None)
            if set_margins is not None:
                set_margins(*tokens.tab_margins)
            set_spacing = getattr(tab_layout, "setSpacing", None)
            if set_spacing is not None:
                set_spacing(tokens.tab_spacing)

    main_window.apply_density_tokens(content, qt_widgets, tokens)


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
