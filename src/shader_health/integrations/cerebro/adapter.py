from __future__ import annotations

from typing import Any

from shader_health.integrations.cerebro.config import CerebroConfig


class PyCerebroDatabaseAdapter:
    """Wrap py_cerebro.database.Database when the server package is installed."""

    def __init__(self, config: CerebroConfig) -> None:
        self._config = config
        self._database: Any | None = None

    def connect(self, user: str, password: str) -> bool:
        database_module = _import_py_cerebro_database()
        self._database = database_module.Database(
            self._config.db_host,
            self._config.resolved_db_port,
            db_timeout=int(self._config.timeout_seconds),
        )
        self._database.connect(user, password)
        return True

    def task_by_url(self, task_url: str) -> int | None:
        database = _require_database(self._database)
        task_row = database.task_by_url(task_url)
        if task_row is None:
            return None
        task_id = task_row[0]
        if task_id is None:
            return None
        return int(task_id)

    def task_definition_message_id(self, task_id: int) -> int | None:
        database = _require_database(self._database)
        dbtypes = _import_py_cerebro_dbtypes()
        definition = database.task_definition(task_id)
        if not definition:
            return None
        message_id = definition[dbtypes.MESSAGE_DATA_ID]
        if message_id in (None, 0):
            return None
        return int(message_id)

    def add_note(self, task_id: int, parent_message_id: int, html_text: str) -> int | None:
        database = _require_database(self._database)
        message_id = database.add_note(task_id, parent_message_id, html_text)
        if message_id in (None, 0):
            return None
        return int(message_id)


def default_database_port_factory(config: CerebroConfig) -> PyCerebroDatabaseAdapter:
    """Create the default production database adapter for Cerebro."""

    return PyCerebroDatabaseAdapter(config)


def _import_py_cerebro_database() -> Any:
    try:
        from py_cerebro import database  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "py_cerebro is required for the Cerebro connector. "
            "Install Cerebro service-tools and ensure py_cerebro is on PYTHONPATH."
        ) from exc
    return database


def _import_py_cerebro_dbtypes() -> Any:
    from py_cerebro import dbtypes

    return dbtypes


def _require_database(database: Any | None) -> Any:
    if database is None:
        raise RuntimeError("Cerebro database connection has not been established.")
    return database
