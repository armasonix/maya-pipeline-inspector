"""Thin REST client for Slack incoming webhooks."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable

HttpTransport = Callable[["HttpRequest", float], "SlackResponse"]

@dataclass(frozen=True)
class HttpRequest:
    """Low-level HTTP request passed to a transport implementation."""

    method: str
    url: str
    body: bytes | None
    headers: Mapping[str, str]

@dataclass(frozen=True)
class SlackResponse:
    """Normalized Slack incoming webhook response."""

    status_code: int
    body: str
    json_data: dict[str, Any] | list[Any] | None = None

class SlackClientError(RuntimeError):
    """Raised when the Slack incoming webhook returns an unexpected response."""

class SlackClient:
    """REST wrapper for Slack incoming webhook endpoints."""

    def __init__(
        self,
        *,
        transport: HttpTransport | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._transport = transport or default_http_transport
        self._timeout_seconds = timeout_seconds

    def request(
        self,
        webhook_url: str,
        *,
        payload: Mapping[str, Any] | None = None,
    ) -> SlackResponse:
        """Send a POST request to a Slack incoming webhook URL."""

        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers = {**headers, "Content-Type": "application/json"}
        request = HttpRequest(method="POST", url=webhook_url, body=body, headers=headers)
        return self._transport(request, self._timeout_seconds)

    def ping(self, webhook_url: str) -> bool:
        """Return True when the webhook accepts a minimal blocks payload."""

        response = self.send_blocks(
            webhook_url,
            {
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Pipeline Inspector* webhook connection test.",
                        },
                    }
                ]
            },
        )
        return response.status_code == 200

    def send_blocks(self, webhook_url: str, payload: Mapping[str, Any]) -> SlackResponse:
        """Send a Block Kit payload to the given webhook URL."""

        return self.request(webhook_url, payload=dict(payload))

def default_http_transport(request: HttpRequest, timeout: float) -> SlackResponse:
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
            return SlackResponse(
                status_code=response.status,
                body=body,
                json_data=_parse_json_body(body),
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return SlackResponse(
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
