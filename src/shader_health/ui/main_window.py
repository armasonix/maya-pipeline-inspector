"""Maya Shader Health Inspector panel content."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from shader_health import __version__
from shader_health.maya.validation_pipeline import (
    ASSET_CLASS_NONE_ID,
    ProfileOption,
    list_asset_class_profile_options,
    list_workflow_profile_options,
)
from shader_health.studio_config import StudioConfig
from shader_health.ui.farm_tab import FarmActionCallbacks, build_farm_tab
from shader_health.ui.fix_queue import FixQueueActionCallbacks, build_fix_queue
from shader_health.ui.qt import load_qt_core
from shader_health.ui.settings_panel import SettingsActionCallbacks, build_settings_view
from shader_health.ui.table_widgets import configure_read_only_table, make_read_only_item
from shader_health.ui.waiver_manager import WaiverManagerCallbacks, build_waiver_manager
from shader_health.user_config import UserPreferences

PANEL_OBJECT_NAME = "shaderHealthInspectorPanel"
PANEL_TITLE = "Maya Shader Health Inspector"
PANEL_CONTENT_OBJECT_NAME = "shaderHealthInspectorPanelContent"
TAB_WIDGET_OBJECT_NAME = "shaderHealthInspectorTabWidget"
PANEL_HEADER_OBJECT_NAME = "shaderHealthInspectorPanelHeader"
PANEL_HEADER_TITLE_OBJECT_NAME = "shaderHealthInspectorPanelHeaderTitle"
SETTINGS_GEAR_BUTTON_OBJECT_NAME = "shaderHealthInspectorSettingsGearButton"
PANEL_BODY_STACK_OBJECT_NAME = "shaderHealthInspectorPanelBodyStack"
MAIN_VIEW_OBJECT_NAME = "shaderHealthInspectorMainView"
SETTINGS_VIEW_INDEX = 1
SUMMARY_HEADER_OBJECT_NAME = "shaderHealthInspectorSummaryHeader"
VALIDATE_STICKY_CHROME_OBJECT_NAME = "shaderHealthInspectorValidateStickyChrome"
VALIDATE_ACTION_BAR_OBJECT_NAME = "shaderHealthInspectorValidateActionBar"
VALIDATE_PRIMARY_ACTIONS_OBJECT_NAME = "shaderHealthInspectorValidatePrimaryActions"
VALIDATE_PIPELINE_ACTIONS_OBJECT_NAME = "shaderHealthInspectorValidatePipelineActions"
VALIDATE_TRIAGE_ACTIONS_OBJECT_NAME = "shaderHealthInspectorValidateTriageActions"
VALIDATE_ISSUES_SPLITTER_OBJECT_NAME = "shaderHealthInspectorValidateIssuesSplitter"
HEALTH_SCORE_LABEL_OBJECT_NAME = "shaderHealthInspectorHealthScoreLabel"
SEVERITY_COUNTS_LABEL_OBJECT_NAME = "shaderHealthInspectorSeverityCountsLabel"
SEVERITY_COUNTS_ROW_OBJECT_NAME = "shaderHealthInspectorSeverityCountsRow"
CRITICAL_COUNT_LABEL_OBJECT_NAME = "shaderHealthInspectorCriticalCountLabel"
ERROR_COUNT_LABEL_OBJECT_NAME = "shaderHealthInspectorErrorCountLabel"
WARNING_COUNT_LABEL_OBJECT_NAME = "shaderHealthInspectorWarningCountLabel"
INFO_COUNT_LABEL_OBJECT_NAME = "shaderHealthInspectorInfoCountLabel"
PUBLISH_BLOCK_LABEL_OBJECT_NAME = "shaderHealthInspectorPublishBlockLabel"
PUBLISH_BLOCK_LAMP_OBJECT_NAME = "shaderHealthInspectorPublishBlockLamp"
DEADLINE_BLOCK_LABEL_OBJECT_NAME = "shaderHealthInspectorDeadlineBlockLabel"
DEADLINE_BLOCK_LAMP_OBJECT_NAME = "shaderHealthInspectorDeadlineBlockLamp"
BLOCK_STATUS_LABEL_OBJECT_NAME = "shaderHealthInspectorBlockStatusLabel"
SCENE_NAME_LABEL_OBJECT_NAME = "shaderHealthInspectorSceneNameLabel"
LAST_VALIDATED_LABEL_OBJECT_NAME = "shaderHealthInspectorLastValidatedLabel"
SCAN_SCOPE_LABEL_OBJECT_NAME = "shaderHealthInspectorScanScopeLabel"
PROFILE_CHIP_LABEL_OBJECT_NAME = "shaderHealthInspectorProfileChipLabel"
ASSET_CLASS_CHIP_LABEL_OBJECT_NAME = "shaderHealthInspectorAssetClassChipLabel"
PROFILE_LABEL_OBJECT_NAME = "shaderHealthInspectorProfileLabel"
PROFILE_DROPDOWN_OBJECT_NAME = "shaderHealthInspectorProfileDropdown"
ASSET_CLASS_LABEL_OBJECT_NAME = "shaderHealthInspectorAssetClassLabel"
ASSET_CLASS_DROPDOWN_OBJECT_NAME = "shaderHealthInspectorAssetClassDropdown"
ISSUES_TABLE_WIDGET_OBJECT_NAME = "shaderHealthInspectorIssuesTableWidget"
ISSUES_SEVERITY_FILTER_OBJECT_NAME = "shaderHealthInspectorIssuesSeverityFilter"
ISSUES_SORT_DROPDOWN_OBJECT_NAME = "shaderHealthInspectorIssuesSortDropdown"
ISSUES_TABLE_OBJECT_NAME = "shaderHealthInspectorIssuesTable"
DETAILS_PANEL_OBJECT_NAME = "shaderHealthInspectorIssueDetailsPanel"
DETAILS_SCROLL_AREA_OBJECT_NAME = "shaderHealthInspectorIssueDetailsScrollArea"
DETAILS_SCROLL_CONTENT_OBJECT_NAME = "shaderHealthInspectorIssueDetailsScrollContent"
DETAILS_PANEL_MIN_WIDTH = 180
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
VALIDATE_STATUS_ROW_OBJECT_NAME = "shaderHealthInspectorValidateStatusRow"
VALIDATE_PROGRESS_BAR_OBJECT_NAME = "shaderHealthInspectorValidateProgressBar"
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
SEVERITY_ROW_NUMBER_COLORS = {
    "critical": "#e74c3c",
    "error": "#e67e22",
    "warning": "#f1c40f",
    "info": "#22d3ee",
}
BLOCK_LAMP_COLORS = {
    True: "#e74c3c",
    False: "#2ecc71",
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
    scene_name: str = ""
    last_validated_at: str = ""
    scan_scope: str = ""
    workflow_display_name: str = ""
    asset_class_display_name: str = ASSET_CLASS_NONE_LABEL


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
class PanelNavigationCallbacks:
    """Callbacks for persistent panel chrome outside the tab bodies."""

    on_open_settings: Optional[Callable[[], None]] = None


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
    settings_callbacks: Optional[SettingsActionCallbacks] = None,
    navigation_callbacks: Optional[PanelNavigationCallbacks] = None,
    studio_config: Optional[StudioConfig] = None,
    user_config: Optional[UserPreferences] = None,
) -> Any:
    """Build the visible UI shell for the dockable Maya panel."""

    export_callbacks = export_callbacks or ExportActionCallbacks()
    validation_callbacks = validation_callbacks or ValidationActionCallbacks()
    issue_details_callbacks = issue_details_callbacks or IssueDetailsActionCallbacks()
    waiver_callbacks = waiver_callbacks or WaiverManagerCallbacks()
    farm_callbacks = farm_callbacks or FarmActionCallbacks()
    settings_callbacks = settings_callbacks or SettingsActionCallbacks()
    navigation_callbacks = navigation_callbacks or PanelNavigationCallbacks()
    active_studio_config = studio_config or StudioConfig.default()
    active_user_config = user_config or UserPreferences.default()

    widget = qt_widgets.QWidget()
    widget.setObjectName(PANEL_CONTENT_OBJECT_NAME)

    layout = qt_widgets.QVBoxLayout(widget)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(4)

    layout.addWidget(build_panel_header(qt_widgets, navigation_callbacks=navigation_callbacks))

    stack = qt_widgets.QStackedWidget()
    stack.setObjectName(PANEL_BODY_STACK_OBJECT_NAME)

    main_view = qt_widgets.QWidget()
    main_view.setObjectName(MAIN_VIEW_OBJECT_NAME)
    main_layout = qt_widgets.QVBoxLayout(main_view)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(4)

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
    main_layout.addWidget(tabs)
    stack.addWidget(main_view)

    settings_view = build_settings_view(
        qt_widgets,
        config=active_studio_config,
        user_config=active_user_config,
        callbacks=settings_callbacks,
    )
    stack.addWidget(settings_view)

    layout.addWidget(stack)

    return widget


def build_panel_header(
    qt_widgets: Any,
    *,
    version: str = __version__,
    navigation_callbacks: Optional[PanelNavigationCallbacks] = None,
) -> Any:
    """Build the persistent title row with a settings gear on the left."""

    navigation_callbacks = navigation_callbacks or PanelNavigationCallbacks()

    row = qt_widgets.QWidget()
    row.setObjectName(PANEL_HEADER_OBJECT_NAME)
    row_layout = qt_widgets.QHBoxLayout(row)
    row_layout.setContentsMargins(0, 0, 0, 0)
    row_layout.setSpacing(8)

    gear_button = qt_widgets.QPushButton("\u2699")
    gear_button.setObjectName(SETTINGS_GEAR_BUTTON_OBJECT_NAME)
    set_tooltip = getattr(gear_button, "setToolTip", None)
    if set_tooltip is not None:
        set_tooltip("Open settings")
    set_fixed_width = getattr(gear_button, "setFixedWidth", None)
    if set_fixed_width is not None:
        set_fixed_width(34)
    clicked = getattr(gear_button, "clicked", None)
    connect = getattr(clicked, "connect", None)
    if connect is not None and navigation_callbacks.on_open_settings is not None:
        connect(navigation_callbacks.on_open_settings)
    row_layout.addWidget(gear_button)

    title_label = qt_widgets.QLabel(f"{PANEL_TITLE}  v{version}")
    title_label.setObjectName(PANEL_HEADER_TITLE_OBJECT_NAME)
    set_style = getattr(title_label, "setStyleSheet", None)
    if set_style is not None:
        set_style("font-size: 14pt; font-weight: bold;")
    row_layout.addWidget(title_label, 1)

    return row


def build_validation_actions(
    qt_widgets: Any,
    callbacks: Optional[ValidationActionCallbacks] = None,
    issue_details_callbacks: Optional[IssueDetailsActionCallbacks] = None,
) -> Any:
    """Build grouped validate controls: primary, pipeline, and issue triage actions."""

    validation_callbacks = callbacks or ValidationActionCallbacks()
    issue_callbacks = issue_details_callbacks or IssueDetailsActionCallbacks()
    widget = qt_widgets.QWidget()
    widget.setObjectName(VALIDATE_ACTION_BAR_OBJECT_NAME)

    layout = qt_widgets.QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)

    primary_group = qt_widgets.QWidget()
    primary_group.setObjectName(VALIDATE_PRIMARY_ACTIONS_OBJECT_NAME)
    primary_layout = qt_widgets.QHBoxLayout(primary_group)
    primary_layout.setContentsMargins(0, 0, 0, 0)
    primary_layout.setSpacing(4)
    primary_layout.addWidget(
        _compact_button(
            qt_widgets,
            "Validate Scene",
            VALIDATE_SCENE_BUTTON_OBJECT_NAME,
            "Scan and validate the current Maya scene. Shortcut: F5.",
            validation_callbacks.on_validate_scene,
        )
    )
    primary_layout.addWidget(
        _compact_button(
            qt_widgets,
            "Validate Selection",
            VALIDATE_SELECTION_BUTTON_OBJECT_NAME,
            "Scan and validate the current Maya selection.",
            validation_callbacks.on_validate_selection,
        )
    )
    layout.addWidget(primary_group)
    layout.addWidget(_action_bar_separator(qt_widgets))

    pipeline_group = qt_widgets.QWidget()
    pipeline_group.setObjectName(VALIDATE_PIPELINE_ACTIONS_OBJECT_NAME)
    pipeline_layout = qt_widgets.QHBoxLayout(pipeline_group)
    pipeline_layout.setContentsMargins(0, 0, 0, 0)
    pipeline_layout.setSpacing(4)
    pipeline_layout.addWidget(
        _compact_button(
            qt_widgets,
            "Publish Preflight",
            VALIDATE_PUBLISH_PREFLIGHT_BUTTON_OBJECT_NAME,
            "Run publish_strict validation and report whether publish would be blocked.",
            validation_callbacks.on_publish_preflight,
        )
    )
    pipeline_layout.addWidget(
        _compact_button(
            qt_widgets,
            "Manifest Gate",
            VALIDATE_MANIFEST_GATE_BUTTON_OBJECT_NAME,
            "Compare the current scene manifest against the approved sidecar using gate policy.",
            validation_callbacks.on_manifest_gate,
        )
    )
    layout.addWidget(pipeline_group)
    layout.addWidget(_action_bar_separator(qt_widgets))
    layout.addWidget(_build_triage_action_group(qt_widgets, issue_callbacks))
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
    """Build the compact sticky summary/header widget for the Validate tab."""

    summary_state = state or SummaryHeaderState()
    widget = qt_widgets.QWidget()
    widget.setObjectName(SUMMARY_HEADER_OBJECT_NAME)

    layout = qt_widgets.QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)

    metrics_row = qt_widgets.QWidget()
    metrics_layout = qt_widgets.QHBoxLayout(metrics_row)
    metrics_layout.setContentsMargins(0, 0, 0, 0)
    metrics_layout.setSpacing(8)

    health_score_label = qt_widgets.QLabel(_health_score_text(summary_state))
    health_score_label.setObjectName(HEALTH_SCORE_LABEL_OBJECT_NAME)
    metrics_layout.addWidget(health_score_label)

    severity_counts_row = _build_severity_counts_row(qt_widgets, summary_state)
    metrics_layout.addWidget(severity_counts_row)

    publish_label = qt_widgets.QLabel(
        f"Publish Block: {_yes_no(summary_state.block_publish)}"
    )
    publish_label.setObjectName(PUBLISH_BLOCK_LABEL_OBJECT_NAME)
    metrics_layout.addWidget(publish_label)

    publish_lamp = qt_widgets.QLabel("")
    publish_lamp.setObjectName(PUBLISH_BLOCK_LAMP_OBJECT_NAME)
    _apply_block_lamp_style(publish_lamp, summary_state.block_publish)
    metrics_layout.addWidget(publish_lamp)

    deadline_label = qt_widgets.QLabel(
        f"Deadline Block: {_yes_no(summary_state.block_deadline)}"
    )
    deadline_label.setObjectName(DEADLINE_BLOCK_LABEL_OBJECT_NAME)
    metrics_layout.addWidget(deadline_label)

    deadline_lamp = qt_widgets.QLabel("")
    deadline_lamp.setObjectName(DEADLINE_BLOCK_LAMP_OBJECT_NAME)
    _apply_block_lamp_style(deadline_lamp, summary_state.block_deadline)
    metrics_layout.addWidget(deadline_lamp)

    _set_compact_horizontal(qt_widgets, publish_label)
    _set_compact_horizontal(qt_widgets, deadline_label)
    metrics_layout.addStretch(1)
    layout.addWidget(metrics_row)

    context_row = qt_widgets.QWidget()
    context_layout = qt_widgets.QHBoxLayout(context_row)
    context_layout.setContentsMargins(0, 0, 0, 0)
    context_layout.setSpacing(8)

    scene_label = qt_widgets.QLabel(format_scene_display_name(summary_state.scene_name))
    scene_label.setObjectName(SCENE_NAME_LABEL_OBJECT_NAME)
    context_layout.addWidget(scene_label)

    profile_chip = qt_widgets.QLabel(
        format_profile_chip_text(
            summary_state.workflow_display_name,
            summary_state.profile_id,
        )
    )
    profile_chip.setObjectName(PROFILE_CHIP_LABEL_OBJECT_NAME)
    context_layout.addWidget(profile_chip)

    asset_chip = qt_widgets.QLabel(
        format_asset_class_chip_text(summary_state.asset_class_display_name)
    )
    asset_chip.setObjectName(ASSET_CLASS_CHIP_LABEL_OBJECT_NAME)
    context_layout.addWidget(asset_chip)

    last_validated_label = qt_widgets.QLabel(
        format_last_validated_display(summary_state.last_validated_at)
    )
    last_validated_label.setObjectName(LAST_VALIDATED_LABEL_OBJECT_NAME)
    context_layout.addWidget(last_validated_label)

    scan_scope_label = qt_widgets.QLabel(format_scan_scope_display(summary_state.scan_scope))
    scan_scope_label.setObjectName(SCAN_SCOPE_LABEL_OBJECT_NAME)
    context_layout.addWidget(scan_scope_label)
    context_layout.addStretch(1)
    layout.addWidget(context_row)

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
    profile_layout.addWidget(profile_dropdown, 0)
    _set_compact_horizontal(qt_widgets, profile_dropdown)

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
        "Optional overlay for texture resolution budgets. Hero=4096px, Prop=2048px, "
        "Background=1024px. None skips resolution rules."
    )
    _connect_combo_changed(asset_class_dropdown, asset_class_changed)
    profile_layout.addWidget(asset_class_dropdown, 0)
    _set_compact_horizontal(qt_widgets, asset_class_dropdown)
    profile_layout.addStretch(1)

    layout.addWidget(profile_row)
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
    filters_layout.setSpacing(4)

    severity_filter = _issues_filter_combo_compact(
        qt_widgets,
        label="Severity",
        object_name=ISSUES_SEVERITY_FILTER_OBJECT_NAME,
        items=list(severity_filter_options(issue_rows)),
        tooltip="Filter issues by severity.",
    )
    owner_filter = _issues_filter_combo_compact(
        qt_widgets,
        label="Owner",
        object_name=ISSUES_OWNER_FILTER_OBJECT_NAME,
        items=[ALL_OWNERS_LABEL],
        tooltip="Filter issues by owner.",
    )
    view_filter = _issues_filter_combo_compact(
        qt_widgets,
        label="View",
        object_name=ISSUES_VIEW_FILTER_OBJECT_NAME,
        items=[ALL_ISSUES_LABEL, BLOCKING_ONLY_LABEL, AUTO_FIXABLE_LABEL],
        tooltip="Filter blocking or auto-fixable issues.",
    )
    sort_dropdown = _issues_filter_combo_compact(
        qt_widgets,
        label="Sort",
        object_name=ISSUES_SORT_DROPDOWN_OBJECT_NAME,
        items=list(ISSUES_SORT_KEYS),
        tooltip="Sort the issues table by column.",
        current_text="severity",
    )

    for combo in (
        severity_filter,
        owner_filter,
        view_filter,
        sort_dropdown,
    ):
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
    widget = qt_widgets.QWidget()
    widget.setObjectName(DETAILS_PANEL_OBJECT_NAME)

    layout = qt_widgets.QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)
    _set_expanding_panel(qt_widgets, widget)
    set_minimum_width = getattr(widget, "setMinimumWidth", None)
    if set_minimum_width is not None:
        set_minimum_width(DETAILS_PANEL_MIN_WIDTH)

    title_label = qt_widgets.QLabel("Issue Details")
    _set_compact_horizontal(qt_widgets, title_label)
    layout.addWidget(title_label)

    detail_sections = (
        _details_label(
            qt_widgets,
            DETAILS_MESSAGE_LABEL_OBJECT_NAME,
            _details_message_text(details_state),
        ),
        _details_label(
            qt_widgets,
            DETAILS_WHY_LABEL_OBJECT_NAME,
            _details_why_text(details_state),
        ),
        _details_label(
            qt_widgets,
            DETAILS_VALUES_LABEL_OBJECT_NAME,
            _details_values_text(details_state),
        ),
        _details_label(
            qt_widgets,
            DETAILS_GRAPH_TRACE_LABEL_OBJECT_NAME,
            _details_graph_trace_text(details_state),
        ),
        _details_label(
            qt_widgets,
            DETAILS_REFERENCE_LABEL_OBJECT_NAME,
            _details_reference_text(details_state),
        ),
        _details_label(
            qt_widgets,
            DETAILS_FIX_LABEL_OBJECT_NAME,
            _details_fix_text(details_state),
        ),
    )

    scroll_area_class = getattr(qt_widgets, "QScrollArea", None)
    if scroll_area_class is None:
        for index, label in enumerate(detail_sections):
            _set_details_section_label(qt_widgets, label)
            layout.addWidget(label)
            if index < len(detail_sections) - 1:
                layout.addWidget(_details_separator(qt_widgets))
        layout.addStretch(1)
        return widget

    scroll_area = scroll_area_class()
    scroll_area.setObjectName(DETAILS_SCROLL_AREA_OBJECT_NAME)
    _configure_borderless_scroll_area(scroll_area, qt_widgets)
    set_widget_resizable = getattr(scroll_area, "setWidgetResizable", None)
    if set_widget_resizable is not None:
        set_widget_resizable(True)
    set_horizontal_scroll = getattr(scroll_area, "setHorizontalScrollBarPolicy", None)
    scroll_bar_policy = getattr(qt_widgets, "Qt", None)
    if set_horizontal_scroll is not None and scroll_bar_policy is not None:
        scroll_always_off = getattr(scroll_bar_policy, "ScrollBarAlwaysOff", None)
        if scroll_always_off is not None:
            set_horizontal_scroll(scroll_always_off)
    _set_expanding_panel(qt_widgets, scroll_area)

    scroll_content = qt_widgets.QWidget()
    scroll_content.setObjectName(DETAILS_SCROLL_CONTENT_OBJECT_NAME)
    content_layout = qt_widgets.QVBoxLayout(scroll_content)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(2)
    for index, label in enumerate(detail_sections):
        _set_details_section_label(qt_widgets, label)
        content_layout.addWidget(label)
        if index < len(detail_sections) - 1:
            content_layout.addWidget(_details_separator(qt_widgets))
    content_layout.addStretch(1)

    set_widget = getattr(scroll_area, "setWidget", None)
    if set_widget is not None:
        set_widget(scroll_content)
    layout.addWidget(scroll_area, 1)

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

    status_label = qt_widgets.QLabel(build_reports_status_text())
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
            item = make_read_only_item(qt_widgets, value)
            if column_index == 0:
                _apply_severity_text_color(item, row.severity)
            table.setItem(row_index, column_index, item)


def update_severity_count_indicators(
    content: Any,
    qt_widgets: Any,
    *,
    critical_count: int,
    error_count: int,
    warning_count: int,
    info_count: int,
) -> None:
    """Update per-severity summary labels with colored count numbers."""

    for object_name, severity_key, label, count in (
        (CRITICAL_COUNT_LABEL_OBJECT_NAME, "critical", "Critical", critical_count),
        (ERROR_COUNT_LABEL_OBJECT_NAME, "error", "Error", error_count),
        (WARNING_COUNT_LABEL_OBJECT_NAME, "warning", "Warning", warning_count),
        (INFO_COUNT_LABEL_OBJECT_NAME, "info", "Info", info_count),
    ):
        severity_label = _find_child_widget(content, qt_widgets, object_name)
        if severity_label is None:
            continue
        set_text = getattr(severity_label, "setText", None)
        if set_text is not None:
            set_text(_severity_count_html(severity_key, label, count))


def update_block_status_indicators(
    content: Any,
    qt_widgets: Any,
    *,
    block_publish: bool,
    block_deadline: bool,
) -> None:
    """Update publish/deadline block labels and lamps after validation."""

    publish_label = _find_child_widget(content, qt_widgets, PUBLISH_BLOCK_LABEL_OBJECT_NAME)
    if publish_label is not None:
        publish_label.setText(f"Publish Block: {_yes_no(block_publish)}")
    publish_lamp = _find_child_widget(content, qt_widgets, PUBLISH_BLOCK_LAMP_OBJECT_NAME)
    if publish_lamp is not None:
        _apply_block_lamp_style(publish_lamp, block_publish)

    deadline_label = _find_child_widget(content, qt_widgets, DEADLINE_BLOCK_LABEL_OBJECT_NAME)
    if deadline_label is not None:
        deadline_label.setText(f"Deadline Block: {_yes_no(block_deadline)}")
    deadline_lamp = _find_child_widget(content, qt_widgets, DEADLINE_BLOCK_LAMP_OBJECT_NAME)
    if deadline_lamp is not None:
        _apply_block_lamp_style(deadline_lamp, block_deadline)


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


def build_validate_sticky_chrome(
    qt_widgets: Any,
    validation_callbacks: ValidationActionCallbacks,
    issue_details_callbacks: Optional[IssueDetailsActionCallbacks] = None,
) -> Any:
    """Build pinned summary + action bar chrome for the Validate tab."""

    widget = qt_widgets.QWidget()
    widget.setObjectName(VALIDATE_STICKY_CHROME_OBJECT_NAME)
    layout = qt_widgets.QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    layout.addWidget(
        build_summary_header(
            qt_widgets,
            profile_changed=validation_callbacks.on_profile_changed,
            asset_class_changed=validation_callbacks.on_asset_class_changed,
        )
    )
    layout.addWidget(
        build_validation_actions(
            qt_widgets,
            callbacks=validation_callbacks,
            issue_details_callbacks=issue_details_callbacks,
        )
    )
    return widget


def format_scene_display_name(scene_path: str) -> str:
    """Return a compact scene label for the sticky summary."""

    if not scene_path:
        return "Scene: (unsaved)"
    return f"Scene: {Path(scene_path).name}"


def format_last_validated_display(scanned_at_utc: str) -> str:
    """Return a local-time last-validated label from an ISO UTC timestamp."""

    if not scanned_at_utc:
        return "Last validated: —"
    try:
        normalized = scanned_at_utc.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone()
        return f"Last validated: {parsed.strftime('%Y-%m-%d %H:%M:%S')}"
    except ValueError:
        return f"Last validated: {scanned_at_utc}"


def format_scan_scope_display(scan_scope: str) -> str:
    """Return a scan-scope chip label."""

    if scan_scope == "selection":
        return "Scope: selection"
    if scan_scope:
        return "Scope: scene"
    return "Scope: —"


def format_profile_chip_text(display_name: str, profile_id: str) -> str:
    """Return a profile chip label."""

    label = display_name or profile_id or "artist_relaxed"
    return f"Profile: {label}"


def format_asset_class_chip_text(display_name: str) -> str:
    """Return an asset-class chip label."""

    label = display_name or ASSET_CLASS_NONE_LABEL
    return f"Asset: {label}"


def build_reports_status_text(
    *,
    scene_path: str = "",
    scanned_at_utc: str = "",
    scan_scope: str = "",
    export_message: str = "",
) -> str:
    """Build the Reports tab status line from last validation and export feedback."""

    if export_message:
        return export_message

    if not scanned_at_utc and not scene_path:
        return (
            "Reports export validation artifacts. Run Validate Scene first so exports "
            "include current results. Manifest Gate lives on the Validate tab."
        )

    parts = [
        format_scene_display_name(scene_path),
        format_last_validated_display(scanned_at_utc),
        format_scan_scope_display(scan_scope),
    ]
    if scanned_at_utc:
        parts.append("Exports reflect the last validation run.")
    else:
        parts.append("Validation age unknown — revalidate before publishing exports.")
    return "   ".join(parts)


def profile_display_name(
    profile_id: str,
    options: Sequence[ProfileOption] = DEFAULT_WORKFLOW_PROFILE_OPTIONS,
) -> str:
    """Resolve a workflow profile id to its UI display name."""

    for option in options:
        if option.profile_id == profile_id:
            return option.display_name
    return profile_id


def asset_class_display_name(
    asset_class_id: str,
    options: Sequence[ProfileOption] = DEFAULT_ASSET_CLASS_PROFILE_OPTIONS,
) -> str:
    """Resolve an asset-class profile id to its UI display name."""

    if not asset_class_id or asset_class_id == ASSET_CLASS_NONE_ID:
        return ASSET_CLASS_NONE_LABEL
    for option in options:
        if option.profile_id == asset_class_id:
            return option.display_name
    return asset_class_id


def combo_profile_id(combo: Any) -> str:
    """Return the profile id stored on the active combo box item."""

    current_data = getattr(combo, "currentData", None)
    if current_data is not None:
        data = current_data()
        if data is not None:
            return str(data)
    current_text = getattr(combo, "currentText", lambda: "")()
    return str(current_text or "")


def select_workflow_profile(
    combo: Any,
    profile_id: str,
    *,
    options: Sequence[ProfileOption] = DEFAULT_WORKFLOW_PROFILE_OPTIONS,
) -> None:
    """Select a workflow profile on an existing combo box."""

    selected = profile_id.strip() or "artist_relaxed"
    _set_combo_selection(combo, options, selected)


def select_asset_class_profile(
    combo: Any,
    asset_class_id: str,
    *,
    options: Sequence[ProfileOption] = DEFAULT_ASSET_CLASS_PROFILE_OPTIONS,
) -> None:
    """Select an asset class overlay on an existing combo box."""

    normalized = asset_class_id.strip() or ASSET_CLASS_NONE_ID
    if normalized == ASSET_CLASS_NONE_ID:
        set_current = getattr(combo, "setCurrentIndex", None)
        if set_current is not None:
            set_current(0)
        return
    _set_combo_selection(combo, options, normalized)


def _build_validate_tab(
    qt_widgets: Any,
    validation_callbacks: ValidationActionCallbacks,
    issue_details_callbacks: IssueDetailsActionCallbacks,
) -> Any:
    tab = qt_widgets.QWidget()
    layout = qt_widgets.QVBoxLayout(tab)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(6)

    layout.addWidget(
        build_validate_sticky_chrome(
            qt_widgets,
            validation_callbacks,
            issue_details_callbacks,
        )
    )

    issues_table = build_issues_table(qt_widgets)
    details_panel = build_issue_details_panel(qt_widgets, callbacks=issue_details_callbacks)
    splitter_class = getattr(qt_widgets, "QSplitter", None)
    if splitter_class is None:
        issues_host = qt_widgets.QWidget()
        issues_layout = qt_widgets.QVBoxLayout(issues_host)
        issues_layout.setContentsMargins(0, 0, 0, 0)
        issues_layout.setSpacing(4)
        issues_layout.addWidget(issues_table, 3)
        issues_layout.addWidget(details_panel, 2)
        layout.addWidget(issues_host, 1)
    else:
        splitter = splitter_class()
        splitter.setObjectName(VALIDATE_ISSUES_SPLITTER_OBJECT_NAME)
        orientation = getattr(qt_widgets, "Qt", None)
        if orientation is not None:
            horizontal = getattr(orientation, "Horizontal", None)
            set_orientation = getattr(splitter, "setOrientation", None)
            if horizontal is not None and set_orientation is not None:
                set_orientation(horizontal)
        splitter.addWidget(issues_table)
        splitter.addWidget(details_panel)
        set_stretch = getattr(splitter, "setStretchFactor", None)
        if set_stretch is not None:
            set_stretch(0, 3)
            set_stretch(1, 2)
        set_children_collapsible = getattr(splitter, "setChildrenCollapsible", None)
        if set_children_collapsible is not None:
            set_children_collapsible(False)
        set_collapsible = getattr(splitter, "setCollapsible", None)
        if set_collapsible is not None:
            set_collapsible(0, False)
            set_collapsible(1, False)
        layout.addWidget(splitter, 1)

    description = qt_widgets.QLabel("Ready to validate the current scene or selection.")
    description.setObjectName(VALIDATE_STATUS_LABEL_OBJECT_NAME)
    description.setWordWrap(True)

    status_row = qt_widgets.QWidget()
    status_row.setObjectName(VALIDATE_STATUS_ROW_OBJECT_NAME)
    status_layout = qt_widgets.QHBoxLayout(status_row)
    status_layout.setContentsMargins(0, 0, 0, 0)
    status_layout.setSpacing(6)
    status_layout.addWidget(description, 1)

    progress_bar = qt_widgets.QProgressBar()
    progress_bar.setObjectName(VALIDATE_PROGRESS_BAR_OBJECT_NAME)
    progress_bar.setTextVisible(False)
    progress_bar.setMaximum(0)
    progress_bar.setMinimum(0)
    set_fixed_height = getattr(progress_bar, "setFixedHeight", None)
    set_max_width = getattr(progress_bar, "setMaximumWidth", None)
    if set_fixed_height is not None:
        set_fixed_height(8)
    if set_max_width is not None:
        set_max_width(160)
    set_visible = getattr(progress_bar, "setVisible", None)
    if set_visible is not None:
        set_visible(False)
    status_layout.addWidget(progress_bar, 0)
    layout.addWidget(status_row)
    return tab


def _build_waivers_tab(
    qt_widgets: Any,
    waiver_callbacks: WaiverManagerCallbacks,
) -> Any:
    tab = qt_widgets.QWidget()
    layout = qt_widgets.QVBoxLayout(tab)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(6)

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


def _build_severity_counts_row(qt_widgets: Any, state: SummaryHeaderState) -> Any:
    row = qt_widgets.QWidget()
    row.setObjectName(SEVERITY_COUNTS_ROW_OBJECT_NAME)
    layout = qt_widgets.QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)
    for object_name, severity_key, label, count in (
        (CRITICAL_COUNT_LABEL_OBJECT_NAME, "critical", "Critical", state.critical_count),
        (ERROR_COUNT_LABEL_OBJECT_NAME, "error", "Error", state.error_count),
        (WARNING_COUNT_LABEL_OBJECT_NAME, "warning", "Warning", state.warning_count),
        (INFO_COUNT_LABEL_OBJECT_NAME, "info", "Info", state.info_count),
    ):
        layout.addWidget(_severity_count_label(qt_widgets, object_name, severity_key, label, count))
    return row


def _severity_count_label(
    qt_widgets: Any,
    object_name: str,
    severity_key: str,
    label: str,
    count: int,
) -> Any:
    severity_label = qt_widgets.QLabel(_severity_count_html(severity_key, label, count))
    severity_label.setObjectName(object_name)
    set_text_format = getattr(severity_label, "setTextFormat", None)
    qt_module = getattr(qt_widgets, "Qt", None)
    rich_text = getattr(qt_module, "RichText", None) if qt_module is not None else None
    if set_text_format is not None and rich_text is not None:
        set_text_format(rich_text)
    return severity_label


def _severity_count_html(severity_key: str, label: str, count: int) -> str:
    color = SEVERITY_ROW_NUMBER_COLORS.get(severity_key)
    if not color:
        return f"{label}: {count}"
    return f'{label}: <span style="color:{color};">{count}</span>'


def _build_triage_action_group(
    qt_widgets: Any,
    issue_callbacks: IssueDetailsActionCallbacks,
) -> Any:
    actions = qt_widgets.QWidget()
    actions.setObjectName(VALIDATE_TRIAGE_ACTIONS_OBJECT_NAME)
    actions_layout = qt_widgets.QHBoxLayout(actions)
    actions_layout.setContentsMargins(0, 0, 0, 0)
    actions_layout.setSpacing(4)

    navigation_group = qt_widgets.QWidget()
    navigation_layout = qt_widgets.QHBoxLayout(navigation_group)
    navigation_layout.setContentsMargins(0, 0, 0, 0)
    navigation_layout.setSpacing(4)
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
    ):
        navigation_layout.addWidget(
            _compact_button(qt_widgets, label, object_name, tooltip, callback)
        )
    actions_layout.addWidget(navigation_group)
    actions_layout.addWidget(_action_bar_separator(qt_widgets))

    file_group = qt_widgets.QWidget()
    file_layout = qt_widgets.QHBoxLayout(file_group)
    file_layout.setContentsMargins(0, 0, 0, 0)
    file_layout.setSpacing(4)
    for label, object_name, tooltip, callback in (
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
        file_layout.addWidget(
            _compact_button(qt_widgets, label, object_name, tooltip, callback)
        )
    actions_layout.addWidget(file_group)
    return actions


def _configure_borderless_scroll_area(scroll_area: Any, qt_widgets: Any) -> None:
    """Remove the default QScrollArea frame so details blend with the splitter pane."""

    frame_class = getattr(qt_widgets, "QFrame", None)
    set_shape = getattr(scroll_area, "setFrameShape", None)
    set_shadow = getattr(scroll_area, "setFrameShadow", None)
    set_line_width = getattr(scroll_area, "setLineWidth", None)
    set_style = getattr(scroll_area, "setStyleSheet", None)
    if frame_class is not None and set_shape is not None:
        no_frame = getattr(frame_class, "NoFrame", None)
        plain = getattr(frame_class, "Plain", None)
        if no_frame is not None:
            set_shape(no_frame)
        if set_shadow is not None and plain is not None:
            set_shadow(plain)
    if set_line_width is not None:
        set_line_width(0)
    if set_style is not None:
        set_style("QScrollArea { border: none; background: transparent; }")


def _details_separator(qt_widgets: Any) -> Any:
    separator = qt_widgets.QFrame()
    separator.setObjectName("shaderHealthInspectorIssueDetailsSeparator")
    frame_class = getattr(qt_widgets, "QFrame", None)
    set_shape = getattr(separator, "setFrameShape", None)
    set_shadow = getattr(separator, "setFrameShadow", None)
    set_fixed_height = getattr(separator, "setFixedHeight", None)
    if frame_class is not None:
        hline = getattr(frame_class, "HLine", None)
        sunken = getattr(frame_class, "Sunken", None)
        if set_shape is not None and hline is not None:
            set_shape(hline)
        if set_shadow is not None and sunken is not None:
            set_shadow(sunken)
    if set_fixed_height is not None:
        set_fixed_height(1)
    return separator


def _action_bar_separator(qt_widgets: Any) -> Any:
    separator = qt_widgets.QLabel("|")
    separator.setObjectName("shaderHealthInspectorValidateActionSeparator")
    return separator


def _find_child_widget(content: Any, qt_widgets: Any, object_name: str) -> Any:
    if content is None:
        return None
    finder = getattr(content, "findChild", None)
    widget_class = getattr(qt_widgets, "QWidget", None)
    if finder is not None and widget_class is not None:
        found = finder(widget_class, object_name)
        if found is not None:
            return found
    return _find_descendant_by_object_name(content, object_name)


def _find_descendant_by_object_name(root: Any, object_name: str) -> Any:
    if getattr(root, "object_name", None) == object_name:
        return root
    for child in getattr(root, "children", []) or []:
        found = _find_descendant_by_object_name(child, object_name)
        if found is not None:
            return found
    return None


def _apply_block_lamp_style(lamp: Any, blocked: bool) -> None:
    color = BLOCK_LAMP_COLORS[bool(blocked)]
    set_style = getattr(lamp, "setStyleSheet", None)
    if set_style is not None:
        set_style(
            "background-color: "
            f"{color}; border-radius: 7px; min-width: 14px; max-width: 14px; "
            "min-height: 14px; max-height: 14px;"
        )
    set_fixed_size = getattr(lamp, "setFixedSize", None)
    if set_fixed_size is not None:
        set_fixed_size(14, 14)
    set_tooltip = getattr(lamp, "setToolTip", None)
    if set_tooltip is not None:
        set_tooltip("Blocked" if blocked else "Clear")


def _apply_severity_text_color(item: Any, severity: str) -> None:
    hex_color = SEVERITY_ROW_NUMBER_COLORS.get(_normalized_text(severity))
    if not hex_color:
        return
    try:
        qt_core = load_qt_core()
    except RuntimeError:
        return
    color_class = getattr(qt_core, "QColor", None)
    brush_class = getattr(qt_core, "QBrush", None)
    set_foreground = getattr(item, "setForeground", None)
    if color_class is None or brush_class is None or set_foreground is None:
        return
    set_foreground(brush_class(color_class(hex_color)))


def _set_issue_row_number_style(
    qt_widgets: Any,
    table: Any,
    row_index: int,
    severity: str,
) -> None:
    """Legacy helper kept for compatibility; row numbers are no longer severity-colored."""

    row_item = make_read_only_item(qt_widgets, str(row_index + 1))
    set_vertical_header_item = getattr(table, "setVerticalHeaderItem", None)
    if set_vertical_header_item is not None:
        set_vertical_header_item(row_index, row_item)


def _set_expanding_panel(qt_widgets: Any, widget: Any) -> None:
    size_policy = getattr(qt_widgets, "QSizePolicy", None)
    set_policy = getattr(widget, "setSizePolicy", None)
    if size_policy is None or set_policy is None:
        return
    expanding = getattr(size_policy, "Expanding", None)
    if expanding is not None:
        set_policy(expanding, expanding)


def _set_details_section_label(qt_widgets: Any, widget: Any) -> None:
    size_policy = getattr(qt_widgets, "QSizePolicy", None)
    set_policy = getattr(widget, "setSizePolicy", None)
    if size_policy is None or set_policy is None:
        return
    preferred = getattr(size_policy, "Preferred", None)
    minimum = getattr(size_policy, "Minimum", None)
    if preferred is not None and minimum is not None:
        set_policy(preferred, minimum)


def _set_compact_horizontal(qt_widgets: Any, widget: Any) -> None:
    size_policy = getattr(qt_widgets, "QSizePolicy", None)
    set_policy = getattr(widget, "setSizePolicy", None)
    if size_policy is None or set_policy is None:
        return
    preferred = getattr(size_policy, "Preferred", None)
    fixed = getattr(size_policy, "Fixed", None)
    if preferred is not None and fixed is not None:
        set_policy(preferred, fixed)


def _set_compact_vertical(qt_widgets: Any, widget: Any) -> None:
    size_policy = getattr(qt_widgets, "QSizePolicy", None)
    set_policy = getattr(widget, "setSizePolicy", None)
    if size_policy is None or set_policy is None:
        return
    preferred = getattr(size_policy, "Preferred", None)
    maximum = getattr(size_policy, "Maximum", None)
    if preferred is not None and maximum is not None:
        set_policy(preferred, maximum)


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


def _issues_filter_combo_compact(
    qt_widgets: Any,
    *,
    label: str,
    object_name: str,
    items: Sequence[str],
    tooltip: str,
    current_text: Optional[str] = None,
) -> Any:
    """Build a compact filter combo with tooltip text instead of a separate label."""

    combo = qt_widgets.QComboBox()
    combo.setObjectName(object_name)
    combo.addItems(list(items))
    combo.setToolTip(f"{label}: {tooltip}")
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
    return combo


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
