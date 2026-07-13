from __future__ import annotations

from typing import Any

from tests.unit.test_maya_summary_header import FakeQtWidgets, _find

from pipeline_inspector import __version__
from pipeline_inspector.ui import main_window


def _panel_header_widgets(header: Any) -> list[Any]:
    assert header.layout is not None
    return list(header.layout.widgets)


def test_panel_header_has_expected_root_object_name():
    header = main_window.build_panel_header(FakeQtWidgets)

    assert header.object_name == main_window.PANEL_HEADER_OBJECT_NAME


def test_panel_header_layout_places_gear_title_docs_report_bug_and_updates_in_order():
    header = main_window.build_panel_header(FakeQtWidgets)
    gear = _find(header, main_window.SETTINGS_GEAR_BUTTON_OBJECT_NAME)
    title = _find(header, main_window.PANEL_HEADER_TITLE_OBJECT_NAME)
    unsaved = _find(header, main_window.PANEL_HEADER_UNSAVED_OBJECT_NAME)
    docs = _find(header, main_window.DOCUMENTATION_BUTTON_OBJECT_NAME)
    report_bug = _find(header, main_window.REPORT_BUG_BUTTON_OBJECT_NAME)
    updates = _find(header, main_window.CHECK_FOR_UPDATES_BUTTON_OBJECT_NAME)

    widgets = _panel_header_widgets(header)
    assert widgets == [gear, title, unsaved, docs, report_bug, updates]


def test_panel_header_title_receives_horizontal_stretch():
    header = main_window.build_panel_header(FakeQtWidgets)
    title = _find(header, main_window.PANEL_HEADER_TITLE_OBJECT_NAME)

    assert header.layout is not None
    title_index = header.layout.widgets.index(title)
    assert header.layout.widget_stretches[title_index] == 0


def test_panel_header_layout_uses_zero_margins_and_compact_spacing():
    header = main_window.build_panel_header(FakeQtWidgets)

    assert header.layout is not None
    assert header.layout.margins == (0, 0, 0, 0)
    assert header.layout.spacing == 8


def test_panel_header_button_object_names_are_stable():
    header = main_window.build_panel_header(FakeQtWidgets)

    assert (
        _find(header, main_window.SETTINGS_GEAR_BUTTON_OBJECT_NAME).object_name
        == main_window.SETTINGS_GEAR_BUTTON_OBJECT_NAME
    )
    assert (
        _find(header, main_window.PANEL_HEADER_TITLE_OBJECT_NAME).object_name
        == main_window.PANEL_HEADER_TITLE_OBJECT_NAME
    )
    assert (
        _find(header, main_window.DOCUMENTATION_BUTTON_OBJECT_NAME).object_name
        == main_window.DOCUMENTATION_BUTTON_OBJECT_NAME
    )
    assert (
        _find(header, main_window.REPORT_BUG_BUTTON_OBJECT_NAME).object_name
        == main_window.REPORT_BUG_BUTTON_OBJECT_NAME
    )
    assert (
        _find(header, main_window.CHECK_FOR_UPDATES_BUTTON_OBJECT_NAME).object_name
        == main_window.CHECK_FOR_UPDATES_BUTTON_OBJECT_NAME
    )


def test_panel_header_button_tooltips_are_set():
    header = main_window.build_panel_header(FakeQtWidgets)
    gear = _find(header, main_window.SETTINGS_GEAR_BUTTON_OBJECT_NAME)
    docs = _find(header, main_window.DOCUMENTATION_BUTTON_OBJECT_NAME)
    report_bug = _find(header, main_window.REPORT_BUG_BUTTON_OBJECT_NAME)
    updates = _find(header, main_window.CHECK_FOR_UPDATES_BUTTON_OBJECT_NAME)

    assert gear.tooltip == main_window.SETTINGS_GEAR_TOOLTIP
    assert docs.tooltip == main_window.DOCUMENTATION_BUTTON_TOOLTIP
    assert report_bug.tooltip == main_window.REPORT_BUG_BUTTON_TOOLTIP
    assert updates.tooltip == main_window.CHECK_FOR_UPDATES_BUTTON_TOOLTIP


