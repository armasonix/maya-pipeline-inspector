"""Bug report relay configuration for studio-hosted HTTPS relays."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

DEFAULT_TIMEOUT_SECONDS = 30.0
BUG_REPORT_MAX_REPORTS_PER_DAY = 3
DEFAULT_PUBLIC_BUG_REPORT_RELAY_URL = (
    "https://maya-pipeline-inspector-bug-report.armasonix.workers.dev"
)


def effective_bug_report_relay_url(relay_url: str) -> str:
    """Return the configured relay URL or the shipped public default."""

    normalized = relay_url.strip()
    if normalized:
        return normalized
    return DEFAULT_PUBLIC_BUG_REPORT_RELAY_URL


def is_public_bug_report_relay_url(relay_url: str) -> bool:
    """Return True when the relay URL targets the shipped public worker."""

    return (
        effective_bug_report_relay_url(relay_url).rstrip("/")
        == DEFAULT_PUBLIC_BUG_REPORT_RELAY_URL.rstrip("/")
    )


@dataclass(frozen=True)
class BugReportRelayConfig:
    """Connection defaults for a studio bug report relay endpoint."""

    relay_url: str
    api_key: str
    max_reports_per_day: int = BUG_REPORT_MAX_REPORTS_PER_DAY
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    def with_overrides(self, **kwargs: Any) -> BugReportRelayConfig:
        """Return a copy with selected fields replaced."""

        return replace(self, **kwargs)
