"""Readiness tab UI for machine environment checks."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Optional

from pipeline_inspector.integrations.readiness.engine import ReadinessCheckResult
from pipeline_inspector.ui.table_widgets import configure_read_only_table, make_read_only_item

READINESS_TAB_OBJECT_NAME = "pipelineInspectorReadinessTab"
READINESS_SUMMARY_LABEL_OBJECT_NAME = "pipelineInspectorReadinessSummaryLabel"
READINESS_RESULTS_TABLE_OBJECT_NAME = "pipelineInspectorReadinessResultsTable"
READINESS_STATUS_LABEL_OBJECT_NAME = "pipelineInspectorReadinessStatusLabel"
READINESS_RUN_BUTTON_OBJECT_NAME = "pipelineInspectorReadinessRunButton"
READINESS_SEND_SYSADMIN_BUTTON_OBJECT_NAME = "pipelineInspectorReadinessSendSysadminButton"
READINESS_SEND_SUPPORT_BUTTON_OBJECT_NAME = "pipelineInspectorReadinessSendSupportButton"
READINESS_SEND_SUPERVISOR_BUTTON_OBJECT_NAME = "pipelineInspectorReadinessSendSupervisorButton"
READINESS_ACTION_BUTTONS_OBJECT_NAME = "pipelineInspectorReadinessActionButtons"

READINESS_RESULTS_TABLE_COLUMNS = (
    "Status",
    "Check",
    "Description",
    "Details",
)

READINESS_CATEGORY_LABELS = {
    "maya_plugin": "Maya plugin",
    "mapped_drive": "Mapped drive",
    "env_var": "Environment variable",
    "network_path": "Network path",
    "software_version": "Installed software",
}


@dataclass(frozen=True)
class ReadinessTabState:
    """Display data for the Readiness tab."""

    summary: str = "Run Machine Readiness to evaluate plugins, drives, env vars, and network paths."
    status_message: str = "No readiness check has been run yet."
    results: tuple[ReadinessCheckResult, ...] = ()
    checks_configured: bool = False
    all_passed: bool = False
    can_send_report: bool = False


@dataclass(frozen=True)
class ReadinessActionCallbacks:
    """Callbacks for Readiness tab actions."""

    on_run_readiness_check: Optional[Callable[[], None]] = None
    on_send_report_to_sysadmin: Optional[Callable[[], None]] = None
    on_send_report_to_support: Optional[Callable[[], None]] = None


def build_readiness_tab(
    qt_widgets: Any,
    callbacks: Optional[ReadinessActionCallbacks] = None,
    state: Optional[ReadinessTabState] = None,
) -> Any:
    """Build the Readiness tab with results and escalation actions."""

    readiness_callbacks = callbacks or ReadinessActionCallbacks()
    readiness_state = state or ReadinessTabState()
    tab = qt_widgets.QWidget()
    tab.setObjectName(READINESS_TAB_OBJECT_NAME)

    layout = qt_widgets.QVBoxLayout(tab)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(6)

    summary_label = qt_widgets.QLabel(readiness_state.summary)
    summary_label.setObjectName(READINESS_SUMMARY_LABEL_OBJECT_NAME)
    summary_label.setWordWrap(True)
    layout.addWidget(summary_label)

    results_table = qt_widgets.QTableWidget()
    set_row_count = getattr(results_table, "setRowCount", None)
    set_column_count = getattr(results_table, "setColumnCount", None)
    if set_row_count is not None:
        set_row_count(0)
    if set_column_count is not None:
        set_column_count(len(READINESS_RESULTS_TABLE_COLUMNS))
    results_table.setObjectName(READINESS_RESULTS_TABLE_OBJECT_NAME)
    results_table.setHorizontalHeaderLabels(READINESS_RESULTS_TABLE_COLUMNS)
    configure_read_only_table(results_table, qt_widgets)
    layout.addWidget(results_table)

    buttons_row = qt_widgets.QWidget()
    buttons_row.setObjectName(READINESS_ACTION_BUTTONS_OBJECT_NAME)
    buttons_layout = qt_widgets.QGridLayout(buttons_row)
    buttons_layout.setContentsMargins(0, 0, 0, 0)
    buttons_layout.setSpacing(4)

    run_button = _readiness_button(
        qt_widgets,
        "Run Machine Readiness",
        READINESS_RUN_BUTTON_OBJECT_NAME,
        "Evaluate configured plugins, drives, environment variables, and network paths.",
        readiness_callbacks.on_run_readiness_check,
    )
    sysadmin_button = _readiness_button(
        qt_widgets,
        "Send report to Sysadmin",
        READINESS_SEND_SYSADMIN_BUTTON_OBJECT_NAME,
        "Send the latest readiness failure report to the configured sysadmin Telegram chat.",
        readiness_callbacks.on_send_report_to_sysadmin,
    )
    support_button = _readiness_button(
        qt_widgets,
        "Send report to Support",
        READINESS_SEND_SUPPORT_BUTTON_OBJECT_NAME,
        "Send the latest readiness failure report to the configured support Telegram chat.",
        readiness_callbacks.on_send_report_to_support,
    )
    buttons_layout.addWidget(run_button, 0, 0)
    buttons_layout.addWidget(sysadmin_button, 0, 1)
    buttons_layout.addWidget(support_button, 0, 2)
    layout.addWidget(buttons_row)

    status_label = qt_widgets.QLabel(readiness_state.status_message)
    status_label.setObjectName(READINESS_STATUS_LABEL_OBJECT_NAME)
    status_label.setWordWrap(True)
    layout.addWidget(status_label)
    layout.addStretch(1)

    update_readiness_tab(tab, qt_widgets, readiness_state)
    return tab


def update_readiness_tab(
    tab_root: Any,
    qt_widgets: Any,
    state: ReadinessTabState,
) -> None:
    """Refresh Readiness tab labels and action availability."""

    _set_label(tab_root, qt_widgets, READINESS_SUMMARY_LABEL_OBJECT_NAME, state.summary)
    _set_label(tab_root, qt_widgets, READINESS_STATUS_LABEL_OBJECT_NAME, state.status_message)
    _populate_results_table(tab_root, qt_widgets, state.results)
    _update_action_buttons(tab_root, qt_widgets, state)


def readiness_tab_state_from_report(
    *,
    summary: str,
    status_message: str,
    results: tuple[ReadinessCheckResult, ...],
    checks_configured: bool,
    can_send_report: bool,
) -> ReadinessTabState:
    """Build tab state from a readiness engine report."""

    all_passed = bool(results) and all(result.ok for result in results)
    return ReadinessTabState(
        summary=summary,
        status_message=status_message,
        results=results,
        checks_configured=checks_configured,
        all_passed=all_passed,
        can_send_report=can_send_report,
    )


def _populate_results_table(
    tab_root: Any,
    qt_widgets: Any,
    results: tuple[ReadinessCheckResult, ...],
) -> None:
    table = _find_child(tab_root, qt_widgets.QTableWidget, READINESS_RESULTS_TABLE_OBJECT_NAME)
    if table is None:
        return
    set_count = getattr(table, "setRowCount", None)
    if set_count is None:
        return
    set_count(len(results))
    for row_index, result in enumerate(results):
        _set_table_item(table, qt_widgets, row_index, 0, "PASS" if result.ok else "FAIL")
        _set_table_item(table, qt_widgets, row_index, 1, result.label)
        _set_table_item(table, qt_widgets, row_index, 2, result.message)
        _set_table_item(
            table,
            qt_widgets,
            row_index,
            3,
            _readiness_result_details(result),
        )


def _readiness_result_details(result: ReadinessCheckResult) -> str:
    category_label = READINESS_CATEGORY_LABELS.get(result.category, result.category)
    check_id = str(result.check_id or "").strip()
    if check_id:
        return f"{category_label} · {check_id}"
    return category_label


def _update_action_buttons(tab_root: Any, qt_widgets: Any, state: ReadinessTabState) -> None:
    run_button = _find_child(tab_root, qt_widgets.QPushButton, READINESS_RUN_BUTTON_OBJECT_NAME)
    sysadmin_button = _find_child(
        tab_root,
        qt_widgets.QPushButton,
        READINESS_SEND_SYSADMIN_BUTTON_OBJECT_NAME,
    )
    support_button = _find_child(
        tab_root,
        qt_widgets.QPushButton,
        READINESS_SEND_SUPPORT_BUTTON_OBJECT_NAME,
    )
    send_enabled = state.can_send_report and not state.all_passed and bool(state.results)
    for button, enabled in (
        (run_button, True),
        (sysadmin_button, send_enabled),
        (support_button, send_enabled),
    ):
        if button is None:
            continue
        set_enabled = getattr(button, "setEnabled", None)
        if set_enabled is not None:
            set_enabled(enabled)


def _readiness_button(
    qt_widgets: Any,
    label: str,
    object_name: str,
    tooltip: str,
    callback: Optional[Callable[[], None]],
) -> Any:
    button = qt_widgets.QPushButton(label)
    button.setObjectName(object_name)
    set_tooltip = getattr(button, "setToolTip", None)
    if set_tooltip is not None:
        set_tooltip(tooltip)
    clicked = getattr(button, "clicked", None)
    connect = getattr(clicked, "connect", None) if clicked is not None else None
    if connect is not None and callback is not None:
        connect(callback)
    return button


def _set_label(tab_root: Any, qt_widgets: Any, object_name: str, text: str) -> None:
    label = _find_child(tab_root, qt_widgets.QLabel, object_name)
    if label is None:
        return
    set_text = getattr(label, "setText", None)
    if set_text is not None:
        set_text(text)


def _set_table_item(table: Any, qt_widgets: Any, row: int, column: int, text: str) -> None:
    set_item = getattr(table, "setItem", None)
    if set_item is None:
        return
    set_item(row, column, make_read_only_item(qt_widgets, text))


def _find_child(root: Any, widget_type: Any, object_name: str) -> Any:
    if root is None:
        return None
    if _widget_object_name(root) == object_name:
        return root
    children_attr = getattr(root, "children", None)
    if children_attr is None:
        children: list[Any] = []
    elif callable(children_attr):
        children = children_attr()
    else:
        children = list(children_attr)
    for child in children:
        if isinstance(child, widget_type) and _widget_object_name(child) == object_name:
            return child
        if hasattr(child, "children") or hasattr(child, "layout"):
            found = _find_child(child, widget_type, object_name)
            if found is not None:
                return found
    find_children = getattr(root, "findChildren", None)
    if find_children is not None:
        matches = find_children(widget_type)
        for match in matches:
            if _widget_object_name(match) == object_name:
                return match
    return None


def _widget_object_name(widget: Any) -> str:
    object_name_fn = getattr(widget, "objectName", None)
    if callable(object_name_fn):
        return str(object_name_fn() or "")
    return str(getattr(widget, "object_name", "") or "")
