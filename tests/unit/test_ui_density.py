from __future__ import annotations

from typing import Any, Optional

from tests.unit.test_maya_summary_header import FakePushButton, FakeQtWidgets, _find

from pipeline_inspector.ui import main_window
from pipeline_inspector.ui.ui_density_tokens import (
    ISSUES_TABLE_OWNER_COLUMN_INDEX,
    ISSUES_TABLE_RULE_COLUMN_INDEX,
    density_tokens,
    validate_tab_chrome_footprint,
)
from pipeline_inspector.ui.user_preferences_ui import apply_user_preferences_to_panel
from pipeline_inspector.user_config import UserPreferences


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


def test_apply_ui_density_compact_hides_low_priority_issue_columns_and_shortens_rows():
    widget = main_window.build_main_widget(DensityFakeQtWidgets)

    apply_user_preferences_to_panel(
        widget,
        DensityFakeQtWidgets,
        UserPreferences(ui_density="compact"),
    )

    table = _find(widget, main_window.ISSUES_TABLE_OBJECT_NAME)
    tokens = density_tokens("compact")

    assert table.hidden_columns[ISSUES_TABLE_OWNER_COLUMN_INDEX] is True
    assert table.hidden_columns[ISSUES_TABLE_RULE_COLUMN_INDEX] is True
    assert table.vertical_header.default_section_size == tokens.table_row_height


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
