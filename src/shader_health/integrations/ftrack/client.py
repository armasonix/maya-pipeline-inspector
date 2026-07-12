"""Thin HTTP client for the Ftrack batch API."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Callable

from shader_health.integrations.ftrack.config import FtrackConfig
from shader_health.integrations.ftrack.queries import (
    ping_user_expression,
    status_by_name_expression,
    task_assignees_expression,
    user_by_username_expression,
)

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


@dataclass(frozen=True)
class FtrackCreateResult:
    """Result of a Ftrack batch create operation."""

    entity: dict[str, Any] | None
    status_code: int
    exception_message: str = ""


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

        rows, status_code, exception_message = self.query_rows(
            ping_user_expression(self._config.api_user)
        )
        return status_code == 200 and bool(rows) and not exception_message

    def query_response(self, expression: str) -> FtrackResponse:
        """Run an Ftrack query expression and return the raw API response."""

        return self.request([{"action": "query", "expression": expression}])

    def query_rows(self, expression: str) -> tuple[list[dict[str, Any]], int, str]:
        """Run a query and return entity rows, HTTP status, and batch exception text."""

        response = self.query_response(expression)
        rows, exception_message = _extract_query_rows(response.json_data)
        return rows, response.status_code, exception_message

    def query(self, expression: str) -> list[dict[str, Any]]:
        """Run an Ftrack query expression and return entity rows."""

        rows, status_code, exception_message = self.query_rows(expression)
        if status_code != 200 or exception_message:
            return []
        return rows

    def create_task_note(self, *, task_id: str, content: str) -> FtrackCreateResult:
        """Create a note on a task and return the created entity payload."""

        author_id = self._resolve_note_author_id()
        recipient_ids = self._task_assignee_resource_ids(task_id)
        note_id = str(uuid.uuid4())
        entity_data: dict[str, Any] = {
            "__entity_type__": "Note",
            "id": note_id,
            "content": content,
            "parent_id": task_id,
            "parent_type": "Task",
        }
        if author_id:
            entity_data["author"] = {
                "__entity_type__": "User",
                "id": author_id,
            }

        operations: list[dict[str, Any]] = [
            {
                "action": "create",
                "entity_type": "Note",
                "entity_key": [note_id],
                "entity_data": entity_data,
            }
        ]
        for resource_id in recipient_ids:
            recipient_id = str(uuid.uuid4())
            operations.append(
                {
                    "action": "create",
                    "entity_type": "Recipient",
                    "entity_key": [recipient_id],
                    "entity_data": {
                        "__entity_type__": "Recipient",
                        "id": recipient_id,
                        "note_id": note_id,
                        "resource_id": resource_id,
                    },
                }
            )

        response = self.request(operations)
        entity, exception_message = _extract_batch_operation(response.json_data)
        if response.status_code != 200:
            return FtrackCreateResult(
                entity=None,
                status_code=response.status_code,
                exception_message=exception_message or f"HTTP {response.status_code}",
            )
        if exception_message:
            return FtrackCreateResult(
                entity=None,
                status_code=response.status_code,
                exception_message=exception_message,
            )
        return FtrackCreateResult(
            entity=entity,
            status_code=response.status_code,
            exception_message="",
        )

    def update_task_status(self, *, task_id: str, status_name: str) -> FtrackCreateResult:
        """Set a task status by human-readable status name."""

        normalized_status = status_name.strip()
        if not normalized_status:
            return FtrackCreateResult(
                entity=None,
                status_code=0,
                exception_message="missing_status_name",
            )

        rows, status_code, exception_message = self.query_rows(
            status_by_name_expression(normalized_status)
        )
        if status_code != 200 or exception_message or not rows:
            message = exception_message or f"status_not_found: {normalized_status}"
            return FtrackCreateResult(
                entity=None,
                status_code=status_code,
                exception_message=message,
            )

        status_id = str(rows[0].get("id", "") or "").strip()
        if not status_id:
            return FtrackCreateResult(
                entity=None,
                status_code=status_code,
                exception_message=f"status_not_found: {normalized_status}",
            )

        response = self.request(
            [
                {
                    "action": "update",
                    "entity_type": "Task",
                    "entity_key": [task_id],
                    "entity_data": {"status_id": status_id},
                }
            ]
        )
        entity, exception_message = _extract_batch_operation(response.json_data)
        if response.status_code != 200:
            return FtrackCreateResult(
                entity=None,
                status_code=response.status_code,
                exception_message=exception_message or f"HTTP {response.status_code}",
            )
        if exception_message:
            return FtrackCreateResult(
                entity=None,
                status_code=response.status_code,
                exception_message=exception_message,
            )
        return FtrackCreateResult(
            entity=entity,
            status_code=response.status_code,
            exception_message="",
        )

    def _resolve_note_author_id(self) -> str:
        candidates: list[str] = []
        note_author = self._config.note_author_username.strip()
        if note_author:
            candidates.append(note_author)
        api_user = self._config.api_user.strip()
        if api_user and api_user not in candidates:
            candidates.append(api_user)

        for username in candidates:
            rows, status_code, exception_message = self.query_rows(
                user_by_username_expression(username)
            )
            if status_code != 200 or exception_message or not rows:
                continue
            author_id = str(rows[0].get("id", "") or "").strip()
            if author_id:
                return author_id
        return ""

    def _task_assignee_resource_ids(self, task_id: str) -> tuple[str, ...]:
        rows, status_code, exception_message = self.query_rows(
            task_assignees_expression(task_id)
        )
        if status_code != 200 or exception_message:
            return ()

        assignee_ids: list[str] = []
        seen: set[str] = set()
        for row in rows:
            resource_id = str(row.get("resource_id", "") or "").strip()
            if not resource_id or resource_id in seen:
                continue
            seen.add(resource_id)
            assignee_ids.append(resource_id)
        return tuple(assignee_ids)

    def _current_user_id(self) -> str:
        rows, status_code, exception_message = self.query_rows(
            ping_user_expression(self._config.api_user)
        )
        if status_code != 200 or exception_message or not rows:
            return ""
        return str(rows[0].get("id", "") or "").strip()


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


def _extract_batch_exception(operation: dict[str, Any]) -> str:
    """Return a human-readable batch exception message when present."""

    exception = operation.get("exception")
    if exception is None:
        return ""
    if isinstance(exception, str):
        message = exception.strip()
        detail = operation.get("content")
        if detail:
            detail_text = str(detail).strip()
            if detail_text and detail_text not in message:
                return f"{message}: {detail_text}" if message else detail_text
        return message
    if isinstance(exception, dict):
        for key in ("message", "msg", "detail", "content", "data"):
            value = exception.get(key)
            if value:
                return str(value).strip()
        class_name = str(exception.get("class_name", "") or "").strip()
        if class_name:
            return class_name
        return str(exception).strip()
    error = operation.get("error")
    if isinstance(error, dict):
        for key in ("message", "detail", "content"):
            value = error.get(key)
            if value:
                return str(value).strip()
    elif isinstance(error, str) and error.strip():
        return error.strip()
    return str(exception).strip()


def _normalize_query_data(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return []


def _extract_batch_operation(
    json_data: list[Any] | dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, str]:
    if isinstance(json_data, dict):
        return _extract_created_entity(json_data), _extract_batch_exception(json_data)
    if not isinstance(json_data, list) or not json_data:
        return None, ""
    first = json_data[0]
    if not isinstance(first, dict):
        return None, ""
    return _extract_created_entity(first), _extract_batch_exception(first)


def _extract_query_rows(
    json_data: list[Any] | dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], str]:
    if isinstance(json_data, dict):
        return _normalize_query_data(json_data.get("data")), _extract_batch_exception(json_data)
    if not isinstance(json_data, list) or not json_data:
        return [], ""
    first = json_data[0]
    if not isinstance(first, dict):
        return [], ""
    return _normalize_query_data(first.get("data")), _extract_batch_exception(first)


def _extract_created_entity(operation: dict[str, Any]) -> dict[str, Any] | None:
    data = operation.get("data")
    if isinstance(data, dict):
        return data
    entity_data = operation.get("entity_data")
    if isinstance(entity_data, dict):
        return entity_data
    return None
