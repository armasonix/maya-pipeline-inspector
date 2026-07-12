"""ShotGrid API configuration for Shader Health task tracker integration."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_ENTITY_TYPE = "Shot"
SUPPORTED_ENTITY_TYPES: frozenset[str] = frozenset({"Shot", "Asset"})

@dataclass(frozen=True)
class ShotGridConfig:
    """Connection defaults for the ShotGrid REST API."""

    site_url: str
    script_name: str
    api_key: str
    project: str
    entity_type: str = DEFAULT_ENTITY_TYPE
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    def with_overrides(self, **kwargs: Any) -> ShotGridConfig:
        """Return a copy with selected fields replaced."""

        return replace(self, **kwargs)

    @property
    def normalized_entity_type(self) -> str:
        """Return a supported ShotGrid entity type for note links."""

        normalized = self.entity_type.strip().title()
        if normalized in SUPPORTED_ENTITY_TYPES:
            return normalized
        return DEFAULT_ENTITY_TYPE

    @property
    def entity_collection(self) -> str:
        """Return the REST collection name for the configured entity type."""

        return "assets" if self.normalized_entity_type == "Asset" else "shots"

    @property
    def api_base_url(self) -> str:
        """Return the normalized ShotGrid REST API base URL."""

        normalized = self.site_url.strip().rstrip("/")
        if not normalized:
            return ""
        if normalized.endswith("/api/v1"):
            return normalized
        if normalized.endswith("/api"):
            return f"{normalized}/v1"
        return f"{normalized}/api/v1"
