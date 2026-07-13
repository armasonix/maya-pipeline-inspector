"""Issue triage helpers for filter persistence and table interactions."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from pipeline_inspector.ui.main_window import (
    ALL_ISSUES_LABEL,
    ALL_OWNERS_LABEL,
    ALL_SEVERITIES_LABEL,
    ISSUES_OWNER_FILTER_OBJECT_NAME,
    ISSUES_SEVERITY_FILTER_OBJECT_NAME,
    ISSUES_SORT_DROPDOWN_OBJECT_NAME,
    ISSUES_VIEW_FILTER_OBJECT_NAME,
)

ISSUE_FILTER_PREFS_ATTR = "_pipeline_inspector_issue_filter_prefs"

@dataclass(frozen=True)
class IssueFilterPrefs:
    """Per-session issues table filter and sort preferences."""

    severity: str = ALL_SEVERITIES_LABEL
    owner: str = ALL_OWNERS_LABEL
    view: str = ALL_ISSUES_LABEL
    sort: str = "severity"

def resolve_combo_preference(
    preferred: str,
    options: Sequence[str],
    *,
    fallback: str,
) -> str:
    """Return the preferred combo value when still valid, otherwise a fallback."""

    if preferred in options:
        return preferred
    if fallback in options:
        return fallback
    return options[0] if options else preferred

def read_issue_filter_prefs(content: Any) -> IssueFilterPrefs:
    """Read stored issue filter preferences from panel content."""

    stored = getattr(content, ISSUE_FILTER_PREFS_ATTR, None)
    if isinstance(stored, IssueFilterPrefs):
        return stored
    return IssueFilterPrefs()

def write_issue_filter_prefs(content: Any, prefs: IssueFilterPrefs) -> None:
    """Persist issue filter preferences on panel content."""

    setattr(content, ISSUE_FILTER_PREFS_ATTR, prefs)

def read_issue_filter_prefs_from_widgets(
    content: Any,
    qt_widgets: Any,
    *,
    find_child: Any,
) -> IssueFilterPrefs:
    """Capture the current issues-table filter controls into prefs."""

    severity_filter = find_child(
        content,
        qt_widgets.QComboBox,
        ISSUES_SEVERITY_FILTER_OBJECT_NAME,
    )
    owner_filter = find_child(
        content,
        qt_widgets.QComboBox,
        ISSUES_OWNER_FILTER_OBJECT_NAME,
    )
    view_filter = find_child(
        content,
        qt_widgets.QComboBox,
        ISSUES_VIEW_FILTER_OBJECT_NAME,
    )
    sort_dropdown = find_child(
        content,
        qt_widgets.QComboBox,
        ISSUES_SORT_DROPDOWN_OBJECT_NAME,
    )
    prefs = IssueFilterPrefs(
        severity=_combo_text(severity_filter, ALL_SEVERITIES_LABEL),
        owner=_combo_text(owner_filter, ALL_OWNERS_LABEL),
        view=_combo_text(view_filter, ALL_ISSUES_LABEL),
        sort=_combo_text(sort_dropdown, "severity"),
    )
    write_issue_filter_prefs(content, prefs)
    return prefs

def apply_combo_preference(
    combo: Any,
    options: Sequence[str],
    preferred: str,
    *,
    fallback: str,
) -> str:
    """Set a combo box to a stored preference when possible."""

    if combo is None or not options:
        return preferred
    choice = resolve_combo_preference(preferred, options, fallback=fallback)
    set_current = getattr(combo, "setCurrentText", None)
    if set_current is not None:
        set_current(choice)
    return choice

def _combo_text(combo: Any, default: str) -> str:
    current_text = getattr(combo, "currentText", None)
    if current_text is None:
        return default
    value = current_text()
    return str(value or default)
