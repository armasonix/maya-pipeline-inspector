"""Thin REST client for Thinkbox Deadline 10 on-prem Web Service."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Callable

from shader_health.integrations.deadline.config import DeadlineConfig

HttpTransport = Callable[["HttpRequest", float], "DeadlineResponse"]


@dataclass(frozen=True)
class HttpRequest:
    """Low-level HTTP request passed to a transport implementation."""

    method: str
    url: str
    body: bytes | None
    headers: Mapping[str, str]


@dataclass(frozen=True)
class DeadlineResponse:
    """Normalized Deadline Web Service response."""

    status_code: int
    body: str
    json_data: dict[str, Any] | list[Any] | None = None


class DeadlineClientError(RuntimeError):
    """Raised when the Deadline Web Service returns an unexpected response."""


class DeadlineClient:
    """REST wrapper for Deadline 10 on-prem Web Service endpoints."""

    def __init__(
        self,
        config: DeadlineConfig,
        *,
        transport: HttpTransport | None = None,
    ) -> None:
        self._config = config
        self._transport = transport or default_http_transport

    @property
    def config(self) -> DeadlineConfig:
        return self._config

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, str] | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> DeadlineResponse:
        """Send a raw HTTP request to the Deadline Web Service."""

        url = self._build_url(path, query)
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers = {**headers, "Content-Type": "application/json"}
        request = HttpRequest(method=method.upper(), url=url, body=body, headers=headers)
        return self._transport(request, self._config.timeout_seconds)

    def get(self, path: str, *, query: Mapping[str, str] | None = None) -> DeadlineResponse:
        return self.request("GET", path, query=query)

    def post(self, path: str, payload: Mapping[str, Any]) -> DeadlineResponse:
        return self.request("POST", path, payload=payload)

    def put(self, path: str, payload: Mapping[str, Any]) -> DeadlineResponse:
        return self.request("PUT", path, payload=payload)

    def delete(self, path: str, *, query: Mapping[str, str] | None = None) -> DeadlineResponse:
        return self.request("DELETE", path, query=query)

    def ping(self) -> bool:
        """Return True when the Web Service responds to a lightweight jobs query."""

        response = self.get("/api/jobs", query={"IdOnly": "true"})
        return response.status_code == 200

    def get_job(self, job_id: str) -> dict[str, Any]:
        """Return one Deadline job record."""

        response = self.get("/api/jobs", query={"JobID": job_id})
        self._raise_for_status(response, f"get job {job_id}")
        if not isinstance(response.json_data, dict):
            raise DeadlineClientError(
                f"Expected JSON object for job {job_id}, got {response.body!r}"
            )
        return response.json_data

    def submit_job(
        self,
        *,
        job_info: Mapping[str, Any],
        plugin_info: Mapping[str, Any],
        aux_files: Sequence[str] = (),
        id_only: bool = True,
    ) -> str:
        """Submit a Deadline job and return the created job ID."""

        payload = {
            "JobInfo": dict(job_info),
            "PluginInfo": dict(plugin_info),
            "AuxFiles": list(aux_files),
            "IdOnly": id_only,
        }
        response = self.post("/api/jobs", payload)
        self._raise_for_status(response, "submit job")
        return _extract_job_id(response)

    def _build_url(self, path: str, query: Mapping[str, str] | None) -> str:
        base = self._config.api_url.rstrip("/")
        normalized = path if path.startswith("/") else f"/{path}"
        url = f"{base}{normalized}"
        if not query:
            return url
        encoded = urllib.parse.urlencode(query)
        return f"{url}?{encoded}"

    def _raise_for_status(self, response: DeadlineResponse, action: str) -> None:
        if response.status_code == 200:
            return
        raise DeadlineClientError(
            f"Deadline {action} failed with HTTP {response.status_code}: {response.body.strip()}"
        )


def default_http_transport(request: HttpRequest, timeout: float) -> DeadlineResponse:
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
            return DeadlineResponse(
                status_code=response.status,
                body=body,
                json_data=_parse_json_body(body),
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return DeadlineResponse(
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


def _extract_job_id(response: DeadlineResponse) -> str:
    if isinstance(response.json_data, dict):
        for key in ("_id", "JobID", "job_id", "id"):
            value = response.json_data.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
    text = response.body.strip()
    if text:
        return text
    raise DeadlineClientError("Deadline submit job succeeded but returned no job id")
