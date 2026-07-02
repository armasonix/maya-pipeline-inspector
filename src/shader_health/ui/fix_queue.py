"""Safe Auto-Fix Queue UI helpers."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Optional

FIX_QUEUE_OBJECT_NAME = "shaderHealthInspectorFixQueue"
FIX_QUEUE_TABLE_OBJECT_NAME = "shaderHealthInspectorFixQueueTable"
FIX_QUEUE_APPLY_SELECTED_BUTTON_OBJECT_NAME = "shaderHealthInspectorApplySelectedFixesButton"
FIX_QUEUE_APPLY_SAFE_BUTTON_OBJECT_NAME = "shaderHealthInspectorApplySafeFixesButton"
FIX_QUEUE_RISKY_CONFIRMATION_LABEL_OBJECT_NAME = "shaderHealthInspectorRiskyFixConfirmationLabel"
FIX_QUEUE_COLUMNS = (
    "Selected",
    "Risk",
    "Target",
    "Attribute",
    "Before",
    "After",
    "Blocked",
)
HIGH_RISK = "high"


@dataclass(frozen=True)
class FixQueueRow:
    """Display row for the Safe Auto-Fix Queue."""

    selected: bool
    title: str
    risk: str
    target_node: str
    target_attr: str
    before_value: str
    after_value: str
    blocked: bool = False
    requires_confirmation: bool = False


@dataclass(frozen=True)
class FixQueueActionCallbacks:
    """Optional callbacks for Safe Auto-Fix Queue buttons."""

    on_apply_selected: Optional[Callable[[], None]] = None
    on_apply_safe: Optional[Callable[[], None]] = None


def build_fix_queue(
    qt_widgets: Any,
    rows: Sequence[FixQueueRow] = (),
    callbacks: Optional[FixQueueActionCallbacks] = None,
) -> Any:
    """Build the visible Safe Auto-Fix Queue widget."""

    fix_rows = tuple(rows)
    fix_callbacks = callbacks or FixQueueActionCallbacks()
    widget = qt_widgets.QWidget()
    widget.setObjectName(FIX_QUEUE_OBJECT_NAME)

    layout = qt_widgets.QVBoxLayout(widget)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(4)

    title_label = qt_widgets.QLabel("Safe Auto-Fix Queue")
    layout.addWidget(title_label)

    table = qt_widgets.QTableWidget()
    table.setObjectName(FIX_QUEUE_TABLE_OBJECT_NAME)
    table.setColumnCount(len(FIX_QUEUE_COLUMNS))
    table.setHorizontalHeaderLabels(list(FIX_QUEUE_COLUMNS))
    populate_fix_queue(qt_widgets, table, fix_rows)
    layout.addWidget(table)

    confirmation_label = qt_widgets.QLabel(_risky_confirmation_text(fix_rows))
    confirmation_label.setObjectName(FIX_QUEUE_RISKY_CONFIRMATION_LABEL_OBJECT_NAME)
    confirmation_label.setWordWrap(True)
    layout.addWidget(confirmation_label)

    apply_selected_button = _fix_queue_button(
        qt_widgets,
        "Apply Selected Fixes",
        FIX_QUEUE_APPLY_SELECTED_BUTTON_OBJECT_NAME,
        "Apply selected non-blocked fixes. Risky fixes require confirmation.",
        fix_callbacks.on_apply_selected,
    )
    layout.addWidget(apply_selected_button)

    apply_safe_button = _fix_queue_button(
        qt_widgets,
        "Apply Safe Fixes",
        FIX_QUEUE_APPLY_SAFE_BUTTON_OBJECT_NAME,
        "Apply all non-blocked low/medium risk fixes.",
        fix_callbacks.on_apply_safe,
    )
    layout.addWidget(apply_safe_button)

    return widget


def populate_fix_queue(
    qt_widgets: Any,
    table: Any,
    rows: Sequence[FixQueueRow],
) -> None:
    """Populate a Qt table widget with fix queue rows."""

    table.setRowCount(len(rows))
    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(fix_queue_row_cells(row)):
            table.setItem(row_index, column_index, qt_widgets.QTableWidgetItem(value))


def selected_fix_rows(rows: Sequence[FixQueueRow]) -> tuple[FixQueueRow, ...]:
    """Return selected queue rows that are not blocked."""

    return tuple(row for row in rows if row.selected and not row.blocked)


def safe_fix_rows(rows: Sequence[FixQueueRow]) -> tuple[FixQueueRow, ...]:
    """Return non-blocked low/medium risk rows that can be batch-applied."""

    return tuple(
        row
        for row in rows
        if not row.blocked and not row.requires_confirmation and row.risk != HIGH_RISK
    )


def risky_fix_rows(rows: Sequence[FixQueueRow]) -> tuple[FixQueueRow, ...]:
    """Return rows that require explicit confirmation before application."""

    return tuple(
        row
        for row in rows
        if not row.blocked and (row.requires_confirmation or row.risk == HIGH_RISK)
    )


def fix_queue_row_cells(row: FixQueueRow) -> tuple[str, str, str, str, str, str, str]:
    """Return display cells in fix queue column order."""

    return (
        _yes_no(row.selected),
        row.risk,
        row.target_node,
        row.target_attr,
        row.before_value,
        row.after_value,
        _yes_no(row.blocked),
    )


def _risky_confirmation_text(rows: Sequence[FixQueueRow]) -> str:
    risky_count = len(risky_fix_rows(rows))
    if risky_count:
        return f"Risky fixes require confirmation: {risky_count} pending."
    return "Risky fixes require confirmation before they can be applied."


def _fix_queue_button(
    qt_widgets: Any,
    label: str,
    object_name: str,
    tooltip: str,
    callback: Optional[Callable[[], None]],
) -> Any:
    button = qt_widgets.QPushButton(label)
    button.setObjectName(object_name)
    button.setToolTip(tooltip)
    _connect_button(button, callback)
    return button


def _connect_button(button: Any, callback: Optional[Callable[[], None]]) -> None:
    if callback is None:
        return
    clicked = getattr(button, "clicked", None)
    connect = getattr(clicked, "connect", None)
    if connect is not None:
        connect(callback)


def _yes_no(value: bool) -> str:
    return "YES" if value else "NO"
