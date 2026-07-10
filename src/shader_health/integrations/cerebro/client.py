"""Thin client for the Cerebro server-side database API."""
from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

from shader_health.integrations.cerebro.adapter import default_database_port_factory
from shader_health.integrations.cerebro.config import CerebroConfig
from shader_health.integrations.cerebro.port import CerebroDatabasePort

CerebroDatabasePortFactory = Callable[[CerebroConfig], CerebroDatabasePort]


class CerebroClientError(RuntimeError):
    """Raised when the Cerebro API returns an unexpected response."""


class CerebroClient:
    """Wrapper around a Cerebro database port for task note publishing."""

    def __init__(
        self,
        config: CerebroConfig,
        *,
        database_port: CerebroDatabasePort | None = None,
        database_port_factory: CerebroDatabasePortFactory | None = None,
    ) -> None:
        self._config = config
        if database_port is not None:
            self._database = database_port
        else:
            factory = database_port_factory or default_database_port_factory
            self._database = factory(config)
        self._connected = False

    @property
    def config(self) -> CerebroConfig:
        return self._config

    def ping(self) -> bool:
        """Return True when credentials authenticate against the Cerebro database."""

        return self._ensure_connected()

    def resolve_task_id(self, task_url: str) -> int | None:
        """Resolve a task id from a Cerebro locator path."""

        if not self._ensure_connected():
            return None
        return self._database.task_by_url(task_url)

    def create_task_note(self, *, task_id: int, content: str) -> dict[str, Any] | None:
        """Create a note message on a task and return the created message payload."""

        if not self._ensure_connected():
            return None

        parent_message_id = self._database.task_definition_message_id(task_id)
        if parent_message_id is None:
            return None

        message_id = self._database.add_note(
            task_id,
            parent_message_id,
            format_note_html(content),
        )
        if message_id is None:
            return None
        return {"id": message_id, "task_id": task_id}

    def _ensure_connected(self) -> bool:
        if self._connected:
            return True
        connected = self._database.connect(
            self._config.api_user,
            self._config.api_password,
        )
        self._connected = bool(connected)
        return self._connected


def format_note_html(content: str) -> str:
    """Convert plain text validation summaries into simple HTML for Cerebro notes."""

    escaped = html.escape(content)
    return escaped.replace("\n", "<br/>")
