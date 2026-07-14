"""Database port abstraction for Cerebro server API access."""
from __future__ import annotations

from typing import Protocol


class CerebroDatabasePort(Protocol):
    """Minimal Cerebro database surface used by the connector client."""

    def connect(self, user: str, password: str) -> bool:
        """Authenticate against the Cerebro database."""

    def task_by_url(self, task_url: str) -> int | None:
        """Resolve a task id from a Cerebro locator path."""

    def task_definition_message_id(self, task_id: int) -> int | None:
        """Return the parent definition message id for a task."""

    def add_note(self, task_id: int, parent_message_id: int, html_text: str) -> int | None:
        """Create a Note-type message on a task."""

    def list_role_names(self, *, username: str = "") -> tuple[str, ...]:
        """Return role or group names visible to the connected API session."""
