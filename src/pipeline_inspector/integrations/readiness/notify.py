"""Telegram delivery for machine readiness failure reports."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from pipeline_inspector.core.supervisor_routing import resolve_supervisor_route
from pipeline_inspector.integrations.readiness.engine import (
    ReadinessReport,
    format_readiness_report_text,
)
from pipeline_inspector.integrations.telegram.client import TelegramClient
from pipeline_inspector.integrations.telegram.config import TelegramConfig
from pipeline_inspector.studio_config import StudioConfig, resolve_telegram_config

ReadinessRecipient = Literal["sysadmin", "support"]
TelegramClientFactory = Callable[[TelegramConfig], TelegramClient]


@dataclass(frozen=True)
class ReadinessNotifyResult:
    """Outcome from sending a readiness report to support staff."""

    sent: bool
    recipient: ReadinessRecipient
    chat_id: str = ""
    error_message: str = ""


def send_readiness_report_to_telegram(
    studio_config: StudioConfig | None,
    report: ReadinessReport,
    *,
    recipient: ReadinessRecipient,
    client_factory: TelegramClientFactory | None = None,
    chat_id_override: str | None = None,
) -> ReadinessNotifyResult:
    """Send a readiness failure report to the configured support Telegram chat."""

    if studio_config is None:
        return ReadinessNotifyResult(
            sent=False,
            recipient=recipient,
            error_message="studio_config_missing",
        )

    override_chat_id = str(chat_id_override or "").strip()
    chat_id = override_chat_id or _resolve_support_chat_id(studio_config, recipient)
    if not chat_id:
        return ReadinessNotifyResult(
            sent=False,
            recipient=recipient,
            error_message="support_chat_id_missing",
        )

    telegram_config = resolve_telegram_config(studio_config)
    if telegram_config is None:
        return ReadinessNotifyResult(
            sent=False,
            recipient=recipient,
            chat_id=chat_id,
            error_message="telegram_connector_disabled",
        )

    factory = client_factory or TelegramClient
    client = factory(
        TelegramConfig(
            bot_token=telegram_config.bot_token,
            chat_id=chat_id,
            api_base_url=telegram_config.api_base_url,
            timeout_seconds=telegram_config.timeout_seconds,
        )
    )
    response = client.send_message(format_readiness_report_text(report))
    if response.status_code != 200:
        return ReadinessNotifyResult(
            sent=False,
            recipient=recipient,
            chat_id=chat_id,
            error_message="telegram_api_error",
        )
    if isinstance(response.json_data, dict) and not response.json_data.get("ok", True):
        return ReadinessNotifyResult(
            sent=False,
            recipient=recipient,
            chat_id=chat_id,
            error_message="telegram_api_error",
        )
    return ReadinessNotifyResult(
        sent=True,
        recipient=recipient,
        chat_id=chat_id,
    )


def send_readiness_report_to_supervisor(
    studio_config: StudioConfig | None,
    report: ReadinessReport,
    *,
    reporter_role: str,
    client_factory: TelegramClientFactory | None = None,
) -> ReadinessNotifyResult:
    """Send a readiness report to the supervisor route for the reporter role."""

    if studio_config is None:
        return ReadinessNotifyResult(
            sent=False,
            recipient="support",
            error_message="studio_config_missing",
        )

    from pipeline_inspector.core.governance import normalize_pipeline_role

    normalized_role = normalize_pipeline_role(reporter_role) or "technical_artist"
    routing = resolve_supervisor_route(studio_config.governance, normalized_role)
    if routing is None:
        return ReadinessNotifyResult(
            sent=False,
            recipient="support",
            error_message="supervisor_route_missing",
        )

    chat_id = routing.route.telegram_chat_id.strip()
    if not chat_id:
        return ReadinessNotifyResult(
            sent=False,
            recipient="support",
            error_message="supervisor_telegram_chat_missing",
        )

    return send_readiness_report_to_telegram(
        studio_config,
        report,
        recipient="support",
        client_factory=client_factory,
        chat_id_override=chat_id,
    )


def _resolve_support_chat_id(
    studio_config: StudioConfig,
    recipient: ReadinessRecipient,
) -> str:
    support = studio_config.readiness.support
    if recipient == "sysadmin":
        return support.sysadmin_telegram_chat_id.strip()
    return support.support_telegram_chat_id.strip()
