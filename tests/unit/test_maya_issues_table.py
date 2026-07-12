from __future__ import annotations

from typing import Any, Optional

from pipeline_inspector.ui import main_window


class FakeWidget:
    def __init__(self) -> None:
        self.object_name: Optional[str] = None
        self.children: list[Any] = []
        self.layout: Optional[FakeVBoxLayout] = None
        self.size_policy: Optional[tuple[Any, Any]] = None
        self.visible = True

    def setObjectName(self, object_name: str) -> None:
        self.object_name = object_name

    def setSizePolicy(self, horizontal: Any, vertical: Any) -> None:
        self.size_policy = (horizontal, vertical)

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

    def setText(self, text: str) -> None:
        self.text = text

    def setTextFormat(self, text_format: Any) -> None:
        _ = text_format


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


class FakeTableWidget(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.column_count = 0
        self.row_count = 0
        self.headers: list[str] = []
        self.sorting_enabled = False
        self.items: dict[tuple[int, int], FakeTableWidgetItem] = {}
        self.vertical_header: dict[int, FakeTableWidgetItem] = {}

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

    def setVerticalHeaderItem(self, row: int, item: FakeTableWidgetItem) -> None:
        self.vertical_header[row] = item


class FakeTableWidgetItem:
    def __init__(self, text: str) -> None:
        self.text = text
        self.foreground_color: Any = None

    def setForeground(self, brush: Any) -> None:
        self.foreground_color = brush


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


class FakeSplitter(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.widgets: list[Any] = []
        self.stretch_factors: list[tuple[int, int]] = []
        self.orientation: Optional[Any] = None
        self.children_collapsible: Optional[bool] = None
        self.collapsible: dict[int, bool] = {}

    def setOrientation(self, orientation: Any) -> None:
        self.orientation = orientation

    def addWidget(self, widget: Any) -> None:
        self.widgets.append(widget)
        self.children.append(widget)

    def setStretchFactor(self, index: int, stretch: int) -> None:
        self.stretch_factors.append((index, stretch))

    def setChildrenCollapsible(self, enabled: bool) -> None:
        self.children_collapsible = enabled

    def setCollapsible(self, index: int, enabled: bool) -> None:
        self.collapsible[index] = enabled


class FakeQScrollArea(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.widget_resizable = False
        self.scroll_widget: Any = None
        self.horizontal_scroll_policy: Any = None
        self.size_policy: Optional[tuple[Any, Any]] = None

    def setWidgetResizable(self, enabled: bool) -> None:
        self.widget_resizable = enabled

    def setHorizontalScrollBarPolicy(self, policy: Any) -> None:
        self.horizontal_scroll_policy = policy

    def setWidget(self, widget: Any) -> None:
        self.scroll_widget = widget
        self.children.append(widget)

    def setSizePolicy(self, horizontal: Any, vertical: Any) -> None:
        self.size_policy = (horizontal, vertical)


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


class FakeQt:
    Horizontal = "horizontal"
    RichText = "rich_text"
    ScrollBarAlwaysOff = "scroll_bar_always_off"


class FakeSizePolicy:
    Preferred = "preferred"
    Fixed = "fixed"
    Maximum = "maximum"
    Expanding = "expanding"
    Minimum = "minimum"


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
    QSplitter = FakeSplitter
    QSizePolicy = FakeSizePolicy
    Qt = FakeQt


def test_issues_table_displays_required_columns_and_cells():
    rows = _sample_rows()

    widget = main_window.build_issues_table(FakeQtWidgets, rows=rows)

    table = _find(widget, main_window.ISSUES_TABLE_OBJECT_NAME)
    assert table.headers == list(main_window.ISSUES_TABLE_COLUMNS)
    assert table.column_count == len(main_window.ISSUES_TABLE_COLUMNS)
    assert table.row_count == 3
    assert table.items[(0, 0)].text == "warning"
    assert table.items[(0, 1)].text == "Hero_Mat"
    assert table.items[(0, 2)].text == "file1"
    assert table.items[(0, 3)].text == "Missing texture"
    assert table.items[(0, 4)].text == "lookdev"
    assert table.items[(0, 5)].text == "missing_texture"


def test_issues_table_builds_filter_and_sort_controls():
    widget = main_window.build_issues_table(FakeQtWidgets, rows=_sample_rows())

    filters_row = _find(widget, main_window.ISSUES_FILTERS_ROW_OBJECT_NAME)
    severity_filter = _find(widget, main_window.ISSUES_SEVERITY_FILTER_OBJECT_NAME)
    sort_dropdown = _find(widget, main_window.ISSUES_SORT_DROPDOWN_OBJECT_NAME)
    table = _find(widget, main_window.ISSUES_TABLE_OBJECT_NAME)

    assert filters_row.layout is not None
    assert widget.layout.widgets[0] is filters_row
    assert "Severity:" in severity_filter.tooltip
    assert [label for label, _data in severity_filter.items] == [
        main_window.ALL_SEVERITIES_LABEL,
        "critical",
        "error",
        "warning",
    ]
    assert [label for label, _data in sort_dropdown.items] == list(main_window.ISSUES_SORT_KEYS)
    assert sort_dropdown.currentText() == "severity"
    assert table.sorting_enabled is True


def test_filter_issue_rows_filters_by_severity():
    rows = _sample_rows()

    filtered = main_window.filter_issue_rows(rows, severity_filter="critical")

    assert filtered == (rows[1],)


def test_sort_issue_rows_sorts_by_severity_and_material():
    rows = _sample_rows()

    by_severity = main_window.sort_issue_rows(rows, sort_key="severity")
    by_material = main_window.sort_issue_rows(rows, sort_key="material")

    assert by_severity == (rows[1], rows[2], rows[0])
    assert by_material == (rows[2], rows[0], rows[1])


def test_sort_issue_rows_rejects_unknown_sort_key():
    try:
        main_window.sort_issue_rows(_sample_rows(), sort_key="unknown")
    except ValueError as exc:
        assert "Unsupported issue table sort key" in str(exc)
    else:
        raise AssertionError("Expected unknown issue table sort key to fail")


def test_populate_issues_table_colors_severity_column_by_severity(monkeypatch):
    class FakeColor:
        def __init__(self, hex_color: str) -> None:
            self.hex_color = hex_color

    class FakeBrush:
        def __init__(self, color: FakeColor) -> None:
            self.color = color

    class FakeQtCore:
        QColor = FakeColor
        QBrush = FakeBrush

    monkeypatch.setattr(main_window, "load_qt_core", lambda: FakeQtCore())

    table = FakeTableWidget()
    rows = _sample_rows()
    main_window.populate_issues_table(FakeQtWidgets, table, rows)

    assert table.items[(0, 0)].foreground_color.color.hex_color == "#f1c40f"
    assert table.items[(1, 0)].foreground_color.color.hex_color == "#e74c3c"
    assert table.items[(2, 0)].foreground_color.color.hex_color == "#e67e22"
    assert table.vertical_header == {}


def test_main_widget_contains_issues_table():
    widget = main_window.build_main_widget(FakeQtWidgets)

    table = _find(widget, main_window.ISSUES_TABLE_OBJECT_NAME)

    assert table.object_name == main_window.ISSUES_TABLE_OBJECT_NAME


def _sample_rows() -> tuple[main_window.IssueTableRow, ...]:
    return (
        main_window.IssueTableRow(
            severity="warning",
            material="Hero_Mat",
            node="file1",
            issue="Missing texture",
            owner="lookdev",
            rule="missing_texture",
        ),
        main_window.IssueTableRow(
            severity="critical",
            material="Vehicle_Mat",
            node="VRayMtl1",
            issue="Publish blocker",
            owner="lighting",
            rule="deadline_blocker",
        ),
        main_window.IssueTableRow(
            severity="error",
            material="Background_Mat",
            node="aiStandardSurface1",
            issue="Wrong color space",
            owner="surfacing",
            rule="color_space",
        ),
    )


def _find(widget: Any, object_name: str) -> Any:
    stack = [widget]
    while stack:
        current = stack.pop()
        if getattr(current, "object_name", None) == object_name:
            return current
        stack.extend(getattr(current, "children", []))
    raise AssertionError(f"Could not find object named {object_name!r}")
