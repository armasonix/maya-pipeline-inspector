from __future__ import annotations

from shader_health.ui.fix_queue import (
    FIX_QUEUE_ACTIONS_ROW_OBJECT_NAME,
    FIX_QUEUE_BLOCKED_COLUMN_INDEX,
    FIX_QUEUE_SELECT_COLUMN_INDEX,
    FixQueueRow,
    blocked_selection_message,
    build_fix_queue,
    checked_fix_rows,
    fix_rows_from_table,
    safe_fix_rows,
    selected_fix_rows,
    selected_from_table_item,
)
from shader_health.ui.table_widgets import FIX_QUEUE_SELECT_BUTTON_OBJECT_NAME


class FakeItem:
    def __init__(self, text: str = "NO") -> None:
        self.text_value = text

    def text(self) -> str:
        return self.text_value

    def setText(self, value: str) -> None:
        self.text_value = value


class FakeCheckBox:
    def __init__(self, *, checked: bool = False) -> None:
        self._checked = checked

    def objectName(self) -> str:
        return FIX_QUEUE_SELECT_BUTTON_OBJECT_NAME

    def isChecked(self) -> bool:
        return self._checked


class FakeCell:
    def __init__(self, *, control: FakeCheckBox) -> None:
        self._shader_health_select_button = control


class FakeTable:
    def __init__(
        self,
        *,
        checked_by_row: dict[int, bool] | None = None,
        text_by_row: dict[int, str] | None = None,
    ) -> None:
        self.checked_by_row = checked_by_row or {}
        self.text_by_row = text_by_row or {}

    def cellWidget(self, row_index: int, column_index: int):
        if column_index != FIX_QUEUE_SELECT_COLUMN_INDEX:
            return None
        if row_index not in self.checked_by_row:
            return None
        return FakeCell(control=FakeCheckBox(checked=self.checked_by_row[row_index]))

    def item(self, row_index: int, column_index: int):
        if column_index != FIX_QUEUE_SELECT_COLUMN_INDEX:
            return None
        if row_index in self.checked_by_row:
            return None
        return FakeItem(self.text_by_row.get(row_index, "NO"))


def test_fix_rows_from_table_reads_select_controls():
    rows = (
        FixQueueRow(
            selected=False,
            title="Fix A",
            risk="low",
            target_node="file1",
            target_attr="colorSpace",
            before_value="sRGB",
            after_value="Raw",
        ),
        FixQueueRow(
            selected=False,
            title="Fix B",
            risk="low",
            target_node="file2",
            target_attr="colorSpace",
            before_value="sRGB",
            after_value="Raw",
        ),
    )
    table = FakeTable(checked_by_row={0: True, 1: False})

    synced = fix_rows_from_table(table, rows)
    selected = selected_fix_rows(synced)

    assert synced[0].selected is True
    assert synced[1].selected is False
    assert len(selected) == 1
    assert selected[0].target_node == "file1"


def test_selected_from_table_item():
    assert selected_from_table_item(FakeItem("YES")) is True
    assert selected_from_table_item(FakeItem("NO")) is False
    assert selected_from_table_item(None) is False


def test_blocked_selection_message_lists_blocked_targets():
    rows = (
        FixQueueRow(
            selected=True,
            title="Blocked",
            risk="medium",
            target_node="demo_albedo_v001_2",
            target_attr="fileTextureName",
            before_value="D:/tex/old.exr",
            after_value="${ASSET_ROOT}/tex/old.exr",
            blocked=True,
        ),
    )

    message = blocked_selection_message(rows)

    assert "demo_albedo_v001_2.fileTextureName" in message
    assert "blocked" in message.lower()


def test_checked_fix_rows_includes_blocked_selection():
    rows = (
        FixQueueRow(
            selected=True,
            title="Blocked",
            risk="medium",
            target_node="file1",
            target_attr="fileTextureName",
            before_value="a",
            after_value="b",
            blocked=True,
        ),
        FixQueueRow(
            selected=False,
            title="Clear",
            risk="low",
            target_node="file2",
            target_attr="colorSpace",
            before_value="a",
            after_value="b",
        ),
    )

    assert len(checked_fix_rows(rows)) == 1
    assert len(selected_fix_rows(rows)) == 0


def test_safe_fix_rows_excludes_medium_and_high_risk_fixes():
    rows = (
        FixQueueRow(
            selected=False,
            title="Low",
            risk="low",
            target_node="file1",
            target_attr="colorSpace",
            before_value="sRGB",
            after_value="Raw",
        ),
        FixQueueRow(
            selected=False,
            title="Medium relink",
            risk="medium",
            target_node="file2",
            target_attr="fileTextureName",
            before_value="v001",
            after_value="v003",
        ),
        FixQueueRow(
            selected=False,
            title="High",
            risk="high",
            target_node="file3",
            target_attr="displacement",
            before_value=True,
            after_value=False,
        ),
    )

    safe_rows = safe_fix_rows(rows)

    assert [row.title for row in safe_rows] == ["Low"]


class FakeWidget:
    def __init__(self) -> None:
        self.object_name = ""
        self.children: list = []
        self.layout = None
        self.size_policy = None

    def setObjectName(self, object_name: str) -> None:
        self.object_name = object_name

    def setSizePolicy(self, horizontal, vertical) -> None:
        self.size_policy = (horizontal, vertical)


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
        self.tooltip = ""

    def setToolTip(self, text: str) -> None:
        self.tooltip = text


