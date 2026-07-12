"""Bug report relay configuration for studio-hosted HTTPS relays."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

DEFAULT_TIMEOUT_SECONDS = 30.0

@dataclass(frozen=True)
class BugReportRelayConfig:
    """Connection defaults for a studio bug report relay endpoint."""

    relay_url: str
    api_key: str
    allow_screenshot: bool = True
    max_reports_per_day: int = 5
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    def with_overrides(self, **kwargs: Any) -> BugReportRelayConfig:
        """Return a copy with selected fields replaced."""

        return replace(self, **kwargs)
