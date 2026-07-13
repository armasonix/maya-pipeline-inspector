"""Thin REST client for the Telegram Bot API."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable

from pipeline_inspector.integrations.telegram.config import TelegramConfig

HttpTransport = Callable[["HttpRequest", float], "TelegramResponse"]

@dataclass(frozen=True)
class HttpRequest:
    """Low-level HTTP request passed to a transport implementation."""

    method: str
    url: str
    body: bytes | None
    headers: Mapping[str, str]

@dataclass(frozen=True)
class TelegramResponse:
    """Normalized Telegram Bot API response."""

    status_code: int
    body: str
    json_data: dict[str, Any] | list[Any] | None = None

class TelegramClientError(RuntimeError):
    """Raised when the Telegram Bot API returns an unexpected response."""

class TelegramClient:
    """REST wrapper for Telegram Bot API endpoints."""

    def __init__(
        self,
        config: TelegramConfig,
        *,
        transport: HttpTransport | None = None,
    ) -> None:
        self._config = config
        self._transport = transport or default_http_transport

    @property
    def config(self) -> TelegramConfig:
        return self._config

    def request(
        self,
        method: str,
        api_method: str,
        *,
        payload: Mapping[str, Any] | None = None,
    ) -> TelegramResponse:
        """Send a raw HTTP request to the Telegram Bot API."""

        url = self._build_url(api_method)
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers = {**headers, "Content-Type": "application/json"}
        request = HttpRequest(method=method.upper(), url=url, body=body, headers=headers)
        return self._transport(request, self._config.timeout_seconds)

    def ping(self) -> bool:
        """Return True when the bot token is valid and getMe succeeds."""

        response = self.request("GET", "getMe")
        if response.status_code != 200:
            return False
        if isinstance(response.json_data, dict):
            return bool(response.json_data.get("ok"))
        return False

    def send_message(self, text: str) -> TelegramResponse:
        """Send a text message to the configured chat."""

        return self.request(
            "POST",
            "sendMessage",
            payload={
                "chat_id": self._config.chat_id,
                "text": text,
            },
        )

    def _build_url(self, api_method: str) -> str:
        base = self._config.api_base_url.rstrip("/")
        normalized = api_method if api_method.startswith("/") else f"/{api_method}"
        return f"{base}/bot{self._config.bot_token}{normalized}"

def default_http_transport(request: HttpRequest, timeout: float) -> TelegramResponse:
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
            return TelegramResponse(
                status_code=response.status,
                body=body,
                json_data=_parse_json_body(body),
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return TelegramResponse(
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
