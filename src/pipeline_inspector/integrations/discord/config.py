"""Discord incoming webhook configuration for Pipeline Inspector notifications."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

DEFAULT_TIMEOUT_SECONDS = 10.0
USER_AGENT = "PipelineInspector/0.5 (Maya; +https://github.com/ledorub/maya-pipeline-inspector)"


@dataclass(frozen=True)
class DiscordConfig:
    """Connection defaults for a Discord incoming webhook."""

    webhook_url: str
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    def with_overrides(self, **kwargs: Any) -> DiscordConfig:
        """Return a copy with selected fields replaced."""

        return replace(self, **kwargs)
