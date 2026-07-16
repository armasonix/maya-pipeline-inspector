"""Persist and restore Qt table column widths for the Maya panel."""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from pipeline_inspector.ui.table_widgets import connect_qt_signal


def read_table_column_widths(table: Any) -> tuple[int, ...]:
    """Return current column widths for a table widget."""

    column_count_fn = getattr(table, "columnCount", None)
    column_count = int(column_count_fn()) if callable(column_count_fn) else 0
    if column_count <= 0:
        return ()

    column_width_fn = getattr(table, "columnWidth", None)
    if not callable(column_width_fn):
        return ()

    widths: list[int] = []
    for column_index in range(column_count):
        width = int(column_width_fn(column_index) or 0)
        if width > 0:
            widths.append(width)
    return tuple(widths)


def apply_table_column_widths(
    table: Any,
    qt_widgets: Any,
    widths: Sequence[int],
) -> None:
    """Apply saved column widths and allow further interactive resizing."""

    if not widths:
        return

    column_count_fn = getattr(table, "columnCount", None)
    column_count = int(column_count_fn()) if callable(column_count_fn) else 0
    if column_count <= 0:
        return

    horizontal_header = getattr(table, "horizontalHeader", lambda: None)()
    if horizontal_header is None:
        return

    header_view = getattr(qt_widgets, "QHeaderView", None)
    set_section_resize_mode = getattr(horizontal_header, "setSectionResizeMode", None)
    interactive = getattr(header_view, "Interactive", None) if header_view is not None else None
    set_column_width = getattr(table, "setColumnWidth", None)
    if set_column_width is None:
        return

    for column_index, width in enumerate(widths):
        if column_index >= column_count or width <= 0:
            continue
        if set_section_resize_mode is not None and interactive is not None:
            set_section_resize_mode(column_index, interactive)
        set_column_width(column_index, int(width))


def wire_table_column_persistence(
    table: Any,
    qt_widgets: Any,
    *,
    table_key: str,
    on_widths_changed: Callable[[str, tuple[int, ...]], None],
    enabled: bool = True,
) -> None:
    """Persist column widths whenever the user resizes a table header section."""

    if not enabled:
        return

    horizontal_header = getattr(table, "horizontalHeader", lambda: None)()
    if horizontal_header is None:
        return

    section_resized = getattr(horizontal_header, "sectionResized", None)

    def _persist_column_widths(_index: int, _old_size: int, _new_size: int) -> None:
        widths = read_table_column_widths(table)
        if widths:
            on_widths_changed(table_key, widths)

    connect_qt_signal(section_resized, _persist_column_widths)


def normalize_table_column_widths(
    raw: Mapping[str, Sequence[int]] | None,
) -> dict[str, tuple[int, ...]]:
    """Return a sanitized table-key to widths mapping."""

    if not raw:
        return {}

    normalized: dict[str, tuple[int, ...]] = {}
    for table_key, widths in raw.items():
        key = str(table_key or "").strip()
        if not key or not isinstance(widths, Sequence) or isinstance(widths, (str, bytes)):
            continue
        cleaned = tuple(int(width) for width in widths if int(width) > 0)
        if cleaned:
            normalized[key] = cleaned
    return normalized
