"""Central notification dispatcher for Shader Health validation events."""

from shader_health.integrations.notify.dispatcher import (
    NOTIFICATION_CONNECTOR_IDS,
    ConnectorNotificationOutcome,
    ValidationNotificationDispatchResult,
    dispatch_validation_notifications,
    report_validation_notification_outcomes,
)

__all__ = [
    "NOTIFICATION_CONNECTOR_IDS",
    "ConnectorNotificationOutcome",
    "ValidationNotificationDispatchResult",
    "dispatch_validation_notifications",
    "report_validation_notification_outcomes",
]
