"""Maya Shader Health Inspector panel content."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

PANEL_OBJECT_NAME = "shaderHealthInspectorPanel"
PANEL_TITLE = "Maya Shader Health Inspector"
PANEL_CONTENT_OBJECT_NAME = "shaderHealthInspectorPanelContent"
SUMMARY_HEADER_OBJECT_NAME = "shaderHealthInspectorSummaryHeader"
HEALTH_SCORE_LABEL_OBJECT_NAME = "shaderHealthInspectorHealthScoreLabel"
SEVERITY_COUNTS_LABEL_OBJECT_NAME = "shaderHealthInspectorSeverityCountsLabel"
BLOCK_STATUS_LABEL_OBJECT_NAME = "shaderHealthInspectorBlockStatusLabel"
PROFILE_LABEL_OBJECT_NAME = "shaderHealthInspectorProfileLabel"
PROFILE_DROPDOWN_OBJECT_NAME = "shaderHealthInspectorProfileDropdown"
DEFAULT_PROFILE_OPTIONS = (
    "artist_relaxed",
    "publish_strict",
    "deadline_critical",
    "supervisor_full",
)


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

    description = qt_widgets.QLabel(
        "Summary/header baseline. Validation, issues table, details, and export "
        "actions will be added by the next Milestone 6 issues."
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
    state: SummaryHeaderState | None = None,
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


def _yes_no(value: bool) -> str:
    return "YES" if value else "NO"
