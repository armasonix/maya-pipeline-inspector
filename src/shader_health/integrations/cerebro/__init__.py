"""Cerebro task tracker integration for Shader Health Inspector."""

from shader_health.integrations.cerebro.adapter import (
    PyCerebroDatabaseAdapter,
    default_database_port_factory,
)
from shader_health.integrations.cerebro.client import (
    CerebroClient,
    CerebroClientError,
    format_note_html,
)
from shader_health.integrations.cerebro.config import (
    DEFAULT_DB_PORT,
    DEFAULT_TIMEOUT_SECONDS,
    CerebroConfig,
)
from shader_health.integrations.cerebro.port import CerebroDatabasePort
from shader_health.integrations.cerebro.publish import (
    build_task_url,
    maybe_publish_validation_summary,
    publish_validation_summary,
    resolve_task_id,
)
from shader_health.integrations.trackers.base import TrackerPublishResult

__all__ = [
    "DEFAULT_DB_PORT",
    "DEFAULT_TIMEOUT_SECONDS",
    "CerebroClient",
    "CerebroClientError",
    "CerebroConfig",
    "CerebroDatabasePort",
    "PyCerebroDatabaseAdapter",
    "TrackerPublishResult",
    "build_task_url",
    "default_database_port_factory",
    "format_note_html",
    "maybe_publish_validation_summary",
    "publish_validation_summary",
    "resolve_task_id",
]
