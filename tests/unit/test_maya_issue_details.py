from __future__ import annotations

from typing import Any, Optional

from shader_health.ui import main_window


class FakeWidget:
    def __init__(self) -> None:
        self.object_name: Optional[str] = None
        self.children: list[Any] = []
        self.layout: Optional[FakeVBoxLayout] = None
        self.size_policy: Optional[tuple[Any, Any]] = None
        self.minimum_width: Optional[int] = None
        self.visible = True

    def setObjectName(self, object_name: str) -> None:
        self.object_name = object_name

    def setSizePolicy(self, horizontal: Any, vertical: Any) -> None:
        self.size_policy = (horizontal, vertical)

    def setMinimumWidth(self, width: int) -> None:
        self.minimum_width = width

    def setVisible(self, visible: bool) -> None:
        self.visible = visible

    def setLayout(self, layout: Any) -> None:
        self.layout = layout
        for widget in getattr(layout, "widgets", []):
            if widget not in self.children:
                self.children.append(widget)


class FakePlainTextEdit(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.value = text
        self.plainTextChanged = FakeSignal()

    def setPlainText(self, text: str) -> None:
        self.value = text

    def toPlainText(self) -> str:
        return self.value

    def setPlaceholderText(self, text: str) -> None:
        _ = text

    def setToolTip(self, text: str) -> None:
        _ = text


class FakeLineEdit(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.value = text

    def setText(self, text: str) -> None:
        self.value = text

    def text(self) -> str:
        return self.value

    def setPlaceholderText(self, text: str) -> None:
        _ = text

    def setToolTip(self, text: str) -> None:
        _ = text

    @property
    def editingFinished(self) -> FakeSignal:
        return FakeSignal()


class FakeSignal:
    def __init__(self) -> None:
        self.handlers: list[Any] = []

    def connect(self, handler: Any) -> None:
        self.handlers.append(handler)


class FakeLabel(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.text = text
        self.word_wrap = False

    def setWordWrap(self, enabled: bool) -> None:
        self.word_wrap = enabled

    def setSizePolicy(self, horizontal: Any, vertical: Any) -> None:
        _ = (horizontal, vertical)


class FakePushButton(FakeLabel):
    def __init__(self, text: str = "") -> None:
        super().__init__(text)
        self.enabled = True
        self.tooltip = ""
        self.checkable = False
        self.checked = False
        self.style_sheet = ""
        self.fixed_width: int | None = None

    def setEnabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def setToolTip(self, text: str) -> None:
        self.tooltip = text

    def setCheckable(self, enabled: bool) -> None:
        self.checkable = enabled

    def setChecked(self, checked: bool) -> None:
        self.checked = checked

    def isChecked(self) -> bool:
        return self.checked

    def setStyleSheet(self, style: str) -> None:
        self.style_sheet = style

    def setFixedWidth(self, width: int) -> None:
        self.fixed_width = width


class FakeComboBox(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[tuple[str, str]] = []
        self.current_index = 0
        self.current_text = ""
        self.tooltip = ""
        self.currentIndexChanged = FakeSignal()

    def addItem(self, text: str, user_data: str = "") -> None:
        self.items.append((text, user_data or text))

    def addItems(self, items: list[str]) -> None:
        for item in items:
            self.addItem(item)

    def setCurrentIndex(self, index: int) -> None:
        self.current_index = index

    def setCurrentText(self, text: str) -> None:
        for index, (label, _data) in enumerate(self.items):
            if label == text:
                self.current_index = index
                return
        self.current_text = text

    def currentText(self) -> str:
        if not self.items:
            return self.current_text
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
    def __init__(self, parent: FakeWidget | None = None) -> None:
        self.parent = parent
        self.widgets: list[Any] = []
        self.layouts: list[Any] = []
        self.stretches: list[int] = []
        if parent is not None:
            parent.layout = self

    def setContentsMargins(self, left: int, top: int, right: int, bottom: int) -> None:
        _ = (left, top, right, bottom)

    def setSpacing(self, spacing: int) -> None:
        _ = spacing

    def addWidget(self, widget: Any, stretch: Optional[int] = None) -> None:
        self.widgets.append(widget)
        self._attach_widget(widget)
        _ = stretch

    def addLayout(self, layout: Any) -> None:
        self.layouts.append(layout)
        for _label, field in getattr(layout, "rows", []):
            self._attach_widget(field)
        for widget in getattr(layout, "widgets", []):
            self._attach_widget(widget)
        for nested in getattr(layout, "layouts", []):
            for widget in getattr(nested, "widgets", []):
                self._attach_widget(widget)

    def addStretch(self, stretch: int) -> None:
        self.stretches.append(stretch)

    def _attach_widget(self, widget: Any) -> None:
        if self.parent is not None and widget not in self.parent.children:
            self.parent.children.append(widget)


class FakeHBoxLayout(FakeVBoxLayout):
    pass


class FakeGridLayout(FakeVBoxLayout):
    def addWidget(self, widget: Any, row: int = 0, column: int = 0, *_args: Any) -> None:
        self._attach_widget(widget)
        _ = (row, column)


class FakeFormLayout:
    def __init__(self, parent: FakeWidget | None = None) -> None:
        self.parent = parent
        self.rows: list[tuple[str, Any]] = []
        if parent is not None:
            parent.layout = self

    def setContentsMargins(self, *_args: Any) -> None:
        return

    def addRow(self, label: str, field: Any) -> None:
        self.rows.append((label, field))
        if self.parent is not None and field not in self.parent.children:
            self.parent.children.append(field)


class FakeTabWidget(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.tabs: list[tuple[str, FakeWidget]] = []

    def addTab(self, widget: FakeWidget, title: str) -> None:
        self.tabs.append((title, widget))
        self.children.append(widget)


class FakeStackedWidget(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.pages: list[Any] = []
        self.current_index = 0

    def addWidget(self, widget: Any) -> None:
        self.pages.append(widget)
        self.children.append(widget)

    def setCurrentIndex(self, index: int) -> None:
        self.current_index = index


class FakeCheckBox(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.text = text
        self.checked = False
        self.stateChanged = FakeSignal()

    def setText(self, text: str) -> None:
        self.text = text

    def setChecked(self, checked: bool) -> None:
        self.checked = checked

    def isChecked(self) -> bool:
        return self.checked


class FakeQFrame(FakeWidget):
    HLine = "hline"
    Sunken = "sunken"
    NoFrame = "no_frame"
    Plain = "plain"

    def __init__(self) -> None:
        super().__init__()
        self.frame_shape: Optional[Any] = None
        self.frame_shadow: Optional[Any] = None
        self.fixed_height: Optional[int] = None

    def setFrameShape(self, shape: Any) -> None:
        self.frame_shape = shape

    def setFrameShadow(self, shadow: Any) -> None:
        self.frame_shadow = shadow

    def setFixedHeight(self, height: int) -> None:
        self.fixed_height = height


class FakeProgressBar(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.visible = True
        self.maximum = 1
        self.minimum = 0
        self.text_visible = True

    def setTextVisible(self, visible: bool) -> None:
        self.text_visible = visible

    def setMaximum(self, value: int) -> None:
        self.maximum = value

    def setMinimum(self, value: int) -> None:
        self.minimum = value

    def setFixedHeight(self, height: int) -> None:
        _ = height

    def setMaximumWidth(self, width: int) -> None:
        _ = width

    def setVisible(self, visible: bool) -> None:
        self.visible = visible


class FakeQScrollArea(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.widget_resizable = False
        self.scroll_widget: Any = None
        self.horizontal_scroll_policy: Any = None
        self.size_policy: Optional[tuple[Any, Any]] = None
        self.frame_shape: Optional[Any] = None
        self.frame_shadow: Optional[Any] = None
        self.line_width: Optional[int] = None
        self.style_sheet = ""

    def setWidgetResizable(self, enabled: bool) -> None:
        self.widget_resizable = enabled

    def setHorizontalScrollBarPolicy(self, policy: Any) -> None:
        self.horizontal_scroll_policy = policy

    def setWidget(self, widget: Any) -> None:
        self.scroll_widget = widget
        self.children.append(widget)

    def setSizePolicy(self, horizontal: Any, vertical: Any) -> None:
        self.size_policy = (horizontal, vertical)

    def setFrameShape(self, shape: Any) -> None:
        self.frame_shape = shape

    def setFrameShadow(self, shadow: Any) -> None:
        self.frame_shadow = shadow

    def setLineWidth(self, width: int) -> None:
        self.line_width = width

    def setStyleSheet(self, style: str) -> None:
        self.style_sheet = style

    def frameShape(self) -> Any:
        return self.frame_shape


class FakeSizePolicy:
    Preferred = "preferred"
    Fixed = "fixed"
    Maximum = "maximum"
    Expanding = "expanding"
    Minimum = "minimum"


class FakeQt:
    ScrollBarAlwaysOff = "scroll_bar_always_off"


class FakeQtWidgets:
    QWidget = FakeWidget
    QLabel = FakeLabel
    QLineEdit = FakeLineEdit
    QPlainTextEdit = FakePlainTextEdit
    QFrame = FakeQFrame
    QScrollArea = FakeQScrollArea
    QProgressBar = FakeProgressBar
    QPushButton = FakePushButton
    QComboBox = FakeComboBox
    QTableWidget = FakeTableWidget
    QTableWidgetItem = FakeTableWidgetItem
    QVBoxLayout = FakeVBoxLayout
    QHBoxLayout = FakeHBoxLayout
    QGridLayout = FakeGridLayout
    QFormLayout = FakeFormLayout
    QTabWidget = FakeTabWidget
    QStackedWidget = FakeStackedWidget
    QCheckBox = FakeCheckBox
    QSizePolicy = FakeSizePolicy
    Qt = FakeQt


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


def test_issue_details_panel_uses_scroll_area_with_stable_expanding_policy():
    details_panel = main_window.build_issue_details_panel(FakeQtWidgets)

    assert details_panel.size_policy == ("expanding", "expanding")
    assert details_panel.minimum_width == main_window.DETAILS_PANEL_MIN_WIDTH
    scroll_area = _find(details_panel, main_window.DETAILS_SCROLL_AREA_OBJECT_NAME)
    assert scroll_area.widget_resizable is True
    assert scroll_area.scroll_widget is not None
    assert scroll_area.size_policy == ("expanding", "expanding")
    assert scroll_area.frame_shape == FakeQFrame.NoFrame
    assert scroll_area.frame_shadow == FakeQFrame.Plain
    assert scroll_area.line_width == 0
    assert "border: none" in scroll_area.style_sheet


def test_issue_details_panel_uses_horizontal_separators_between_sections():
    details_panel = main_window.build_issue_details_panel(FakeQtWidgets)
    scroll_content = _find(details_panel, main_window.DETAILS_SCROLL_CONTENT_OBJECT_NAME)

    separators = [
        child
        for child in scroll_content.children
        if getattr(child, "frame_shape", None) == FakeQFrame.HLine
    ]
    assert len(separators) == 5


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
