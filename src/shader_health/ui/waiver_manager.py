"""Waiver manager UI for the Maya Shader Health Inspector panel."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Optional

from shader_health.core.waivers import WaiverRecord, waiver_status_label
from shader_health.ui.table_widgets import configure_read_only_table, make_read_only_item

WAIVER_MANAGER_OBJECT_NAME = "shaderHealthInspectorWaiverManager"
WAIVER_STATUS_LABEL_OBJECT_NAME = "shaderHealthInspectorWaiverStatusLabel"
WAIVER_TABLE_OBJECT_NAME = "shaderHealthInspectorWaiverTable"
WAIVER_REVOKE_BUTTON_OBJECT_NAME = "shaderHealthInspectorRevokeWaiverButton"
WAIVER_REFRESH_BUTTON_OBJECT_NAME = "shaderHealthInspectorRefreshWaiversButton"
WAIVER_MAKE_WAIVE_BUTTON_OBJECT_NAME = "shaderHealthInspectorMakeWaiveButton"

WAIVER_TABLE_COLUMNS = (
    "Status",
    "Rule",
    "Target",
    "Approver",
    "Expires",
)

@dataclass(frozen=True)
class WaiverTableRow:
    """Display row for the waiver manager table."""

    waiver_id: str
    status: str
    rule_id: str
    target: str
    approved_by: str
    expires_at_utc: str

@dataclass(frozen=True)
class WaiverManagerCallbacks:
    """Optional callbacks for waiver manager UI actions."""

    on_refresh: Optional[Callable[[], None]] = None
    on_revoke_selected: Optional[Callable[[], None]] = None
    on_make_waive: Optional[Callable[[], None]] = None
    on_waiver_selected: Optional[Callable[[], None]] = None

def build_waiver_manager(
    qt_widgets: Any,
    *,
    callbacks: Optional[WaiverManagerCallbacks] = None,
) -> Any:
    """Build the waiver manager section for the Maya panel."""

    manager_callbacks = callbacks or WaiverManagerCallbacks()
    widget = qt_widgets.QWidget()
    widget.setObjectName(WAIVER_MANAGER_OBJECT_NAME)

    layout = qt_widgets.QVBoxLayout(widget)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(4)

    title = qt_widgets.QLabel("Waiver Manager")
    layout.addWidget(title)

    status_label = qt_widgets.QLabel("No waiver sidecar loaded.")
    status_label.setObjectName(WAIVER_STATUS_LABEL_OBJECT_NAME)
    status_label.setWordWrap(True)
    layout.addWidget(status_label)

    table = qt_widgets.QTableWidget()
    table.setObjectName(WAIVER_TABLE_OBJECT_NAME)
    table.setColumnCount(len(WAIVER_TABLE_COLUMNS))
    table.setHorizontalHeaderLabels(list(WAIVER_TABLE_COLUMNS))
    configure_read_only_table(table, qt_widgets)
    layout.addWidget(table)

    actions = qt_widgets.QWidget()
    actions_layout = qt_widgets.QHBoxLayout(actions)
    actions_layout.setContentsMargins(0, 0, 0, 0)
    actions_layout.setSpacing(4)
    actions_layout.addWidget(
        _button(
            qt_widgets,
            "Make Waive",
            WAIVER_MAKE_WAIVE_BUTTON_OBJECT_NAME,
            (
                "Approve a known exception for the selected issue on the Validate tab: "
                "writes a waiver sidecar next to the saved scene."
            ),
            manager_callbacks.on_make_waive,
        )
    )
    actions_layout.addWidget(
        _button(
            qt_widgets,
            "Refresh Waivers",
            WAIVER_REFRESH_BUTTON_OBJECT_NAME,
            "Reload waivers from the scene sidecar JSON.",
            manager_callbacks.on_refresh,
        )
    )
    actions_layout.addWidget(
        _button(
            qt_widgets,
            "Revoke Selected",
            WAIVER_REVOKE_BUTTON_OBJECT_NAME,
            "Remove the selected waiver from the scene sidecar.",
            manager_callbacks.on_revoke_selected,
        )
    )
    layout.addWidget(actions)

    return widget

def waiver_rows_from_records(
    waivers: Sequence[WaiverRecord],
    *,
    now_utc: Optional[str] = None,
) -> tuple[WaiverTableRow, ...]:
    """Convert waiver records into display rows for the manager table."""

    rows: list[WaiverTableRow] = []
    for waiver in waivers:
        target = waiver.target_node or waiver.target_id
        if waiver.target_material:
            target = f"{target} ({waiver.target_material})"
        rows.append(
            WaiverTableRow(
                waiver_id=waiver.id,
                status=waiver_status_label(waiver, now_utc=now_utc),
                rule_id=waiver.rule_id,
                target=target,
                approved_by=waiver.approved_by,
                expires_at_utc=waiver.expires_at_utc,
            )
        )
    return tuple(rows)

def populate_waiver_table(
    qt_widgets: Any,
    table: Any,
    rows: Sequence[WaiverTableRow],
) -> None:
    """Populate the waiver manager table."""

    table.setRowCount(len(rows))
    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(waiver_row_cells(row)):
            table.setItem(row_index, column_index, make_read_only_item(qt_widgets, value))

def waiver_summary_text(
    rows: Sequence[WaiverTableRow],
    *,
    sidecar_path: str = "",
) -> str:
    """Build the waiver manager status line."""

    if not rows:
        if sidecar_path:
            return f"No waivers in {sidecar_path}."
        return "No waiver sidecar loaded."

    active_count = sum(1 for row in rows if row.status == "active")
    expired_count = sum(1 for row in rows if row.status == "expired")
    path_hint = f" Sidecar: {sidecar_path}." if sidecar_path else ""
    if expired_count:
        return (
            f"{active_count} active, {expired_count} expired (ignored on validate).{path_hint}"
        )
    return f"{active_count} active waiver(s).{path_hint}"

def waiver_row_cells(row: WaiverTableRow) -> tuple[str, str, str, str, str]:
    """Return display cells in waiver table column order."""

    status = row.status
    if status == "expired":
        status = "expired (ignored)"
    return (
        status,
        row.rule_id,
        row.target,
        row.approved_by,
        row.expires_at_utc,
    )

def _button(
    qt_widgets: Any,
    label: str,
    object_name: str,
    tooltip: str,
    callback: Optional[Callable[[], None]],
) -> Any:
    button = qt_widgets.QPushButton(label)
    button.setObjectName(object_name)
    button.setToolTip(tooltip)
    clicked = getattr(button, "clicked", None)
    connect = getattr(clicked, "connect", None)
    if callback is not None and connect is not None:
        connect(lambda *_: callback())
    return button
