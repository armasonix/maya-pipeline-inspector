from __future__ import annotations

from pipeline_inspector.ui.table_column_persistence import (
    apply_table_column_widths,
    normalize_table_column_widths,
    read_table_column_widths,
    wire_table_column_persistence,
)


class FakeHeader:
    def __init__(self) -> None:
        self.resize_modes: dict[int, object] = {}
        self.handlers: list = []

    def setSectionResizeMode(self, column: int, mode: object) -> None:
        self.resize_modes[column] = mode

    @property
    def sectionResized(self):
        return self

    def connect(self, handler) -> None:
        self.handlers.append(handler)


class FakeTable:
    def __init__(self, *, column_count: int, widths: dict[int, int] | None = None) -> None:
        self._column_count = column_count
        self._widths = dict(widths or {})
        self._horizontal_header = FakeHeader()

    def columnCount(self) -> int:
        return self._column_count

    def columnWidth(self, column: int) -> int:
        return self._widths.get(column, 0)

    def setColumnWidth(self, column: int, width: int) -> None:
        self._widths[column] = width

    def horizontalHeader(self) -> FakeHeader:
        return self._horizontal_header


class FakeQHeaderView:
    Interactive = "interactive"


class FakeQtWidgets:
    QHeaderView = FakeQHeaderView


def test_read_and_apply_table_column_widths():
    table = FakeTable(column_count=3, widths={0: 80, 1: 160, 2: 240})
    qt_widgets = FakeQtWidgets()

    assert read_table_column_widths(table) == (80, 160, 240)

    target = FakeTable(column_count=3)
    apply_table_column_widths(target, qt_widgets, (90, 150, 210))

    assert target._widths == {0: 90, 1: 150, 2: 210}
    assert target._horizontal_header.resize_modes == {
        0: "interactive",
        1: "interactive",
        2: "interactive",
    }


def test_wire_table_column_persistence_calls_save_callback():
    table = FakeTable(column_count=2, widths={0: 100, 1: 200})
    qt_widgets = FakeQtWidgets()
    saved: list[tuple[str, tuple[int, ...]]] = []

    wire_table_column_persistence(
        table,
        qt_widgets,
        table_key="issues",
        on_widths_changed=lambda key, widths: saved.append((key, widths)),
    )

    header = table._horizontal_header
    assert len(header.handlers) == 1
    table.setColumnWidth(1, 260)
    header.handlers[0](1, 200, 260)

    assert saved == [("issues", (100, 260))]


def test_normalize_table_column_widths_filters_invalid_values():
    normalized = normalize_table_column_widths(
        {
            "issues": [120, 0, 180],
            "": [10],
            "bad": "120",
        }
    )

    assert normalized == {"issues": (120, 180)}
