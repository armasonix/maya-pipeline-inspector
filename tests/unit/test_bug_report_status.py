from __future__ import annotations

from pipeline_inspector.integrations.bug_report.relay_client import BugReportRelayResult
from pipeline_inspector.integrations.bug_report.status import (
    format_bug_report_failure_status,
    format_bug_report_issue_url_text,
    format_bug_report_success_headline,
)


def test_format_bug_report_success_headline():
    headline = format_bug_report_success_headline()
    assert "thank you" in headline.lower()
    assert "improve" in headline.lower()


def test_format_bug_report_issue_url_text_trims_whitespace():
    assert (
        format_bug_report_issue_url_text("  https://github.com/org/repo/issues/12  ")
        == "https://github.com/org/repo/issues/12"
    )


def test_format_bug_report_failure_status_maps_disabled_reason():
    result = BugReportRelayResult(submitted=False, skipped_reason="disabled")

    message = format_bug_report_failure_status(result)

    assert "disabled" in message.lower()
    assert "plugin" in message.lower()


def test_format_bug_report_failure_status_prefers_rate_limit_message():
    result = BugReportRelayResult(
        submitted=False,
        skipped_reason="rate_limited",
        error_message="Daily bug report limit reached (2/2).",
    )

    assert format_bug_report_failure_status(result) == "Daily bug report limit reached (2/2)."
