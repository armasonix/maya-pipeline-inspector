"""Slack validation notification helpers."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    resolve_slack_routes,
)
from pipeline_inspector.integrations.slack.blocks import (
    ValidationBlocksContext,
    build_optional_report_link,
    format_validation_blocks,
)
from pipeline_inspector.integrations.slack.client import SlackClient
from pipeline_inspector.integrations.trackers.publish import (
    slack_thread_ts_from_tracker_metadata,
    tracker_metadata_from_run,
)
from pipeline_inspector.studio_config import (
    SlackConnectorSettings,
    StudioConfig,
    resolve_slack_config,
)

SlackClientFactory = Callable[[], SlackClient]

def _scene_basename(scene_path: str) -> str:
    """Return a cross-platform scene filename from Maya/Windows or POSIX paths."""

    if not scene_path:
        return "unsaved scene"
    normalized = scene_path.replace("\\", "/").rstrip("/")
    name = Path(normalized).name
    return name or "unsaved scene"

@dataclass(frozen=True)
class SlackNotificationResult:
    """Outcome from attempting to send Slack validation notifications."""

    sent: bool
    skipped_reason: str = ""
    error_message: str = ""
    routes_sent: int = 0

def validation_notification_context_from_run(result: Any) -> ValidationBlocksContext:
    """Build a notification context from a validation run result object."""

    health = getattr(result, "health_score", None)
    snapshot = getattr(result, "snapshot", None)
    scene_path = str(getattr(snapshot, "scene_path", "") or "")
    return ValidationBlocksContext(
        scene_name=_scene_basename(scene_path),
        scene_path=scene_path,
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

def _configured_validation_events(settings: SlackConnectorSettings) -> tuple[str, ...]:
    configured = set(settings.notify_on)
    for target in settings.notify_targets:
        configured.update(target.events)
    return tuple(configured)


def matched_notify_events(
    settings: SlackConnectorSettings,
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


def should_send_slack_notification(
    settings: SlackConnectorSettings,
    *,
    block_publish: bool,
    block_deadline: bool,
    critical_count: int = 0,
    health_score: int = 0,
    studio_config: StudioConfig | None = None,
) -> bool:
    """Return True when Slack notifications should be sent for this validation."""

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
    return bool(resolve_slack_routes(settings, studio_config, matched))


def _routes_to_event_webhooks(
    routes: tuple[ResolvedNotifyRoute, ...],
) -> tuple[tuple[str, str], ...]:
    flattened: list[tuple[str, str]] = []
    for route in routes:
        webhook_url = route.webhook_url.strip()
        if not webhook_url:
            continue
        primary_event = route.events[0] if route.events else NOTIFY_EVENT_BLOCK_PUBLISH
        flattened.append((primary_event, webhook_url))
    return tuple(flattened)

def _dedupe_routes_by_webhook(
    routes: tuple[tuple[str, str], ...],
) -> tuple[tuple[str, str], ...]:
    """Keep one POST per unique webhook URL."""

    seen: set[str] = set()
    deduped: list[tuple[str, str]] = []
    for event_id, webhook_url in routes:
        if webhook_url in seen:
            continue
        seen.add(webhook_url)
        deduped.append((event_id, webhook_url))
    return tuple(deduped)

def send_slack_validation_notification(
    studio_config: StudioConfig | None,
    context: ValidationBlocksContext,
    *,
    thread_ts: str | None = None,
    client_factory: SlackClientFactory | None = None,
    webhook_url_override: str | None = None,
    force_notify: bool = False,
    reporter_line: str = "",
) -> SlackNotificationResult:
    """Send Slack validation blocks to routed webhooks when settings match block events."""

    settings = (
        StudioConfig().connectors.slack
        if studio_config is None
        else studio_config.connectors.slack
    )
    if not settings.enabled:
        return SlackNotificationResult(sent=False, skipped_reason="disabled")

    config = resolve_slack_config(studio_config)
    if config is None and not str(webhook_url_override or "").strip():
        return SlackNotificationResult(sent=False, skipped_reason="incomplete_config")

    matched_events = matched_notify_events(
        settings,
        block_publish=context.block_publish,
        block_deadline=context.block_deadline,
        critical_count=context.critical_count,
        health_score=context.health_score,
        error_count=context.error_count,
        warning_count=context.warning_count,
    )
    override_webhook = str(webhook_url_override or "").strip()
    if force_notify and override_webhook and not matched_events:
        matched_events = tuple(settings.notify_on) or (NOTIFY_EVENT_BLOCK_PUBLISH,)
    if not matched_events:
        return SlackNotificationResult(
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
        primary_event = matched_events[0] if matched_events else NOTIFY_EVENT_BLOCK_PUBLISH
        routes = _dedupe_routes_by_webhook(((primary_event, override_webhook),))
    else:
        resolved = resolve_slack_routes(settings, studio_config, matched_events)
        routes = _dedupe_routes_by_webhook(_routes_to_event_webhooks(resolved))
    if not routes:
        return SlackNotificationResult(sent=False, skipped_reason="no_routed_webhooks")

    report_link: str | None = None
    if settings.include_report_link:
        render_root = (
            ""
            if studio_config is None
            else studio_config.studio_environment.render_root
        )
        report_link = build_optional_report_link(
            scene_path=context.scene_path,
            render_root=render_root,
        )

    payload = format_validation_blocks(
        context,
        matched_events=matched_events,
        report_link=report_link,
        thread_ts=thread_ts,
        reporter_line=reporter_line,
    )
    factory = client_factory or SlackClient
    client = factory()
    errors: list[str] = []
    routes_sent = 0
    for event_id, webhook_url in routes:
        try:
            response = client.send_blocks(webhook_url, payload)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{event_id}: {exc}")
            continue
        if response.status_code == 200:
            routes_sent += 1
        else:
            errors.append(f"{event_id}: HTTP {response.status_code}")

    if routes_sent == 0:
        return SlackNotificationResult(
            sent=False,
            error_message="; ".join(errors) if errors else "slack_webhook_error",
        )
    return SlackNotificationResult(
        sent=True,
        routes_sent=routes_sent,
        error_message="; ".join(errors),
    )

def maybe_send_slack_validation_notification(
    studio_config: StudioConfig | None,
    result: Any,
    *,
    client_factory: SlackClientFactory | None = None,
    webhook_url_override: str | None = None,
    force_notify: bool = False,
    reporter_line: str = "",
) -> SlackNotificationResult:
    """Send Slack validation blocks for a validation run result."""

    context = validation_notification_context_from_run(result)
    thread_ts = slack_thread_ts_from_tracker_metadata(tracker_metadata_from_run(result))
    return send_slack_validation_notification(
        studio_config,
        context,
        thread_ts=thread_ts,
        client_factory=client_factory,
        webhook_url_override=webhook_url_override,
        force_notify=force_notify,
        reporter_line=reporter_line,
    )


def _send_slack_text_to_routes(
    studio_config: StudioConfig | None,
    settings: SlackConnectorSettings,
    *,
    matched_events: tuple[str, ...],
    text: str,
    client_factory: SlackClientFactory | None = None,
) -> SlackNotificationResult:
    routes = _dedupe_routes_by_webhook(
        _routes_to_event_webhooks(resolve_slack_routes(settings, studio_config, matched_events))
    )
    if not routes:
        return SlackNotificationResult(sent=False, skipped_reason="no_routed_webhooks")

    factory = client_factory or SlackClient
    client = factory()
    errors: list[str] = []
    routes_sent = 0
    for event_id, webhook_url in routes:
        try:
            response = client.request(webhook_url, payload={"text": text})
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{event_id}: {exc}")
            continue
        if response.status_code == 200:
            routes_sent += 1
        else:
            errors.append(f"{event_id}: HTTP {response.status_code}")

    if routes_sent == 0:
        return SlackNotificationResult(
            sent=False,
            error_message="; ".join(errors) if errors else "slack_webhook_error",
        )
    return SlackNotificationResult(sent=True, routes_sent=routes_sent)


def maybe_send_slack_readiness_notification(
    studio_config: StudioConfig | None,
    message: str,
    *,
    client_factory: SlackClientFactory | None = None,
) -> SlackNotificationResult:
    settings = (
        StudioConfig().connectors.slack
        if studio_config is None
        else studio_config.connectors.slack
    )
    if not settings.enabled:
        return SlackNotificationResult(sent=False, skipped_reason="disabled")
    if not standalone_event_enabled(settings.notify_on, NOTIFY_EVENT_ON_READINESS_FAIL):
        return SlackNotificationResult(sent=False, skipped_reason="no_matching_events")
    return _send_slack_text_to_routes(
        studio_config,
        settings,
        matched_events=(NOTIFY_EVENT_ON_READINESS_FAIL,),
        text=message,
        client_factory=client_factory,
    )


def maybe_send_slack_farm_notification(
    studio_config: StudioConfig | None,
    message: str,
    *,
    client_factory: SlackClientFactory | None = None,
) -> SlackNotificationResult:
    settings = (
        StudioConfig().connectors.slack
        if studio_config is None
        else studio_config.connectors.slack
    )
    if not settings.enabled:
        return SlackNotificationResult(sent=False, skipped_reason="disabled")
    if not standalone_event_enabled(settings.notify_on, NOTIFY_EVENT_ON_FARM_COMPLETE):
        return SlackNotificationResult(sent=False, skipped_reason="no_matching_events")
    return _send_slack_text_to_routes(
        studio_config,
        settings,
        matched_events=(NOTIFY_EVENT_ON_FARM_COMPLETE,),
        text=message,
        client_factory=client_factory,
    )
