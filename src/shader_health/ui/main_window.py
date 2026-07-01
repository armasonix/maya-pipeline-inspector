"""Maya Shader Health Inspector panel content."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Optional

PANEL_OBJECT_NAME = "shaderHealthInspectorPanel"
PANEL_TITLE = "Maya Shader Health Inspector"
PANEL_CONTENT_OBJECT_NAME = "shaderHealthInspectorPanelContent"
SUMMARY_HEADER_OBJECT_NAME = "shaderHealthInspectorSummaryHeader"
HEALTH_SCORE_LABEL_OBJECT_NAME = "shaderHealthInspectorHealthScoreLabel"
SEVERITY_COUNTS_LABEL_OBJECT_NAME = "shaderHealthInspectorSeverityCountsLabel"
BLOCK_STATUS_LABEL_OBJECT_NAME = "shaderHealthInspectorBlockStatusLabel"
PROFILE_LABEL_OBJECT_NAME = "shaderHealthInspectorProfileLabel"
PROFILE_DROPDOWN_OBJECT_NAME = "shaderHealthInspectorProfileDropdown"
ISSUES_TABLE_WIDGET_OBJECT_NAME = "shaderHealthInspectorIssuesTableWidget"
ISSUES_SEVERITY_FILTER_OBJECT_NAME = "shaderHealthInspectorIssuesSeverityFilter"
ISSUES_SORT_DROPDOWN_OBJECT_NAME = "shaderHealthInspectorIssuesSortDropdown"
ISSUES_TABLE_OBJECT_NAME = "shaderHealthInspectorIssuesTable"
DEFAULT_PROFILE_OPTIONS = (
    "artist_relaxed",
    "publish_strict",
    "deadline_critical",
    "supervisor_full",
)
ISSUES_TABLE_COLUMNS = (
    "Severity",
    "Material",
    "Node",
    "Issue",
    "Owner",
    "Rule",
)
ISSUES_SORT_KEYS = (
    "severity",
    "material",
    "node",
    "issue",
    "owner",
    "rule",
)
ALL_SEVERITIES_LABEL = "All severities"
SEVERITY_SORT_ORDER = {
    "critical": 0,
    "error": 1,
    "warning": 2,
    "info": 3,
}


@dataclass(frozen=True)
class SummaryHeaderState:
    """Display data for the Maya UI summary/header widget."""

    health_score: int = 100
    critical_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    block_publish: bool = False
    block_deadline: bool = False
    profile_id: str = "artist_relaxed"


@dataclass(frozen=True)
class IssueTableRow:
    """Display row for the Maya UI issues table."""

    severity: str
    material: str
    node: str
    issue: str
    owner: str
    rule: str


def build_main_widget(qt_widgets: Any) -> Any:
    """Build the visible UI shell for the dockable Maya panel."""

    widget = qt_widgets.QWidget()
    widget.setObjectName(PANEL_CONTENT_OBJECT_NAME)

    layout = qt_widgets.QVBoxLayout(widget)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(8)

    title = qt_widgets.QLabel(PANEL_TITLE)
    title.setObjectName("shaderHealthInspectorTitle")
    layout.addWidget(title)

    layout.addWidget(build_summary_header(qt_widgets))
    layout.addWidget(build_issues_table(qt_widgets))

    description = qt_widgets.QLabel(
        "Issues table baseline. Scene validation, details, and export actions "
        "will be added by the next Milestone 6 issues."
    )
    description.setObjectName("shaderHealthInspectorDescription")
    description.setWordWrap(True)
    layout.addWidget(description)

    validate_button = qt_widgets.QPushButton("Validate Scene")
    validate_button.setObjectName("shaderHealthInspectorValidateSceneButton")
    validate_button.setEnabled(False)
    validate_button.setToolTip("Validation is added in a later Maya UI issue.")
    layout.addWidget(validate_button)

    layout.addStretch(1)
    return widget


def build_summary_header(
    qt_widgets: Any,
    state: Optional[SummaryHeaderState] = None,
    profile_options: Sequence[str] = DEFAULT_PROFILE_OPTIONS,
) -> Any:
    """Build the summary/header widget shown at the top of the Maya panel."""

    summary_state = state or SummaryHeaderState()
    widget = qt_widgets.QWidget()
    widget.setObjectName(SUMMARY_HEADER_OBJECT_NAME)

    layout = qt_widgets.QVBoxLayout(widget)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(4)

    health_score_label = qt_widgets.QLabel(_health_score_text(summary_state))
    health_score_label.setObjectName(HEALTH_SCORE_LABEL_OBJECT_NAME)
    layout.addWidget(health_score_label)

    severity_counts_label = qt_widgets.QLabel(_severity_counts_text(summary_state))
    severity_counts_label.setObjectName(SEVERITY_COUNTS_LABEL_OBJECT_NAME)
    layout.addWidget(severity_counts_label)

    block_status_label = qt_widgets.QLabel(_block_status_text(summary_state))
    block_status_label.setObjectName(BLOCK_STATUS_LABEL_OBJECT_NAME)
    layout.addWidget(block_status_label)

    profile_label = qt_widgets.QLabel("Profile")
    profile_label.setObjectName(PROFILE_LABEL_OBJECT_NAME)
    layout.addWidget(profile_label)

    profile_dropdown = qt_widgets.QComboBox()
    profile_dropdown.setObjectName(PROFILE_DROPDOWN_OBJECT_NAME)
    profile_dropdown.addItems(list(profile_options))
    if summary_state.profile_id in profile_options:
        profile_dropdown.setCurrentText(summary_state.profile_id)
    profile_dropdown.setToolTip("Validation profile selection is wired in a later issue.")
    layout.addWidget(profile_dropdown)

    return widget


def build_issues_table(
    qt_widgets: Any,
    rows: Sequence[IssueTableRow] = (),
) -> Any:
    """Build the filterable/sortable issues table widget."""

    issue_rows = tuple(rows)
    widget = qt_widgets.QWidget()
    widget.setObjectName(ISSUES_TABLE_WIDGET_OBJECT_NAME)

    layout = qt_widgets.QVBoxLayout(widget)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(4)

    severity_filter_label = qt_widgets.QLabel("Severity Filter")
    layout.addWidget(severity_filter_label)

    severity_filter = qt_widgets.QComboBox()
    severity_filter.setObjectName(ISSUES_SEVERITY_FILTER_OBJECT_NAME)
    severity_filter.addItems(list(severity_filter_options(issue_rows)))
    severity_filter.setToolTip("Severity filtering is wired to validation results later.")
    layout.addWidget(severity_filter)

    sort_label = qt_widgets.QLabel("Sort By")
    layout.addWidget(sort_label)

    sort_dropdown = qt_widgets.QComboBox()
    sort_dropdown.setObjectName(ISSUES_SORT_DROPDOWN_OBJECT_NAME)
    sort_dropdown.addItems(list(ISSUES_SORT_KEYS))
    sort_dropdown.setCurrentText("severity")
    sort_dropdown.setToolTip("Column sorting is enabled on the issues table.")
    layout.addWidget(sort_dropdown)

    table = qt_widgets.QTableWidget()
    table.setObjectName(ISSUES_TABLE_OBJECT_NAME)
    table.setColumnCount(len(ISSUES_TABLE_COLUMNS))
    table.setHorizontalHeaderLabels(list(ISSUES_TABLE_COLUMNS))
    table.setSortingEnabled(True)
    populate_issues_table(qt_widgets, table, issue_rows)
    layout.addWidget(table)

    return widget


def populate_issues_table(
    qt_widgets: Any,
    table: Any,
    rows: Sequence[IssueTableRow],
) -> None:
    """Populate a Qt table widget with issue display rows."""

    table.setRowCount(len(rows))
    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(issue_row_cells(row)):
            table.setItem(row_index, column_index, qt_widgets.QTableWidgetItem(value))


def filter_issue_rows(
    rows: Sequence[IssueTableRow],
    severity_filter: str = ALL_SEVERITIES_LABEL,
) -> tuple[IssueTableRow, ...]:
    """Return issue rows matching the selected severity filter."""

    if severity_filter == ALL_SEVERITIES_LABEL:
        return tuple(rows)
    severity = _normalized_text(severity_filter)
    return tuple(row for row in rows if _normalized_text(row.severity) == severity)


def sort_issue_rows(
    rows: Sequence[IssueTableRow],
    sort_key: str = "severity",
    *,
    descending: bool = False,
) -> tuple[IssueTableRow, ...]:
    """Return issue rows sorted by a supported issues table column."""

    return tuple(
        sorted(
            rows,
            key=lambda row: _issue_sort_value(row, sort_key),
            reverse=descending,
        )
    )


def severity_filter_options(rows: Sequence[IssueTableRow]) -> tuple[str, ...]:
    """Return deterministic severity filter options for the supplied rows."""

    severities = sorted(
        {_normalized_text(row.severity) for row in rows if row.severity},
        key=lambda severity: (SEVERITY_SORT_ORDER.get(severity, 999), severity),
    )
    return (ALL_SEVERITIES_LABEL, *severities)


def issue_row_cells(row: IssueTableRow) -> tuple[str, str, str, str, str, str]:
    """Return display cells in issues table column order."""

    return (
        row.severity,
        row.material,
        row.node,
        row.issue,
        row.owner,
        row.rule,
    )


def _health_score_text(state: SummaryHeaderState) -> str:
    return f"Health: {state.health_score} / 100"


def _severity_counts_text(state: SummaryHeaderState) -> str:
    return (
        f"Critical: {state.critical_count}   "
        f"Error: {state.error_count}   "
        f"Warning: {state.warning_count}   "
        f"Info: {state.info_count}"
    )


def _block_status_text(state: SummaryHeaderState) -> str:
    publish_status = _yes_no(state.block_publish)
    deadline_status = _yes_no(state.block_deadline)
    return f"Publish Block: {publish_status}   Deadline Block: {deadline_status}"


def _issue_sort_value(row: IssueTableRow, sort_key: str) -> tuple[int, str]:
    if sort_key == "severity":
        severity = _normalized_text(row.severity)
        return (SEVERITY_SORT_ORDER.get(severity, 999), severity)
    if sort_key == "material":
        return (0, _normalized_text(row.material))
    if sort_key == "node":
        return (0, _normalized_text(row.node))
    if sort_key == "issue":
        return (0, _normalized_text(row.issue))
    if sort_key == "owner":
        return (0, _normalized_text(row.owner))
    if sort_key == "rule":
        return (0, _normalized_text(row.rule))
    raise ValueError(f"Unsupported issue table sort key: {sort_key}")


def _normalized_text(value: str) -> str:
    return value.casefold()


def _yes_no(value: bool) -> str:
    return "YES" if value else "NO"
