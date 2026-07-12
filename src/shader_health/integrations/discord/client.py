"""Thin REST client for Discord incoming webhooks."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable

from shader_health.integrations.discord.config import DiscordConfig, USER_AGENT

HttpTransport = Callable[["HttpRequest", float], "DiscordResponse"]


@dataclass(frozen=True)
class HttpRequest:
    """Low-level HTTP request passed to a transport implementation."""

    method: str
    url: str
    body: bytes | None
    headers: Mapping[str, str]


@dataclass(frozen=True)
class DiscordResponse:
    """Normalized Discord webhook response."""

    status_code: int
    body: str
    json_data: dict[str, Any] | list[Any] | None = None


class DiscordClientError(RuntimeError):
    """Raised when the Discord webhook returns an unexpected response."""


class DiscordClient:
    """REST wrapper for Discord incoming webhook endpoints."""

    def __init__(
        self,
        config: DiscordConfig,
        *,
        transport: HttpTransport | None = None,
    ) -> None:
        self._config = config
        self._transport = transport or default_http_transport

    @property
    def config(self) -> DiscordConfig:
        return self._config

    def request(
        self,
        *,
        payload: Mapping[str, Any] | None = None,
    ) -> DiscordResponse:
        """Send a POST request to the configured webhook URL."""

        body = None
        headers = {
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers = {**headers, "Content-Type": "application/json"}
        request = HttpRequest(
            method="POST",
            url=self._config.webhook_url,
            body=body,
            headers=headers,
        )
        return self._transport(request, self._config.timeout_seconds)

    def ping(self) -> bool:
        """Return True when the webhook accepts a minimal embed payload."""

        response = self.send_embed(
            {
                "title": "Shader Health",
                "description": "Discord webhook connection test.",
            }
        )
        if response.status_code not in (200, 204):
            return False
        if response.status_code == 204 or not response.body.strip():
            return True
        return isinstance(response.json_data, dict)

    def send_embed(self, embed: Mapping[str, Any], *, content: str = "") -> DiscordResponse:
        """Send a single embed payload to the configured webhook."""

        payload: dict[str, Any] = {"embeds": [dict(embed)]}
        if content:
            payload["content"] = content
        return self.request(payload=payload)


def default_http_transport(request: HttpRequest, timeout: float) -> DiscordResponse:
    """Send an HTTP request using the Python standard library."""

    urllib_request = urllib.request.Request(
        request.url,
        data=request.body,
        headers=dict(request.headers),
        method=request.method,
    )
    try:
        with urllib.request.urlopen(urllib_request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return DiscordResponse(
                status_code=response.status,
                body=body,
                json_data=_parse_json_body(body),
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return DiscordResponse(
            status_code=exc.code,
            body=body,
            json_data=_parse_json_body(body),
        )


def _parse_json_body(body: str) -> dict[str, Any] | list[Any] | None:
    text = body.strip()
    if not text or text[0] not in "{[":
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, (dict, list)):
        return parsed
    return None
