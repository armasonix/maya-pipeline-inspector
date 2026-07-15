"""Maya Pipeline Inspector panel content."""
from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pipeline_inspector import __version__
from pipeline_inspector.maya.validation_pipeline import (
    ASSET_CLASS_NONE_ID,
    ProfileOption,
    list_asset_class_profile_options,
    list_workflow_profile_options,
)
from pipeline_inspector.studio_config import StudioConfig
from pipeline_inspector.ui.farm_tab import FarmActionCallbacks, build_farm_tab
from pipeline_inspector.ui.fix_queue import FixQueueActionCallbacks, build_fix_queue
from pipeline_inspector.ui.qt import load_qt_core
from pipeline_inspector.ui.readiness_tab import ReadinessActionCallbacks, build_readiness_tab
from pipeline_inspector.ui.settings_panel import SettingsActionCallbacks, build_settings_view
from pipeline_inspector.ui.table_widgets import configure_read_only_table, make_read_only_item
from pipeline_inspector.ui.waiver_manager import WaiverManagerCallbacks, build_waiver_manager
from pipeline_inspector.user_config import UserPreferences

PANEL_OBJECT_NAME = "pipelineInspectorPanel"
PANEL_TITLE = "Maya Pipeline Inspector"
PANEL_CONTENT_OBJECT_NAME = "pipelineInspectorPanelContent"
TAB_WIDGET_OBJECT_NAME = "pipelineInspectorTabWidget"
VALIDATE_TAB_OBJECT_NAME = "pipelineInspectorValidateTab"
REPORTS_TAB_OBJECT_NAME = "pipelineInspectorReportsTab"
READINESS_TAB_OBJECT_NAME = "pipelineInspectorReadinessTab"
PANEL_HEADER_OBJECT_NAME = "pipelineInspectorPanelHeader"
PANEL_HEADER_TITLE_OBJECT_NAME = "pipelineInspectorPanelHeaderTitle"
PANEL_HEADER_UNSAVED_OBJECT_NAME = "pipelineInspectorPanelHeaderUnsaved"
SETTINGS_GEAR_BUTTON_OBJECT_NAME = "pipelineInspectorSettingsGearButton"
DOCUMENTATION_BUTTON_OBJECT_NAME = "pipelineInspectorDocumentationButton"
REPORT_BUG_BUTTON_OBJECT_NAME = "pipelineInspectorReportBugButton"
CHECK_FOR_UPDATES_BUTTON_OBJECT_NAME = "pipelineInspectorCheckForUpdatesButton"
PANEL_HEADER_OVERFLOW_BUTTON_OBJECT_NAME = "pipelineInspectorPanelHeaderOverflowButton"
SUMMARY_CONTEXT_ROW_OBJECT_NAME = "pipelineInspectorSummaryContextRow"
SUMMARY_PROFILE_ROW_OBJECT_NAME = "pipelineInspectorSummaryProfileRow"
VALIDATE_ACTION_OVERFLOW_BUTTON_OBJECT_NAME = "pipelineInspectorValidateActionOverflowButton"
VALIDATE_ACTION_BAR_SEPARATOR_OBJECT_NAME = "pipelineInspectorValidateActionBarSeparator"
SETTINGS_GEAR_TOOLTIP = "Open settings"
DOCUMENTATION_BUTTON_TOOLTIP = "Open Pipeline Inspector documentation in your browser."
REPORT_BUG_BUTTON_TOOLTIP = (
    "Report a bug in Pipeline Inspector to the plugin maintainers. "
)
CHECK_FOR_UPDATES_BUTTON_TOOLTIP = (
    "Open the update wizard shell and preview staged progress steps."
)
PANEL_BODY_STACK_OBJECT_NAME = "pipelineInspectorPanelBodyStack"
MAIN_VIEW_OBJECT_NAME = "pipelineInspectorMainView"
SETTINGS_VIEW_INDEX = 1
SUMMARY_HEADER_OBJECT_NAME = "pipelineInspectorSummaryHeader"
SUMMARY_METRICS_ROW_OBJECT_NAME = "pipelineInspectorSummaryMetricsRow"
VALIDATE_STICKY_CHROME_OBJECT_NAME = "pipelineInspectorValidateStickyChrome"
VALIDATE_ACTION_BAR_OBJECT_NAME = "pipelineInspectorValidateActionBar"
VALIDATE_PRIMARY_ACTIONS_OBJECT_NAME = "pipelineInspectorValidatePrimaryActions"
VALIDATE_PIPELINE_ACTIONS_OBJECT_NAME = "pipelineInspectorValidatePipelineActions"
VALIDATE_TRIAGE_ACTIONS_OBJECT_NAME = "pipelineInspectorValidateTriageActions"
VALIDATE_ISSUES_SPLITTER_OBJECT_NAME = "pipelineInspectorValidateIssuesSplitter"
HEALTH_SCORE_LABEL_OBJECT_NAME = "pipelineInspectorHealthScoreLabel"
SEVERITY_COUNTS_LABEL_OBJECT_NAME = "pipelineInspectorSeverityCountsLabel"
SEVERITY_COUNTS_ROW_OBJECT_NAME = "pipelineInspectorSeverityCountsRow"
CRITICAL_COUNT_LABEL_OBJECT_NAME = "pipelineInspectorCriticalCountLabel"
ERROR_COUNT_LABEL_OBJECT_NAME = "pipelineInspectorErrorCountLabel"
WARNING_COUNT_LABEL_OBJECT_NAME = "pipelineInspectorWarningCountLabel"
INFO_COUNT_LABEL_OBJECT_NAME = "pipelineInspectorInfoCountLabel"
PUBLISH_BLOCK_LABEL_OBJECT_NAME = "pipelineInspectorPublishBlockLabel"
PUBLISH_BLOCK_LAMP_OBJECT_NAME = "pipelineInspectorPublishBlockLamp"
DEADLINE_BLOCK_LABEL_OBJECT_NAME = "pipelineInspectorDeadlineBlockLabel"
DEADLINE_BLOCK_LAMP_OBJECT_NAME = "pipelineInspectorDeadlineBlockLamp"
BLOCK_STATUS_LABEL_OBJECT_NAME = "pipelineInspectorBlockStatusLabel"
SCENE_NAME_LABEL_OBJECT_NAME = "pipelineInspectorSceneNameLabel"
LAST_VALIDATED_LABEL_OBJECT_NAME = "pipelineInspectorLastValidatedLabel"
SCAN_SCOPE_LABEL_OBJECT_NAME = "pipelineInspectorScanScopeLabel"
PROFILE_CHIP_LABEL_OBJECT_NAME = "pipelineInspectorProfileChipLabel"
ASSET_CLASS_CHIP_LABEL_OBJECT_NAME = "pipelineInspectorAssetClassChipLabel"
PROFILE_LABEL_OBJECT_NAME = "pipelineInspectorProfileLabel"
PROFILE_DROPDOWN_OBJECT_NAME = "pipelineInspectorProfileDropdown"
ASSET_CLASS_LABEL_OBJECT_NAME = "pipelineInspectorAssetClassLabel"
ASSET_CLASS_DROPDOWN_OBJECT_NAME = "pipelineInspectorAssetClassDropdown"
ISSUES_TABLE_WIDGET_OBJECT_NAME = "pipelineInspectorIssuesTableWidget"
ISSUES_SEVERITY_FILTER_OBJECT_NAME = "pipelineInspectorIssuesSeverityFilter"
ISSUES_SORT_DROPDOWN_OBJECT_NAME = "pipelineInspectorIssuesSortDropdown"
ISSUES_TABLE_OBJECT_NAME = "pipelineInspectorIssuesTable"
DETAILS_PANEL_OBJECT_NAME = "pipelineInspectorIssueDetailsPanel"
DETAILS_SCROLL_AREA_OBJECT_NAME = "pipelineInspectorIssueDetailsScrollArea"
DETAILS_SCROLL_CONTENT_OBJECT_NAME = "pipelineInspectorIssueDetailsScrollContent"
DETAILS_PANEL_MIN_WIDTH = 180
_QT_WIDGETSIZE_MAX = 16777215
DETAILS_MESSAGE_LABEL_OBJECT_NAME = "pipelineInspectorIssueDetailsMessage"
DETAILS_WHY_LABEL_OBJECT_NAME = "pipelineInspectorIssueDetailsWhy"
DETAILS_VALUES_LABEL_OBJECT_NAME = "pipelineInspectorIssueDetailsValues"
DETAILS_GRAPH_TRACE_LABEL_OBJECT_NAME = "pipelineInspectorIssueDetailsGraphTrace"
DETAILS_REFERENCE_LABEL_OBJECT_NAME = "pipelineInspectorIssueDetailsReference"
DETAILS_FIX_LABEL_OBJECT_NAME = "pipelineInspectorIssueDetailsFix"
ISSUES_FILTERS_ROW_OBJECT_NAME = "pipelineInspectorIssuesFiltersRow"
EXPORT_ACTIONS_OBJECT_NAME = "pipelineInspectorExportActions"
EXPORT_ACTIONS_GRID_OBJECT_NAME = "pipelineInspectorExportActionsGrid"
EXPORT_JSON_BUTTON_OBJECT_NAME = "pipelineInspectorExportJsonButton"
EXPORT_HTML_BUTTON_OBJECT_NAME = "pipelineInspectorExportHtmlButton"
EXPORT_MANIFEST_BUTTON_OBJECT_NAME = "pipelineInspectorExportManifestButton"
EXPORT_MANIFEST_DIFF_BUTTON_OBJECT_NAME = "pipelineInspectorExportManifestDiffButton"
EXPORT_COMPARE_APPROVED_MANIFEST_BUTTON_OBJECT_NAME = (
    "pipelineInspectorCompareApprovedManifestButton"
)
REPORTS_STATUS_LABEL_OBJECT_NAME = "pipelineInspectorReportsStatusLabel"
VALIDATE_STATUS_LABEL_OBJECT_NAME = "pipelineInspectorDescription"
VALIDATE_STATUS_ROW_OBJECT_NAME = "pipelineInspectorValidateStatusRow"
VALIDATE_PROGRESS_BAR_OBJECT_NAME = "pipelineInspectorValidateProgressBar"
VALIDATE_SCENE_BUTTON_OBJECT_NAME = "pipelineInspectorValidateSceneButton"
VALIDATE_SELECTION_BUTTON_OBJECT_NAME = "pipelineInspectorValidateSelectionButton"
VALIDATE_PUBLISH_PREFLIGHT_BUTTON_OBJECT_NAME = "pipelineInspectorPublishPreflightButton"
VALIDATE_MANIFEST_GATE_BUTTON_OBJECT_NAME = "pipelineInspectorManifestGateButton"
EXPORT_COMPARE_AFTER_FIXES_BUTTON_OBJECT_NAME = "pipelineInspectorCompareAfterFixesButton"
EXPORT_SEND_TO_TRACKER_BUTTON_OBJECT_NAME = "pipelineInspectorSendToTrackerButton"
ASSET_CLASS_HINT_LABEL_OBJECT_NAME = "pipelineInspectorAssetClassHintLabel"
ISSUES_OWNER_FILTER_OBJECT_NAME = "pipelineInspectorIssuesOwnerFilter"
ISSUES_VIEW_FILTER_OBJECT_NAME = "pipelineInspectorIssuesViewFilter"
DETAILS_ACTIONS_OBJECT_NAME = "pipelineInspectorIssueDetailsActions"
SELECT_NODE_BUTTON_OBJECT_NAME = "pipelineInspectorSelectNodeButton"
OPEN_ATTR_EDITOR_BUTTON_OBJECT_NAME = "pipelineInspectorOpenAttrEditorButton"
COPY_PATH_BUTTON_OBJECT_NAME = "pipelineInspectorCopyPathButton"
REVEAL_FILE_BUTTON_OBJECT_NAME = "pipelineInspectorRevealFileButton"
CREATE_RULE_DRAFT_BUTTON_OBJECT_NAME = "pipelineInspectorCreateRuleDraftButton"
CREATE_RULE_DRAFT_BUTTON_OBJECT_NAME = "pipelineInspectorCreateRuleDraftButton"
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
SEVERITY_COUNT_SPECS = (
    (CRITICAL_COUNT_LABEL_OBJECT_NAME, "critical", "Critical"),
    (ERROR_COUNT_LABEL_OBJECT_NAME, "error", "Error"),
    (WARNING_COUNT_LABEL_OBJECT_NAME, "warning", "Warning"),
    (INFO_COUNT_LABEL_OBJECT_NAME, "info", "Info"),
)
_SEVERITY_COUNTS_ATTR = "_pipeline_inspector_severity_counts"
_FULL_EXPORT_BUTTON_LABELS = {
    EXPORT_JSON_BUTTON_OBJECT_NAME: "Export JSON Report",
    EXPORT_HTML_BUTTON_OBJECT_NAME: "Export HTML Report",
    EXPORT_MANIFEST_BUTTON_OBJECT_NAME: "Export Shader Manifest",
    EXPORT_COMPARE_AFTER_FIXES_BUTTON_OBJECT_NAME: "Compare After Fixes",
    EXPORT_MANIFEST_DIFF_BUTTON_OBJECT_NAME: "Export Manifest Diff",
    EXPORT_COMPARE_APPROVED_MANIFEST_BUTTON_OBJECT_NAME: "Compare to Approved Manifest",
    EXPORT_SEND_TO_TRACKER_BUTTON_OBJECT_NAME: "Send to Tracker",
}
_COMPACT_EXPORT_BUTTON_LABELS = {
    EXPORT_JSON_BUTTON_OBJECT_NAME: "JSON Report",
    EXPORT_HTML_BUTTON_OBJECT_NAME: "HTML Report",
    EXPORT_MANIFEST_BUTTON_OBJECT_NAME: "Shader Manifest",
    EXPORT_COMPARE_AFTER_FIXES_BUTTON_OBJECT_NAME: "After Fixes",
    EXPORT_MANIFEST_DIFF_BUTTON_OBJECT_NAME: "Manifest Diff",
    EXPORT_COMPARE_APPROVED_MANIFEST_BUTTON_OBJECT_NAME: "Approved Diff",
    EXPORT_SEND_TO_TRACKER_BUTTON_OBJECT_NAME: "Send Tracker",
}
_EXPORT_BUTTON_LAYOUT_ORDER = (
    EXPORT_JSON_BUTTON_OBJECT_NAME,
    EXPORT_HTML_BUTTON_OBJECT_NAME,
    EXPORT_MANIFEST_BUTTON_OBJECT_NAME,
    EXPORT_COMPARE_AFTER_FIXES_BUTTON_OBJECT_NAME,
    EXPORT_MANIFEST_DIFF_BUTTON_OBJECT_NAME,
    EXPORT_COMPARE_APPROVED_MANIFEST_BUTTON_OBJECT_NAME,
    EXPORT_SEND_TO_TRACKER_BUTTON_OBJECT_NAME,
)
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
    on_open_documentation: Optional[Callable[[], None]] = None
    on_report_bug: Optional[Callable[[], None]] = None
    on_check_for_updates: Optional[Callable[[], None]] = None


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
    on_send_to_tracker: Optional[Callable[[], None]] = None


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
    on_create_rule_draft: Optional[Callable[[], None]] = None


