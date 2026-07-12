"""Cerebro API configuration for Shader Health task tracker integration."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any
from urllib.parse import urlparse

DEFAULT_DB_PORT = 45432
DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_TOKEN_CLIENT_TYPE = 655360


def normalize_cerebro_field(value: str) -> str:
    return str(value or "").strip()


def is_cerebro_rpc_url(server_url: str) -> bool:
    normalized = normalize_cerebro_field(server_url).lower()
    return normalized.startswith("http://") or normalized.startswith("https://")


def cerebro_auth_hint() -> str:
    return (
        "API user must be the API Users email from Cerebro web (for example api@studio). "
        "Paste the Access token from the same page into Access token. "
        "For cloud Cerebro, paste the full Server API Url "
        "(for example https://db5.cerebrohq.com/dapi5/rpc.php) into Database host."
    )


_PLACEHOLDER_DB_HOSTS = frozenset({"host", "hostname", "server", "your-host"})


@dataclass(frozen=True)
class CerebroConfig:
    """Connection defaults for the Cerebro server-side database API."""

    server_url: str
    api_user: str
    api_password: str
    project: str
    service_tools_path: str = ""
    db_port: int = DEFAULT_DB_PORT
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    pause_status_name: str = "Pause"
    set_pause_status_on_publish: bool = True

    def with_overrides(self, **kwargs: Any) -> CerebroConfig:
        """Return a copy with selected fields replaced."""

        return replace(self, **kwargs)

    @property
    def normalized_api_user(self) -> str:
        return normalize_cerebro_field(self.api_user)

    @property
    def normalized_api_password(self) -> str:
        return normalize_cerebro_field(self.api_password)

    @property
    def normalized_server_url(self) -> str:
        return normalize_cerebro_field(self.server_url)

    @property
    def db_host(self) -> str:
        """Return the normalized Cerebro database host."""

        return resolve_cerebro_server_endpoint(self.normalized_server_url)[0]

    @property
    def resolved_db_port(self) -> int:
        """Return the configured or parsed Cerebro database port."""

        parsed_port = resolve_cerebro_server_endpoint(self.normalized_server_url)[1]
        return parsed_port if parsed_port is not None else self.db_port

    @property
    def server_endpoint_source(self) -> str:
        """Return how the database endpoint was parsed from server_url."""

        return resolve_cerebro_server_endpoint(self.normalized_server_url)[2]


def is_placeholder_db_host(host: str) -> bool:
    normalized = normalize_cerebro_field(host).lower()
    return not normalized or normalized in _PLACEHOLDER_DB_HOSTS


def resolve_cerebro_server_endpoint(server_url: str) -> tuple[str, int | None, str]:
    """Return (host, port, source) parsed from a database host or Server API Url."""

    normalized = normalize_cerebro_field(server_url)
    if not normalized:
        return "", None, "empty"

    host, port = _parse_server_endpoint(normalized)
    if is_placeholder_db_host(host):
        return host, port, "placeholder"

    lowered = normalized.lower()
    if lowered.startswith("http://") or lowered.startswith("https://"):
        return host, port, "server_api_url"
    if ":" in normalized.split("//")[-1].split("/")[0]:
        return host, port, "host_port"
    return host, port, "host_only"


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
