from __future__ import annotations

from typing import Any, Optional

from shader_health.ui import main_window


class FakeWidget:
    def __init__(self) -> None:
        self.object_name: Optional[str] = None
        self.children: list[Any] = []
        self.layout: Optional[FakeVBoxLayout] = None
        self.size_policy: Optional[tuple[Any, Any]] = None

    def setObjectName(self, object_name: str) -> None:
        self.object_name = object_name

    def setSizePolicy(self, horizontal: Any, vertical: Any) -> None:
        self.size_policy = (horizontal, vertical)


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


class FakeCheckBox(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.checked = False

    def setChecked(self, checked: bool) -> None:
        self.checked = checked


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

    def setOrientation(self, orientation: Any) -> None:
        self.orientation = orientation

    def addWidget(self, widget: Any) -> None:
        self.widgets.append(widget)
        self.children.append(widget)

    def setStretchFactor(self, index: int, stretch: int) -> None:
        self.stretch_factors.append((index, stretch))


class FakeQt:
    Horizontal = "horizontal"
    RichText = "rich_text"


class FakeSizePolicy:
    Preferred = "preferred"
    Fixed = "fixed"
    Maximum = "maximum"


class FakeQtWidgets:
    QWidget = FakeWidget
    QLabel = FakeLabel
    QFrame = FakeQFrame
    QPushButton = FakePushButton
    QComboBox = FakeComboBox
    QTableWidget = FakeTableWidget
    QTableWidgetItem = FakeTableWidgetItem
    QVBoxLayout = FakeVBoxLayout
    QHBoxLayout = FakeHBoxLayout
    QGridLayout = FakeGridLayout
    QTabWidget = FakeTabWidget
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
    assert severity_filter.items == [
        main_window.ALL_SEVERITIES_LABEL,
        "critical",
        "error",
        "warning",
    ]
    assert sort_dropdown.items == list(main_window.ISSUES_SORT_KEYS)
    assert sort_dropdown.current_text == "severity"
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
