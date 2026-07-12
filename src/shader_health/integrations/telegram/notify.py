"""Telegram validation notification helpers."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shader_health.integrations.telegram.client import TelegramClient
from shader_health.integrations.telegram.config import TelegramConfig
from shader_health.studio_config import (
    TELEGRAM_NOTIFY_EVENT_BLOCK_DEADLINE,
    TELEGRAM_NOTIFY_EVENT_BLOCK_PUBLISH,
    StudioConfig,
    TelegramConnectorSettings,
    resolve_telegram_config,
)

TelegramClientFactory = Callable[[TelegramConfig], TelegramClient]

_EVENT_LABELS = {
    TELEGRAM_NOTIFY_EVENT_BLOCK_PUBLISH: "Publish block",
    TELEGRAM_NOTIFY_EVENT_BLOCK_DEADLINE: "Deadline block",
}


def _scene_basename(scene_path: str) -> str:
    """Return a cross-platform scene filename from Maya/Windows or POSIX paths."""

    if not scene_path:
        return "unsaved scene"
    normalized = scene_path.replace("\\", "/").rstrip("/")
    name = Path(normalized).name
    return name or "unsaved scene"


@dataclass(frozen=True)
class ValidationNotificationContext:
    """Normalized validation payload for Telegram summary messages."""

    scene_name: str
    scan_scope: str
    profile_id: str
    asset_class_id: str
    health_score: int
    critical_count: int
    error_count: int
    warning_count: int
    info_count: int
    block_publish: bool
    block_deadline: bool


@dataclass(frozen=True)
class TelegramNotificationResult:
    """Outcome from attempting to send a Telegram validation notification."""

    sent: bool
    skipped_reason: str = ""
    error_message: str = ""


def validation_notification_context_from_run(result: Any) -> ValidationNotificationContext:
    """Build a notification context from a validation run result object."""

    health = getattr(result, "health_score", None)
    snapshot = getattr(result, "snapshot", None)
    scene_path = str(getattr(snapshot, "scene_path", "") or "")
    scene_name = _scene_basename(scene_path)
    return ValidationNotificationContext(
        scene_name=scene_name,
        scan_scope=str(getattr(result, "scan_scope", "") or "scene"),
        profile_id=str(getattr(result, "profile_id", "") or ""),
        asset_class_id=str(getattr(result, "asset_class_id", "") or ""),
        health_score=int(getattr(health, "score", 0) or 0),
        critical_count=int(getattr(health, "critical", 0) or 0),
        error_count=int(getattr(health, "error", 0) or 0),
        warning_count=int(getattr(health, "warning", 0) or 0),
        info_count=int(getattr(health, "info", 0) or 0),
        block_publish=bool(getattr(health, "block_publish", False)),
        block_deadline=bool(getattr(health, "block_deadline", False)),
    )


def matched_notify_events(
    settings: TelegramConnectorSettings,
    *,
    block_publish: bool,
    block_deadline: bool,
) -> tuple[str, ...]:
    """Return configured notify events that match active block flags."""

    notify_on = set(settings.notify_on)
    events: list[str] = []
    if block_publish and TELEGRAM_NOTIFY_EVENT_BLOCK_PUBLISH in notify_on:
        events.append(TELEGRAM_NOTIFY_EVENT_BLOCK_PUBLISH)
    if block_deadline and TELEGRAM_NOTIFY_EVENT_BLOCK_DEADLINE in notify_on:
        events.append(TELEGRAM_NOTIFY_EVENT_BLOCK_DEADLINE)
    return tuple(events)


def should_send_telegram_notification(
    settings: TelegramConnectorSettings,
    *,
    block_publish: bool,
    block_deadline: bool,
) -> bool:
    """Return True when Telegram notifications should be sent for this validation."""

    if not settings.enabled:
        return False
    return bool(
        matched_notify_events(
            settings,
            block_publish=block_publish,
            block_deadline=block_deadline,
        )
    )


def format_validation_summary_message(
    context: ValidationNotificationContext,
    *,
    matched_events: tuple[str, ...],
) -> str:
    """Format the Telegram validation summary message."""

    from shader_health.integrations.messaging.validation_summary import (
        render_validation_summary_from_context,
    )

    event_labels = ", ".join(_EVENT_LABELS.get(event, event) for event in matched_events)
    return render_validation_summary_from_context(
        context,
        platform="chat",
        event_labels=event_labels,
    )


def send_telegram_validation_notification(
    studio_config: StudioConfig | None,
    context: ValidationNotificationContext,
    *,
    client_factory: TelegramClientFactory | None = None,
) -> TelegramNotificationResult:
    """Send a Telegram validation summary when connector settings match block events."""

    settings = (
        StudioConfig().connectors.telegram
        if studio_config is None
        else studio_config.connectors.telegram
    )
    if not settings.enabled:
        return TelegramNotificationResult(sent=False, skipped_reason="disabled")

    config = resolve_telegram_config(studio_config)
    if config is None:
        return TelegramNotificationResult(sent=False, skipped_reason="incomplete_config")

    matched_events = matched_notify_events(
        settings,
        block_publish=context.block_publish,
        block_deadline=context.block_deadline,
    )
    if not matched_events:
        return TelegramNotificationResult(sent=False, skipped_reason="no_matching_events")

    message = format_validation_summary_message(context, matched_events=matched_events)
    factory = client_factory or TelegramClient
    try:
        response = factory(config).send_message(message)
    except Exception as exc:  # noqa: BLE001
        return TelegramNotificationResult(sent=False, error_message=str(exc))

    if response.status_code != 200:
        return TelegramNotificationResult(
            sent=False,
            error_message=f"HTTP {response.status_code}",
        )
    if not isinstance(response.json_data, dict) or not response.json_data.get("ok"):
        return TelegramNotificationResult(sent=False, error_message="telegram_api_error")

    return TelegramNotificationResult(sent=True)


def maybe_send_telegram_validation_notification(
    studio_config: StudioConfig | None,
    result: Any,
    *,
    client_factory: TelegramClientFactory | None = None,
) -> TelegramNotificationResult:
    """Send a Telegram validation summary for a validation run result."""

    context = validation_notification_context_from_run(result)
    return send_telegram_validation_notification(
        studio_config,
        context,
        client_factory=client_factory,
    )
