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
from shader_health.integrations.slack.notify import (
    SlackNotificationResult,
    maybe_send_slack_validation_notification,
    send_slack_validation_notification,
    should_send_slack_notification,
    validation_notification_context_from_run,
)

__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "HttpRequest",
    "HttpTransport",
    "SlackClient",
    "SlackClientError",
    "SlackConfig",
    "SlackNotificationResult",
    "SlackResponse",
    "ValidationBlocksContext",
    "build_optional_report_link",
    "default_http_transport",
    "format_validation_blocks",
    "maybe_send_slack_validation_notification",
    "route_matched_events",
    "send_slack_validation_notification",
    "should_send_slack_notification",
    "validation_notification_context_from_run",
    "webhook_url_for_event",
]
