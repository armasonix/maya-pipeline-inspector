"""Telegram validation notification helpers."""
from __future__ import annotations

import json
import sys
import time
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

_DEBUG_LOG_PATH = Path(__file__).resolve().parents[4] / "debug-ee1eca.log"


def _agent_debug_log(
    *,
    hypothesis_id: str,
    location: str,
    message: str,
    data: dict[str, object],
    run_id: str = "pre-fix",
) -> None:
    # region agent log
    try:
        payload = {
            "sessionId": "ee1eca",
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with _DEBUG_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
    except OSError:
        return
    # endregion


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
    raw_scene_name = Path(scene_path).name if scene_path else "unsaved scene"
    scene_name = _scene_basename(scene_path)
    # region agent log
    _agent_debug_log(
        hypothesis_id="A",
        location="notify.py:validation_notification_context_from_run",
        message="scene path basename resolution",
        data={
            "platform": sys.platform,
            "scene_path": scene_path,
            "raw_path_name": raw_scene_name,
            "normalized_scene_name": scene_name,
        },
    )
    # endregion
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

    event_labels = ", ".join(_EVENT_LABELS.get(event, event) for event in matched_events)
    profile_label = context.profile_id or "unknown"
    if context.asset_class_id:
        profile_label = f"{profile_label}+{context.asset_class_id}"
    scope_label = context.scan_scope.title() if context.scan_scope else "Scene"
    return "\n".join(
        (
            f"Shader Health: {event_labels}",
            f"Scene: {context.scene_name}",
            f"Profile: {profile_label}",
            f"Scope: {scope_label}",
            f"Health: {context.health_score}/100",
            (
                "Issues: "
                f"{context.critical_count} critical, "
                f"{context.error_count} error, "
                f"{context.warning_count} warning, "
                f"{context.info_count} info"
            ),
        )
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
