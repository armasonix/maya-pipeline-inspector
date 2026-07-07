from __future__ import annotations

from shader_health.ui.fix_queue import (
    FIX_QUEUE_SELECT_COLUMN_INDEX,
    FixQueueRow,
    blocked_selection_message,
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
