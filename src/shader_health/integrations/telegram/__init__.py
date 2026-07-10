"""Telegram Bot API integration for Shader Health Inspector notifications."""

from shader_health.integrations.telegram.client import (
    HttpRequest,
    HttpTransport,
    TelegramClient,
    TelegramClientError,
    TelegramResponse,
    default_http_transport,
)
from shader_health.integrations.telegram.config import (
    DEFAULT_API_BASE_URL,
    DEFAULT_TIMEOUT_SECONDS,
    TelegramConfig,
)

__all__ = [
    "DEFAULT_API_BASE_URL",
    "DEFAULT_TIMEOUT_SECONDS",
    "HttpRequest",
    "HttpTransport",
    "TelegramClient",
    "TelegramClientError",
    "TelegramConfig",
    "TelegramResponse",
    "default_http_transport",
]
