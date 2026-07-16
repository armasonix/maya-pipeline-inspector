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
from pipeline_inspector.integrations.notification_triggers import (
    NOTIFY_EVENT_BLOCK_PUBLISH,
    NOTIFY_EVENT_ON_FARM_COMPLETE,
    NOTIFY_EVENT_ON_READINESS_FAIL,
    ValidationTriggerContext,
    describe_validation_notify_skip,
    match_validation_notify_events,
    standalone_event_enabled,
    validation_trigger_context_from_counts,
)
from pipeline_inspector.integrations.notify.routing import (
    ResolvedNotifyRoute,
    resolve_discord_routes,
)
from pipeline_inspector.studio_config import (
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


def _configured_validation_events(settings: DiscordConnectorSettings) -> tuple[str, ...]:
    configured = set(settings.notify_on)
    for target in settings.notify_targets:
        configured.update(target.events)
    return tuple(configured)


def matched_notify_events(
    settings: DiscordConnectorSettings,
    *,
    block_publish: bool,
    block_deadline: bool,
    critical_count: int = 0,
    health_score: int = 0,
    error_count: int = 0,
    warning_count: int = 0,
) -> tuple[str, ...]:
    """Return configured notify events that match the validation run state."""

    configured = _configured_validation_events(settings)
    return match_validation_notify_events(
        configured,
        validation_trigger_context_from_counts(
            block_publish=block_publish,
            block_deadline=block_deadline,
            critical_count=critical_count,
            health_score=health_score,
            error_count=error_count,
            warning_count=warning_count,
        ),
        notify_score_below=settings.notify_score_below,
    )


def should_send_discord_notification(
    settings: DiscordConnectorSettings,
    *,
    block_publish: bool,
    block_deadline: bool,
    critical_count: int = 0,
    health_score: int = 0,
    studio_config: StudioConfig | None = None,
) -> bool:
    """Return True when Discord notifications should be sent for this validation."""

    if not settings.enabled:
        return False
    matched = matched_notify_events(
        settings,
        block_publish=block_publish,
        block_deadline=block_deadline,
        critical_count=critical_count,
        health_score=health_score,
    )
    if not matched:
        return False
    return bool(resolve_discord_routes(settings, studio_config, matched))


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
    webhook_url_override: str | None = None,
    force_notify: bool = False,
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
    if config is None and not str(webhook_url_override or "").strip():
        return DiscordNotificationResult(sent=False, skipped_reason="incomplete_config")

    override_webhook = str(webhook_url_override or "").strip()

    matched_events = matched_notify_events(
        settings,
        block_publish=context.block_publish,
        block_deadline=context.block_deadline,
        critical_count=context.critical_count,
        health_score=context.health_score,
        error_count=context.error_count,
        warning_count=context.warning_count,
    )
    if force_notify and override_webhook and not matched_events:
        matched_events = tuple(settings.notify_on) or (NOTIFY_EVENT_BLOCK_PUBLISH,)
    if not matched_events:
        return DiscordNotificationResult(
            sent=False,
            skipped_reason=describe_validation_notify_skip(
                _configured_validation_events(settings),
                validation_trigger_context_from_counts(
                    block_publish=context.block_publish,
                    block_deadline=context.block_deadline,
                    critical_count=context.critical_count,
                    health_score=context.health_score,
                    error_count=context.error_count,
                    warning_count=context.warning_count,
                ),
                notify_score_below=settings.notify_score_below,
            ),
        )

    if override_webhook:
        routes: tuple[ResolvedNotifyRoute, ...] = (
            ResolvedNotifyRoute(events=matched_events, webhook_url=override_webhook),
        )
    else:
        routes = resolve_discord_routes(settings, studio_config, matched_events)
    if not routes:
        return DiscordNotificationResult(sent=False, skipped_reason="no_routed_webhooks")

    embed = format_validation_embed(context, matched_events=matched_events)
    factory = client_factory or DiscordClient
    errors: list[str] = []
    routes_sent = 0
    for route in routes:
        webhook_url = route.webhook_url.strip() or override_webhook
        if not webhook_url:
            continue
        route_config = DiscordConfig(webhook_url=webhook_url)
        try:
            response = factory(route_config).send_embed(embed)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
            continue

        if response.status_code not in (200, 204):
            errors.append(format_discord_http_error(response))
            continue
        routes_sent += 1

    if routes_sent == 0:
        return DiscordNotificationResult(sent=False, error_message="; ".join(errors))
    return DiscordNotificationResult(sent=True)


def maybe_send_discord_validation_notification(
    studio_config: StudioConfig | None,
    result: Any,
    *,
    client_factory: DiscordClientFactory | None = None,
    webhook_url_override: str | None = None,
    force_notify: bool = False,
) -> DiscordNotificationResult:
    """Send a Discord validation embed for a validation run result."""

    context = validation_notification_context_from_run(result)
    return send_discord_validation_notification(
        studio_config,
        context,
        client_factory=client_factory,
        webhook_url_override=webhook_url_override,
        force_notify=force_notify,
    )


def _send_discord_content_to_routes(
    studio_config: StudioConfig | None,
    settings: DiscordConnectorSettings,
    *,
    matched_events: tuple[str, ...],
    content: str,
    client_factory: DiscordClientFactory | None = None,
) -> DiscordNotificationResult:
    routes = resolve_discord_routes(settings, studio_config, matched_events)
    if not routes:
        return DiscordNotificationResult(sent=False, skipped_reason="no_routed_webhooks")

    factory = client_factory or DiscordClient
    errors: list[str] = []
    routes_sent = 0
    for route in routes:
        webhook_url = route.webhook_url.strip()
        if not webhook_url:
            continue
        try:
            response = factory(DiscordConfig(webhook_url=webhook_url)).request(
                payload={"content": content}
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
            continue
        if response.status_code not in (200, 204):
            errors.append(format_discord_http_error(response))
            continue
        routes_sent += 1

    if routes_sent == 0:
        return DiscordNotificationResult(sent=False, error_message="; ".join(errors))
    return DiscordNotificationResult(sent=True)


def maybe_send_discord_readiness_notification(
    studio_config: StudioConfig | None,
    message: str,
    *,
    client_factory: DiscordClientFactory | None = None,
) -> DiscordNotificationResult:
    settings = (
        StudioConfig().connectors.discord
        if studio_config is None
        else studio_config.connectors.discord
    )
    if not settings.enabled:
        return DiscordNotificationResult(sent=False, skipped_reason="disabled")
    if not standalone_event_enabled(settings.notify_on, NOTIFY_EVENT_ON_READINESS_FAIL):
        return DiscordNotificationResult(sent=False, skipped_reason="no_matching_events")
    return _send_discord_content_to_routes(
        studio_config,
        settings,
        matched_events=(NOTIFY_EVENT_ON_READINESS_FAIL,),
        content=message,
        client_factory=client_factory,
    )


def maybe_send_discord_farm_notification(
    studio_config: StudioConfig | None,
    message: str,
    *,
    client_factory: DiscordClientFactory | None = None,
) -> DiscordNotificationResult:
    settings = (
        StudioConfig().connectors.discord
        if studio_config is None
        else studio_config.connectors.discord
    )
    if not settings.enabled:
        return DiscordNotificationResult(sent=False, skipped_reason="disabled")
    if not standalone_event_enabled(settings.notify_on, NOTIFY_EVENT_ON_FARM_COMPLETE):
        return DiscordNotificationResult(sent=False, skipped_reason="no_matching_events")
    return _send_discord_content_to_routes(
        studio_config,
        settings,
        matched_events=(NOTIFY_EVENT_ON_FARM_COMPLETE,),
        content=message,
        client_factory=client_factory,
    )
