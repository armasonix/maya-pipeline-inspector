"""Thin HTTP client for the ShotGrid REST API."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable

from shader_health.integrations.shotgrid.config import ShotGridConfig

HttpTransport = Callable[["HttpRequest", float], "ShotGridResponse"]


@dataclass(frozen=True)
class HttpRequest:
    """Low-level HTTP request passed to a transport implementation."""

    method: str
    url: str
    body: bytes | None
    headers: Mapping[str, str]


@dataclass(frozen=True)
class ShotGridResponse:
    """Normalized ShotGrid REST API response."""

    status_code: int
    body: str
    json_data: dict[str, Any] | list[Any] | None = None


class ShotGridClientError(RuntimeError):
    """Raised when the ShotGrid API returns an unexpected response."""


class ShotGridClient:
    """REST wrapper for ShotGrid auth, entity lookup, and note creation."""

    def __init__(
        self,
        config: ShotGridConfig,
        *,
        transport: HttpTransport | None = None,
    ) -> None:
        self._config = config
        self._transport = transport or default_http_transport
        self._access_token = ""

    @property
    def config(self) -> ShotGridConfig:
        return self._config

    def ping(self) -> bool:
        """Return True when the API accepts an authenticated projects query."""

        response = self._api_request("GET", "/entity/projects", params={"page[size]": "1"})
        return response.status_code == 200

    def find_project_id(self, project_name: str) -> int | None:
        """Resolve a project id from its display name."""

        response = self._api_request(
            "GET",
            "/entity/projects",
            params={
                "fields": "id,name",
                "filter[name]": project_name,
                "page[size]": "1",
            },
        )
        if response.status_code != 200:
            return None
        rows = _extract_entity_rows(response.json_data)
        if not rows:
            return None
        project_id = rows[0].get("id")
        if isinstance(project_id, int):
            return project_id
        if isinstance(project_id, str) and project_id.isdigit():
            return int(project_id)
        return None

    def find_entity(
        self,
        *,
        entity_type: str,
        code: str,
        project_name: str,
    ) -> dict[str, Any] | None:
        """Find a Shot or Asset by code within a named project."""

        collection = "assets" if entity_type == "Asset" else "shots"
        response = self._api_request(
            "GET",
            f"/entity/{collection}",
            params={
                "fields": "id,code,project",
                "filter[code]": code,
                "filter[project.Project.name]": project_name,
                "page[size]": "1",
            },
        )
        if response.status_code != 200:
            return None
        rows = _extract_entity_rows(response.json_data)
        if not rows:
            return None
        return rows[0]

    def create_entity_note(
        self,
        *,
        content: str,
        project_id: int,
        entity_type: str,
        entity_id: int,
    ) -> dict[str, Any] | None:
        """Create a note linked to a Shot or Asset."""

        payload = {
            "content": content,
            "project": {"type": "Project", "id": project_id},
            "note_links": [{"type": entity_type, "id": entity_id}],
        }
        response = self._api_request(
            "POST",
            "/entity/notes",
            json_body=payload,
        )
        if response.status_code not in (200, 201):
            return None
        return _extract_created_entity(response.json_data)

    def _api_request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
        json_body: Mapping[str, Any] | None = None,
        form_body: Mapping[str, str] | None = None,
        auth: bool = True,
    ) -> ShotGridResponse:
        url = self._build_url(path, params)
        headers = {"Accept": "application/json"}
        body: bytes | None = None

        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            headers = {**headers, "Content-Type": "application/json"}
        elif form_body is not None:
            body = urllib.parse.urlencode(form_body).encode("utf-8")
            headers = {**headers, "Content-Type": "application/x-www-form-urlencoded"}

        if auth:
            token = self._ensure_access_token()
            if not token:
                return ShotGridResponse(status_code=401, body="", json_data=None)
            headers = {**headers, "Authorization": f"Bearer {token}"}

        request = HttpRequest(method=method, url=url, body=body, headers=headers)
        return self._transport(request, self._config.timeout_seconds)

    def _ensure_access_token(self) -> str:
        if self._access_token:
            return self._access_token

        response = self._api_request(
            "POST",
            "/auth/access_token",
            form_body={
                "grant_type": "client_credentials",
                "client_id": self._config.script_name,
                "client_secret": self._config.api_key,
            },
            auth=False,
        )
        if response.status_code != 200:
            return ""

        token = _extract_access_token(response.json_data)
        self._access_token = token
        return token

    def _build_url(self, path: str, params: Mapping[str, str] | None) -> str:
        base = self._config.api_base_url.rstrip("/")
        normalized_path = path if path.startswith("/") else f"/{path}"
        url = f"{base}{normalized_path}"
        if params:
            query = urllib.parse.urlencode(params)
            url = f"{url}?{query}"
        return url


def default_http_transport(request: HttpRequest, timeout: float) -> ShotGridResponse:
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
            return ShotGridResponse(
                status_code=response.status,
                body=body,
                json_data=_parse_json_body(body),
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return ShotGridResponse(
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


def _extract_access_token(json_data: dict[str, Any] | list[Any] | None) -> str:
    if not isinstance(json_data, dict):
        return ""
    data = json_data.get("data")
    if isinstance(data, dict):
        token = data.get("access_token")
        if isinstance(token, str):
            return token
    token = json_data.get("access_token")
    if isinstance(token, str):
        return token
    return ""


def _extract_entity_rows(json_data: dict[str, Any] | list[Any] | None) -> list[dict[str, Any]]:
    if not isinstance(json_data, dict):
        return []
    data = json_data.get("data")
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)]


def _extract_created_entity(json_data: dict[str, Any] | list[Any] | None) -> dict[str, Any] | None:
    if not isinstance(json_data, dict):
        return None
    data = json_data.get("data")
    if isinstance(data, dict):
        return data
    return None