class FakeHeader:
    def __init__(self) -> None:
        self.resize_modes: dict[int, str] = {}
        self.stretch_last_section: bool | None = None
        self.default_section_size: int | None = None

    def setSectionResizeMode(self, section_or_mode, mode=None) -> None:
        if mode is None:
            self.fixed_mode = section_or_mode
            return
        self.resize_modes[section_or_mode] = mode

    def setStretchLastSection(self, enabled: bool) -> None:
        self.stretch_last_section = enabled

    def setDefaultSectionSize(self, size: int) -> None:
        self.default_section_size = size

    def height(self) -> int:
        return 28


class FakeUICheckBox(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.text = text
        self.checked = False
        self.tooltip = ""

    def setChecked(self, checked: bool) -> None:
        self.checked = checked

    def isChecked(self) -> bool:
        return self.checked

    def setText(self, text: str) -> None:
        self.text = text

    def setToolTip(self, text: str) -> None:
        self.tooltip = text

    def setObjectName(self, object_name: str) -> None:
        self.object_name = object_name


class FakeTableWidget(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.column_count = 0
        self.row_count = 0
        self.headers: list[str] = []
        self.column_widths: dict[int, int] = {}
        self.fixed_height: int | None = None
        self.minimum_height: int | None = None
        self.maximum_height: int | None = None
        self.horizontal_header = FakeHeader()
        self.vertical_header = FakeHeader()

    def setColumnCount(self, count: int) -> None:
        self.column_count = count

    def setRowCount(self, count: int) -> None:
        self.row_count = count

    def setHorizontalHeaderLabels(self, headers: list[str]) -> None:
        self.headers = headers

    def setColumnWidth(self, column: int, width: int) -> None:
        self.column_widths[column] = width

    def setMinimumHeight(self, height: int) -> None:
        self.minimum_height = height

    def setMaximumHeight(self, height: int) -> None:
        self.maximum_height = height

    def setFixedHeight(self, height: int) -> None:
        self.fixed_height = height

    def horizontalHeader(self) -> FakeHeader:
        return self.horizontal_header

    def verticalHeader(self) -> FakeHeader:
        return self.vertical_header

    def setCellWidget(self, row_index: int, column_index: int, widget) -> None:
        _ = (row_index, column_index, widget)

    def setItem(self, row_index: int, column_index: int, item) -> None:
        _ = (row_index, column_index, item)


class FakeVBoxLayout:
    def __init__(self, parent: FakeWidget) -> None:
        self.parent = parent
        self.parent.layout = self
        self.widgets: list[tuple] = []
        self.stretches: list[int] = []

    def setContentsMargins(self, *_args) -> None:
        return

    def setSpacing(self, _spacing: int) -> None:
        return

    def addWidget(self, widget, stretch: int = 0) -> None:
        self.widgets.append((widget, stretch))
        self.parent.children.append(widget)

    def addStretch(self, stretch: int = 0) -> None:
        self.stretches.append(stretch)


class FakeHBoxLayout(FakeVBoxLayout):
    pass


class FakeQHeaderView:
    Fixed = "fixed"
    Stretch = "stretch"
    ResizeToContents = "resize_to_contents"


class FakeSizePolicy:
    Expanding = "expanding"
    Preferred = "preferred"
    Minimum = "minimum"


class FakeAbstractItemView:
    NoEditTriggers = "no_edit_triggers"


class FakeQtWidgets:
    QWidget = FakeWidget
    QLabel = FakeLabel
    QPushButton = FakePushButton
    QCheckBox = FakeUICheckBox
    QTableWidget = FakeTableWidget
    QTableWidgetItem = FakeItem
    QVBoxLayout = FakeVBoxLayout
    QHBoxLayout = FakeHBoxLayout
    QHeaderView = FakeQHeaderView
    QSizePolicy = FakeSizePolicy
    QAbstractItemView = FakeAbstractItemView


def _find(widget, object_name: str):
    stack = [widget]
    while stack:
        current = stack.pop()
        if getattr(current, "object_name", "") == object_name:
            return current
        stack.extend(getattr(current, "children", []))
    raise AssertionError(f"Missing widget {object_name!r}")


def test_build_fix_queue_keeps_actions_under_table_without_table_stretch():
    rows = (
        FixQueueRow(
            selected=False,
            title="Fix A",
            risk="medium",
            target_node="file1",
            target_attr="fileTextureName",
            before_value="D:/old.exr",
            after_value="${ASSET_ROOT}/old.exr",
        ),
    )
    widget = build_fix_queue(FakeQtWidgets, rows=rows)

    layout = widget.layout
    assert layout.stretches == [1]
    assert layout.widgets[0][1] == 0
    assert layout.widgets[1][1] == 0
    assert layout.widgets[2][1] == 0
    _find(widget, FIX_QUEUE_ACTIONS_ROW_OBJECT_NAME)


def test_configure_fix_queue_table_stretches_content_columns():
    table = FakeTableWidget()
    from shader_health.ui.fix_queue import _configure_fix_queue_table

    _configure_fix_queue_table(table, FakeQtWidgets)

    assert table.horizontal_header.resize_modes[0] == "fixed"
    assert table.horizontal_header.resize_modes[1] == "resize_to_contents"
    assert table.horizontal_header.resize_modes[2] == "stretch"
    assert table.horizontal_header.resize_modes[3] == "stretch"
    assert table.horizontal_header.resize_modes[4] == "stretch"
    assert table.horizontal_header.resize_modes[5] == "stretch"
    blocked_mode = table.horizontal_header.resize_modes[FIX_QUEUE_BLOCKED_COLUMN_INDEX]
    assert blocked_mode == "resize_to_contents"
    assert table.horizontal_header.stretch_last_section is False
    assert table.column_widths[0] == 108
