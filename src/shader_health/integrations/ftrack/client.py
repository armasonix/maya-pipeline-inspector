"""Thin HTTP client for the Ftrack batch API."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Callable

from shader_health.integrations.ftrack.config import FtrackConfig

HttpTransport = Callable[["HttpRequest", float], "FtrackResponse"]


@dataclass(frozen=True)
class HttpRequest:
    """Low-level HTTP request passed to a transport implementation."""

    method: str
    url: str
    body: bytes | None
    headers: Mapping[str, str]


@dataclass(frozen=True)
class FtrackResponse:
    """Normalized Ftrack batch API response."""

    status_code: int
    body: str
    json_data: list[Any] | dict[str, Any] | None = None


class FtrackClientError(RuntimeError):
    """Raised when the Ftrack API returns an unexpected response."""


class FtrackClient:
    """REST wrapper for Ftrack batch query/create operations."""

    def __init__(
        self,
        config: FtrackConfig,
        *,
        transport: HttpTransport | None = None,
    ) -> None:
        self._config = config
        self._transport = transport or default_http_transport

    @property
    def config(self) -> FtrackConfig:
        return self._config

    def request(self, operations: Sequence[Mapping[str, Any]]) -> FtrackResponse:
        """Send a batch request to the configured Ftrack API endpoint."""

        body = json.dumps(list(operations)).encode("utf-8")
        request = HttpRequest(
            method="POST",
            url=self._config.endpoint_url,
            body=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "ftrack-user": self._config.api_user,
                "ftrack-api-key": self._config.api_key,
            },
        )
        return self._transport(request, self._config.timeout_seconds)

    def ping(self) -> bool:
        """Return True when the API accepts an authenticated query."""

        response = self.query("limit 1 User")
        return bool(response)

    def query(self, expression: str) -> list[dict[str, Any]]:
        """Run an Ftrack query expression and return entity rows."""

        response = self.request([{"action": "query", "expression": expression}])
        if response.status_code != 200:
            return []
        return _extract_query_rows(response.json_data)

    def create_task_note(self, *, task_id: str, content: str) -> dict[str, Any] | None:
        """Create a note on a task and return the created entity payload."""

        response = self.request(
            [
                {
                    "action": "create",
                    "entityType": "Note",
                    "data": {
                        "content": content,
                        "parent_id": task_id,
                        "parent_type": "task",
                    },
                }
            ]
        )
        if response.status_code != 200:
            return None
        return _extract_created_entity(response.json_data)


def default_http_transport(request: HttpRequest, timeout: float) -> FtrackResponse:
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
            return FtrackResponse(
                status_code=response.status,
                body=body,
                json_data=_parse_json_body(body),
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return FtrackResponse(
            status_code=exc.code,
            body=body,
            json_data=_parse_json_body(body),
        )


def _parse_json_body(body: str) -> list[Any] | dict[str, Any] | None:
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


def _extract_query_rows(json_data: list[Any] | dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(json_data, list) or not json_data:
        return []
    first = json_data[0]
    if not isinstance(first, dict):
        return []
    data = first.get("data")
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)]


def _extract_created_entity(json_data: list[Any] | dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(json_data, list) or not json_data:
        return None
    first = json_data[0]
    if not isinstance(first, dict):
        return None
    data = first.get("data")
    if isinstance(data, dict):
        return data
    return None