def build_main_widget(
    qt_widgets: Any,
    export_callbacks: Optional[ExportActionCallbacks] = None,
    fix_queue_callbacks: Optional[FixQueueActionCallbacks] = None,
    validation_callbacks: Optional[ValidationActionCallbacks] = None,
    issue_details_callbacks: Optional[IssueDetailsActionCallbacks] = None,
    waiver_callbacks: Optional[WaiverManagerCallbacks] = None,
    farm_callbacks: Optional[FarmActionCallbacks] = None,
    readiness_callbacks: Optional[ReadinessActionCallbacks] = None,
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
    readiness_callbacks = readiness_callbacks or ReadinessActionCallbacks()
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
        _build_validate_tab(
            qt_widgets,
            validation_callbacks,
            issue_details_callbacks,
            waiver_callbacks=waiver_callbacks,
            user_config=active_user_config,
        ),
        "Validate",
    )
    tabs.addTab(_build_waivers_tab(qt_widgets, waiver_callbacks), "Waivers")
    tabs.addTab(_build_fixes_tab(qt_widgets, fix_queue_callbacks), "Fixes")
    tabs.addTab(_build_reports_tab(qt_widgets, export_callbacks), "Reports")
    tabs.addTab(
        build_readiness_tab(qt_widgets, callbacks=readiness_callbacks),
        "Readiness",
    )
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

    from pipeline_inspector.ui.user_preferences_ui import apply_user_preferences_to_panel

    apply_user_preferences_to_panel(widget, qt_widgets, active_user_config)

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
        set_tooltip(SETTINGS_GEAR_TOOLTIP)
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
    row_layout.addWidget(title_label, 0)

    unsaved_label = qt_widgets.QLabel("")
    unsaved_label.setObjectName(PANEL_HEADER_UNSAVED_OBJECT_NAME)
    set_unsaved_style = getattr(unsaved_label, "setStyleSheet", None)
    if set_unsaved_style is not None:
        set_unsaved_style("color: #6eb5ff; font-size: 11pt; font-weight: normal;")
    set_unsaved_visible = getattr(unsaved_label, "setVisible", None)
    if set_unsaved_visible is not None:
        set_unsaved_visible(False)
    row_layout.addWidget(unsaved_label, 0)
    row_layout.addStretch(1)

    docs_button = _compact_button(
        qt_widgets,
        "Documentation",
        DOCUMENTATION_BUTTON_OBJECT_NAME,
        DOCUMENTATION_BUTTON_TOOLTIP,
        navigation_callbacks.on_open_documentation,
    )
    row_layout.addWidget(docs_button)

    report_bug_button = _compact_button(
        qt_widgets,
        "Report Plugin Bug",
        REPORT_BUG_BUTTON_OBJECT_NAME,
        REPORT_BUG_BUTTON_TOOLTIP,
        navigation_callbacks.on_report_bug,
    )
    row_layout.addWidget(report_bug_button)

    updates_button = _compact_button(
        qt_widgets,
        "Check for Updates",
        CHECK_FOR_UPDATES_BUTTON_OBJECT_NAME,
        CHECK_FOR_UPDATES_BUTTON_TOOLTIP,
        navigation_callbacks.on_check_for_updates,
    )
    row_layout.addWidget(updates_button)

    overflow_button = _build_panel_header_overflow_button(
        qt_widgets,
        navigation_callbacks=navigation_callbacks,
        secondary_buttons=(docs_button, report_bug_button, updates_button),
    )
    row_layout.addWidget(overflow_button)

    return row


