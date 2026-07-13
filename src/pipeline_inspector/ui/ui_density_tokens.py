"""Density tokens and Validate-tab footprint metrics for UI density modes."""
from __future__ import annotations

from dataclasses import dataclass

from pipeline_inspector.user_config import SUPPORTED_UI_DENSITIES

ISSUES_TABLE_MATERIAL_COLUMN_INDEX = 1
ISSUES_TABLE_NODE_COLUMN_INDEX = 2
ISSUES_TABLE_ISSUE_COLUMN_INDEX = 3
ISSUES_TABLE_OWNER_COLUMN_INDEX = 4
ISSUES_TABLE_RULE_COLUMN_INDEX = 5
ISSUES_TABLE_LOW_PRIORITY_COLUMNS = (
    ISSUES_TABLE_OWNER_COLUMN_INDEX,
    ISSUES_TABLE_RULE_COLUMN_INDEX,
)
ISSUES_TABLE_COMPACT_HIDDEN_COLUMNS = (
    ISSUES_TABLE_MATERIAL_COLUMN_INDEX,
    ISSUES_TABLE_NODE_COLUMN_INDEX,
    ISSUES_TABLE_ISSUE_COLUMN_INDEX,
    ISSUES_TABLE_OWNER_COLUMN_INDEX,
    ISSUES_TABLE_RULE_COLUMN_INDEX,
)
ISSUES_VIEW_FILTER_OBJECT_NAME = "pipelineInspectorIssuesViewFilter"
ISSUES_SORT_DROPDOWN_OBJECT_NAME = "pipelineInspectorIssuesSortDropdown"
ISSUES_TABLE_COMPACT_HIDDEN_FILTERS = frozenset(
    {
        ISSUES_VIEW_FILTER_OBJECT_NAME,
        ISSUES_SORT_DROPDOWN_OBJECT_NAME,
    }
)
COMPACT_PANEL_MAX_WIDTH = 300


@dataclass(frozen=True)
class UiDensityTokens:
    """Layout and typography tokens for a UI density mode."""

    content_margins: tuple[int, int, int, int]
    content_spacing: int
    tab_margins: tuple[int, int, int, int]
    tab_spacing: int
    sticky_chrome_spacing: int
    panel_title_font_css: str
    summary_style_sheet: str
    summary_visible_rows: int
    summary_row_height: int
    summary_layout_spacing: int
    show_summary_context_row: bool
    show_publish_deadline_labels: bool
    action_bar_height: int
    show_pipeline_actions: bool
    show_triage_actions: bool
    show_action_bar_separators: bool
    filters_row_height: int
    status_row_height: int
    table_row_height: int
    panel_header_overflow: bool
    validate_action_overflow: bool
    hidden_issue_columns: frozenset[int]
    hidden_filter_object_names: frozenset[str]
    show_make_waive_in_filters: bool
    filters_row_stretch: bool
    issues_table_shrink_to_contents: bool
    metrics_row_stretch: bool
    profile_row_stretch: bool
    panel_max_width: int | None
    issues_pane_vertical: bool
    issues_pane_sizes: tuple[int, int] | None


_COMFORTABLE_TOKENS = UiDensityTokens(
    content_margins=(8, 8, 8, 8),
    content_spacing=4,
    tab_margins=(8, 8, 8, 8),
    tab_spacing=6,
    sticky_chrome_spacing=4,
    panel_title_font_css="font-size: 14pt; font-weight: bold;",
    summary_style_sheet="",
    summary_visible_rows=3,
    summary_row_height=26,
    summary_layout_spacing=2,
    show_summary_context_row=True,
    show_publish_deadline_labels=True,
    action_bar_height=32,
    show_pipeline_actions=True,
    show_triage_actions=True,
    show_action_bar_separators=True,
    filters_row_height=28,
    status_row_height=24,
    table_row_height=24,
    panel_header_overflow=False,
    validate_action_overflow=False,
    hidden_issue_columns=frozenset(),
    hidden_filter_object_names=frozenset(),
    show_make_waive_in_filters=True,
    filters_row_stretch=True,
    issues_table_shrink_to_contents=False,
    metrics_row_stretch=True,
    profile_row_stretch=True,
    panel_max_width=None,
    issues_pane_vertical=False,
    issues_pane_sizes=None,
)

_COMPACT_TOKENS = UiDensityTokens(
    content_margins=(4, 4, 4, 4),
    content_spacing=2,
    tab_margins=(4, 4, 4, 4),
    tab_spacing=2,
    sticky_chrome_spacing=2,
    panel_title_font_css="font-size: 11pt; font-weight: bold;",
    summary_style_sheet="QLabel { font-size: 10pt; }",
    summary_visible_rows=2,
    summary_row_height=16,
    summary_layout_spacing=1,
    show_summary_context_row=False,
    show_publish_deadline_labels=False,
    action_bar_height=18,
    show_pipeline_actions=False,
    show_triage_actions=False,
    show_action_bar_separators=False,
    filters_row_height=16,
    status_row_height=12,
    table_row_height=18,
    panel_header_overflow=True,
    validate_action_overflow=True,
    hidden_issue_columns=frozenset(ISSUES_TABLE_COMPACT_HIDDEN_COLUMNS),
    hidden_filter_object_names=ISSUES_TABLE_COMPACT_HIDDEN_FILTERS,
    show_make_waive_in_filters=False,
    filters_row_stretch=False,
    issues_table_shrink_to_contents=True,
    metrics_row_stretch=False,
    profile_row_stretch=False,
    panel_max_width=COMPACT_PANEL_MAX_WIDTH,
    issues_pane_vertical=True,
    issues_pane_sizes=(180, 120),
)


def normalize_density(density: str) -> str:
    """Return a supported density id, defaulting to comfortable."""

    if density in SUPPORTED_UI_DENSITIES:
        return density
    return "comfortable"


def density_tokens(density: str) -> UiDensityTokens:
    """Return layout tokens for the requested density mode."""

    if normalize_density(density) == "compact":
        return _COMPACT_TOKENS
    return _COMFORTABLE_TOKENS


def validate_tab_chrome_footprint(density: str) -> int:
    """Estimate fixed Validate-tab chrome height from density tokens."""

    tokens = density_tokens(density)
    vertical_margins = tokens.tab_margins[1] + tokens.tab_margins[3]
    summary_height = (
        tokens.summary_visible_rows * tokens.summary_row_height
        + max(0, tokens.summary_visible_rows - 1) * tokens.summary_layout_spacing
    )
    section_gaps = 2 * tokens.tab_spacing
    return (
        vertical_margins
        + summary_height
        + tokens.sticky_chrome_spacing
        + tokens.action_bar_height
        + tokens.filters_row_height
        + tokens.status_row_height
        + section_gaps
    )
