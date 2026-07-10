"""ShotGrid task tracker integration for Shader Health Inspector."""

from shader_health.integrations.shotgrid.client import (
    HttpRequest,
    HttpTransport,
    ShotGridClient,
    ShotGridClientError,
    ShotGridResponse,
    default_http_transport,
)
from shader_health.integrations.shotgrid.config import (
    DEFAULT_ENTITY_TYPE,
    DEFAULT_TIMEOUT_SECONDS,
    SUPPORTED_ENTITY_TYPES,
    ShotGridConfig,
)
from shader_health.integrations.shotgrid.publish import (
    maybe_publish_validation_summary,
    publish_validation_summary,
    resolve_entity,
)
from shader_health.integrations.trackers.base import TrackerPublishResult

__all__ = [
    "DEFAULT_ENTITY_TYPE",
    "DEFAULT_TIMEOUT_SECONDS",
    "HttpRequest",
    "HttpTransport",
    "SUPPORTED_ENTITY_TYPES",
    "ShotGridClient",
    "ShotGridClientError",
    "ShotGridConfig",
    "ShotGridResponse",
    "TrackerPublishResult",
    "default_http_transport",
    "maybe_publish_validation_summary",
    "publish_validation_summary",
    "resolve_entity",
]
