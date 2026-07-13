"""HTTPS client for studio-hosted bug report relays."""
from __future__ import annotations

import json
import secrets
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pipeline_inspector.integrations.bug_report.config import BugReportRelayConfig
from pipeline_inspector.integrations.bug_report.payload import BugReportPayload
from pipeline_inspector.integrations.bug_report.throttle import (
    RATE_LIMITED_SKIPPED_REASON,
    evaluate_bug_report_throttle,
    format_rate_limit_message,
    record_bug_report_submission,
)
from pipeline_inspector.studio_config import StudioConfig, resolve_bug_report_config

HttpTransport = Callable[["HttpRequest", float], "RelayResponse"]

JPEG_MAGIC_PREFIX = b"\xff\xd8\xff"
SCREENSHOT_FIELD_NAME = "screenshot"
SCREENSHOT_FILENAME = "screenshot.jpg"
PAYLOAD_FIELD_NAME = "payload"

@dataclass(frozen=True)
class HttpRequest:
    """Low-level HTTP request passed to a transport implementation."""

    method: str
    url: str
    body: bytes | None
    headers: Mapping[str, str]

@dataclass(frozen=True)
class RelayResponse:
    """Normalized bug report relay response."""

    status_code: int
    body: str
    json_data: dict[str, Any] | list[Any] | None = None

@dataclass(frozen=True)
class BugReportRelayResult:
    """Outcome from submitting a bug report to the studio relay."""

    submitted: bool
    issue_url: str = ""
    skipped_reason: str = ""
    error_message: str = ""
    status_code: int = 0

class BugReportRelayClientError(RuntimeError):
    """Raised when the bug report relay returns an unexpected response."""

class BugReportRelayClient:
    """Multipart client for studio bug report relay endpoints."""

    def __init__(
        self,
        config: BugReportRelayConfig,
        *,
        transport: HttpTransport | None = None,
    ) -> None:
        self._config = config
        self._transport = transport or default_http_transport

    @property
    def config(self) -> BugReportRelayConfig:
        return self._config

    def submit(
        self,
        payload: BugReportPayload,
        *,
        screenshot_jpeg: bytes | None = None,
    ) -> BugReportRelayResult:
        """Submit a bug report payload to the configured relay URL."""

        relay_url = self._config.relay_url.strip()
        api_key = self._config.api_key.strip()
        if not relay_url or not api_key:
            return BugReportRelayResult(
                submitted=False,
                skipped_reason="incomplete_config",
            )

        attachment = _validated_screenshot(
            screenshot_jpeg,
            allow_screenshot=self._config.allow_screenshot,
        )
        body, content_type = build_multipart_body(
            fields={PAYLOAD_FIELD_NAME: payload.to_json()},
            files=(
                {
                    SCREENSHOT_FIELD_NAME: (
                        SCREENSHOT_FILENAME,
                        "image/jpeg",
                        attachment,
                    )
                }
                if attachment is not None
                else None
            ),
        )
        request = HttpRequest(
            method="POST",
            url=relay_url,
            body=body,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
                "Content-Type": content_type,
            },
        )
        response = self._transport(request, self._config.timeout_seconds)
        issue_url = parse_issue_url(response)
        if response.status_code in (200, 201) and issue_url:
            return BugReportRelayResult(
                submitted=True,
                issue_url=issue_url,
                status_code=response.status_code,
            )
        if response.status_code == 429:
            return BugReportRelayResult(
                submitted=False,
                skipped_reason=RATE_LIMITED_SKIPPED_REASON,
                error_message=_relay_error_message(response),
                status_code=response.status_code,
            )
        if response.status_code in (200, 201):
            return BugReportRelayResult(
                submitted=False,
                error_message="relay_missing_issue_url",
                status_code=response.status_code,
            )
        return BugReportRelayResult(
            submitted=False,
            error_message=_relay_error_message(response),
            status_code=response.status_code,
        )

