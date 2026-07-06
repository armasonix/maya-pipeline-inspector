"""Safe Auto-Fix Queue UI helpers."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Optional

from shader_health.ui.table_widgets import configure_read_only_table, make_read_only_item

FIX_QUEUE_OBJECT_NAME = "shaderHealthInspectorFixQueue"
FIX_QUEUE_TABLE_OBJECT_NAME = "shaderHealthInspectorFixQueueTable"
FIX_QUEUE_APPLY_SELECTED_BUTTON_OBJECT_NAME = "shaderHealthInspectorApplySelectedFixesButton"
FIX_QUEUE_APPLY_SAFE_BUTTON_OBJECT_NAME = "shaderHealthInspectorApplySafeFixesButton"
FIX_QUEUE_RISKY_CONFIRMATION_LABEL_OBJECT_NAME = "shaderHealthInspectorRiskyFixConfirmationLabel"
SUPERVISOR_FULL_PROFILE_ID = "supervisor_full"
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
MEDIUM_RISK = "medium"


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
    set_tooltip = getattr(title_label, "setToolTip", None)
    if set_tooltip is not None:
        set_tooltip("Click Selected (YES/NO) to choose fixes for Apply Selected Fixes.")
    layout.addWidget(title_label)

    table = qt_widgets.QTableWidget()
    table.setObjectName(FIX_QUEUE_TABLE_OBJECT_NAME)
    table.setColumnCount(len(FIX_QUEUE_COLUMNS))
    table.setHorizontalHeaderLabels(list(FIX_QUEUE_COLUMNS))
    populate_fix_queue(qt_widgets, table, fix_rows)
    configure_read_only_table(table, qt_widgets)
    layout.addWidget(table)

    confirmation_label = qt_widgets.QLabel(risky_confirmation_text(fix_rows))
    confirmation_label.setObjectName(FIX_QUEUE_RISKY_CONFIRMATION_LABEL_OBJECT_NAME)
    confirmation_label.setWordWrap(True)
    layout.addWidget(confirmation_label)

    apply_selected_button = _fix_queue_button(
        qt_widgets,
        "Apply Selected Fixes",
        FIX_QUEUE_APPLY_SELECTED_BUTTON_OBJECT_NAME,
        "Apply checked YES rows in the Selected column.",
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
            table.setItem(row_index, column_index, make_read_only_item(qt_widgets, value))


def selected_from_table_item(item: Any) -> bool:
    """Return whether a fix queue Selected cell is marked YES."""

    if item is None:
        return False
    text = getattr(item, "text", lambda: "")()
    return str(text).strip().upper() == "YES"


def toggle_selected_table_item(item: Any) -> bool:
    """Toggle a fix queue Selected cell between YES and NO."""

    selected = not selected_from_table_item(item)
    set_text = getattr(item, "setText", None)
    if set_text is not None:
        set_text(_yes_no(selected))
    return selected


def fix_rows_from_table(table: Any, rows: Sequence[FixQueueRow]) -> tuple[FixQueueRow, ...]:
    """Return fix queue rows with Selected state read from YES/NO cells."""

    synced: list[FixQueueRow] = []
    for row_index, row in enumerate(rows):
        item = table.item(row_index, 0) if hasattr(table, "item") else None
        selected = selected_from_table_item(item) if item is not None else row.selected
        synced.append(
            FixQueueRow(
                selected=selected,
                title=row.title,
                risk=row.risk,
                target_node=row.target_node,
                target_attr=row.target_attr,
                before_value=row.before_value,
                after_value=row.after_value,
                blocked=row.blocked,
                requires_confirmation=row.requires_confirmation,
            )
        )
    return tuple(synced)


def selected_fix_rows(rows: Sequence[FixQueueRow]) -> tuple[FixQueueRow, ...]:
    """Return selected queue rows that are not blocked."""

    return tuple(row for row in rows if row.selected and not row.blocked)


def safe_fix_rows(rows: Sequence[FixQueueRow]) -> tuple[FixQueueRow, ...]:
    """Return non-blocked low/medium risk rows that can be batch-applied."""

    return tuple(
        row
        for row in rows
        if not row.blocked
        and not row.requires_confirmation
        and row.risk not in (HIGH_RISK, MEDIUM_RISK)
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


def allows_batch_risky_confirmation(profile_id: str) -> bool:
    """Return whether the active profile may confirm risky fixes in one batch dialog."""

    return profile_id.strip() == SUPERVISOR_FULL_PROFILE_ID


def risky_confirmation_text(
    rows: Sequence[FixQueueRow],
    *,
    selected_rows: Optional[Sequence[FixQueueRow]] = None,
) -> str:
    """Build the fix queue confirmation helper label."""

    pending = risky_fix_rows(rows)
    pending_count = len(pending)
    if pending_count == 0:
        return "Risky fixes require confirmation before they can be applied."

    selected_risky = risky_fix_rows(selected_rows or ())
    selected_count = len(selected_risky)
    if selected_count:
        return (
            f"Risky fixes require confirmation: {pending_count} pending, "
            f"{selected_count} selected."
        )
    return f"Risky fixes require confirmation: {pending_count} pending."


def update_risky_confirmation_label(
    label: Any,
    rows: Sequence[FixQueueRow],
    *,
    selected_rows: Optional[Sequence[FixQueueRow]] = None,
) -> None:
    """Refresh the risky-fix confirmation helper label."""

    set_text = getattr(label, "setText", None)
    if set_text is not None:
        set_text(risky_confirmation_text(rows, selected_rows=selected_rows))


def confirm_risky_fixes(
    qt_widgets: Any,
    rows: Sequence[FixQueueRow],
    *,
    profile_id: str = "",
) -> bool:
    """Ask the user to confirm high-risk fixes before application."""

    risky = risky_fix_rows(rows)
    if not risky:
        return True

    if allows_batch_risky_confirmation(profile_id):
        return _confirm_risky_fix_batch(qt_widgets, risky)

    return all(_confirm_single_risky_fix(qt_widgets, row) for row in risky)


def _confirm_risky_fix_batch(qt_widgets: Any, risky: Sequence[FixQueueRow]) -> bool:
    message_box = qt_widgets.QMessageBox
    lines = [_risky_fix_summary_line(row) for row in risky[:8]]
    if len(risky) > 8:
        lines.append(f"... and {len(risky) - 8} more")
    message = (
        f"Apply {len(risky)} high-risk fix(es)? "
        "These changes can affect render look or farm safety.\n\n" + "\n".join(lines)
    )
    return _message_box_confirmed(message_box, "Confirm Risky Fixes", message)


def _confirm_single_risky_fix(qt_widgets: Any, row: FixQueueRow) -> bool:
    message_box = qt_widgets.QMessageBox
    message = (
        "Apply this high-risk fix?\n\n"
        f"{_risky_fix_summary_line(row)}\n\n"
        "Cancel leaves the scene unchanged."
    )
    return _message_box_confirmed(
        message_box,
        "Confirm Risky Fix",
        message,
        default_no=True,
    )


def _risky_fix_summary_line(row: FixQueueRow) -> str:
    risk_bits = [f"risk={row.risk}"]
    if row.requires_confirmation and row.risk != HIGH_RISK:
        risk_bits.append("supervisor")
    risk_label = ", ".join(risk_bits)
    return (
        f"[{risk_label}] {row.target_node}.{row.target_attr}: "
        f"{row.before_value} -> {row.after_value}"
    )


def _message_box_confirmed(
    message_box: Any,
    title: str,
    message: str,
    *,
    default_no: bool = True,
) -> bool:
    standard_button = getattr(message_box, "StandardButton", None)
    if standard_button is not None:
        yes_button = standard_button.Yes
        no_button = standard_button.No
        default_button = standard_button.No if default_no else standard_button.Yes
        reply = message_box.warning(
            None,
            title,
            message,
            yes_button | no_button,
            default_button,
        )
        return reply == yes_button

    yes = message_box.Yes
    no = message_box.No
    default = no if default_no else yes
    reply = message_box.warning(None, title, message, yes | no, default)
    return reply == yes


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
