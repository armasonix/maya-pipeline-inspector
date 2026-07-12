from __future__ import annotations

from shader_health.ui import main_window
from shader_health.ui.theme_loader import (
    DEFAULT_THEME,
    load_theme_stylesheet,
    normalize_theme,
    theme_stylesheet_path,
)
from shader_health.ui.user_preferences_ui import apply_user_preferences_to_panel
from shader_health.user_config import UserPreferences


def test_theme_stylesheet_paths_exist_for_supported_themes():
    assert theme_stylesheet_path("classic").is_file()
    assert theme_stylesheet_path("dark").is_file()


def test_load_theme_stylesheet_returns_non_empty_qss():
    classic = load_theme_stylesheet("classic")
    dark = load_theme_stylesheet("dark")

    assert "shaderHealthInspectorPanelContent" in classic
    assert "shaderHealthInspectorPanelContent" in dark
    assert "#cccccc" in classic
    assert "#2b2b2b" in dark


def test_normalize_theme_falls_back_to_classic_for_unknown_values():
    assert normalize_theme("dark") == "dark"
    assert normalize_theme("neon") == DEFAULT_THEME
    assert normalize_theme("") == DEFAULT_THEME


def test_apply_panel_theme_sets_stylesheet_on_content_root():
    from tests.unit.test_maya_summary_header import FakeQtWidgets as MainWindowFakeQtWidgets

    widget = main_window.build_main_widget(
        MainWindowFakeQtWidgets,
        user_config=UserPreferences(theme="classic"),
    )
    assert widget._shader_health_theme == "classic"
    assert "#cccccc" in widget.style_sheet

    apply_user_preferences_to_panel(
        widget,
        MainWindowFakeQtWidgets,
        UserPreferences(theme="dark"),
    )

    assert widget._shader_health_theme == "dark"
    assert "#2b2b2b" in widget.style_sheet


class _FakeThemeWidget:
    def __init__(self) -> None:
        self.style_sheet = ""
        self._shader_health_theme = ""

    def setStyleSheet(self, stylesheet: str) -> None:
        self.style_sheet = stylesheet


def test_apply_panel_theme_normalizes_unknown_theme_ids():
    from shader_health.ui.theme_loader import apply_panel_theme

    widget = _FakeThemeWidget()

    applied = apply_panel_theme(widget, "neon")

    assert applied == DEFAULT_THEME
    assert widget._shader_health_theme == DEFAULT_THEME
    assert "#cccccc" in widget.style_sheet
