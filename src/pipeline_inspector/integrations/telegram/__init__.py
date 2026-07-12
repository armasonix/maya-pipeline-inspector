"""Telegram Bot API integration for Pipeline Inspector notifications."""

from pipeline_inspector.integrations.telegram.client import (
    HttpRequest,
    HttpTransport,
    TelegramClient,
    TelegramClientError,
    TelegramResponse,
    default_http_transport,
)
from pipeline_inspector.integrations.telegram.config import (
    DEFAULT_API_BASE_URL,
    DEFAULT_TIMEOUT_SECONDS,
    TelegramConfig,
)
from pipeline_inspector.integrations.telegram.notify import (
    TelegramNotificationResult,
    ValidationNotificationContext,
    format_validation_summary_message,
    matched_notify_events,
    maybe_send_telegram_validation_notification,
    send_telegram_validation_notification,
    should_send_telegram_notification,
    validation_notification_context_from_run,
)

__all__ = [
    "DEFAULT_API_BASE_URL",
    "DEFAULT_TIMEOUT_SECONDS",
    "HttpRequest",
    "HttpTransport",
    "TelegramClient",
    "TelegramClientError",
    "TelegramConfig",
    "TelegramNotificationResult",
    "TelegramResponse",
    "ValidationNotificationContext",
    "default_http_transport",
    "format_validation_summary_message",
    "maybe_send_telegram_validation_notification",
    "matched_notify_events",
    "send_telegram_validation_notification",
    "should_send_telegram_notification",
    "validation_notification_context_from_run",
]
