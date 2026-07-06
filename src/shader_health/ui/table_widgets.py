"""Shared Qt table helpers for Maya Shader Health Inspector UI."""
from __future__ import annotations

from typing import Any, Optional

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


FIX_QUEUE_SELECT_BUTTON_OBJECT_NAME = "shaderHealthFixQueueSelectButton"


def make_fix_queue_select_cell(
    qt_widgets: Any,
    *,
    checked: bool = False,
    on_toggled: Optional[Any] = None,
) -> Any:
    """Return a right-aligned Select toggle button for the fix queue table."""

    cell = qt_widgets.QWidget()
    layout = qt_widgets.QHBoxLayout(cell)
    set_margins = getattr(layout, "setContentsMargins", None)
    if set_margins is not None:
        set_margins(4, 2, 4, 2)
    add_stretch = getattr(layout, "addStretch", None)
    if add_stretch is not None:
        add_stretch()

    button = qt_widgets.QPushButton(_fix_queue_select_label(checked))
    button.setObjectName(FIX_QUEUE_SELECT_BUTTON_OBJECT_NAME)
    button.setCheckable(True)
    button.setChecked(checked)
    set_tooltip = getattr(button, "setToolTip", None)
    if set_tooltip is not None:
        set_tooltip("Select this fix for Apply Selected Fixes.")
    _update_fix_queue_select_button_style(button, checked)

    clicked = getattr(button, "clicked", None)
    connect = getattr(clicked, "connect", None)
    if connect is not None and on_toggled is not None:

        def _emit_toggled(_checked: bool = False) -> None:
            is_checked = getattr(button, "isChecked", None)
            checked_now = bool(is_checked()) if is_checked is not None else False
            _update_fix_queue_select_button_style(button, checked_now)
            on_toggled(checked_now)

        connect(_emit_toggled)

    add_widget = getattr(layout, "addWidget", None)
    if add_widget is not None:
        add_widget(button)
    cell._shader_health_select_button = button
    return cell


def is_fix_queue_select_checked(table: Any, row_index: int) -> bool:
    """Return whether a fix-queue Select button row is active."""

    cell_widget = table.cellWidget(row_index, 0) if hasattr(table, "cellWidget") else None
    if cell_widget is None:
        return False
    button = _find_fix_queue_select_button(cell_widget)
    if button is None:
        return False
    is_checked = getattr(button, "isChecked", None)
    return bool(is_checked()) if is_checked is not None else False


def set_fix_queue_select_checked(table: Any, row_index: int, checked: bool) -> bool:
    """Update a fix-queue Select button and return the new checked state."""

    cell_widget = table.cellWidget(row_index, 0) if hasattr(table, "cellWidget") else None
    if cell_widget is None:
        return checked
    button = _find_fix_queue_select_button(cell_widget)
    if button is None:
        return checked
    set_checked = getattr(button, "setChecked", None)
    if set_checked is not None:
        set_checked(checked)
    _update_fix_queue_select_button_style(button, checked)
    return checked


def _find_fix_queue_select_button(cell_widget: Any) -> Any:
    stored = getattr(cell_widget, "_shader_health_select_button", None)
    if stored is not None:
        return stored

    children = getattr(cell_widget, "children", None)
    if children is None:
        return None
    for child in children() or ():
        object_name = getattr(child, "objectName", lambda: "")()
        if object_name == FIX_QUEUE_SELECT_BUTTON_OBJECT_NAME:
            return child
    return None


def _fix_queue_select_label(checked: bool) -> str:
    return "Selected" if checked else "Select"


def _update_fix_queue_select_button_style(button: Any, checked: bool) -> None:
    set_text = getattr(button, "setText", None)
    if set_text is not None:
        set_text(_fix_queue_select_label(checked))


def is_checkbox_checked(item: Any) -> bool:
    """Return True when a fix-queue checkbox cell is checked."""

    try:
        qt_core = load_qt_core()
    except RuntimeError:
        return False
    checked_state = getattr(qt_core.Qt, "Checked", None)
    check_state = getattr(item, "checkState", lambda: None)()
    return checked_state is not None and check_state == checked_state
