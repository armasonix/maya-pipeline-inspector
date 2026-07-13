"""User-visible status messages for bug report relay submissions."""
from __future__ import annotations

from pipeline_inspector.integrations.bug_report.relay_client import BugReportRelayResult


def format_bug_report_success_headline() -> str:
    """Return the success headline shown after a relay accepts a report."""

    return (
        "Plugin bug report sent to Pipeline Inspector maintainers. "
        "Track the fix on GitHub:"
    )

def format_bug_report_issue_url_text(issue_url: str) -> str:
    """Return the issue URL label text shown on successful submission."""

    return issue_url.strip()

def format_bug_report_failure_status(result: BugReportRelayResult) -> str:
    """Return a user-visible failure message for a relay submission outcome."""

    if result.skipped_reason == "disabled":
        return "Plugin bug reports are disabled. Enable them in Settings → Bug Report."
    if result.skipped_reason == "incomplete_config":
        return (
            "Plugin bug report relay is not configured. "
            "Enable Bug Report in Settings or ask your TD to set a studio relay URL."
        )
    if result.skipped_reason == "rate_limited":
        if result.error_message:
            return result.error_message
        return "Daily bug report limit reached."
    if result.error_message:
        return result.error_message
    if result.status_code:
        return f"Bug report relay failed (HTTP {result.status_code})."
    return "Bug report relay failed."
