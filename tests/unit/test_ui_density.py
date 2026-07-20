from __future__ import annotations

from typing import Any, Optional

from tests.unit.test_maya_summary_header import FakePushButton, FakeQtWidgets, _find

from pipeline_inspector.ui import main_window
from pipeline_inspector.ui.ui_density_tokens import (
    COMPACT_PANEL_MAX_WIDTH,
    ISSUES_TABLE_ISSUE_COLUMN_INDEX,
    ISSUES_TABLE_MATERIAL_COLUMN_INDEX,
    ISSUES_TABLE_NODE_COLUMN_INDEX,
    ISSUES_TABLE_OWNER_COLUMN_INDEX,
    ISSUES_TABLE_RULE_COLUMN_INDEX,
    density_tokens,
    validate_tab_chrome_footprint,
)
from pipeline_inspector.ui.user_preferences_ui import apply_user_preferences_to_panel
from pipeline_inspector.user_config import UserPreferences


def _find_all(widget: Any, object_name: str) -> list[Any]:
    matches: list[Any] = []
    stack = [widget]
    while stack:
        current = stack.pop()
        if getattr(current, "object_name", None) == object_name:
            matches.append(current)
        stack.extend(getattr(current, "children", []))
    return matches


class FakeQAction:
    def __init__(self, label: str, callback: Any = None) -> None:
        self.label = label
        self.callback = callback
        self.triggered = FakeSignal()

    def connect_callback(self) -> None:
        if self.callback is not None:
            self.triggered.connect(self.callback)


class FakeQToolButton(FakePushButton):
    InstantPopup = "instant_popup"
    MenuButtonPopup = "menu_button_popup"

    def __init__(self, text: str = "") -> None:
        super().__init__(text)
        self.popup_mode: Any = None
        self.menu: Any = None

    def setPopupMode(self, mode: Any) -> None:
        self.popup_mode = mode

    def setMenu(self, menu: Any) -> None:
        self.menu = menu


class FakeQMenu:
    def __init__(self, parent: Any = None) -> None:
        self.parent = parent
        self.actions: list[FakeQAction] = []

    def addAction(self, label: str, callback: Any = None) -> FakeQAction:
        action = FakeQAction(label, callback)
        action.connect_callback()
        self.actions.append(action)
        return action

    def popup(self, *_args: Any) -> None:
        return

    def exec_(self) -> None:
        return


class FakeVerticalHeader:
    def __init__(self) -> None:
        self.default_section_size: Optional[int] = None

    def setDefaultSectionSize(self, size: int) -> None:
        self.default_section_size = size


class FakeSignal:
    def __init__(self) -> None:
        self.handlers: list[Any] = []

    def connect(self, handler: Any) -> None:
        self.handlers.append(handler)

    def emit(self, *_args: Any) -> None:
        for handler in self.handlers:
            handler()


