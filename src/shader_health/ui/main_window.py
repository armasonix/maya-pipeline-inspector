"""Maya Shader Health Inspector panel content."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Optional

from shader_health import __version__
from shader_health.maya.validation_pipeline import (
    ASSET_CLASS_NONE_ID,
    ProfileOption,
    list_asset_class_profile_options,
    list_workflow_profile_options,
)
from shader_health.ui.farm_tab import FarmActionCallbacks, build_farm_tab
from shader_health.ui.fix_queue import FixQueueActionCallbacks, build_fix_queue
from shader_health.ui.table_widgets import configure_read_only_table, make_read_only_item
from shader_health.ui.waiver_manager import WaiverManagerCallbacks, build_waiver_manager

PANEL_OBJECT_NAME = "shaderHealthInspectorPanel"
PANEL_TITLE = "Maya Shader Health Inspector"
PANEL_CONTENT_OBJECT_NAME = "shaderHealthInspectorPanelContent"
TAB_WIDGET_OBJECT_NAME = "shaderHealthInspectorTabWidget"
PANEL_HEADER_OBJECT_NAME = "shaderHealthInspectorPanelHeader"
SUMMARY_HEADER_OBJECT_NAME = "shaderHealthInspectorSummaryHeader"
HEALTH_SCORE_LABEL_OBJECT_NAME = "shaderHealthInspectorHealthScoreLabel"
SEVERITY_COUNTS_LABEL_OBJECT_NAME = "shaderHealthInspectorSeverityCountsLabel"
BLOCK_STATUS_LABEL_OBJECT_NAME = "shaderHealthInspectorBlockStatusLabel"
PROFILE_LABEL_OBJECT_NAME = "shaderHealthInspectorProfileLabel"
PROFILE_DROPDOWN_OBJECT_NAME = "shaderHealthInspectorProfileDropdown"
ASSET_CLASS_LABEL_OBJECT_NAME = "shaderHealthInspectorAssetClassLabel"
ASSET_CLASS_DROPDOWN_OBJECT_NAME = "shaderHealthInspectorAssetClassDropdown"
ISSUES_TABLE_WIDGET_OBJECT_NAME = "shaderHealthInspectorIssuesTableWidget"
ISSUES_SEVERITY_FILTER_OBJECT_NAME = "shaderHealthInspectorIssuesSeverityFilter"
ISSUES_SORT_DROPDOWN_OBJECT_NAME = "shaderHealthInspectorIssuesSortDropdown"
ISSUES_TABLE_OBJECT_NAME = "shaderHealthInspectorIssuesTable"
DETAILS_PANEL_OBJECT_NAME = "shaderHealthInspectorIssueDetailsPanel"
DETAILS_MESSAGE_LABEL_OBJECT_NAME = "shaderHealthInspectorIssueDetailsMessage"
DETAILS_WHY_LABEL_OBJECT_NAME = "shaderHealthInspectorIssueDetailsWhy"
DETAILS_VALUES_LABEL_OBJECT_NAME = "shaderHealthInspectorIssueDetailsValues"
DETAILS_GRAPH_TRACE_LABEL_OBJECT_NAME = "shaderHealthInspectorIssueDetailsGraphTrace"
DETAILS_REFERENCE_LABEL_OBJECT_NAME = "shaderHealthInspectorIssueDetailsReference"
DETAILS_FIX_LABEL_OBJECT_NAME = "shaderHealthInspectorIssueDetailsFix"
ISSUES_FILTERS_ROW_OBJECT_NAME = "shaderHealthInspectorIssuesFiltersRow"
EXPORT_ACTIONS_OBJECT_NAME = "shaderHealthInspectorExportActions"
EXPORT_JSON_BUTTON_OBJECT_NAME = "shaderHealthInspectorExportJsonButton"
EXPORT_HTML_BUTTON_OBJECT_NAME = "shaderHealthInspectorExportHtmlButton"
EXPORT_MANIFEST_BUTTON_OBJECT_NAME = "shaderHealthInspectorExportManifestButton"
EXPORT_MANIFEST_DIFF_BUTTON_OBJECT_NAME = "shaderHealthInspectorExportManifestDiffButton"
EXPORT_COMPARE_APPROVED_MANIFEST_BUTTON_OBJECT_NAME = (
    "shaderHealthInspectorCompareApprovedManifestButton"
)
REPORTS_STATUS_LABEL_OBJECT_NAME = "shaderHealthInspectorReportsStatusLabel"
VALIDATE_STATUS_LABEL_OBJECT_NAME = "shaderHealthInspectorDescription"
VALIDATE_SCENE_BUTTON_OBJECT_NAME = "shaderHealthInspectorValidateSceneButton"
VALIDATE_SELECTION_BUTTON_OBJECT_NAME = "shaderHealthInspectorValidateSelectionButton"
VALIDATE_PUBLISH_PREFLIGHT_BUTTON_OBJECT_NAME = "shaderHealthInspectorPublishPreflightButton"
VALIDATE_MANIFEST_GATE_BUTTON_OBJECT_NAME = "shaderHealthInspectorManifestGateButton"
EXPORT_COMPARE_AFTER_FIXES_BUTTON_OBJECT_NAME = "shaderHealthInspectorCompareAfterFixesButton"
ASSET_CLASS_HINT_LABEL_OBJECT_NAME = "shaderHealthInspectorAssetClassHintLabel"
ISSUES_OWNER_FILTER_OBJECT_NAME = "shaderHealthInspectorIssuesOwnerFilter"
ISSUES_VIEW_FILTER_OBJECT_NAME = "shaderHealthInspectorIssuesViewFilter"
DETAILS_ACTIONS_OBJECT_NAME = "shaderHealthInspectorIssueDetailsActions"
SELECT_NODE_BUTTON_OBJECT_NAME = "shaderHealthInspectorSelectNodeButton"
OPEN_ATTR_EDITOR_BUTTON_OBJECT_NAME = "shaderHealthInspectorOpenAttrEditorButton"
COPY_PATH_BUTTON_OBJECT_NAME = "shaderHealthInspectorCopyPathButton"
REVEAL_FILE_BUTTON_OBJECT_NAME = "shaderHealthInspectorRevealFileButton"
ASSET_CLASS_NONE_LABEL = "None"
DEFAULT_WORKFLOW_PROFILE_OPTIONS = list_workflow_profile_options() or (
    ProfileOption("artist_relaxed", "Artist Relaxed"),
    ProfileOption("publish_strict", "Publish Strict"),
    ProfileOption("deadline_critical", "Deadline Critical"),
    ProfileOption("supervisor_full", "Supervisor Full"),
)
DEFAULT_ASSET_CLASS_PROFILE_OPTIONS = list_asset_class_profile_options()
ALL_ISSUES_LABEL = "All issues"
BLOCKING_ONLY_LABEL = "Blocking only"
AUTO_FIXABLE_LABEL = "Auto-fixable"
ALL_OWNERS_LABEL = "All owners"
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
    asset_class_id: str = ASSET_CLASS_NONE_ID


@dataclass(frozen=True)
class IssueTableRow:
    """Display row for the Maya UI issues table."""

    severity: str
    material: str
    node: str
    issue: str
    owner: str
    rule: str


@dataclass(frozen=True)
class IssueDetailsState:
    """Display data for the Maya UI issue details panel."""

    message: str = "No issue selected"
    why: str = "Select an issue row to inspect why it failed."
    current_value: str = "N/A"
    expected_value: str = "N/A"
    graph_trace: str = "N/A"
    reference_safety: str = "Reference safety: N/A"
    fix_available: bool = False
    fix_description: str = "No safe fix selected."


@dataclass(frozen=True)
class ExportActionCallbacks:
    """Optional callbacks for report export UI buttons."""

    on_export_json: Optional[Callable[[], None]] = None
    on_export_html: Optional[Callable[[], None]] = None
    on_export_manifest: Optional[Callable[[], None]] = None
    on_export_manifest_diff: Optional[Callable[[], None]] = None
    on_compare_approved_manifest: Optional[Callable[[], None]] = None
    on_compare_after_fixes: Optional[Callable[[], None]] = None
    on_manifest_gate: Optional[Callable[[], None]] = None


@dataclass(frozen=True)
class ValidationActionCallbacks:
    """Optional callbacks for validation UI buttons."""

    on_validate_scene: Optional[Callable[[], None]] = None
    on_validate_selection: Optional[Callable[[], None]] = None
    on_publish_preflight: Optional[Callable[[], None]] = None
    on_manifest_gate: Optional[Callable[[], None]] = None
    on_profile_changed: Optional[Callable[[], None]] = None
    on_asset_class_changed: Optional[Callable[[], None]] = None


@dataclass(frozen=True)
class IssueDetailsActionCallbacks:
    """Optional callbacks for issue detail navigation actions."""

    on_select_node: Optional[Callable[[], None]] = None
    on_open_in_hypershade: Optional[Callable[[], None]] = None
    on_copy_path: Optional[Callable[[], None]] = None
    on_reveal_file: Optional[Callable[[], None]] = None


def build_main_widget(
    qt_widgets: Any,
    export_callbacks: Optional[ExportActionCallbacks] = None,
    fix_queue_callbacks: Optional[FixQueueActionCallbacks] = None,
    validation_callbacks: Optional[ValidationActionCallbacks] = None,
    issue_details_callbacks: Optional[IssueDetailsActionCallbacks] = None,
    waiver_callbacks: Optional[WaiverManagerCallbacks] = None,
    farm_callbacks: Optional[FarmActionCallbacks] = None,
) -> Any:
    """Build the visible UI shell for the dockable Maya panel."""

    export_callbacks = export_callbacks or ExportActionCallbacks()
    validation_callbacks = validation_callbacks or ValidationActionCallbacks()
    issue_details_callbacks = issue_details_callbacks or IssueDetailsActionCallbacks()
    waiver_callbacks = waiver_callbacks or WaiverManagerCallbacks()
    farm_callbacks = farm_callbacks or FarmActionCallbacks()

    widget = qt_widgets.QWidget()
    widget.setObjectName(PANEL_CONTENT_OBJECT_NAME)

    layout = qt_widgets.QVBoxLayout(widget)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(4)

    tabs = qt_widgets.QTabWidget()
    tabs.setObjectName(TAB_WIDGET_OBJECT_NAME)
    tabs.addTab(
        _build_validate_tab(qt_widgets, validation_callbacks, issue_details_callbacks),
        "Validate",
    )
    tabs.addTab(_build_waivers_tab(qt_widgets, waiver_callbacks), "Waivers")
    tabs.addTab(_build_fixes_tab(qt_widgets, fix_queue_callbacks), "Fixes")
    tabs.addTab(_build_reports_tab(qt_widgets, export_callbacks), "Reports")
    tabs.addTab(build_farm_tab(qt_widgets, callbacks=farm_callbacks), "Farm")
    layout.addWidget(tabs)

    return widget


def build_panel_header(qt_widgets: Any, *, version: str = __version__) -> Any:
    """Build the large title + version header shown at the top of each tab."""

    label = qt_widgets.QLabel(f"{PANEL_TITLE}  v{version}")
    label.setObjectName(PANEL_HEADER_OBJECT_NAME)
    set_style = getattr(label, "setStyleSheet", None)
    if set_style is not None:
        set_style("font-size: 14pt; font-weight: bold;")
    return label


def build_validation_actions(
    qt_widgets: Any,
    callbacks: Optional[ValidationActionCallbacks] = None,
) -> Any:
    """Build validate scene/selection controls."""

    validation_callbacks = callbacks or ValidationActionCallbacks()
    widget = qt_widgets.QWidget()
    widget.setObjectName("shaderHealthInspectorValidationActions")

    layout = qt_widgets.QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    layout.addWidget(
        _compact_button(
            qt_widgets,
            "Validate Scene",
            VALIDATE_SCENE_BUTTON_OBJECT_NAME,
            "Scan and validate the current Maya scene.",
            validation_callbacks.on_validate_scene,
        )
    )
    layout.addWidget(
        _compact_button(
            qt_widgets,
            "Validate Selection",
            VALIDATE_SELECTION_BUTTON_OBJECT_NAME,
            "Scan and validate the current Maya selection.",
            validation_callbacks.on_validate_selection,
        )
    )
    layout.addWidget(
        _compact_button(
            qt_widgets,
            "Publish Preflight",
            VALIDATE_PUBLISH_PREFLIGHT_BUTTON_OBJECT_NAME,
            "Run publish_strict validation and report whether publish would be blocked.",
            validation_callbacks.on_publish_preflight,
        )
    )
    layout.addWidget(
        _compact_button(
            qt_widgets,
            "Manifest Gate",
            VALIDATE_MANIFEST_GATE_BUTTON_OBJECT_NAME,
            "Compare the current scene manifest against the approved sidecar using gate policy.",
            validation_callbacks.on_manifest_gate,
        )
    )
    layout.addStretch(1)
    return widget


def build_summary_header(
    qt_widgets: Any,
    state: Optional[SummaryHeaderState] = None,
    workflow_options: Sequence[ProfileOption] = DEFAULT_WORKFLOW_PROFILE_OPTIONS,
    asset_class_options: Sequence[ProfileOption] = DEFAULT_ASSET_CLASS_PROFILE_OPTIONS,
    profile_changed: Optional[Callable[[], None]] = None,
    asset_class_changed: Optional[Callable[[], None]] = None,
) -> Any:
    """Build the summary/header widget shown on the Validate tab."""

    summary_state = state or SummaryHeaderState()
    widget = qt_widgets.QWidget()
    widget.setObjectName(SUMMARY_HEADER_OBJECT_NAME)

    layout = qt_widgets.QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
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

    profile_row = qt_widgets.QWidget()
    profile_layout = qt_widgets.QHBoxLayout(profile_row)
    profile_layout.setContentsMargins(0, 0, 0, 0)
    profile_layout.setSpacing(8)

    profile_label = qt_widgets.QLabel("Workflow")
    profile_label.setObjectName(PROFILE_LABEL_OBJECT_NAME)
    profile_layout.addWidget(profile_label)

    profile_dropdown = qt_widgets.QComboBox()
    profile_dropdown.setObjectName(PROFILE_DROPDOWN_OBJECT_NAME)
    _populate_profile_combo(profile_dropdown, workflow_options, summary_state.profile_id)
    profile_dropdown.setToolTip(
        "Validation workflow: role and publish/deadline blocking policy."
    )
    _connect_combo_changed(profile_dropdown, profile_changed)
    profile_layout.addWidget(profile_dropdown, 1)

    asset_class_label = qt_widgets.QLabel("Asset class")
    asset_class_label.setObjectName(ASSET_CLASS_LABEL_OBJECT_NAME)
    profile_layout.addWidget(asset_class_label)

    asset_class_dropdown = qt_widgets.QComboBox()
    asset_class_dropdown.setObjectName(ASSET_CLASS_DROPDOWN_OBJECT_NAME)
    _populate_asset_class_combo(
        asset_class_dropdown,
        asset_class_options,
        summary_state.asset_class_id,
    )
    asset_class_dropdown.setToolTip(
        "Optional overlay for texture resolution budgets. Select Hero/Prop/Background "
        "to enable resolution rules (4096/2048/1024 px). Workflow alone does not enable them."
    )
    _connect_combo_changed(asset_class_dropdown, asset_class_changed)
    profile_layout.addWidget(asset_class_dropdown, 1)

    layout.addWidget(profile_row)

    asset_class_hint = qt_widgets.QLabel(
        "Asset class enables resolution budget checks. Use Hero for 4096px, Prop for 2048px, "
        "Background for 1024px. Leave None to skip resolution rules."
    )
    asset_class_hint.setObjectName(ASSET_CLASS_HINT_LABEL_OBJECT_NAME)
    asset_class_hint.setWordWrap(True)
    layout.addWidget(asset_class_hint)
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
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)

    filters_row = qt_widgets.QWidget()
    filters_row.setObjectName(ISSUES_FILTERS_ROW_OBJECT_NAME)
    filters_layout = qt_widgets.QHBoxLayout(filters_row)
    filters_layout.setContentsMargins(0, 0, 0, 0)
    filters_layout.setSpacing(8)

    severity_filter = _issues_filter_combo(
        qt_widgets,
        label="Severity",
        object_name=ISSUES_SEVERITY_FILTER_OBJECT_NAME,
        items=list(severity_filter_options(issue_rows)),
        tooltip="Filter issues by severity.",
    )
    owner_filter = _issues_filter_combo(
        qt_widgets,
        label="Owner",
        object_name=ISSUES_OWNER_FILTER_OBJECT_NAME,
        items=[ALL_OWNERS_LABEL],
        tooltip="Filter issues by owner.",
    )
    view_filter = _issues_filter_combo(
        qt_widgets,
        label="View",
        object_name=ISSUES_VIEW_FILTER_OBJECT_NAME,
        items=[ALL_ISSUES_LABEL, BLOCKING_ONLY_LABEL, AUTO_FIXABLE_LABEL],
        tooltip="Filter blocking or auto-fixable issues.",
    )
    sort_dropdown = _issues_filter_combo(
        qt_widgets,
        label="Sort",
        object_name=ISSUES_SORT_DROPDOWN_OBJECT_NAME,
        items=list(ISSUES_SORT_KEYS),
        tooltip="Column sorting is enabled on the issues table.",
        current_text="severity",
    )

    for label, combo in (
        severity_filter,
        owner_filter,
        view_filter,
        sort_dropdown,
    ):
        filters_layout.addWidget(label)
        filters_layout.addWidget(combo, 0)

    filters_layout.addStretch(1)
    layout.addWidget(filters_row)

    table = qt_widgets.QTableWidget()
    table.setObjectName(ISSUES_TABLE_OBJECT_NAME)
    table.setColumnCount(len(ISSUES_TABLE_COLUMNS))
    table.setHorizontalHeaderLabels(list(ISSUES_TABLE_COLUMNS))
    table.setSortingEnabled(True)
    configure_read_only_table(table, qt_widgets)
    populate_issues_table(qt_widgets, table, issue_rows)
    layout.addWidget(table)

    return widget


def build_issue_details_panel(
    qt_widgets: Any,
    state: Optional[IssueDetailsState] = None,
    callbacks: Optional[IssueDetailsActionCallbacks] = None,
) -> Any:
    """Build the selected issue details panel."""

    details_state = state or IssueDetailsState()
    issue_callbacks = callbacks or IssueDetailsActionCallbacks()
    widget = qt_widgets.QWidget()
    widget.setObjectName(DETAILS_PANEL_OBJECT_NAME)

    layout = qt_widgets.QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)

    title_label = qt_widgets.QLabel("Issue Details")
    layout.addWidget(title_label)

    layout.addWidget(
        _details_label(
            qt_widgets,
            DETAILS_MESSAGE_LABEL_OBJECT_NAME,
            _details_message_text(details_state),
        )
    )
    layout.addWidget(
        _details_label(
            qt_widgets,
            DETAILS_WHY_LABEL_OBJECT_NAME,
            _details_why_text(details_state),
        )
    )
    layout.addWidget(
        _details_label(
            qt_widgets,
            DETAILS_VALUES_LABEL_OBJECT_NAME,
            _details_values_text(details_state),
        )
    )
    layout.addWidget(
        _details_label(
            qt_widgets,
            DETAILS_GRAPH_TRACE_LABEL_OBJECT_NAME,
            _details_graph_trace_text(details_state),
        )
    )
    layout.addWidget(
        _details_label(
            qt_widgets,
            DETAILS_REFERENCE_LABEL_OBJECT_NAME,
            _details_reference_text(details_state),
        )
    )
    layout.addWidget(
        _details_label(
            qt_widgets,
            DETAILS_FIX_LABEL_OBJECT_NAME,
            _details_fix_text(details_state),
        )
    )

    actions = qt_widgets.QWidget()
    actions.setObjectName(DETAILS_ACTIONS_OBJECT_NAME)
    actions_layout = qt_widgets.QHBoxLayout(actions)
    actions_layout.setContentsMargins(0, 0, 0, 0)
    actions_layout.setSpacing(4)
    for label, object_name, tooltip, callback in (
        (
            "Select Node",
            SELECT_NODE_BUTTON_OBJECT_NAME,
            "Select the issue node in Maya.",
            issue_callbacks.on_select_node,
        ),
        (
            "Open in HyperShade",
            OPEN_ATTR_EDITOR_BUTTON_OBJECT_NAME,
            "Open Hypershade shader network for the issue material.",
            issue_callbacks.on_open_in_hypershade,
        ),
        (
            "Copy Path",
            COPY_PATH_BUTTON_OBJECT_NAME,
            "Copy the issue path to the clipboard.",
            issue_callbacks.on_copy_path,
        ),
        (
            "Reveal File",
            REVEAL_FILE_BUTTON_OBJECT_NAME,
            "Reveal the issue file in the host file browser.",
            issue_callbacks.on_reveal_file,
        ),
    ):
        actions_layout.addWidget(
            _compact_button(qt_widgets, label, object_name, tooltip, callback)
        )
    actions_layout.addStretch(1)
    layout.addWidget(actions)

    return widget


def build_export_actions(
    qt_widgets: Any,
    callbacks: Optional[ExportActionCallbacks] = None,
) -> Any:
    """Build compact report export buttons for the Reports tab."""

    export_callbacks = callbacks or ExportActionCallbacks()
    widget = qt_widgets.QWidget()
    widget.setObjectName(EXPORT_ACTIONS_OBJECT_NAME)

    layout = qt_widgets.QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)

    status_label = qt_widgets.QLabel(
        "Reports export validation artifacts. Manifest diff compares the Material Passport "
        "(textures, fingerprints) — not validation fixes like colorSpace. Workflow: "
        "1) Export Shader Manifest as approved baseline, 2) change scene, 3) Compare After Fixes."
    )
    status_label.setObjectName(REPORTS_STATUS_LABEL_OBJECT_NAME)
    status_label.setWordWrap(True)
    layout.addWidget(status_label)

    grid_host = qt_widgets.QWidget()
    grid = qt_widgets.QGridLayout(grid_host)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setSpacing(4)

    buttons = (
        (
            "Export JSON Report",
            EXPORT_JSON_BUTTON_OBJECT_NAME,
            "Write the current shader health JSON report next to the scene.",
            export_callbacks.on_export_json,
        ),
        (
            "Export HTML Report",
            EXPORT_HTML_BUTTON_OBJECT_NAME,
            "Write the current shader health HTML report next to the scene.",
            export_callbacks.on_export_html,
        ),
        (
            "Export Shader Manifest",
            EXPORT_MANIFEST_BUTTON_OBJECT_NAME,
            "Write schema 1.1 Material Passport next to the scene (approved baseline).",
            export_callbacks.on_export_manifest,
        ),
        (
            "Compare After Fixes",
            EXPORT_COMPARE_AFTER_FIXES_BUTTON_OBJECT_NAME,
            "Revalidate, then diff current manifest vs approved sidecar (paths/fingerprints).",
            export_callbacks.on_compare_after_fixes,
        ),
        (
            "Export Manifest Diff",
            EXPORT_MANIFEST_DIFF_BUTTON_OBJECT_NAME,
            "Pick a baseline manifest JSON and export JSON/HTML diff against the current scene.",
            export_callbacks.on_export_manifest_diff,
        ),
        (
            "Compare to Approved Manifest",
            EXPORT_COMPARE_APPROVED_MANIFEST_BUTTON_OBJECT_NAME,
            "Diff against the approved manifest sidecar next to the scene when available.",
            export_callbacks.on_compare_approved_manifest,
        ),
        (
            "Manifest Gate",
            VALIDATE_MANIFEST_GATE_BUTTON_OBJECT_NAME,
            "Run manifest regression gate policy against the approved sidecar.",
            export_callbacks.on_manifest_gate,
        ),
    )
    for index, (label, object_name, tooltip, callback) in enumerate(buttons):
        row = index // 3
        column = index % 3
        grid.addWidget(
            _compact_button(qt_widgets, label, object_name, tooltip, callback),
            row,
            column,
        )

    layout.addWidget(grid_host)
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
            table.setItem(row_index, column_index, make_read_only_item(qt_widgets, value))


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


def owner_filter_options(rows: Sequence[IssueTableRow]) -> tuple[str, ...]:
    """Return deterministic owner filter options for the supplied rows."""

    owners = sorted({_normalized_text(row.owner) for row in rows if row.owner})
    return (ALL_OWNERS_LABEL, *owners)


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


def combo_profile_id(combo: Any) -> str:
    """Return the profile id stored on the active combo box item."""

    current_data = getattr(combo, "currentData", None)
    if current_data is not None:
        data = current_data()
        if data is not None:
            return str(data)
    current_text = getattr(combo, "currentText", lambda: "")()
    return str(current_text or "")


def _build_validate_tab(
    qt_widgets: Any,
    validation_callbacks: ValidationActionCallbacks,
    issue_details_callbacks: IssueDetailsActionCallbacks,
) -> Any:
    tab = qt_widgets.QWidget()
    layout = qt_widgets.QVBoxLayout(tab)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(6)

    layout.addWidget(build_panel_header(qt_widgets))
    layout.addWidget(
        build_summary_header(
            qt_widgets,
            profile_changed=validation_callbacks.on_profile_changed,
            asset_class_changed=validation_callbacks.on_asset_class_changed,
        )
    )
    layout.addWidget(build_validation_actions(qt_widgets, callbacks=validation_callbacks))
    layout.addWidget(build_issues_table(qt_widgets))
    layout.addWidget(build_issue_details_panel(qt_widgets, callbacks=issue_details_callbacks))

    description = qt_widgets.QLabel("Ready to validate the current scene or selection.")
    description.setObjectName(VALIDATE_STATUS_LABEL_OBJECT_NAME)
    description.setWordWrap(True)
    layout.addWidget(description)
    layout.addStretch(1)
    return tab


def _build_waivers_tab(
    qt_widgets: Any,
    waiver_callbacks: WaiverManagerCallbacks,
) -> Any:
    tab = qt_widgets.QWidget()
    layout = qt_widgets.QVBoxLayout(tab)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(6)

    layout.addWidget(build_panel_header(qt_widgets))
    layout.addWidget(build_waiver_manager(qt_widgets, callbacks=waiver_callbacks))
    layout.addStretch(1)
    return tab


def _build_fixes_tab(
    qt_widgets: Any,
    fix_queue_callbacks: Optional[FixQueueActionCallbacks],
) -> Any:
    tab = qt_widgets.QWidget()
    layout = qt_widgets.QVBoxLayout(tab)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(6)

    layout.addWidget(build_panel_header(qt_widgets))
    layout.addWidget(build_fix_queue(qt_widgets, callbacks=fix_queue_callbacks), 1)
    return tab


def _build_reports_tab(
    qt_widgets: Any,
    export_callbacks: ExportActionCallbacks,
) -> Any:
    tab = qt_widgets.QWidget()
    layout = qt_widgets.QVBoxLayout(tab)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(6)

    layout.addWidget(build_panel_header(qt_widgets))
    layout.addWidget(build_export_actions(qt_widgets, callbacks=export_callbacks))
    layout.addStretch(1)
    return tab


def _populate_profile_combo(
    combo: Any,
    options: Sequence[ProfileOption],
    selected_id: str,
) -> None:
    add_item = getattr(combo, "addItem", None)
    if add_item is None:
        return
    for option in options:
        add_item(option.display_name, option.profile_id)
    _set_combo_selection(combo, options, selected_id)


def _populate_asset_class_combo(
    combo: Any,
    options: Sequence[ProfileOption],
    selected_id: str,
) -> None:
    add_item = getattr(combo, "addItem", None)
    if add_item is None:
        return
    add_item(ASSET_CLASS_NONE_LABEL, ASSET_CLASS_NONE_ID)
    for option in options:
        add_item(option.display_name, option.profile_id)
    normalized = selected_id or ASSET_CLASS_NONE_ID
    if normalized == ASSET_CLASS_NONE_ID:
        set_current = getattr(combo, "setCurrentIndex", None)
        if set_current is not None:
            set_current(0)
        return
    _set_combo_selection(combo, options, normalized)


def _set_combo_selection(
    combo: Any,
    options: Sequence[ProfileOption],
    selected_id: str,
) -> None:
    find_data = getattr(combo, "findData", None)
    set_current_index = getattr(combo, "setCurrentIndex", None)
    if find_data is None or set_current_index is None:
        set_current_text = getattr(combo, "setCurrentText", None)
        if set_current_text is not None:
            for option in options:
                if option.profile_id == selected_id:
                    set_current_text(option.display_name)
                    return
        return
    index = find_data(selected_id)
    if index >= 0:
        set_current_index(index)


def _connect_combo_changed(combo: Any, callback: Optional[Callable[[], None]]) -> None:
    if callback is None:
        return
    signal = getattr(combo, "currentIndexChanged", None)
    connect = getattr(signal, "connect", None)
    if connect is not None:
        connect(lambda *_: callback())


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


def _details_label(qt_widgets: Any, object_name: str, text: str) -> Any:
    label = qt_widgets.QLabel(text)
    label.setObjectName(object_name)
    label.setWordWrap(True)
    return label


def _details_message_text(state: IssueDetailsState) -> str:
    return f"Message: {state.message}"


def _details_why_text(state: IssueDetailsState) -> str:
    return f"Why: {state.why}"


def _details_values_text(state: IssueDetailsState) -> str:
    return f"Current: {state.current_value}   Expected: {state.expected_value}"


def _details_graph_trace_text(state: IssueDetailsState) -> str:
    return f"Graph Trace: {state.graph_trace}"


def _details_reference_text(state: IssueDetailsState) -> str:
    return state.reference_safety


def _details_fix_text(state: IssueDetailsState) -> str:
    fix_status = _yes_no(state.fix_available)
    return f"Fix Available: {fix_status}   {state.fix_description}"


def _issues_filter_combo(
    qt_widgets: Any,
    *,
    label: str,
    object_name: str,
    items: Sequence[str],
    tooltip: str,
    current_text: Optional[str] = None,
) -> tuple[Any, Any]:
    label_widget = qt_widgets.QLabel(label)
    combo = qt_widgets.QComboBox()
    combo.setObjectName(object_name)
    combo.addItems(list(items))
    combo.setToolTip(tooltip)
    if current_text is not None:
        combo.setCurrentText(current_text)
    minimum_contents = getattr(combo, "setMinimumContentsLength", None)
    if minimum_contents is not None:
        minimum_contents(max(len(item) for item in items) if items else 8)
    size_policy = getattr(qt_widgets, "QSizePolicy", None)
    policy = getattr(combo, "setSizePolicy", None)
    if size_policy is not None and policy is not None:
        policy(size_policy.Preferred, size_policy.Fixed)
    adjust_policy = getattr(combo, "setSizeAdjustPolicy", None)
    combo_class = getattr(qt_widgets, "QComboBox", None)
    adjust_to_contents = getattr(combo_class, "AdjustToContents", None)
    if adjust_policy is not None and adjust_to_contents is not None:
        adjust_policy(adjust_to_contents)
    return label_widget, combo


def _compact_button(
    qt_widgets: Any,
    label: str,
    object_name: str,
    tooltip: str,
    callback: Optional[Callable[[], None]],
) -> Any:
    button = qt_widgets.QPushButton(label)
    button.setObjectName(object_name)
    button.setToolTip(tooltip)
    size_policy = getattr(qt_widgets, "QSizePolicy", None)
    policy = getattr(button, "setSizePolicy", None)
    if size_policy is not None and policy is not None:
        policy(size_policy.Preferred, size_policy.Fixed)
    _connect_button(button, callback)
    return button


def _connect_button(button: Any, callback: Optional[Callable[[], None]]) -> None:
    if callback is None:
        return
    clicked = getattr(button, "clicked", None)
    connect = getattr(clicked, "connect", None)
    if connect is not None:
        connect(callback)


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
