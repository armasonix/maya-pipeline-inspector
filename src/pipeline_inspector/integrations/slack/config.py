"""Slack incoming webhook configuration for Pipeline Inspector notifications."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

DEFAULT_TIMEOUT_SECONDS = 10.0

@dataclass(frozen=True)
class SlackConfig:
    """Connection defaults for Slack incoming webhooks with channel routing."""

    publish_webhook_url: str = ""
    deadline_webhook_url: str = ""
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    def with_overrides(self, **kwargs: Any) -> SlackConfig:
        """Return a copy with selected fields replaced."""

        return replace(self, **kwargs)