def maybe_submit_bug_report(
    studio_config: StudioConfig | None,
    payload: BugReportPayload,
    *,
    screenshot_jpeg: bytes | None = None,
    transport: HttpTransport | None = None,
    throttle_state_path: Path | None = None,
) -> BugReportRelayResult:
    """Submit a bug report when studio relay settings are enabled and complete."""

    config = resolve_bug_report_config(studio_config)
    if config is None:
        settings = (
            StudioConfig().bug_report
            if studio_config is None
            else studio_config.bug_report
        )
        if not settings.enabled:
            return BugReportRelayResult(submitted=False, skipped_reason="disabled")
        return BugReportRelayResult(submitted=False, skipped_reason="incomplete_config")

    throttle_decision = evaluate_bug_report_throttle(
        config,
        machine_id=payload.machine_id,
        os_user=payload.os_user,
        state_path=throttle_state_path,
    )
    if not throttle_decision.allowed:
        return BugReportRelayResult(
            submitted=False,
            skipped_reason=throttle_decision.skipped_reason,
            error_message=format_rate_limit_message(throttle_decision),
        )

    client = BugReportRelayClient(config, transport=transport)
    result = client.submit(payload, screenshot_jpeg=screenshot_jpeg)
    if result.submitted:
        record_bug_report_submission(
            machine_id=payload.machine_id,
            os_user=payload.os_user,
            state_path=throttle_state_path,
        )
    return result

def build_multipart_body(
    *,
    fields: Mapping[str, str],
    files: Mapping[str, tuple[str, str, bytes]] | None = None,
    boundary: str | None = None,
) -> tuple[bytes, str]:
    """Build a multipart/form-data request body and Content-Type header."""

    chosen_boundary = boundary or _generate_boundary()
    parts: list[bytes] = []

    for name, value in fields.items():
        parts.append(_encode_field_part(chosen_boundary, name, value))

    for name, (filename, content_type, data) in (files or {}).items():
        parts.append(
            _encode_file_part(
                chosen_boundary,
                field_name=name,
                filename=filename,
                content_type=content_type,
                data=data,
            )
        )

    parts.append(f"--{chosen_boundary}--\r\n".encode("ascii"))
    body = b"".join(parts)
    content_type = f"multipart/form-data; boundary={chosen_boundary}"
    return body, content_type

def parse_issue_url(response: RelayResponse) -> str:
    """Extract a created GitHub issue URL from a relay response."""

    if response.status_code not in (200, 201):
        return ""
    data = response.json_data
    if not isinstance(data, dict):
        return ""
    for key in ("issue_url", "html_url", "url"):
        value = str(data.get(key, "") or "").strip()
        if value:
            return value
    return ""

def default_http_transport(request: HttpRequest, timeout: float) -> RelayResponse:
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
            return RelayResponse(
                status_code=response.status,
                body=body,
                json_data=_parse_json_body(body),
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return RelayResponse(
            status_code=exc.code,
            body=body,
            json_data=_parse_json_body(body),
        )

def _validated_screenshot(
    screenshot_jpeg: bytes | None,
    *,
    allow_screenshot: bool,
) -> bytes | None:
    if not screenshot_jpeg:
        return None
    if not allow_screenshot:
        return None
    if not is_jpeg_bytes(screenshot_jpeg):
        return None
    return screenshot_jpeg

def is_jpeg_bytes(data: bytes) -> bool:
    """Return True when bytes look like a JPEG image."""

    return len(data) >= 3 and data[:3] == JPEG_MAGIC_PREFIX

def _relay_error_message(response: RelayResponse) -> str:
    if isinstance(response.json_data, dict):
        for key in ("error", "message", "detail"):
            value = str(response.json_data.get(key, "") or "").strip()
            if value:
                return value
    body = response.body.strip()
    if body:
        return body
    return f"relay_http_{response.status_code}"

def _generate_boundary() -> str:
    return f"shader-health-{secrets.token_hex(16)}"

def _encode_field_part(boundary: str, name: str, value: str) -> bytes:
    return (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{name}"\r\n'
        f"\r\n"
        f"{value}\r\n"
    ).encode()

def _encode_file_part(
    boundary: str,
    *,
    field_name: str,
    filename: str,
    content_type: str,
    data: bytes,
) -> bytes:
    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n"
        f"\r\n"
    ).encode("ascii")
    return header + data + b"\r\n"

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
