"""Shared Qt table helpers for Maya Shader Health Inspector UI."""
from __future__ import annotations

from typing import Any

from shader_health.ui.qt import load_qt_core


def configure_read_only_table(table: Any, qt_widgets: Any) -> None:
    """Disable in-cell text editing for validation result tables."""

    abstract_view = getattr(qt_widgets, "QAbstractItemView", None)
    set_triggers = getattr(table, "setEditTriggers", None)
    if abstract_view is None or set_triggers is None:
        return
    no_edit_triggers = getattr(abstract_view, "NoEditTriggers", None)
    if no_edit_triggers is not None:
        set_triggers(no_edit_triggers)


def make_read_only_item(qt_widgets: Any, text: str) -> Any:
    """Return a table cell that cannot be edited by the user."""

    item = qt_widgets.QTableWidgetItem(text)
    set_flags = getattr(item, "setFlags", None)
    flags_fn = getattr(item, "flags", None)
    if set_flags is None or flags_fn is None:
        return item
    try:
        qt_core = load_qt_core()
    except RuntimeError:
        return item
    editable = getattr(qt_core.Qt, "ItemIsEditable", None)
    if editable is not None:
        set_flags(flags_fn() & ~editable)
    return item


def make_checkbox_item(qt_widgets: Any, *, checked: bool = False) -> Any:
    """Return a checkable Selected cell for the fix queue table."""

    item = qt_widgets.QTableWidgetItem()
    set_flags = getattr(item, "setFlags", None)
    set_check_state = getattr(item, "setCheckState", None)
    if set_flags is None or set_check_state is None:
        return item
    try:
        qt_core = load_qt_core()
    except RuntimeError:
        return item
    qt = qt_core.Qt
    item.setFlags(getattr(qt, "ItemIsUserCheckable", 0) | getattr(qt, "ItemIsEnabled", 0))
    checked_state = getattr(qt, "Checked", None)
    unchecked_state = getattr(qt, "Unchecked", None)
    if checked_state is not None and unchecked_state is not None:
        item.setCheckState(checked_state if checked else unchecked_state)
    return item


def is_checkbox_checked(item: Any) -> bool:
    """Return True when a fix-queue checkbox cell is checked."""

    try:
        qt_core = load_qt_core()
    except RuntimeError:
        return False
    checked_state = getattr(qt_core.Qt, "Checked", None)
    check_state = getattr(item, "checkState", lambda: None)()
    return checked_state is not None and check_state == checked_state
