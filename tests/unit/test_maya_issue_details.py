from __future__ import annotations

from typing import Any, Optional

from shader_health.ui import main_window


class FakeWidget:
    def __init__(self) -> None:
        self.object_name: Optional[str] = None
        self.children: list[Any] = []
        self.layout: Optional[FakeVBoxLayout] = None

    def setObjectName(self, object_name: str) -> None:
        self.object_name = object_name


class FakeLabel(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.text = text
        self.word_wrap = False

    def setWordWrap(self, enabled: bool) -> None:
        self.word_wrap = enabled


class FakePushButton(FakeLabel):
    def __init__(self, text: str = "") -> None:
        super().__init__(text)
        self.enabled = True
        self.tooltip = ""

    def setEnabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def setToolTip(self, text: str) -> None:
        self.tooltip = text


class FakeComboBox(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[str] = []
        self.current_text = ""
        self.tooltip = ""

    def addItems(self, items: list[str]) -> None:
        self.items.extend(items)

    def setCurrentText(self, text: str) -> None:
        self.current_text = text

    def setToolTip(self, text: str) -> None:
        self.tooltip = text


class FakeTableWidgetItem:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeTableWidget(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.column_count = 0
        self.row_count = 0
        self.headers: list[str] = []
        self.sorting_enabled = False
        self.items: dict[tuple[int, int], FakeTableWidgetItem] = {}

    def setColumnCount(self, count: int) -> None:
        self.column_count = count

    def setRowCount(self, count: int) -> None:
        self.row_count = count

    def setHorizontalHeaderLabels(self, headers: list[str]) -> None:
        self.headers = headers

    def setSortingEnabled(self, enabled: bool) -> None:
        self.sorting_enabled = enabled

    def setItem(self, row: int, column: int, item: FakeTableWidgetItem) -> None:
        self.items[(row, column)] = item


class FakeVBoxLayout:
    def __init__(self, parent: FakeWidget) -> None:
        self.parent = parent
        self.parent.layout = self
        self.widgets: list[Any] = []
        self.stretches: list[int] = []

    def setContentsMargins(self, left: int, top: int, right: int, bottom: int) -> None:
        _ = (left, top, right, bottom)

    def setSpacing(self, spacing: int) -> None:
        _ = spacing

    def addWidget(self, widget: Any, stretch: Optional[int] = None) -> None:
        self.widgets.append(widget)
        self.parent.children.append(widget)
        _ = stretch

    def addStretch(self, stretch: int) -> None:
        self.stretches.append(stretch)


class FakeHBoxLayout(FakeVBoxLayout):
    pass


class FakeQtWidgets:
    QWidget = FakeWidget
    QLabel = FakeLabel
    QPushButton = FakePushButton
    QComboBox = FakeComboBox
    QTableWidget = FakeTableWidget
    QTableWidgetItem = FakeTableWidgetItem
    QVBoxLayout = FakeVBoxLayout
    QHBoxLayout = FakeHBoxLayout


def test_issue_details_defaults_show_empty_selection_state():
    details_panel = main_window.build_issue_details_panel(FakeQtWidgets)

    assert _find(details_panel, main_window.DETAILS_MESSAGE_LABEL_OBJECT_NAME).text == (
        "Message: No issue selected"
    )
    assert _find(details_panel, main_window.DETAILS_WHY_LABEL_OBJECT_NAME).text == (
        "Why: Select an issue row to inspect why it failed."
    )
    assert _find(details_panel, main_window.DETAILS_VALUES_LABEL_OBJECT_NAME).text == (
        "Current: N/A   Expected: N/A"
    )
    assert _find(details_panel, main_window.DETAILS_GRAPH_TRACE_LABEL_OBJECT_NAME).text == (
        "Graph Trace: N/A"
    )
    assert _find(details_panel, main_window.DETAILS_FIX_LABEL_OBJECT_NAME).text == (
        "Fix Available: NO   No safe fix selected."
    )


def test_issue_details_show_selected_issue_explainability_fields():
    state = main_window.IssueDetailsState(
        message="Missing texture file",
        why="Render farm cannot resolve the texture dependency.",
        current_value="Z:/missing/hero_albedo.tx",
        expected_value="$ASSET_ROOT/textures/hero_albedo.tx",
        graph_trace="shadingEngine1 -> heroMaterial -> file1.fileTextureName",
        fix_available=True,
        fix_description="Can relink to approved asset root path.",
    )

    details_panel = main_window.build_issue_details_panel(FakeQtWidgets, state=state)

    assert _find(details_panel, main_window.DETAILS_MESSAGE_LABEL_OBJECT_NAME).text == (
        "Message: Missing texture file"
    )
    assert _find(details_panel, main_window.DETAILS_WHY_LABEL_OBJECT_NAME).text == (
        "Why: Render farm cannot resolve the texture dependency."
    )
    assert _find(details_panel, main_window.DETAILS_VALUES_LABEL_OBJECT_NAME).text == (
        "Current: Z:/missing/hero_albedo.tx   "
        "Expected: $ASSET_ROOT/textures/hero_albedo.tx"
    )
    assert _find(details_panel, main_window.DETAILS_GRAPH_TRACE_LABEL_OBJECT_NAME).text == (
        "Graph Trace: shadingEngine1 -> heroMaterial -> file1.fileTextureName"
    )
    assert _find(details_panel, main_window.DETAILS_FIX_LABEL_OBJECT_NAME).text == (
        "Fix Available: YES   Can relink to approved asset root path."
    )


def test_issue_details_labels_are_word_wrapped():
    details_panel = main_window.build_issue_details_panel(FakeQtWidgets)

    assert _find(details_panel, main_window.DETAILS_MESSAGE_LABEL_OBJECT_NAME).word_wrap is True
    assert _find(details_panel, main_window.DETAILS_WHY_LABEL_OBJECT_NAME).word_wrap is True
    assert _find(details_panel, main_window.DETAILS_GRAPH_TRACE_LABEL_OBJECT_NAME).word_wrap is True
    assert _find(details_panel, main_window.DETAILS_FIX_LABEL_OBJECT_NAME).word_wrap is True


def test_main_widget_contains_issue_details_panel():
    widget = main_window.build_main_widget(FakeQtWidgets)

    details_panel = _find(widget, main_window.DETAILS_PANEL_OBJECT_NAME)

    assert details_panel.object_name == main_window.DETAILS_PANEL_OBJECT_NAME


def _find(widget: Any, object_name: str) -> Any:
    stack = [widget]
    while stack:
        current = stack.pop()
        if getattr(current, "object_name", None) == object_name:
            return current
        stack.extend(getattr(current, "children", []))
    raise AssertionError(f"Could not find object named {object_name!r}")
