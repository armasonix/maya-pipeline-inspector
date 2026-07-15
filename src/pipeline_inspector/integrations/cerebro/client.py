"""Thin client for the Cerebro server-side database API."""
from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

from pipeline_inspector.integrations.cerebro.adapter import (
    PY_CEREBRO_MISSING_MESSAGE,
    PyCerebroNotInstalledError,
    default_database_port_factory,
    probe_cerebro_runtime,
)
from pipeline_inspector.integrations.cerebro.config import CerebroConfig
from pipeline_inspector.integrations.cerebro.port import CerebroDatabasePort

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
        self._uses_injected_port = database_port is not None
        if database_port is not None:
            self._database = database_port
        else:
            factory = database_port_factory or default_database_port_factory
            self._database = factory(config)
        self._connected = False
        self._last_error = ""

    @property
    def config(self) -> CerebroConfig:
        return self._config

    @property
    def last_error(self) -> str:
        return self._last_error

    def ping(self) -> bool:
        """Return True when credentials authenticate against the Cerebro database."""

        return self._ensure_connected()

    def resolve_task_id(self, task_url: str) -> int | None:
        """Resolve a task id from a Cerebro locator path."""

        if not self._ensure_connected():
            return None
        return self._database.task_by_url(task_url)

    def list_root_task_names(self) -> tuple[str, ...]:
        """Return top-level Cerebro task names visible to the connected user."""

        if not self._ensure_connected():
            return ()
        list_root_tasks = getattr(self._database, "list_root_task_names", None)
        if list_root_tasks is not None:
            return tuple(list_root_tasks())
        return ()

    def list_visible_project_names(self) -> tuple[str, ...]:
        """Return Cerebro project names visible to the connected API user."""

        if not self._ensure_connected():
            return ()
        list_projects = getattr(self._database, "list_visible_project_names", None)
        if list_projects is not None:
            return tuple(list_projects())
        return ()

    def resolve_task_in_project(self, project: str, task_name: str) -> int | None:
        """Resolve a task id by project name and direct child task name."""

        if not self._ensure_connected():
            return None
        resolver = getattr(self._database, "resolve_task_in_project", None)
        if resolver is None:
            return None
        return resolver(project, task_name)

    def list_role_names(self, *, username: str = "") -> tuple[str, ...]:
        """Return Cerebro group names for tracker role mapping."""

        if not self._ensure_connected():
            return ()
        list_roles = getattr(self._database, "list_role_names", None)
        if list_roles is None:
            return ()
        return tuple(list_roles(username=username))

    def lookup_user_display_name(self, *, username: str = "") -> str:
        """Return a human-readable Cerebro user name for the given login."""

        if not self._ensure_connected():
            return ""
        lookup_name = getattr(self._database, "lookup_user_display_name", None)
        if lookup_name is None:
            return ""
        return str(lookup_name(username=username) or "").strip()

    def create_task_note(self, *, task_id: int, content: str) -> dict[str, Any] | None:
        """Create a note message on a task and return the created message payload."""

        if not self._ensure_connected():
            return None

        parent_message_id = self._database.task_definition_message_id(task_id)
        if parent_message_id is None:
            self._last_error = "task_definition_missing"
            return None

        message_id = self._database.add_note(
            task_id,
            parent_message_id,
            format_note_html(content),
        )
        if message_id is None:
            self._last_error = "note_create_failed"
            return None
        return {"id": message_id, "task_id": task_id}

    def set_task_status(self, task_id: int, status_name: str) -> bool:
        """Set a Cerebro task status by human-readable status name."""

        if not self._ensure_connected():
            return False
        setter = getattr(self._database, "set_task_status", None)
        if setter is None:
            self._last_error = "task_set_status_unsupported"
            return False
        if not setter(task_id, status_name):
            detail = getattr(self._database, "_last_status_detail", "")
            available = getattr(self._database, "_last_status_available", ())
            if detail and available:
                preview = ", ".join(list(available)[:8])
                self._last_error = f"{detail}; available: {preview}" if preview else detail
            else:
                self._last_error = detail or "task_set_status_failed"
            return False
        return True

    def _ensure_connected(self) -> bool:
        if self._connected:
            return True
        if not self._uses_injected_port:
            _module, import_error = probe_cerebro_runtime(
                service_tools_path=self._config.service_tools_path,
                server_url=self._config.normalized_server_url,
            )
            if _module is None:
                self._last_error = import_error or "py_cerebro_missing"
                return False
        try:
            connected = self._database.connect(
                self._config.normalized_api_user,
                self._config.normalized_api_password,
            )
        except PyCerebroNotInstalledError:
            self._last_error = "py_cerebro_missing"
            return False
        except Exception as exc:
            self._last_error = str(exc).strip() or "cerebro_connect_failed"
            return False
        self._connected = bool(connected)
        if not self._connected:
            self._last_error = "cerebro_connect_failed"
        return self._connected


def format_note_html(content: str) -> str:
    """Convert plain text validation summaries into simple HTML for Cerebro notes."""

    escaped = html.escape(content)
    return escaped.replace("\n", "<br/>")


def cerebro_dependency_error_message() -> str:
    """Return a user-facing message when py_cerebro is unavailable."""

    return PY_CEREBRO_MISSING_MESSAGE
