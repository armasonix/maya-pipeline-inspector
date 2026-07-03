from __future__ import annotations

from shader_health.ui.fix_queue import (
    FixQueueRow,
    fix_rows_from_table,
    selected_fix_rows,
    selected_from_table_item,
    toggle_selected_table_item,
)


class FakeItem:
    def __init__(self, text: str = "NO") -> None:
        self.text_value = text

    def text(self) -> str:
        return self.text_value

    def setText(self, value: str) -> None:
        self.text_value = value


class FakeTable:
    def __init__(self, text_by_row: dict[int, str]) -> None:
        self.text_by_row = text_by_row

    def item(self, row_index: int, column_index: int):
        if column_index != 0:
            return None
        return FakeItem(self.text_by_row.get(row_index, "NO"))


def test_fix_rows_from_table_reads_yes_no_cells():
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
    table = FakeTable({0: "YES", 1: "NO"})

    synced = fix_rows_from_table(table, rows)
    selected = selected_fix_rows(synced)

    assert synced[0].selected is True
    assert synced[1].selected is False
    assert len(selected) == 1
    assert selected[0].target_node == "file1"


def test_toggle_selected_table_item_flips_yes_no():
    item = FakeItem("NO")

    assert toggle_selected_table_item(item) is True
    assert item.text() == "YES"
    assert toggle_selected_table_item(item) is False
    assert item.text() == "NO"


def test_selected_from_table_item():
    assert selected_from_table_item(FakeItem("YES")) is True
    assert selected_from_table_item(FakeItem("NO")) is False
    assert selected_from_table_item(None) is False
