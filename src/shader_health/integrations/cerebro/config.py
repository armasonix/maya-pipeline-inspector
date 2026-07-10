"""Cerebro API configuration for Shader Health task tracker integration."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any
from urllib.parse import urlparse

DEFAULT_DB_PORT = 45432
DEFAULT_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True)
class CerebroConfig:
    """Connection defaults for the Cerebro server-side database API."""

    server_url: str
    api_user: str
    api_password: str
    project: str
    db_port: int = DEFAULT_DB_PORT
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    def with_overrides(self, **kwargs: Any) -> CerebroConfig:
        """Return a copy with selected fields replaced."""

        return replace(self, **kwargs)

    @property
    def db_host(self) -> str:
        """Return the normalized Cerebro database host."""

        return _parse_server_endpoint(self.server_url)[0]

    @property
    def resolved_db_port(self) -> int:
        """Return the configured or parsed Cerebro database port."""

        parsed_port = _parse_server_endpoint(self.server_url)[1]
        return parsed_port if parsed_port is not None else self.db_port


def _parse_server_endpoint(server_url: str) -> tuple[str, int | None]:
    normalized = server_url.strip()
    if not normalized:
        return "", None

    if "://" not in normalized:
        normalized = f"//{normalized}"

    parsed = urlparse(normalized)
    host = parsed.hostname or ""
    port = parsed.port
    if not host and parsed.path:
        host = parsed.path.split("/")[0]
    return host, port
