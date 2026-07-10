"""Apply persisted user preferences to the Maya panel shell."""
from __future__ import annotations

from typing import Any

from shader_health.ui import main_window
from shader_health.ui.settings_widgets import find_child
from shader_health.ui.theme_loader import apply_panel_theme
from shader_health.user_config import UserPreferences

_UI_DENSITY_MARGINS = {
    "comfortable": (8, 8, 8, 8),
    "compact": (4, 4, 4, 4),
}
_UI_DENSITY_SPACING = {
    "comfortable": 4,
    "compact": 2,
}


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
        user_config.default_profile_id,
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

    content._shader_health_scan_scope = user_config.default_scan_scope
    content._shader_health_ui_density = user_config.ui_density
    _apply_ui_density(content, qt_widgets, user_config.ui_density)
    apply_panel_theme(content, user_config.theme)


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
