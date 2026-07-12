from __future__ import annotations

from types import SimpleNamespace

from pipeline_inspector.ui.issues_triage import (
    IssueFilterPrefs,
    apply_combo_preference,
    read_issue_filter_prefs,
    resolve_combo_preference,
    write_issue_filter_prefs,
)
from pipeline_inspector.ui.main_window import ALL_SEVERITIES_LABEL


class FakeCombo:
    def __init__(self, *, text: str = ALL_SEVERITIES_LABEL) -> None:
        self.text = text

    def setCurrentText(self, text: str) -> None:
        self.text = text


def test_resolve_combo_preference_keeps_valid_choice():
    choice = resolve_combo_preference(
        "critical",
        ("All severities", "critical", "error"),
        fallback=ALL_SEVERITIES_LABEL,
    )

    assert choice == "critical"


def test_resolve_combo_preference_falls_back_when_choice_missing():
    choice = resolve_combo_preference(
        "info",
        ("All severities", "critical", "error"),
        fallback=ALL_SEVERITIES_LABEL,
    )

    assert choice == ALL_SEVERITIES_LABEL


def test_apply_combo_preference_sets_combo_text():
    combo = FakeCombo()

    applied = apply_combo_preference(
        combo,
        ("All severities", "critical"),
        "critical",
        fallback=ALL_SEVERITIES_LABEL,
    )

    assert applied == "critical"
    assert combo.text == "critical"


def test_read_and_write_issue_filter_prefs_round_trip():
    content = SimpleNamespace()
    prefs = IssueFilterPrefs(
        severity="critical",
        owner="lookdev",
        view="Blocking only",
        sort="material",
    )

    write_issue_filter_prefs(content, prefs)

    assert read_issue_filter_prefs(content) == prefs
