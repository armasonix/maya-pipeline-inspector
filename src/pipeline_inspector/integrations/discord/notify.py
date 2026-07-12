"""Discord validation notification helpers."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pipeline_inspector.integrations.discord.client import DiscordClient
from pipeline_inspector.integrations.discord.config import DiscordConfig
from pipeline_inspector.integrations.discord.embed import (
    ValidationEmbedContext,
    format_validation_embed,
)
from pipeline_inspector.studio_config import (
    DISCORD_NOTIFY_EVENT_BLOCK_DEADLINE,
    DISCORD_NOTIFY_EVENT_BLOCK_PUBLISH,
    DiscordConnectorSettings,
    StudioConfig,
    resolve_discord_config,
)

DiscordClientFactory = Callable[[DiscordConfig], DiscordClient]


def _scene_basename(scene_path: str) -> str:
    """Return a cross-platform scene filename from Maya/Windows or POSIX paths."""

    if not scene_path:
        return "unsaved scene"
    normalized = scene_path.replace("\\", "/").rstrip("/")
    name = Path(normalized).name
    return name or "unsaved scene"


@dataclass(frozen=True)
class DiscordNotificationResult:
    """Outcome from attempting to send a Discord validation notification."""

    sent: bool
    skipped_reason: str = ""
    error_message: str = ""


def validation_notification_context_from_run(result: Any) -> ValidationEmbedContext:
    """Build a notification context from a validation run result object."""

    health = getattr(result, "health_score", None)
    snapshot = getattr(result, "snapshot", None)
    scene_path = str(getattr(snapshot, "scene_path", "") or "")
    return ValidationEmbedContext(
        scene_name=_scene_basename(scene_path),
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
    settings: DiscordConnectorSettings,
    *,
    block_publish: bool,
    block_deadline: bool,
) -> tuple[str, ...]:
    """Return configured notify events that match active block flags."""

    notify_on = set(settings.notify_on)
    events: list[str] = []
    if block_publish and DISCORD_NOTIFY_EVENT_BLOCK_PUBLISH in notify_on:
        events.append(DISCORD_NOTIFY_EVENT_BLOCK_PUBLISH)
    if block_deadline and DISCORD_NOTIFY_EVENT_BLOCK_DEADLINE in notify_on:
        events.append(DISCORD_NOTIFY_EVENT_BLOCK_DEADLINE)
    return tuple(events)


def should_send_discord_notification(
    settings: DiscordConnectorSettings,
    *,
    block_publish: bool,
    block_deadline: bool,
) -> bool:
    """Return True when Discord notifications should be sent for this validation."""

    if not settings.enabled:
        return False
    return bool(
        matched_notify_events(
            settings,
            block_publish=block_publish,
            block_deadline=block_deadline,
        )
    )


def format_discord_http_error(response: Any) -> str:
    """Return a user-visible Discord webhook HTTP error string."""

    status_code = int(getattr(response, "status_code", 0) or 0)
    json_data = getattr(response, "json_data", None)
    if isinstance(json_data, dict):
        message = str(json_data.get("message", "") or "").strip()
        if message:
            return f"HTTP {status_code}: {message}"
    body = str(getattr(response, "body", "") or "").strip()
    if body and len(body) <= 160:
        return f"HTTP {status_code}: {body}"
    return f"HTTP {status_code}"


def send_discord_validation_notification(
    studio_config: StudioConfig | None,
    context: ValidationEmbedContext,
    *,
    client_factory: DiscordClientFactory | None = None,
) -> DiscordNotificationResult:
    """Send a Discord validation embed when connector settings match block events."""

    settings = (
        StudioConfig().connectors.discord
        if studio_config is None
        else studio_config.connectors.discord
    )
    if not settings.enabled:
        return DiscordNotificationResult(sent=False, skipped_reason="disabled")

    config = resolve_discord_config(studio_config)
    if config is None:
        return DiscordNotificationResult(sent=False, skipped_reason="incomplete_config")

    matched_events = matched_notify_events(
        settings,
        block_publish=context.block_publish,
        block_deadline=context.block_deadline,
    )
    if not matched_events:
        return DiscordNotificationResult(sent=False, skipped_reason="no_matching_events")

    embed = format_validation_embed(context, matched_events=matched_events)
    factory = client_factory or DiscordClient
    try:
        response = factory(config).send_embed(embed)
    except Exception as exc:  # noqa: BLE001
        return DiscordNotificationResult(sent=False, error_message=str(exc))

    if response.status_code not in (200, 204):
        return DiscordNotificationResult(
            sent=False,
            error_message=format_discord_http_error(response),
        )

    return DiscordNotificationResult(sent=True)


def maybe_send_discord_validation_notification(
    studio_config: StudioConfig | None,
    result: Any,
    *,
    client_factory: DiscordClientFactory | None = None,
) -> DiscordNotificationResult:
    """Send a Discord validation embed for a validation run result."""

    context = validation_notification_context_from_run(result)
    return send_discord_validation_notification(
        studio_config,
        context,
        client_factory=client_factory,
    )