class DensityFakeTableWidget(FakeQtWidgets.QTableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.hidden_columns: dict[int, bool] = {}
        self.vertical_header = FakeVerticalHeader()
        self.maximum_height: int | None = None

    def setColumnHidden(self, column_index: int, hidden: bool) -> None:
        self.hidden_columns[column_index] = hidden

    def verticalHeader(self) -> FakeVerticalHeader:
        return self.vertical_header

    def columnCount(self) -> int:
        return self.column_count

    def setMaximumHeight(self, height: int) -> None:
        self.maximum_height = height


class DensityFakeQtWidgets(FakeQtWidgets):
    QMenu = FakeQMenu
    QToolButton = FakeQToolButton
    QTableWidget = DensityFakeTableWidget


def test_validate_tab_chrome_footprint_compact_is_at_least_half_of_comfortable():
    comfortable = validate_tab_chrome_footprint("comfortable")
    compact = validate_tab_chrome_footprint("compact")

    assert comfortable > 0
    assert compact <= comfortable // 2


def test_apply_ui_density_compact_hides_secondary_panel_header_actions():
    widget = main_window.build_main_widget(DensityFakeQtWidgets)

    apply_user_preferences_to_panel(
        widget,
        DensityFakeQtWidgets,
        UserPreferences(ui_density="compact"),
    )

    overflow = _find(widget, main_window.PANEL_HEADER_OVERFLOW_BUTTON_OBJECT_NAME)
    docs = _find(widget, main_window.DOCUMENTATION_BUTTON_OBJECT_NAME)
    report_bug = _find(widget, main_window.REPORT_BUG_BUTTON_OBJECT_NAME)
    updates = _find(widget, main_window.CHECK_FOR_UPDATES_BUTTON_OBJECT_NAME)

    assert overflow.visible is True
    assert docs.visible is False
    assert report_bug.visible is False
    assert updates.visible is False
    assert len(overflow.menu.actions) == 3


def test_apply_ui_density_compact_collapses_validate_action_bar_and_summary_context():
    widget = main_window.build_main_widget(DensityFakeQtWidgets)

    apply_user_preferences_to_panel(
        widget,
        DensityFakeQtWidgets,
        UserPreferences(ui_density="compact"),
    )

    context_row = _find(widget, main_window.SUMMARY_CONTEXT_ROW_OBJECT_NAME)
    pipeline = _find(widget, main_window.VALIDATE_PIPELINE_ACTIONS_OBJECT_NAME)
    triage = _find(widget, main_window.VALIDATE_TRIAGE_ACTIONS_OBJECT_NAME)
    overflow = _find(widget, main_window.VALIDATE_ACTION_OVERFLOW_BUTTON_OBJECT_NAME)
    publish_label = _find(widget, main_window.PUBLISH_BLOCK_LABEL_OBJECT_NAME)

    assert context_row.visible is False
    assert pipeline.visible is False
    assert triage.visible is False
    assert overflow.visible is True
    assert publish_label.visible is False


def test_apply_ui_density_compact_shows_severity_and_material_columns_only():
    widget = main_window.build_main_widget(DensityFakeQtWidgets)

    apply_user_preferences_to_panel(
        widget,
        DensityFakeQtWidgets,
        UserPreferences(ui_density="compact"),
    )

    table = _find(widget, main_window.ISSUES_TABLE_OBJECT_NAME)

    assert table.hidden_columns.get(0, False) is False
    assert table.hidden_columns.get(ISSUES_TABLE_MATERIAL_COLUMN_INDEX, False) is False
    assert table.hidden_columns[ISSUES_TABLE_NODE_COLUMN_INDEX] is True
    assert table.hidden_columns[ISSUES_TABLE_ISSUE_COLUMN_INDEX] is True
    assert table.hidden_columns[ISSUES_TABLE_OWNER_COLUMN_INDEX] is True
    assert table.hidden_columns[ISSUES_TABLE_RULE_COLUMN_INDEX] is True


def test_apply_ui_density_compact_hides_wide_issue_columns_and_shortens_rows():
    widget = main_window.build_main_widget(DensityFakeQtWidgets)

    apply_user_preferences_to_panel(
        widget,
        DensityFakeQtWidgets,
        UserPreferences(ui_density="compact"),
    )

    table = _find(widget, main_window.ISSUES_TABLE_OBJECT_NAME)
    tokens = density_tokens("compact")

    assert table.hidden_columns[ISSUES_TABLE_NODE_COLUMN_INDEX] is True
    assert table.hidden_columns[ISSUES_TABLE_ISSUE_COLUMN_INDEX] is True
    assert table.hidden_columns[ISSUES_TABLE_OWNER_COLUMN_INDEX] is True
    assert table.hidden_columns[ISSUES_TABLE_RULE_COLUMN_INDEX] is True
    assert table.vertical_header.default_section_size == tokens.table_row_height


def test_severity_count_value_from_label_ignores_color_hex_digits():
    from tests.unit.test_maya_summary_header import FakeLabel

    critical_label = FakeLabel('Critical: <span style="color:#e74c3c;">0</span>')
    error_label = FakeLabel('<span style="color:#e67e22; font-weight: bold;">5</span>')

    assert main_window._severity_count_value_from_label(critical_label) == 0
    assert main_window._severity_count_value_from_label(error_label) == 5


def test_apply_ui_density_compact_keeps_zero_severity_counts_on_preset_switch():
    widget = main_window.build_main_widget(DensityFakeQtWidgets)

    apply_user_preferences_to_panel(
        widget,
        DensityFakeQtWidgets,
        UserPreferences(ui_density="comfortable"),
    )
    apply_user_preferences_to_panel(
        widget,
        DensityFakeQtWidgets,
        UserPreferences(ui_density="compact"),
    )

    critical = _find(widget, main_window.CRITICAL_COUNT_LABEL_OBJECT_NAME)
    error = _find(widget, main_window.ERROR_COUNT_LABEL_OBJECT_NAME)

    assert critical.text == '<span style="color:#e74c3c; font-weight: bold;">0</span>'
    assert error.text == '<span style="color:#e67e22; font-weight: bold;">0</span>'


def test_apply_ui_density_compact_uses_colored_severity_numbers_only():
    widget = main_window.build_main_widget(DensityFakeQtWidgets)

    apply_user_preferences_to_panel(
        widget,
        DensityFakeQtWidgets,
        UserPreferences(ui_density="compact"),
    )

    main_window.update_severity_count_indicators(
        widget,
        DensityFakeQtWidgets,
        critical_count=3,
        error_count=5,
        warning_count=2,
        info_count=1,
    )

    critical = _find(widget, main_window.CRITICAL_COUNT_LABEL_OBJECT_NAME)
    error = _find(widget, main_window.ERROR_COUNT_LABEL_OBJECT_NAME)

    assert critical.text == '<span style="color:#e74c3c; font-weight: bold;">3</span>'
    assert error.text == '<span style="color:#e67e22; font-weight: bold;">5</span>'
    assert "Critical" not in critical.text
    assert "Error" not in error.text


def test_apply_ui_density_compact_uses_short_export_button_labels():
    widget = main_window.build_main_widget(DensityFakeQtWidgets)

    apply_user_preferences_to_panel(
        widget,
        DensityFakeQtWidgets,
        UserPreferences(ui_density="compact"),
    )

    json_button = _find(widget, main_window.EXPORT_JSON_BUTTON_OBJECT_NAME)
    tracker_button = _find(widget, main_window.EXPORT_SEND_TO_TRACKER_BUTTON_OBJECT_NAME)

    assert json_button.text == "JSON Report"
    assert tracker_button.text == "Send Tracker"


def test_apply_ui_density_compact_clamps_panel_width_and_hides_extra_filters():
    widget = main_window.build_main_widget(DensityFakeQtWidgets)

    apply_user_preferences_to_panel(
        widget,
        DensityFakeQtWidgets,
        UserPreferences(ui_density="compact"),
    )

    view_filter = _find(widget, main_window.ISSUES_VIEW_FILTER_OBJECT_NAME)
    sort_filter = _find(widget, main_window.ISSUES_SORT_DROPDOWN_OBJECT_NAME)

    assert widget.maximum_width == COMPACT_PANEL_MAX_WIDTH
    assert view_filter.visible is False
    assert sort_filter.visible is False


def test_apply_ui_density_compact_stacks_details_below_short_issues_table():
    widget = main_window.build_main_widget(DensityFakeQtWidgets)

    apply_user_preferences_to_panel(
        widget,
        DensityFakeQtWidgets,
        UserPreferences(ui_density="compact"),
    )

    splitter = _find(widget, main_window.VALIDATE_ISSUES_SPLITTER_OBJECT_NAME)
    details = _find(widget, main_window.DETAILS_PANEL_OBJECT_NAME)
    tokens = density_tokens("compact")

    assert splitter.orientation == DensityFakeQtWidgets.Qt.Vertical
    assert splitter.sizes == list(tokens.issues_pane_sizes or ())
    assert details.minimum_width == 0


def test_apply_ui_density_compact_omits_make_waive_filter_button_and_adds_it_to_more_menu():
    from pipeline_inspector.ui.waiver_manager import (
        VALIDATE_MAKE_WAIVE_BUTTON_OBJECT_NAME,
        WaiverManagerCallbacks,
    )

    widget = main_window.build_main_widget(
        DensityFakeQtWidgets,
        waiver_callbacks=WaiverManagerCallbacks(
            on_make_waive=lambda: None,
            on_report_supervisor=lambda: None,
        ),
        user_config=UserPreferences(ui_density="compact"),
    )

    apply_user_preferences_to_panel(
        widget,
        DensityFakeQtWidgets,
        UserPreferences(ui_density="compact"),
    )

    make_waive_buttons = _find_all(widget, VALIDATE_MAKE_WAIVE_BUTTON_OBJECT_NAME)
    overflow = _find(widget, main_window.VALIDATE_ACTION_OVERFLOW_BUTTON_OBJECT_NAME)

    assert make_waive_buttons == []
    assert any(action.label == "Make Waive" for action in overflow.menu.actions)
    assert any(action.label == "Report Supervisor" for action in overflow.menu.actions)


def test_validate_filters_row_has_single_make_waive_button():
    from pipeline_inspector.ui.waiver_manager import (
        VALIDATE_MAKE_WAIVE_BUTTON_OBJECT_NAME,
        WAIVER_MAKE_WAIVE_BUTTON_OBJECT_NAME,
        WaiverManagerCallbacks,
    )

    widget = main_window.build_main_widget(
        DensityFakeQtWidgets,
        waiver_callbacks=WaiverManagerCallbacks(
            on_make_waive=lambda: None,
            on_report_supervisor=lambda: None,
        ),
        user_config=UserPreferences(ui_density="comfortable"),
    )

    validate_buttons = _find_all(widget, VALIDATE_MAKE_WAIVE_BUTTON_OBJECT_NAME)
    waiver_buttons = _find_all(widget, WAIVER_MAKE_WAIVE_BUTTON_OBJECT_NAME)

    assert len(validate_buttons) == 1
    assert len(waiver_buttons) == 1
    assert validate_buttons[0].visible is True


def test_apply_ui_density_compact_tightens_panel_header_gaps():
    widget = main_window.build_main_widget(DensityFakeQtWidgets)
    tokens = density_tokens("compact")

    apply_user_preferences_to_panel(
        widget,
        DensityFakeQtWidgets,
        UserPreferences(ui_density="compact"),
    )

    header = _find(widget, main_window.PANEL_HEADER_OBJECT_NAME)
    tabs = _find(widget, main_window.TAB_WIDGET_OBJECT_NAME)

    assert header.maximum_height == tokens.panel_header_max_height
    assert header.size_policy == (
        DensityFakeQtWidgets.QSizePolicy.Preferred,
        DensityFakeQtWidgets.QSizePolicy.Fixed,
    )
    assert tokens.panel_header_chrome_stylesheet in header.style_sheet
    assert tokens.main_tab_chrome_stylesheet in tabs.style_sheet
    assert tabs.document_mode is True


def test_apply_ui_density_comfortable_tightens_panel_header_gaps():
    widget = main_window.build_main_widget(DensityFakeQtWidgets)
    tokens = density_tokens("comfortable")

    apply_user_preferences_to_panel(
        widget,
        DensityFakeQtWidgets,
        UserPreferences(ui_density="comfortable"),
    )

    header = _find(widget, main_window.PANEL_HEADER_OBJECT_NAME)
    tabs = _find(widget, main_window.TAB_WIDGET_OBJECT_NAME)

    assert widget.layout.margins == (8, 2, 8, 8)
    assert widget.layout.spacing == 2
    assert header.maximum_height == tokens.panel_header_max_height
    assert tokens.panel_header_chrome_stylesheet in header.style_sheet
    assert tokens.main_tab_chrome_stylesheet in tabs.style_sheet
    assert tabs.document_mode is True


def test_apply_ui_density_comfortable_restores_horizontal_issues_pane():
    widget = main_window.build_main_widget(DensityFakeQtWidgets)

    apply_user_preferences_to_panel(
        widget,
        DensityFakeQtWidgets,
        UserPreferences(ui_density="compact"),
    )
    apply_user_preferences_to_panel(
        widget,
        DensityFakeQtWidgets,
        UserPreferences(ui_density="comfortable"),
    )

    splitter = _find(widget, main_window.VALIDATE_ISSUES_SPLITTER_OBJECT_NAME)
    details = _find(widget, main_window.DETAILS_PANEL_OBJECT_NAME)

    assert splitter.orientation == DensityFakeQtWidgets.Qt.Horizontal
    assert details.minimum_width == main_window.DETAILS_PANEL_MIN_WIDTH


def test_apply_ui_density_comfortable_restores_full_validate_chrome():
    widget = main_window.build_main_widget(DensityFakeQtWidgets)

    apply_user_preferences_to_panel(
        widget,
        DensityFakeQtWidgets,
        UserPreferences(ui_density="compact"),
    )
    apply_user_preferences_to_panel(
        widget,
        DensityFakeQtWidgets,
        UserPreferences(ui_density="comfortable"),
    )

    context_row = _find(widget, main_window.SUMMARY_CONTEXT_ROW_OBJECT_NAME)
    docs = _find(widget, main_window.DOCUMENTATION_BUTTON_OBJECT_NAME)
    pipeline = _find(widget, main_window.VALIDATE_PIPELINE_ACTIONS_OBJECT_NAME)
    table = _find(widget, main_window.ISSUES_TABLE_OBJECT_NAME)

    assert context_row.visible is True
    assert docs.visible is True
    assert pipeline.visible is True
    assert table.hidden_columns.get(ISSUES_TABLE_OWNER_COLUMN_INDEX, False) is False
