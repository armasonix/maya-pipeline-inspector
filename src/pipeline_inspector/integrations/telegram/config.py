"""Telegram Bot API configuration for Pipeline Inspector notification integration."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

DEFAULT_API_BASE_URL = "https://api.telegram.org"
DEFAULT_TIMEOUT_SECONDS = 30.0
TELEGRAM_REQUEST_RETRIES = 3

@dataclass(frozen=True)
class TelegramConfig:
    """Connection defaults for the Telegram Bot API."""

    bot_token: str
    chat_id: str
    api_base_url: str = DEFAULT_API_BASE_URL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    def with_overrides(self, **kwargs: Any) -> TelegramConfig:
        """Return a copy with selected fields replaced."""

        return replace(self, **kwargs)
