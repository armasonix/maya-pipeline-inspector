"""Central notification dispatcher for validation and farm events."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pipeline_inspector.core.supervisor_routing import SupervisorRoutingDecision
from pipeline_inspector.integrations.discord.notify import (
    DiscordClientFactory,
    DiscordNotificationResult,
    maybe_send_discord_validation_notification,
)
from pipeline_inspector.integrations.slack.notify import (
    SlackClientFactory,
    SlackNotificationResult,
    maybe_send_slack_validation_notification,
)
from pipeline_inspector.integrations.telegram.notify import (
    TelegramClientFactory,
    TelegramNotificationResult,
    maybe_send_telegram_validation_notification,
)
from pipeline_inspector.studio_config import StudioConfig

NOTIFICATION_CONNECTOR_IDS: tuple[str, ...] = ("telegram", "discord", "slack")

_CONNECTOR_DISPLAY_NAMES = {
    "telegram": "Telegram",
    "discord": "Discord",
    "slack": "Slack",
}


@dataclass(frozen=True)
class ConnectorNotificationOutcome:
    """Outcome from one notification connector during dispatch."""

    connector_id: str
    sent: bool
    skipped_reason: str = ""
    error_message: str = ""


@dataclass(frozen=True)
class ValidationNotificationDispatchResult:
    """Aggregated outcomes from fan-out to all notification connectors."""

    outcomes: tuple[ConnectorNotificationOutcome, ...]


def _outcome_from_telegram(result: TelegramNotificationResult) -> ConnectorNotificationOutcome:
    return ConnectorNotificationOutcome(
        connector_id="telegram",
        sent=result.sent,
        skipped_reason=result.skipped_reason,
        error_message=result.error_message,
    )


def _outcome_from_discord(result: DiscordNotificationResult) -> ConnectorNotificationOutcome:
    return ConnectorNotificationOutcome(
        connector_id="discord",
        sent=result.sent,
        skipped_reason=result.skipped_reason,
        error_message=result.error_message,
    )


def _outcome_from_slack(result: SlackNotificationResult) -> ConnectorNotificationOutcome:
    return ConnectorNotificationOutcome(
        connector_id="slack",
        sent=result.sent,
        skipped_reason=result.skipped_reason,
        error_message=result.error_message,
    )


def dispatch_validation_notifications(
    studio_config: StudioConfig | None,
    result: Any,
    *,
    supervisor_route: SupervisorRoutingDecision | None = None,
    telegram_client_factory: TelegramClientFactory | None = None,
    discord_client_factory: DiscordClientFactory | None = None,
    slack_client_factory: SlackClientFactory | None = None,
) -> ValidationNotificationDispatchResult:
    """Fan out validation notifications to all enabled notification connectors."""

    route = supervisor_route.route if supervisor_route is not None else None
    telegram_chat_id = route.telegram_chat_id.strip() if route is not None else ""
    discord_webhook = route.discord_webhook_url.strip() if route is not None else ""
    slack_webhook = route.slack_webhook_url.strip() if route is not None else ""

    telegram_result = maybe_send_telegram_validation_notification(
        studio_config,
        result,
        client_factory=telegram_client_factory,
        chat_id_override=telegram_chat_id or None,
    )
    discord_result = maybe_send_discord_validation_notification(
        studio_config,
        result,
        client_factory=discord_client_factory,
        webhook_url_override=discord_webhook or None,
    )
    slack_result = maybe_send_slack_validation_notification(
        studio_config,
        result,
        client_factory=slack_client_factory,
        webhook_url_override=slack_webhook or None,
    )
    return ValidationNotificationDispatchResult(
        outcomes=(
            _outcome_from_telegram(telegram_result),
            _outcome_from_discord(discord_result),
            _outcome_from_slack(slack_result),
        )
    )


def report_validation_notification_outcomes(
    dispatch_result: ValidationNotificationDispatchResult,
    *,
    print_fn: Callable[[str], None] | None = None,
) -> None:
    """Print user-visible status for each connector without interrupting UI flow."""

    writer = print_fn or print
    for outcome in dispatch_result.outcomes:
        display_name = _CONNECTOR_DISPLAY_NAMES.get(outcome.connector_id, outcome.connector_id)
        if outcome.sent:
            writer(f"{display_name} notification sent.")
        elif outcome.error_message:
            writer(f"{display_name} notification failed: {outcome.error_message}")
        elif outcome.skipped_reason:
            writer(f"{display_name} notification skipped: {outcome.skipped_reason}")
