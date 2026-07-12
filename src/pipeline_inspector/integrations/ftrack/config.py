"""Ftrack API configuration for Pipeline Inspector task tracker integration."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any
from urllib.parse import urlparse

DEFAULT_TIMEOUT_SECONDS = 15.0


DEFAULT_NOTE_AUTHOR_USERNAME = "maya.pipeline.inspector"
DEFAULT_TASK_STATUS_NAME = "Pending Review"


@dataclass(frozen=True)
class FtrackConfig:
    """Connection defaults for the Ftrack HTTP API."""

    api_url: str
    api_user: str
    api_key: str
    project: str
    note_author_username: str = DEFAULT_NOTE_AUTHOR_USERNAME
    task_status_name: str = DEFAULT_TASK_STATUS_NAME
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    def with_overrides(self, **kwargs: Any) -> FtrackConfig:
        """Return a copy with selected fields replaced."""

        return replace(self, **kwargs)

    @property
    def endpoint_url(self) -> str:
        """Return the normalized Ftrack batch API endpoint."""

        normalized = self.api_url.strip().rstrip("/")
        if not normalized:
            return ""
        parsed = urlparse(normalized)
        if parsed.scheme and parsed.netloc:
            base = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
        else:
            base = normalized
        if base.endswith("/api"):
            return base
        return f"{base}/api"
