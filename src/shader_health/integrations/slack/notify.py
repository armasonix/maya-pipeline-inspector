"""Slack validation notification helpers."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shader_health.integrations.slack.blocks import (
    ValidationBlocksContext,
    build_optional_report_link,
    format_validation_blocks,
    route_matched_events,
)
from shader_health.integrations.slack.client import SlackClient
from shader_health.integrations.trackers.publish import (
    slack_thread_ts_from_tracker_metadata,
    tracker_metadata_from_run,
)
from shader_health.studio_config import (
    SLACK_NOTIFY_EVENT_BLOCK_DEADLINE,
    SLACK_NOTIFY_EVENT_BLOCK_PUBLISH,
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


def matched_notify_events(
    settings: SlackConnectorSettings,
    *,
    block_publish: bool,
    block_deadline: bool,
) -> tuple[str, ...]:
    """Return configured notify events that match active block flags."""

    notify_on = set(settings.notify_on)
    events: list[str] = []
    if block_publish and SLACK_NOTIFY_EVENT_BLOCK_PUBLISH in notify_on:
        events.append(SLACK_NOTIFY_EVENT_BLOCK_PUBLISH)
    if block_deadline and SLACK_NOTIFY_EVENT_BLOCK_DEADLINE in notify_on:
        events.append(SLACK_NOTIFY_EVENT_BLOCK_DEADLINE)
    return tuple(events)


def should_send_slack_notification(
    settings: SlackConnectorSettings,
    *,
    block_publish: bool,
    block_deadline: bool,
) -> bool:
    """Return True when Slack notifications should be sent for this validation."""

    if not settings.enabled:
        return False
    matched = matched_notify_events(
        settings,
        block_publish=block_publish,
        block_deadline=block_deadline,
    )
    if not matched:
        return False
    return bool(route_matched_events(settings, matched))


def send_slack_validation_notification(
    studio_config: StudioConfig | None,
    context: ValidationBlocksContext,
    *,
    thread_ts: str | None = None,
    client_factory: SlackClientFactory | None = None,
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
    if config is None:
        return SlackNotificationResult(sent=False, skipped_reason="incomplete_config")

    matched_events = matched_notify_events(
        settings,
        block_publish=context.block_publish,
        block_deadline=context.block_deadline,
    )
    if not matched_events:
        return SlackNotificationResult(sent=False, skipped_reason="no_matching_events")

    routes = route_matched_events(settings, matched_events)
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
) -> SlackNotificationResult:
    """Send Slack validation blocks for a validation run result."""

    context = validation_notification_context_from_run(result)
    thread_ts = slack_thread_ts_from_tracker_metadata(tracker_metadata_from_run(result))
    return send_slack_validation_notification(
        studio_config,
        context,
        thread_ts=thread_ts,
        client_factory=client_factory,
    )
