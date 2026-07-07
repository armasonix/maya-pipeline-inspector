from __future__ import annotations

from shader_health.ui.table_widgets import (
    FIX_QUEUE_SELECT_BUTTON_OBJECT_NAME,
    _find_fix_queue_select_button,
    is_fix_queue_select_checked,
)


class FakeButton:
    def __init__(self, *, checked: bool = False) -> None:
        self._checked = checked

    def objectName(self) -> str:
        return FIX_QUEUE_SELECT_BUTTON_OBJECT_NAME

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool) -> None:
        self._checked = checked

    def setText(self, _value: str) -> None:
        return None


class FakeCell:
    def __init__(
        self,
        *,
        button: FakeButton | None = None,
        children: tuple[FakeButton, ...] = (),
    ) -> None:
        self._shader_health_select_button = button
        self._children = children

    def children(self) -> tuple[FakeButton, ...]:
        return self._children


class FakeTable:
    def __init__(self, cells: dict[int, FakeCell]) -> None:
        self.cells = cells

    def cellWidget(self, row_index: int, _column_index: int):
        return self.cells.get(row_index)


def test_find_fix_queue_select_button_uses_stored_reference():
    button = FakeButton(checked=True)
    cell = FakeCell(button=button)

    assert _find_fix_queue_select_button(cell) is button


def test_find_fix_queue_select_button_falls_back_to_children():
    button = FakeButton()
    cell = FakeCell(children=(button,))

    assert _find_fix_queue_select_button(cell) is button


def test_is_fix_queue_select_checked_reads_button_state():
    table = FakeTable({0: FakeCell(button=FakeButton(checked=True))})

    assert is_fix_queue_select_checked(table, 0) is True
