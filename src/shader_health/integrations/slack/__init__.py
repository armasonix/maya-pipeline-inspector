"""Slack incoming webhook integration for Shader Health Inspector notifications."""

from shader_health.integrations.slack.blocks import (
    ValidationBlocksContext,
    build_optional_report_link,
    format_validation_blocks,
    route_matched_events,
    webhook_url_for_event,
)
from shader_health.integrations.slack.client import (
    HttpRequest,
    HttpTransport,
    SlackClient,
    SlackClientError,
    SlackResponse,
    default_http_transport,
)
from shader_health.integrations.slack.config import (
    DEFAULT_TIMEOUT_SECONDS,
    SlackConfig,
)

__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "HttpRequest",
    "HttpTransport",
    "SlackClient",
    "SlackClientError",
    "SlackConfig",
    "SlackResponse",
    "ValidationBlocksContext",
    "build_optional_report_link",
    "default_http_transport",
    "format_validation_blocks",
    "route_matched_events",
    "webhook_url_for_event",
]