def update_panel_header_unsaved_indicator(
    root: Any,
    qt_widgets: Any,
    *,
    dirty: bool,
) -> None:
    """Show or hide the panel header unsaved-settings hint."""

    from pipeline_inspector.ui.settings_widgets import find_child

    label = find_child(root, qt_widgets.QLabel, PANEL_HEADER_UNSAVED_OBJECT_NAME)
    if label is None:
        return
    set_text = getattr(label, "setText", None)
    set_visible = getattr(label, "setVisible", None)
    if dirty:
        if set_text is not None:
            set_text("* unsaved changes")
        if set_visible is not None:
            set_visible(True)
        return
    if set_text is not None:
        set_text("")
    if set_visible is not None:
        set_visible(False)


def build_validation_actions(
    qt_widgets: Any,
    callbacks: Optional[ValidationActionCallbacks] = None,
    issue_details_callbacks: Optional[IssueDetailsActionCallbacks] = None,
    *,
    on_make_waive: Optional[Callable[[], None]] = None,
    on_report_supervisor: Optional[Callable[[], None]] = None,
    show_make_waive_in_overflow: bool = False,
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
    layout.addWidget(
        _action_bar_separator(qt_widgets, VALIDATE_ACTION_BAR_SEPARATOR_OBJECT_NAME)
    )

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
    layout.addWidget(
        _action_bar_separator(
            qt_widgets,
            f"{VALIDATE_ACTION_BAR_SEPARATOR_OBJECT_NAME}Pipeline",
        )
    )
    triage_group = _build_triage_action_group(qt_widgets, issue_callbacks)
    layout.addWidget(triage_group)
    overflow_actions: list[tuple[str, Optional[Callable[[], None]]]] = [
        ("Publish Preflight", validation_callbacks.on_publish_preflight),
        ("Manifest Gate", validation_callbacks.on_manifest_gate),
        ("Select Node", issue_callbacks.on_select_node),
        ("Open in HyperShade", issue_callbacks.on_open_in_hypershade),
        ("Copy Path", issue_callbacks.on_copy_path),
        ("Reveal File", issue_callbacks.on_reveal_file),
        ("Create Rule Draft", issue_callbacks.on_create_rule_draft),
    ]
    if on_make_waive is not None and show_make_waive_in_overflow:
        overflow_actions.append(("Make Waive", on_make_waive))
    if on_report_supervisor is not None and show_make_waive_in_overflow:
        overflow_actions.append(("Report Supervisor", on_report_supervisor))
    layout.addWidget(
        _build_validate_action_overflow_button(
            qt_widgets,
            pipeline_group=pipeline_group,
            triage_group=triage_group,
            overflow_actions=overflow_actions,
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
    """Build the compact sticky summary/header widget for the Validate tab."""

    summary_state = state or SummaryHeaderState()
    widget = qt_widgets.QWidget()
    widget.setObjectName(SUMMARY_HEADER_OBJECT_NAME)

    layout = qt_widgets.QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)

    metrics_row = qt_widgets.QWidget()
    metrics_row.setObjectName(SUMMARY_METRICS_ROW_OBJECT_NAME)
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
    context_row.setObjectName(SUMMARY_CONTEXT_ROW_OBJECT_NAME)
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
    profile_row.setObjectName(SUMMARY_PROFILE_ROW_OBJECT_NAME)
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
    *,
    on_make_waive: Optional[Callable[[], None]] = None,
    on_report_supervisor: Optional[Callable[[], None]] = None,
    show_make_waive_in_filters: bool = True,
    show_report_supervisor_in_filters: bool = True,
    filters_row_stretch: bool = True,
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

    if on_make_waive is not None and show_make_waive_in_filters:
        from pipeline_inspector.ui.settings_widgets import wire_button
        from pipeline_inspector.ui.waiver_manager import VALIDATE_MAKE_WAIVE_BUTTON_OBJECT_NAME

        make_waive_button = qt_widgets.QPushButton("Make Waive")
        make_waive_button.setObjectName(VALIDATE_MAKE_WAIVE_BUTTON_OBJECT_NAME)
        set_tooltip = getattr(make_waive_button, "setToolTip", None)
        if set_tooltip is not None:
            set_tooltip(
                "Create a waiver for the selected issue in the Validate table."
            )
        wire_button(make_waive_button, on_make_waive)
        filters_layout.addWidget(make_waive_button, 0)

    if on_report_supervisor is not None and show_report_supervisor_in_filters:
        from pipeline_inspector.ui.settings_widgets import wire_button
        from pipeline_inspector.ui.waiver_manager import (
            VALIDATE_REPORT_SUPERVISOR_BUTTON_OBJECT_NAME,
        )

        report_supervisor_button = qt_widgets.QPushButton("Report Supervisor")
        report_supervisor_button.setObjectName(VALIDATE_REPORT_SUPERVISOR_BUTTON_OBJECT_NAME)
        set_tooltip = getattr(report_supervisor_button, "setToolTip", None)
        if set_tooltip is not None:
            set_tooltip(
                "Send the latest validation summary to your supervisor route "
                "(Telegram, Discord, or Slack)."
            )
        wire_button(report_supervisor_button, on_report_supervisor)
        filters_layout.addWidget(report_supervisor_button, 0)

    if filters_row_stretch:
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
    grid_host.setObjectName(EXPORT_ACTIONS_GRID_OBJECT_NAME)
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
            "Send to Tracker",
            EXPORT_SEND_TO_TRACKER_BUTTON_OBJECT_NAME,
            "Publish the last validation summary to the first enabled task tracker.",
            export_callbacks.on_send_to_tracker,
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

    numbers_only = _severity_counts_numbers_only_for_content(content)
    counts = {
        "critical": critical_count,
        "error": error_count,
        "warning": warning_count,
        "info": info_count,
    }
    setattr(content, _SEVERITY_COUNTS_ATTR, dict(counts))
    for object_name, severity_key, label in SEVERITY_COUNT_SPECS:
        severity_label = _find_child_widget(content, qt_widgets, object_name)
        if severity_label is None:
            continue
        set_text = getattr(severity_label, "setText", None)
        if set_text is not None:
            set_text(
                _severity_count_html(
                    severity_key,
                    label,
                    counts[severity_key],
                    numbers_only=numbers_only,
                )
            )


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
    *,
    user_config: Optional[UserPreferences] = None,
    on_make_waive: Optional[Callable[[], None]] = None,
    on_report_supervisor: Optional[Callable[[], None]] = None,
    show_make_waive_in_overflow: bool = False,
) -> Any:
    """Build pinned summary + action bar chrome for the Validate tab."""

    from pipeline_inspector.ui.user_preferences_ui import summary_header_state_from_user_config

    summary_state = (
        summary_header_state_from_user_config(user_config)
        if user_config is not None
        else SummaryHeaderState()
    )
    widget = qt_widgets.QWidget()
    widget.setObjectName(VALIDATE_STICKY_CHROME_OBJECT_NAME)
    layout = qt_widgets.QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    layout.addWidget(
        build_summary_header(
            qt_widgets,
            state=summary_state,
            profile_changed=validation_callbacks.on_profile_changed,
            asset_class_changed=validation_callbacks.on_asset_class_changed,
        )
    )
    layout.addWidget(
        build_validation_actions(
            qt_widgets,
            callbacks=validation_callbacks,
            issue_details_callbacks=issue_details_callbacks,
            on_make_waive=on_make_waive,
            on_report_supervisor=on_report_supervisor,
            show_make_waive_in_overflow=show_make_waive_in_overflow,
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
        return "Last validated: вЂ”"
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
    return "Scope: вЂ”"


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
        parts.append("Validation age unknown вЂ” revalidate before publishing exports.")
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
    *,
    waiver_callbacks: Optional[WaiverManagerCallbacks] = None,
    user_config: Optional[UserPreferences] = None,
) -> Any:
    tab = qt_widgets.QWidget()
    tab.setObjectName(VALIDATE_TAB_OBJECT_NAME)
    layout = qt_widgets.QVBoxLayout(tab)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(6)

    waiver_callbacks = waiver_callbacks or WaiverManagerCallbacks()

    from pipeline_inspector.ui.ui_density_tokens import density_tokens, normalize_density

    pane_tokens = density_tokens(
        normalize_density(user_config.ui_density if user_config is not None else "comfortable")
    )

    layout.addWidget(
        build_validate_sticky_chrome(
            qt_widgets,
            validation_callbacks,
            issue_details_callbacks,
            user_config=user_config,
            on_make_waive=waiver_callbacks.on_make_waive,
            on_report_supervisor=waiver_callbacks.on_report_supervisor,
            show_make_waive_in_overflow=not pane_tokens.show_make_waive_in_filters,
        )
    )

    issues_table = build_issues_table(
        qt_widgets,
        on_make_waive=waiver_callbacks.on_make_waive,
        on_report_supervisor=waiver_callbacks.on_report_supervisor,
        show_make_waive_in_filters=pane_tokens.show_make_waive_in_filters,
        show_report_supervisor_in_filters=pane_tokens.show_make_waive_in_filters,
        filters_row_stretch=pane_tokens.filters_row_stretch,
    )
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
        pane_orientation = _qt_splitter_orientation(
            qt_widgets,
            vertical=pane_tokens.issues_pane_vertical,
        )
        set_orientation = getattr(splitter, "setOrientation", None)
        if pane_orientation is not None and set_orientation is not None:
            set_orientation(pane_orientation)
        splitter.addWidget(issues_table)
        splitter.addWidget(details_panel)
        set_stretch = getattr(splitter, "setStretchFactor", None)
        if set_stretch is not None:
            if pane_tokens.issues_pane_vertical:
                set_stretch(0, 2)
                set_stretch(1, 1)
            else:
                set_stretch(0, 3)
                set_stretch(1, 2)
        if pane_tokens.issues_pane_sizes is not None:
            set_sizes = getattr(splitter, "setSizes", None)
            if set_sizes is not None:
                set_sizes(list(pane_tokens.issues_pane_sizes))
        if pane_tokens.issues_pane_vertical:
            set_minimum_width = getattr(details_panel, "setMinimumWidth", None)
            if set_minimum_width is not None:
                set_minimum_width(0)
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
    tab.setObjectName(REPORTS_TAB_OBJECT_NAME)
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
        layout.addWidget(
            _severity_count_label(qt_widgets, object_name, severity_key, label, count)
        )
    return row


def _severity_counts_numbers_only_for_content(content: Any) -> bool:
    from pipeline_inspector.ui.ui_density_tokens import density_tokens, normalize_density

    density = str(
        getattr(content, "_pipeline_inspector_ui_density", "comfortable") or "comfortable"
    )
    return density_tokens(normalize_density(density)).severity_counts_numbers_only


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


def _severity_count_html(
    severity_key: str,
    label: str,
    count: int,
    *,
    numbers_only: bool = False,
) -> str:
    color = SEVERITY_ROW_NUMBER_COLORS.get(severity_key)
    if numbers_only and color:
        return f'<span style="color:{color}; font-weight: bold;">{count}</span>'
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
    actions_layout.addWidget(_action_bar_separator(qt_widgets))

    authoring_group = qt_widgets.QWidget()
    authoring_layout = qt_widgets.QHBoxLayout(authoring_group)
    authoring_layout.setContentsMargins(0, 0, 0, 0)
    authoring_layout.setSpacing(4)
    authoring_layout.addWidget(
        _compact_button(
            qt_widgets,
            "Create Rule Draft",
            CREATE_RULE_DRAFT_BUTTON_OBJECT_NAME,
            "Open the new rule wizard prefilled from the selected failed issue.",
            issue_callbacks.on_create_rule_draft,
        )
    )
    actions_layout.addWidget(authoring_group)
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
    separator.setObjectName("pipelineInspectorIssueDetailsSeparator")
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


def _action_bar_separator(
    qt_widgets: Any,
    object_name: str = VALIDATE_ACTION_BAR_SEPARATOR_OBJECT_NAME,
) -> Any:
    separator = qt_widgets.QLabel("|")
    separator.setObjectName(object_name)
    return separator


def _find_child_widget(content: Any, qt_widgets: Any, object_name: str) -> Any:
    from pipeline_inspector.ui.settings_widgets import find_child

    widget_class = getattr(qt_widgets, "QWidget", None)
    if widget_class is None:
        return None
    return find_child(content, widget_class, object_name)


def _find_descendant_by_object_name(root: Any, object_name: str) -> Any:
    from pipeline_inspector.ui.settings_widgets import _widget_children, _widget_object_name

    if _widget_object_name(root) == object_name:
        return root
    for child in _widget_children(root):
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


def apply_density_tokens(content: Any, qt_widgets: Any, tokens: Any) -> None:
    """Apply UI density tokens to the panel shell and Validate tab chrome."""

    from pipeline_inspector.ui.ui_density_tokens import UiDensityTokens

    if not isinstance(tokens, UiDensityTokens):
        return

    _apply_panel_header_density(content, qt_widgets, tokens)
    _apply_main_tab_chrome_density(content, qt_widgets, tokens)
    _apply_summary_header_density(content, qt_widgets, tokens)
    _apply_secondary_tabs_density(content, qt_widgets, tokens)
    _apply_validate_action_bar_density(content, qt_widgets, tokens)
    _apply_issues_table_density(content, qt_widgets, tokens)
    _apply_validate_issues_pane_layout(content, qt_widgets, tokens)
    _apply_validate_sticky_chrome_spacing(content, qt_widgets, tokens)
    _apply_panel_shell_width(content, qt_widgets, tokens)


def _apply_panel_header_density(content: Any, qt_widgets: Any, tokens: Any) -> None:
    header = _find_child_widget(content, qt_widgets, PANEL_HEADER_OBJECT_NAME)
    if header is None:
        return

    title = _find_child_widget(header, qt_widgets, PANEL_HEADER_TITLE_OBJECT_NAME)
    if title is not None:
        set_style = getattr(title, "setStyleSheet", None)
        if set_style is not None:
            set_style(tokens.panel_title_font_css)

    overflow = _find_child_widget(
        header,
        qt_widgets,
        PANEL_HEADER_OVERFLOW_BUTTON_OBJECT_NAME,
    )
    for object_name in (
        DOCUMENTATION_BUTTON_OBJECT_NAME,
        REPORT_BUG_BUTTON_OBJECT_NAME,
        CHECK_FOR_UPDATES_BUTTON_OBJECT_NAME,
    ):
        button = _find_child_widget(header, qt_widgets, object_name)
        if button is None:
            continue
        set_visible = getattr(button, "setVisible", None)
        if set_visible is not None:
            set_visible(not tokens.panel_header_overflow)

    if overflow is not None:
        set_visible = getattr(overflow, "setVisible", None)
        if set_visible is not None:
            set_visible(tokens.panel_header_overflow)

    header_layout = _widget_layout(header)
    if header_layout is not None:
        set_margins = getattr(header_layout, "setContentsMargins", None)
        if set_margins is not None:
            set_margins(0, 0, 0, 0)

    if tokens.panel_header_max_height is not None:
        set_max_height = getattr(header, "setMaximumHeight", None)
        if set_max_height is not None:
            set_max_height(tokens.panel_header_max_height)
        size_policy = getattr(qt_widgets, "QSizePolicy", None)
        set_policy = getattr(header, "setSizePolicy", None)
        if size_policy is not None and set_policy is not None:
            preferred = getattr(size_policy, "Preferred", None)
            fixed = getattr(size_policy, "Fixed", None)
            if preferred is not None and fixed is not None:
                set_policy(preferred, fixed)
    else:
        set_max_height = getattr(header, "setMaximumHeight", None)
        if set_max_height is not None:
            set_max_height(_QT_WIDGETSIZE_MAX)

    set_style = getattr(header, "setStyleSheet", None)
    if set_style is not None:
        set_style(tokens.panel_header_chrome_stylesheet)

    gear_button = _find_child_widget(header, qt_widgets, SETTINGS_GEAR_BUTTON_OBJECT_NAME)
    if gear_button is not None and tokens.panel_header_max_height is not None:
        set_fixed_height = getattr(gear_button, "setFixedHeight", None)
        if set_fixed_height is not None:
            set_fixed_height(tokens.panel_header_max_height)



def _apply_main_tab_chrome_density(content: Any, qt_widgets: Any, tokens: Any) -> None:
    """Tighten the main tab bar against the panel header in comfortable density."""

    tabs = _find_child_widget(content, qt_widgets, TAB_WIDGET_OBJECT_NAME)
    if tabs is None:
        return

    set_document_mode = getattr(tabs, "setDocumentMode", None)
    if tokens.main_tab_chrome_stylesheet and set_document_mode is not None:
        set_document_mode(True)
    elif set_document_mode is not None:
        set_document_mode(False)

    set_style = getattr(tabs, "setStyleSheet", None)
    if set_style is not None:
        set_style(tokens.main_tab_chrome_stylesheet)

    tab_bar = getattr(tabs, "tabBar", None)
    if tab_bar is not None and tokens.main_tab_chrome_stylesheet:
        tab_bar_widget = tab_bar()
        tab_bar_layout = _widget_layout(tab_bar_widget)
        if tab_bar_layout is not None:
            set_margins = getattr(tab_bar_layout, "setContentsMargins", None)
            if set_margins is not None:
                set_margins(0, 0, 0, 0)



def _apply_summary_header_density(content: Any, qt_widgets: Any, tokens: Any) -> None:
    summary = _find_child_widget(content, qt_widgets, SUMMARY_HEADER_OBJECT_NAME)
    if summary is None:
        return

    set_style = getattr(summary, "setStyleSheet", None)
    if set_style is not None:
        set_style(tokens.summary_style_sheet)

    layout = _widget_layout(summary)
    if layout is not None:
        set_spacing = getattr(layout, "setSpacing", None)
        if set_spacing is not None:
            set_spacing(tokens.summary_layout_spacing)

    context_row = _find_child_widget(summary, qt_widgets, SUMMARY_CONTEXT_ROW_OBJECT_NAME)
    if context_row is not None:
        set_visible = getattr(context_row, "setVisible", None)
        if set_visible is not None:
            set_visible(tokens.show_summary_context_row)

    for object_name in (
        PUBLISH_BLOCK_LABEL_OBJECT_NAME,
        DEADLINE_BLOCK_LABEL_OBJECT_NAME,
    ):
        label = _find_child_widget(summary, qt_widgets, object_name)
        if label is None:
            continue
        set_visible = getattr(label, "setVisible", None)
        if set_visible is not None:
            set_visible(tokens.show_publish_deadline_labels)

    for row_object_name in (
        SUMMARY_METRICS_ROW_OBJECT_NAME,
        SUMMARY_PROFILE_ROW_OBJECT_NAME,
    ):
        row = _find_child_widget(summary, qt_widgets, row_object_name)
        if row is None:
            continue
        set_max_width = getattr(row, "setMaximumWidth", None)
        if tokens.panel_max_width is not None and set_max_width is not None:
            set_max_width(tokens.panel_max_width)
        elif set_max_width is not None:
            set_max_width(_QT_WIDGETSIZE_MAX)

    severity_row = _find_child_widget(summary, qt_widgets, SEVERITY_COUNTS_ROW_OBJECT_NAME)
    if severity_row is not None:
        severity_layout = _widget_layout(severity_row)
        if severity_layout is not None:
            set_spacing = getattr(severity_layout, "setSpacing", None)
            if set_spacing is not None:
                set_spacing(4 if tokens.severity_counts_numbers_only else 12)
        for object_name, severity_key, label in SEVERITY_COUNT_SPECS:
            severity_label = _find_child_widget(summary, qt_widgets, object_name)
            if severity_label is None:
                continue
            count = _severity_count_for_density_apply(
                content,
                severity_key,
                severity_label,
            )
            set_text = getattr(severity_label, "setText", None)
            if set_text is not None:
                set_text(
                    _severity_count_html(
                        severity_key,
                        label,
                        count,
                        numbers_only=tokens.severity_counts_numbers_only,
                    )
                )



def _severity_count_for_density_apply(
    content: Any,
    severity_key: str,
    label: Any,
) -> int:
    stored_counts = getattr(content, _SEVERITY_COUNTS_ATTR, None)
    if isinstance(stored_counts, dict) and severity_key in stored_counts:
        try:
            return max(0, int(stored_counts[severity_key]))
        except (TypeError, ValueError):
            pass
    return _severity_count_value_from_label(label)


def _severity_count_value_from_label(label: Any) -> int:
    text_fn = getattr(label, "text", None)
    if callable(text_fn):
        raw_text = str(text_fn())
    elif isinstance(text_fn, str):
        raw_text = text_fn
    else:
        return 0

    span_match = re.search(r">(\d+)</span>\s*$", raw_text)
    if span_match is not None:
        return int(span_match.group(1))

    colon_match = re.search(r":\s*(?:<[^>]+>\s*)?(\d+)\b", raw_text)
    if colon_match is not None:
        return int(colon_match.group(1))

    plain_text = re.sub(r"<[^>]+>", "", raw_text).strip()
    if plain_text.isdigit():
        return int(plain_text)

    return 0


def _apply_secondary_tabs_density(content: Any, qt_widgets: Any, tokens: Any) -> None:
    """Relayout Reports/Farm action buttons for compact panel width."""

    export_labels = (
        _COMPACT_EXPORT_BUTTON_LABELS
        if tokens.secondary_tab_button_columns == 1
        else _FULL_EXPORT_BUTTON_LABELS
    )
    export_grid_host = _find_child_widget(content, qt_widgets, EXPORT_ACTIONS_GRID_OBJECT_NAME)
    export_actions = _find_child_widget(content, qt_widgets, EXPORT_ACTIONS_OBJECT_NAME)
    if export_actions is not None:
        export_layout = _widget_layout(export_actions)
        if export_layout is not None:
            set_margins = getattr(export_layout, "setContentsMargins", None)
            if set_margins is not None:
                bottom_margin = 6 if tokens.secondary_tab_button_columns == 1 else 0
                set_margins(0, 0, 0, bottom_margin)
    if export_grid_host is not None:
        _apply_button_grid_density(
            content,
            export_grid_host,
            qt_widgets,
            _EXPORT_BUTTON_LAYOUT_ORDER,
            export_labels,
            columns=tokens.secondary_tab_button_columns,
            panel_max_width=tokens.panel_max_width,
        )

    from pipeline_inspector.ui.farm_tab import (
        FARM_ACTION_BUTTONS_OBJECT_NAME,
        FARM_BUTTON_LAYOUT_ORDER,
        FARM_COMPACT_BUTTON_LABELS,
        FARM_FULL_BUTTON_LABELS,
    )

    farm_labels = (
        FARM_COMPACT_BUTTON_LABELS
        if tokens.secondary_tab_button_columns == 1
        else FARM_FULL_BUTTON_LABELS
    )
    farm_buttons_host = _find_child_widget(content, qt_widgets, FARM_ACTION_BUTTONS_OBJECT_NAME)
    if farm_buttons_host is not None:
        _apply_button_grid_density(
            content,
            farm_buttons_host,
            qt_widgets,
            FARM_BUTTON_LAYOUT_ORDER,
            farm_labels,
            columns=tokens.secondary_tab_button_columns,
            panel_max_width=tokens.panel_max_width,
        )



def _apply_button_grid_density(
    content: Any,
    grid_host: Any,
    qt_widgets: Any,
    button_order: Sequence[str],
    labels_by_object_name: dict[str, str],
    *,
    columns: int,
    panel_max_width: int | None,
) -> None:
    grid_layout = _widget_layout(grid_host)
    if grid_layout is None:
        return

    buttons: list[Any] = []
    for object_name in button_order:
        button = _find_child_widget(content, qt_widgets, object_name)
        if button is not None:
            buttons.append(button)

    remove_widget = getattr(grid_layout, "removeWidget", None)
    if callable(remove_widget):
        for button in buttons:
            remove_widget(button)

    add_widget = getattr(grid_layout, "addWidget", None)
    if not callable(add_widget):
        return

    normalized_columns = max(1, int(columns))
    for index, button in enumerate(buttons):
        from pipeline_inspector.ui.settings_widgets import _widget_object_name

        object_name = _widget_object_name(button)
        label = labels_by_object_name.get(object_name)
        if label is not None:
            set_text = getattr(button, "setText", None)
            if set_text is not None:
                set_text(label)
        if panel_max_width is not None and normalized_columns == 1:
            set_minimum_width = getattr(button, "setMinimumWidth", None)
            if set_minimum_width is not None:
                set_minimum_width(max(0, panel_max_width - 12))
        size_policy = getattr(qt_widgets, "QSizePolicy", None)
        set_policy = getattr(button, "setSizePolicy", None)
        if size_policy is not None and set_policy is not None:
            if normalized_columns == 1:
                expanding = getattr(size_policy, "Expanding", None)
                fixed = getattr(size_policy, "Fixed", None)
                if expanding is not None and fixed is not None:
                    set_policy(expanding, fixed)
            else:
                preferred = getattr(size_policy, "Preferred", None)
                fixed = getattr(size_policy, "Fixed", None)
                if preferred is not None and fixed is not None:
                    set_policy(preferred, fixed)
        row = index // normalized_columns
        column = index % normalized_columns
        add_widget(button, row, column)


def _apply_validate_action_bar_density(content: Any, qt_widgets: Any, tokens: Any) -> None:
    action_bar = _find_child_widget(content, qt_widgets, VALIDATE_ACTION_BAR_OBJECT_NAME)
    if action_bar is None:
        return

    for object_name in (
        VALIDATE_PIPELINE_ACTIONS_OBJECT_NAME,
        VALIDATE_TRIAGE_ACTIONS_OBJECT_NAME,
    ):
        group = _find_child_widget(action_bar, qt_widgets, object_name)
        if group is None:
            continue
        set_visible = getattr(group, "setVisible", None)
        if set_visible is not None:
            show_group = (
                tokens.show_pipeline_actions
                if object_name == VALIDATE_PIPELINE_ACTIONS_OBJECT_NAME
                else tokens.show_triage_actions
            )
            set_visible(show_group)

    for child in _walk_widget_tree(action_bar):
        from pipeline_inspector.ui.settings_widgets import _widget_object_name

        object_name = _widget_object_name(child)
        if not object_name.startswith(VALIDATE_ACTION_BAR_SEPARATOR_OBJECT_NAME):
            continue
        set_visible = getattr(child, "setVisible", None)
        if set_visible is not None:
            set_visible(tokens.show_action_bar_separators)

    overflow = _find_child_widget(
        action_bar,
        qt_widgets,
        VALIDATE_ACTION_OVERFLOW_BUTTON_OBJECT_NAME,
    )
    if overflow is not None:
        set_visible = getattr(overflow, "setVisible", None)
        if set_visible is not None:
            set_visible(tokens.validate_action_overflow)


def _apply_issues_table_density(content: Any, qt_widgets: Any, tokens: Any) -> None:
    table = _find_child_widget(content, qt_widgets, ISSUES_TABLE_OBJECT_NAME)
    if table is None:
        return

    column_count = getattr(table, "columnCount", None)
    columns = int(column_count()) if callable(column_count) else 0
    for column_index in range(columns):
        set_hidden = getattr(table, "setColumnHidden", None)
        if set_hidden is None:
            continue
        set_hidden(column_index, column_index in tokens.hidden_issue_columns)

    if tokens.issues_table_shrink_to_contents:
        _shrink_issues_table_to_visible_columns(table, qt_widgets, tokens)

    vertical_header = getattr(table, "verticalHeader", lambda: None)()
    if vertical_header is not None:
        set_default_section_size = getattr(vertical_header, "setDefaultSectionSize", None)
        if set_default_section_size is not None:
            set_default_section_size(tokens.table_row_height)

    from pipeline_inspector.ui.waiver_manager import (
        VALIDATE_MAKE_WAIVE_BUTTON_OBJECT_NAME,
        VALIDATE_REPORT_SUPERVISOR_BUTTON_OBJECT_NAME,
    )

    make_waive_button = _find_child_widget(
        content,
        qt_widgets,
        VALIDATE_MAKE_WAIVE_BUTTON_OBJECT_NAME,
    )
    if make_waive_button is not None:
        _set_filter_row_widget_visible(
            content,
            qt_widgets,
            make_waive_button,
            visible=tokens.show_make_waive_in_filters,
        )

    report_supervisor_button = _find_child_widget(
        content,
        qt_widgets,
        VALIDATE_REPORT_SUPERVISOR_BUTTON_OBJECT_NAME,
    )
    if report_supervisor_button is not None:
        _set_filter_row_widget_visible(
            content,
            qt_widgets,
            report_supervisor_button,
            visible=tokens.show_make_waive_in_filters,
        )

    for object_name in (
        ISSUES_VIEW_FILTER_OBJECT_NAME,
        ISSUES_SORT_DROPDOWN_OBJECT_NAME,
    ):
        filter_widget = _find_child_widget(content, qt_widgets, object_name)
        if filter_widget is None:
            continue
        _set_filter_row_widget_visible(
            content,
            qt_widgets,
            filter_widget,
            visible=object_name not in tokens.hidden_filter_object_names,
        )

    issues_host = _find_child_widget(content, qt_widgets, ISSUES_TABLE_WIDGET_OBJECT_NAME)
    if issues_host is not None and tokens.panel_max_width is not None:
        set_max_width = getattr(issues_host, "setMaximumWidth", None)
        if set_max_width is not None:
            set_max_width(tokens.panel_max_width)



def _shrink_issues_table_to_visible_columns(table: Any, qt_widgets: Any, tokens: Any) -> None:
    """Keep only visible issue columns sized to contents in compact density."""

    size_policy = getattr(qt_widgets, "QSizePolicy", None)
    set_policy = getattr(table, "setSizePolicy", None)
    if size_policy is not None and set_policy is not None:
        set_policy(size_policy.Preferred, size_policy.Expanding)

    horizontal_header = getattr(table, "horizontalHeader", lambda: None)()
    if horizontal_header is None:
        return

    set_stretch_last = getattr(horizontal_header, "setStretchLastSection", None)
    if set_stretch_last is not None:
        set_stretch_last(False)

    header_view = getattr(qt_widgets, "QHeaderView", None)
    resize_to_contents = (
        getattr(header_view, "ResizeToContents", None) if header_view is not None else None
    )
    set_section_resize_mode = getattr(horizontal_header, "setSectionResizeMode", None)
    column_count = getattr(table, "columnCount", None)
    columns = int(column_count()) if callable(column_count) else 0
    for column_index in range(columns):
        if column_index in tokens.hidden_issue_columns:
            continue
        if set_section_resize_mode is not None and resize_to_contents is not None:
            set_section_resize_mode(column_index, resize_to_contents)


def _set_filter_row_widget_visible(
    content: Any,
    qt_widgets: Any,
    widget: Any,
    *,
    visible: bool,
) -> None:
    """Show or hide a filters-row widget and detach it from layout when hidden."""

    set_visible = getattr(widget, "setVisible", None)
    if set_visible is not None:
        set_visible(visible)

    filters_row = _find_child_widget(content, qt_widgets, ISSUES_FILTERS_ROW_OBJECT_NAME)
    if filters_row is None:
        return
    filters_layout = _widget_layout(filters_row)
    if filters_layout is None:
        return

    index_of = getattr(filters_layout, "indexOf", None)
    remove_widget = getattr(filters_layout, "removeWidget", None)
    add_widget = getattr(filters_layout, "addWidget", None)
    if not callable(index_of) or not callable(remove_widget) or not callable(add_widget):
        return

    widget_index = index_of(widget)
    if not visible and widget_index >= 0:
        remove_widget(widget)
        return
    if visible and widget_index < 0:
        add_widget(widget, 0)


def _qt_splitter_orientation(qt_widgets: Any, *, vertical: bool) -> Any | None:
    qt_module: Any | None = None
    try:
        from pipeline_inspector.ui.qt import load_qt_core

        qt_module = load_qt_core().Qt
    except RuntimeError:
        qt_module = getattr(qt_widgets, "Qt", None)
    if qt_module is None:
        return None
    return getattr(qt_module, "Vertical" if vertical else "Horizontal", None)


def _apply_validate_issues_pane_layout(content: Any, qt_widgets: Any, tokens: Any) -> None:
    """Re-stack the issues table and details pane for compact density."""

    splitter_class = getattr(qt_widgets, "QSplitter", None)
    splitter = None
    if splitter_class is not None:
        from pipeline_inspector.ui.settings_widgets import find_child

        splitter = find_child(content, splitter_class, VALIDATE_ISSUES_SPLITTER_OBJECT_NAME)
    if splitter is None:
        splitter = _find_child_widget(content, qt_widgets, VALIDATE_ISSUES_SPLITTER_OBJECT_NAME)
    if splitter is None:
        return

    pane_orientation = _qt_splitter_orientation(
        qt_widgets,
        vertical=tokens.issues_pane_vertical,
    )
    set_orientation = getattr(splitter, "setOrientation", None)
    if pane_orientation is not None and set_orientation is not None:
        set_orientation(pane_orientation)

    set_stretch = getattr(splitter, "setStretchFactor", None)
    if set_stretch is not None:
        if tokens.issues_pane_vertical:
            set_stretch(0, 2)
            set_stretch(1, 1)
        else:
            set_stretch(0, 3)
            set_stretch(1, 2)

    if tokens.issues_pane_sizes is not None:
        set_sizes = getattr(splitter, "setSizes", None)
        if set_sizes is not None:
            set_sizes(list(tokens.issues_pane_sizes))
    elif not tokens.issues_pane_vertical:
        set_sizes = getattr(splitter, "setSizes", None)
        if set_sizes is not None:
            saved_sizes = getattr(content, "_pipeline_inspector_validate_splitter_sizes", None)
            if saved_sizes:
                set_sizes([int(size) for size in saved_sizes])
            else:
                set_sizes([520, 300])

    details_panel = _find_child_widget(content, qt_widgets, DETAILS_PANEL_OBJECT_NAME)
    if details_panel is not None:
        set_minimum_width = getattr(details_panel, "setMinimumWidth", None)
        if set_minimum_width is not None:
            set_minimum_width(0 if tokens.issues_pane_vertical else DETAILS_PANEL_MIN_WIDTH)



def _apply_validate_sticky_chrome_spacing(content: Any, qt_widgets: Any, tokens: Any) -> None:
    sticky = _find_child_widget(content, qt_widgets, VALIDATE_STICKY_CHROME_OBJECT_NAME)
    if sticky is None:
        return
    layout = _widget_layout(sticky)
    if layout is None:
        return
    set_spacing = getattr(layout, "setSpacing", None)
    if set_spacing is not None:
        set_spacing(tokens.sticky_chrome_spacing)


def _apply_widget_width_constraint(
    widget: Any,
    max_width: int | None,
    size_policy: Any | None,
) -> None:
    """Clamp a widget to a compact panel width or restore the Qt default."""

    set_max_width = getattr(widget, "setMaximumWidth", None)
    set_policy = getattr(widget, "setSizePolicy", None)
    if max_width is None:
        if set_max_width is not None:
            set_max_width(_QT_WIDGETSIZE_MAX)
        if size_policy is not None and set_policy is not None:
            preferred = getattr(size_policy, "Preferred", None)
            expanding = getattr(size_policy, "Expanding", None)
            if preferred is not None and expanding is not None:
                set_policy(preferred, expanding)
        return

    if set_max_width is not None:
        set_max_width(max_width)
    if size_policy is not None and set_policy is not None:
        maximum = getattr(size_policy, "Maximum", None)
        expanding = getattr(size_policy, "Expanding", None)
        if maximum is not None and expanding is not None:
            set_policy(maximum, expanding)


def _apply_panel_shell_width(content: Any, qt_widgets: Any, tokens: Any) -> None:
    """Clamp the dock shell and Validate body to the compact panel width."""

    size_policy = getattr(qt_widgets, "QSizePolicy", None)
    targets = [content]
    for object_name in (
        PANEL_BODY_STACK_OBJECT_NAME,
        TAB_WIDGET_OBJECT_NAME,
        VALIDATE_STICKY_CHROME_OBJECT_NAME,
        SUMMARY_HEADER_OBJECT_NAME,
        ISSUES_TABLE_WIDGET_OBJECT_NAME,
        DETAILS_PANEL_OBJECT_NAME,
        PANEL_HEADER_OBJECT_NAME,
    ):
        widget = _find_child_widget(content, qt_widgets, object_name)
        if widget is not None:
            targets.append(widget)

    for target in targets:
        _apply_widget_width_constraint(target, tokens.panel_max_width, size_policy)

    dock = getattr(content, "_pipeline_inspector_dock", None)
    if dock is not None:
        _apply_widget_width_constraint(dock, tokens.panel_max_width, size_policy)
        adjust_size = getattr(dock, "adjustSize", None)
        if adjust_size is not None and tokens.panel_max_width is not None:
            adjust_size()



def _widget_layout(widget: Any) -> Any | None:
    layout_attr = getattr(widget, "layout", None)
    if layout_attr is None:
        return None
    if callable(layout_attr):
        return layout_attr()
    return layout_attr


_OVERFLOW_MENU_STYLE_SHEET = (
    "QMenu { background-color: #2b2b2b; color: #e8e8e8; border: 1px solid #555555; }"
    "QMenu::item { padding: 6px 28px; background-color: transparent; }"
    "QMenu::item:selected { background-color: #3d6db8; color: #ffffff; }"
    "QMenu::item:disabled { color: #777777; }"
)


def _configure_overflow_menu(menu: Any) -> None:
    set_style = getattr(menu, "setStyleSheet", None)
    if set_style is not None:
        set_style(_OVERFLOW_MENU_STYLE_SHEET)


def _connect_menu_action(action: Any, callback: Optional[Callable[[], None]]) -> None:
    if callback is None:
        set_enabled = getattr(action, "setEnabled", None)
        if set_enabled is not None:
            set_enabled(False)
        return

    set_enabled = getattr(action, "setEnabled", None)
    if set_enabled is not None:
        set_enabled(True)

    def _invoke_action(*_args: Any) -> None:
        callback()

    for signal_name in ("triggered", "activated"):
        signal = getattr(action, signal_name, None)
        connect = getattr(signal, "connect", None)
        if connect is not None:
            connect(_invoke_action)
            return


def _build_overflow_menu_button(
    qt_widgets: Any,
    *,
    label: str,
    object_name: str,
    tooltip: str,
    actions: Sequence[tuple[str, Optional[Callable[[], None]]]],
) -> Any:
    menu_class = getattr(qt_widgets, "QMenu", None)
    tool_button_class = getattr(qt_widgets, "QToolButton", None)
    if menu_class is None:
        button = qt_widgets.QPushButton(label)
        button.setObjectName(object_name)
        return button

    button = tool_button_class() if tool_button_class is not None else qt_widgets.QPushButton(label)

    button.setObjectName(object_name)
    set_text = getattr(button, "setText", None)
    if set_text is not None:
        set_text(label)
    set_tooltip = getattr(button, "setToolTip", None)
    if set_tooltip is not None:
        set_tooltip(tooltip)
    set_visible = getattr(button, "setVisible", None)
    if set_visible is not None:
        set_visible(False)

    menu = menu_class(button)
    _configure_overflow_menu(menu)
    for action_label, callback in actions:
        add_action = getattr(menu, "addAction", None)
        if add_action is None:
            continue
        action = add_action(action_label)
        _connect_menu_action(action, callback)

    if tool_button_class is not None:
        instant_popup = getattr(tool_button_class, "InstantPopup", None)
        menu_button_popup = getattr(tool_button_class, "MenuButtonPopup", None)
        set_popup_mode = getattr(button, "setPopupMode", None)
        if set_popup_mode is not None and instant_popup is not None:
            set_popup_mode(instant_popup)
        elif set_popup_mode is not None and menu_button_popup is not None:
            set_popup_mode(menu_button_popup)
        set_menu = getattr(button, "setMenu", None)
        if set_menu is not None:
            set_menu(menu)
            button.menu = menu
            return button

    clicked = getattr(button, "clicked", None)
    connect = getattr(clicked, "connect", None)
    if connect is not None:
        exec_fn = getattr(menu, "exec_", None)
        map_to_global = getattr(button, "mapToGlobal", None)

        def _show_menu() -> None:
            if exec_fn is None or map_to_global is None:
                return
            try:
                from pipeline_inspector.ui.qt import load_qt_core

                qt_core = load_qt_core()
                point = qt_core.QPoint(0, int(getattr(button, "height", lambda: 24)() or 24))
                exec_fn(map_to_global(point))
            except RuntimeError:
                exec_fn()

        connect(_show_menu)

    button.menu = menu
    return button


def _build_panel_header_overflow_button(
    qt_widgets: Any,
    *,
    navigation_callbacks: PanelNavigationCallbacks,
    secondary_buttons: Sequence[Any],
) -> Any:
    _ = secondary_buttons
    return _build_overflow_menu_button(
        qt_widgets,
        label="\u22ee",
        object_name=PANEL_HEADER_OVERFLOW_BUTTON_OBJECT_NAME,
        tooltip="More panel actions",
        actions=(
            ("Documentation", navigation_callbacks.on_open_documentation),
            ("Report Plugin Bug", navigation_callbacks.on_report_bug),
            ("Check for Updates", navigation_callbacks.on_check_for_updates),
        ),
    )


def _build_validate_action_overflow_button(
    qt_widgets: Any,
    *,
    pipeline_group: Any,
    triage_group: Any,
    overflow_actions: Sequence[tuple[str, Optional[Callable[[], None]]]],
) -> Any:
    _ = (pipeline_group, triage_group)
    return _build_overflow_menu_button(
        qt_widgets,
        label="More",
        object_name=VALIDATE_ACTION_OVERFLOW_BUTTON_OBJECT_NAME,
        tooltip="Pipeline, triage, and waiver actions",
        actions=overflow_actions,
    )


def _walk_widget_tree(root: Any) -> list[Any]:
    """Return widgets in a depth-first traversal."""

    from pipeline_inspector.ui.settings_widgets import _widget_children

    discovered: list[Any] = []
    stack = [root]
    while stack:
        current = stack.pop()
        discovered.append(current)
        stack.extend(_widget_children(current))
    return discovered


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
