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
        self.style_sheet = ""

    def setWordWrap(self, enabled: bool) -> None:
        self.word_wrap = enabled

    def setStyleSheet(self, style: str) -> None:
        self.style_sheet = style


class FakeComboBox(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[tuple[str, str]] = []
        self.current_index = 0
        self.tooltip = ""

    def addItem(self, text: str, user_data: str = "") -> None:
        self.items.append((text, user_data or text))

    def addItems(self, items: list[str]) -> None:
        for item in items:
            self.addItem(item)

    def setCurrentText(self, text: str) -> None:
        for index, (label, _data) in enumerate(self.items):
            if label == text:
                self.current_index = index
                return

    def setCurrentIndex(self, index: int) -> None:
        self.current_index = index

    def currentText(self) -> str:
        if not self.items:
            return ""
        return self.items[self.current_index][0]

    def currentData(self):
        if not self.items:
            return None
        return self.items[self.current_index][1]

    def findData(self, data: str) -> int:
        for index, (_label, item_data) in enumerate(self.items):
            if item_data == data:
                return index
        return -1

    def setToolTip(self, text: str) -> None:
        self.tooltip = text


class FakePushButton(FakeLabel):
    def __init__(self, text: str = "") -> None:
        super().__init__(text)
        self.enabled = True
        self.tooltip = ""

    def setEnabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def setToolTip(self, text: str) -> None:
        self.tooltip = text


class FakeCheckBox(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.checked = False

    def setChecked(self, checked: bool) -> None:
        self.checked = checked

    def setToolTip(self, _text: str) -> None:
        return


class FakeTableWidget(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.column_count = 0
        self.row_count = 0
        self.headers: list[str] = []
        self.sorting_enabled = False

    def setColumnCount(self, count: int) -> None:
        self.column_count = count

    def setRowCount(self, count: int) -> None:
        self.row_count = count

    def setHorizontalHeaderLabels(self, headers: list[str]) -> None:
        self.headers = headers

    def setSortingEnabled(self, enabled: bool) -> None:
        self.sorting_enabled = enabled


class FakeTableWidgetItem:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeVBoxLayout:
    def __init__(self, parent: FakeWidget) -> None:
        self.parent = parent
        self.parent.layout = self
        self.margins: Optional[tuple[int, int, int, int]] = None
        self.spacing: Optional[int] = None
        self.widgets: list[Any] = []
        self.stretches: list[int] = []

    def setContentsMargins(self, left: int, top: int, right: int, bottom: int) -> None:
        self.margins = (left, top, right, bottom)

    def setSpacing(self, spacing: int) -> None:
        self.spacing = spacing

    def addWidget(self, widget: Any, stretch: Optional[int] = None) -> None:
        self.widgets.append(widget)
        self.parent.children.append(widget)
        _ = stretch

    def addStretch(self, stretch: int) -> None:
        self.stretches.append(stretch)


class FakeHBoxLayout(FakeVBoxLayout):
    pass


class FakeGridLayout(FakeVBoxLayout):
    def addWidget(self, widget: Any, row: int = 0, column: int = 0, *_args: Any) -> None:
        self.parent.children.append(widget)
        _ = (row, column)


class FakeTabWidget(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.tabs: list[tuple[str, FakeWidget]] = []

    def addTab(self, widget: FakeWidget, title: str) -> None:
        self.tabs.append((title, widget))
        self.children.append(widget)


class FakeQtWidgets:
    QWidget = FakeWidget
    QLabel = FakeLabel
    QComboBox = FakeComboBox
    QPushButton = FakePushButton
    QCheckBox = FakeCheckBox
    QTableWidget = FakeTableWidget
    QTableWidgetItem = FakeTableWidgetItem
    QVBoxLayout = FakeVBoxLayout
    QHBoxLayout = FakeHBoxLayout
    QGridLayout = FakeGridLayout
    QTabWidget = FakeTabWidget


def test_summary_header_defaults_show_score_counts_blocks_and_profile_dropdown():
    header = main_window.build_summary_header(FakeQtWidgets)

    assert _find(header, main_window.HEALTH_SCORE_LABEL_OBJECT_NAME).text == "Health: 100 / 100"
    assert (
        _find(header, main_window.SEVERITY_COUNTS_LABEL_OBJECT_NAME).text
        == "Critical: 0   Error: 0   Warning: 0   Info: 0"
    )
    assert (
        _find(header, main_window.BLOCK_STATUS_LABEL_OBJECT_NAME).text
        == "Publish Block: NO   Deadline Block: NO"
    )
    profile_dropdown = _find(header, main_window.PROFILE_DROPDOWN_OBJECT_NAME)
    asset_class_dropdown = _find(header, main_window.ASSET_CLASS_DROPDOWN_OBJECT_NAME)
    workflow_ids = [option.profile_id for option in main_window.DEFAULT_WORKFLOW_PROFILE_OPTIONS]
    assert [item[1] for item in profile_dropdown.items] == workflow_ids
    assert profile_dropdown.currentText() == "Artist Relaxed"
    assert asset_class_dropdown.currentText() == main_window.ASSET_CLASS_NONE_LABEL


def test_summary_header_formats_failed_blocking_state():
    state = main_window.SummaryHeaderState(
        health_score=42,
        critical_count=2,
        error_count=4,
        warning_count=7,
        info_count=11,
        block_publish=True,
        block_deadline=True,
        profile_id="deadline_critical",
    )

    header = main_window.build_summary_header(FakeQtWidgets, state=state)

    assert _find(header, main_window.HEALTH_SCORE_LABEL_OBJECT_NAME).text == "Health: 42 / 100"
    assert (
        _find(header, main_window.SEVERITY_COUNTS_LABEL_OBJECT_NAME).text
        == "Critical: 2   Error: 4   Warning: 7   Info: 11"
    )
    assert (
        _find(header, main_window.BLOCK_STATUS_LABEL_OBJECT_NAME).text
        == "Publish Block: YES   Deadline Block: YES"
    )
    profile_dropdown = _find(header, main_window.PROFILE_DROPDOWN_OBJECT_NAME)
    assert profile_dropdown.currentData() == "deadline_critical"


def test_summary_header_accepts_custom_profile_options():
    from shader_health.maya.validation_pipeline import ProfileOption

    state = main_window.SummaryHeaderState(profile_id="publish_strict")

    header = main_window.build_summary_header(
        FakeQtWidgets,
        state=state,
        workflow_options=(
            ProfileOption("artist_relaxed", "Artist Relaxed"),
            ProfileOption("publish_strict", "Publish Strict"),
        ),
    )

    profile_dropdown = _find(header, main_window.PROFILE_DROPDOWN_OBJECT_NAME)
    assert [item[1] for item in profile_dropdown.items] == ["artist_relaxed", "publish_strict"]
    assert profile_dropdown.currentData() == "publish_strict"


def test_main_widget_contains_tabbed_shell():
    widget = main_window.build_main_widget(FakeQtWidgets)

    tabs = _find(widget, main_window.TAB_WIDGET_OBJECT_NAME)
    assert tabs.object_name == main_window.TAB_WIDGET_OBJECT_NAME
    assert [title for title, _tab in tabs.tabs] == [
        "Validate",
        "Waivers",
        "Fixes",
        "Reports",
    ]


def test_panel_header_includes_version():
    header = main_window.build_panel_header(FakeQtWidgets, version="0.3.0")

    assert "Maya Shader Health Inspector" in header.text
    assert "v0.3.0" in header.text


def _find(widget: Any, object_name: str) -> Any:
    stack = [widget]
    while stack:
        current = stack.pop()
        if getattr(current, "object_name", None) == object_name:
            return current
        stack.extend(getattr(current, "children", []))
    raise AssertionError(f"Could not find object named {object_name!r}")
