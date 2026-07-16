from __future__ import annotations

from typing import Any

from tests.unit.test_maya_summary_header import FakePushButton, FakeQtWidgets, FakeWidget, _find

from pipeline_inspector.integrations.readiness.engine import ReadinessCheckResult
from pipeline_inspector.ui import main_window
from pipeline_inspector.ui.readiness_tab import (
    READINESS_RESULTS_TABLE_OBJECT_NAME,
    READINESS_RUN_BUTTON_OBJECT_NAME,
    READINESS_SEND_SUPPORT_BUTTON_OBJECT_NAME,
    READINESS_TAB_OBJECT_NAME,
    ReadinessTabState,
    build_readiness_tab,
    update_readiness_tab,
)


class FakeSignal:
    def __init__(self) -> None:
        self._callbacks: list[Any] = []

    def connect(self, callback: Any) -> None:
        self._callbacks.append(callback)


class FakeReadinessPushButton(FakePushButton):
    def __init__(self, text: str = "") -> None:
        super().__init__(text)
        self.clicked = FakeSignal()
        self.enabled = True

    def setEnabled(self, enabled: bool) -> None:
        self.enabled = enabled


class FakeReadinessTableWidget(FakeWidget):
    def __init__(self, rows: int = 0, columns: int = 0) -> None:
        super().__init__()
        self.row_count = rows
        self.column_count = columns
        self.headers: list[str] = []
        self.items: dict[tuple[int, int], object] = {}

    def setColumnCount(self, count: int) -> None:
        self.column_count = count

    def setHorizontalHeaderLabels(self, headers: list[str]) -> None:
        self.headers = headers

    def setRowCount(self, count: int) -> None:
        self.row_count = count

    def setItem(self, row: int, column: int, item: object) -> None:
        self.items[(row, column)] = item


class FakeReadinessTableWidgetItem:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeReadinessQtWidgets(FakeQtWidgets):
    QPushButton = FakeReadinessPushButton
    QTableWidget = FakeReadinessTableWidget
    QTableWidgetItem = FakeReadinessTableWidgetItem
    QAbstractItemView = type("FakeAbstractItemView", (), {"NoEditTriggers": 0})
    QGridLayout = FakeQtWidgets.QGridLayout


def test_build_main_widget_includes_readiness_tab():
    widget = main_window.build_main_widget(FakeQtWidgets)
    tabs = _find(widget, main_window.TAB_WIDGET_OBJECT_NAME)
    tab_titles = [title for title, _widget in tabs.tabs]
    assert "Readiness" in tab_titles
    readiness_widget = next(widget for title, widget in tabs.tabs if title == "Readiness")
    assert readiness_widget.object_name == READINESS_TAB_OBJECT_NAME


def test_build_readiness_tab_exposes_run_and_send_actions():
    tab = build_readiness_tab(FakeReadinessQtWidgets)

    assert _find(tab, READINESS_RUN_BUTTON_OBJECT_NAME) is not None
    send_support = _find(tab, READINESS_SEND_SUPPORT_BUTTON_OBJECT_NAME)
    assert send_support is not None
    assert send_support.enabled is False


def test_update_readiness_tab_enables_send_buttons_after_failed_check():
    tab = build_readiness_tab(FakeReadinessQtWidgets)
    state = ReadinessTabState(
        summary="1 of 1 readiness checks failed.",
        status_message="1 of 1 readiness checks failed.",
        results=(
            ReadinessCheckResult(
                check_id="env_var:PIPELINE_ROOT",
                category="env_var",
                label="Environment variable PIPELINE_ROOT",
                ok=False,
                message="Required environment variable 'PIPELINE_ROOT' is not set.",
            ),
        ),
        checks_configured=True,
        all_passed=False,
        can_send_report=True,
    )

    update_readiness_tab(tab, FakeReadinessQtWidgets, state)

    table = _find(tab, READINESS_RESULTS_TABLE_OBJECT_NAME)
    assert list(table.headers) == [
        "Status",
        "Check",
        "Description",
        "Details",
    ]
    assert table.items[(0, 2)].text == (
        "Required environment variable 'PIPELINE_ROOT' is not set."
    )
    assert table.items[(0, 3)].text == "Environment variable · env_var:PIPELINE_ROOT"
    assert _find(tab, READINESS_SEND_SUPPORT_BUTTON_OBJECT_NAME).enabled is True