def test_panel_header_settings_gear_invokes_callback():
    opened: list[str] = []

    header = main_window.build_panel_header(
        FakeQtWidgets,
        navigation_callbacks=main_window.PanelNavigationCallbacks(
            on_open_settings=lambda: opened.append("settings"),
        ),
    )
    gear = _find(header, main_window.SETTINGS_GEAR_BUTTON_OBJECT_NAME)

    gear.clicked.emit()
    assert opened == ["settings"]


def test_panel_header_navigation_callbacks_for_new_buttons():
    opened: list[str] = []

    header = main_window.build_panel_header(
        FakeQtWidgets,
        navigation_callbacks=main_window.PanelNavigationCallbacks(
            on_open_documentation=lambda: opened.append("docs"),
            on_report_bug=lambda: opened.append("report_bug"),
            on_check_for_updates=lambda: opened.append("updates"),
        ),
    )
    docs = _find(header, main_window.DOCUMENTATION_BUTTON_OBJECT_NAME)
    report_bug = _find(header, main_window.REPORT_BUG_BUTTON_OBJECT_NAME)
    updates = _find(header, main_window.CHECK_FOR_UPDATES_BUTTON_OBJECT_NAME)

    docs.clicked.emit()
    report_bug.clicked.emit()
    updates.clicked.emit()
    assert opened == ["docs", "report_bug", "updates"]


def test_panel_header_title_shows_version_and_bold_style():
    header = main_window.build_panel_header(FakeQtWidgets, version="0.5.0-dev")
    title = _find(header, main_window.PANEL_HEADER_TITLE_OBJECT_NAME)

    assert main_window.PANEL_TITLE in title.text
    assert "v0.5.0-dev" in title.text
    assert "font-weight: bold" in title.style_sheet


def test_panel_header_gear_uses_compact_width():
    header = main_window.build_panel_header(FakeQtWidgets)
    gear = _find(header, main_window.SETTINGS_GEAR_BUTTON_OBJECT_NAME)

    assert gear.fixed_width == 34


def test_panel_header_compact_buttons_use_fixed_vertical_size_policy():
    header = main_window.build_panel_header(FakeQtWidgets)
    docs = _find(header, main_window.DOCUMENTATION_BUTTON_OBJECT_NAME)
    report_bug = _find(header, main_window.REPORT_BUG_BUTTON_OBJECT_NAME)
    updates = _find(header, main_window.CHECK_FOR_UPDATES_BUTTON_OBJECT_NAME)

    preferred = FakeQtWidgets.QSizePolicy.Preferred
    fixed = FakeQtWidgets.QSizePolicy.Fixed
    assert docs.size_policy == (preferred, fixed)
    assert report_bug.size_policy == (preferred, fixed)
    assert updates.size_policy == (preferred, fixed)


def test_main_widget_places_panel_header_before_body_stack():
    widget = main_window.build_main_widget(FakeQtWidgets)

    assert widget.layout is not None
    header = widget.layout.widgets[0]
    stack = widget.layout.widgets[1]
    assert header.object_name == main_window.PANEL_HEADER_OBJECT_NAME
    assert stack.object_name == main_window.PANEL_BODY_STACK_OBJECT_NAME
    _find(header, main_window.DOCUMENTATION_BUTTON_OBJECT_NAME)
    _find(header, main_window.REPORT_BUG_BUTTON_OBJECT_NAME)
    _find(header, main_window.CHECK_FOR_UPDATES_BUTTON_OBJECT_NAME)


def test_main_widget_panel_header_uses_installed_version_by_default():
    widget = main_window.build_main_widget(FakeQtWidgets)
    header = _find(widget, main_window.PANEL_HEADER_OBJECT_NAME)
    title = _find(header, main_window.PANEL_HEADER_TITLE_OBJECT_NAME)

    assert f"v{__version__}" in title.text
