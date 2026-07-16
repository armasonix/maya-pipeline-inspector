"""Telegram validation notification helpers."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pipeline_inspector.integrations.notification_triggers import (
    NOTIFY_EVENT_BLOCK_PUBLISH,
    NOTIFY_EVENT_LABELS,
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
    resolve_telegram_routes,
)
from pipeline_inspector.integrations.telegram.client import TelegramClient
from pipeline_inspector.integrations.telegram.config import TelegramConfig
from pipeline_inspector.studio_config import (
    StudioConfig,
    TelegramConnectorSettings,
    resolve_telegram_config,
)

TelegramClientFactory = Callable[[TelegramConfig], TelegramClient]


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


def _validation_trigger_context(
    *,
    block_publish: bool,
    block_deadline: bool,
    critical_count: int = 0,
    health_score: int = 0,
    error_count: int = 0,
    warning_count: int = 0,
) -> ValidationTriggerContext:
    return validation_trigger_context_from_counts(
        block_publish=block_publish,
        block_deadline=block_deadline,
        critical_count=critical_count,
        health_score=health_score,
        error_count=error_count,
        warning_count=warning_count,
    )


def _configured_validation_events(settings: TelegramConnectorSettings) -> tuple[str, ...]:
    configured = set(settings.notify_on)
    for target in settings.notify_targets:
        configured.update(target.events)
    return tuple(configured)


def matched_notify_events(
    settings: TelegramConnectorSettings,
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
        _validation_trigger_context(
            block_publish=block_publish,
            block_deadline=block_deadline,
            critical_count=critical_count,
            health_score=health_score,
            error_count=error_count,
            warning_count=warning_count,
        ),
        notify_score_below=settings.notify_score_below,
    )


def should_send_telegram_notification(
    settings: TelegramConnectorSettings,
    *,
    block_publish: bool,
    block_deadline: bool,
    critical_count: int = 0,
    health_score: int = 0,
    studio_config: StudioConfig | None = None,
) -> bool:
    """Return True when Telegram notifications should be sent for this validation."""

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
    return bool(resolve_telegram_routes(settings, studio_config, matched))


def format_validation_summary_message(
    context: ValidationNotificationContext,
    *,
    matched_events: tuple[str, ...],
) -> str:
    """Format the Telegram validation summary message."""

    from pipeline_inspector.integrations.messaging.validation_summary import (
        render_validation_summary_from_context,
    )

    event_labels = ", ".join(NOTIFY_EVENT_LABELS.get(event, event) for event in matched_events)
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
    chat_id_override: str | None = None,
    force_notify: bool = False,
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

    override_chat_id = str(chat_id_override or "").strip()
    if override_chat_id:
        config = config.with_overrides(chat_id=override_chat_id)

    matched_events = matched_notify_events(
        settings,
        block_publish=context.block_publish,
        block_deadline=context.block_deadline,
        critical_count=context.critical_count,
        health_score=context.health_score,
        error_count=context.error_count,
        warning_count=context.warning_count,
    )
    if force_notify and override_chat_id and not matched_events:
        matched_events = tuple(settings.notify_on) or (NOTIFY_EVENT_BLOCK_PUBLISH,)
    if not matched_events:
        return TelegramNotificationResult(
            sent=False,
            skipped_reason=describe_validation_notify_skip(
                _configured_validation_events(settings),
                _validation_trigger_context(
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

    if override_chat_id:
        routes: tuple[ResolvedNotifyRoute, ...] = (
            ResolvedNotifyRoute(events=matched_events, chat_id=override_chat_id),
        )
    else:
        routes = resolve_telegram_routes(settings, studio_config, matched_events)
    if not routes:
        return TelegramNotificationResult(sent=False, skipped_reason="no_routed_targets")

    message = format_validation_summary_message(context, matched_events=matched_events)
    factory = client_factory or TelegramClient
    errors: list[str] = []
    routes_sent = 0
    for route in routes:
        chat_id = route.chat_id.strip() or override_chat_id
        if not chat_id:
            continue
        route_config = config.with_overrides(chat_id=chat_id)
        try:
            response = factory(route_config).send_message(message)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
            continue

        if response.status_code != 200:
            errors.append(f"HTTP {response.status_code}")
            continue
        if not isinstance(response.json_data, dict) or not response.json_data.get("ok"):
            errors.append("telegram_api_error")
            continue
        routes_sent += 1

    if routes_sent == 0:
        return TelegramNotificationResult(sent=False, error_message="; ".join(errors))
    if errors:
        return TelegramNotificationResult(
            sent=True,
            error_message="; ".join(errors),
        )
    return TelegramNotificationResult(sent=True)


def maybe_send_telegram_validation_notification(
    studio_config: StudioConfig | None,
    result: Any,
    *,
    client_factory: TelegramClientFactory | None = None,
    chat_id_override: str | None = None,
    force_notify: bool = False,
) -> TelegramNotificationResult:
    """Send a Telegram validation summary for a validation run result."""

    context = validation_notification_context_from_run(result)
    return send_telegram_validation_notification(
        studio_config,
        context,
        client_factory=client_factory,
        chat_id_override=chat_id_override,
        force_notify=force_notify,
    )


def _send_telegram_text_to_routes(
    studio_config: StudioConfig | None,
    settings: TelegramConnectorSettings,
    *,
    matched_events: tuple[str, ...],
    message: str,
    client_factory: TelegramClientFactory | None = None,
) -> TelegramNotificationResult:
    config = resolve_telegram_config(studio_config)
    if config is None:
        return TelegramNotificationResult(sent=False, skipped_reason="incomplete_config")

    routes = resolve_telegram_routes(settings, studio_config, matched_events)
    if not routes:
        return TelegramNotificationResult(sent=False, skipped_reason="no_routed_targets")

    factory = client_factory or TelegramClient
    errors: list[str] = []
    routes_sent = 0
    for route in routes:
        chat_id = route.chat_id.strip()
        if not chat_id:
            continue
        try:
            response = factory(config.with_overrides(chat_id=chat_id)).send_message(message)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
            continue
        if response.status_code != 200:
            errors.append(f"HTTP {response.status_code}")
            continue
        if not isinstance(response.json_data, dict) or not response.json_data.get("ok"):
            errors.append("telegram_api_error")
            continue
        routes_sent += 1

    if routes_sent == 0:
        return TelegramNotificationResult(sent=False, error_message="; ".join(errors))
    return TelegramNotificationResult(sent=True)


def maybe_send_telegram_readiness_notification(
    studio_config: StudioConfig | None,
    message: str,
    *,
    client_factory: TelegramClientFactory | None = None,
) -> TelegramNotificationResult:
    """Send a readiness failure notification when the trigger is enabled."""

    settings = (
        StudioConfig().connectors.telegram
        if studio_config is None
        else studio_config.connectors.telegram
    )
    if not settings.enabled:
        return TelegramNotificationResult(sent=False, skipped_reason="disabled")
    if not standalone_event_enabled(settings.notify_on, NOTIFY_EVENT_ON_READINESS_FAIL):
        return TelegramNotificationResult(sent=False, skipped_reason="no_matching_events")
    return _send_telegram_text_to_routes(
        studio_config,
        settings,
        matched_events=(NOTIFY_EVENT_ON_READINESS_FAIL,),
        message=message,
        client_factory=client_factory,
    )


def maybe_send_telegram_farm_notification(
    studio_config: StudioConfig | None,
    message: str,
    *,
    client_factory: TelegramClientFactory | None = None,
) -> TelegramNotificationResult:
    """Send a farm completion notification when the trigger is enabled."""

    settings = (
        StudioConfig().connectors.telegram
        if studio_config is None
        else studio_config.connectors.telegram
    )
    if not settings.enabled:
        return TelegramNotificationResult(sent=False, skipped_reason="disabled")
    if not standalone_event_enabled(settings.notify_on, NOTIFY_EVENT_ON_FARM_COMPLETE):
        return TelegramNotificationResult(sent=False, skipped_reason="no_matching_events")
    return _send_telegram_text_to_routes(
        studio_config,
        settings,
        matched_events=(NOTIFY_EVENT_ON_FARM_COMPLETE,),
        message=message,
        client_factory=client_factory,
    )
