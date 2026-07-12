"""Slack Block Kit formatter and webhook routing for validation summaries."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pipeline_inspector.studio_config import (
    SLACK_NOTIFY_EVENT_BLOCK_DEADLINE,
    SLACK_NOTIFY_EVENT_BLOCK_PUBLISH,
    SlackConnectorSettings,
)

_EVENT_LABELS = {
    SLACK_NOTIFY_EVENT_BLOCK_PUBLISH: "Publish block",
    SLACK_NOTIFY_EVENT_BLOCK_DEADLINE: "Deadline block",
}


@dataclass(frozen=True)
class ValidationBlocksContext:
    """Normalized validation payload for Slack Block Kit messages."""

    scene_name: str
    scene_path: str
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


def build_optional_report_link(*, scene_path: str, render_root: str) -> str | None:
    """Build an optional report path under ``studio_environment.render_root``."""

    root = render_root.strip()
    if not root or not scene_path.strip():
        return None
    normalized_scene = scene_path.replace("\\", "/").rstrip("/")
    scene_stem = Path(normalized_scene).stem
    if not scene_stem:
        return None
    report_name = f"{scene_stem}_pipeline_inspector_report.json"
    return str(Path(root.replace("\\", "/")) / report_name)


def webhook_url_for_event(settings: SlackConnectorSettings, event_id: str) -> str | None:
    """Return the routed webhook URL for a configured block event."""

    if event_id == SLACK_NOTIFY_EVENT_BLOCK_PUBLISH:
        url = settings.publish_webhook_url.strip()
    elif event_id == SLACK_NOTIFY_EVENT_BLOCK_DEADLINE:
        url = settings.deadline_webhook_url.strip()
    else:
        return None
    return url or None


def route_matched_events(
    settings: SlackConnectorSettings,
    matched_events: tuple[str, ...],
) -> tuple[tuple[str, str], ...]:
    """Return routed webhook targets for matched block events."""

    routes: list[tuple[str, str]] = []
    for event_id in matched_events:
        webhook_url = webhook_url_for_event(settings, event_id)
        if webhook_url:
            routes.append((event_id, webhook_url))
    return tuple(routes)


def format_validation_blocks(
    context: ValidationBlocksContext,
    *,
    matched_events: tuple[str, ...],
    report_link: str | None = None,
    thread_ts: str | None = None,
) -> dict[str, Any]:
    """Format a Slack Block Kit payload for a validation summary."""

    from pipeline_inspector.integrations.messaging.validation_summary import (
        render_validation_summary_text,
        validation_summary_from_context,
    )

    event_labels = ", ".join(_EVENT_LABELS.get(event, event) for event in matched_events)
    data = validation_summary_from_context(context, event_labels=event_labels)
    text = render_validation_summary_text(data, platform="chat")
    blocks: list[dict[str, Any]] = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": text},
        },
    ]
    if report_link:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📎 *Report:*\n`{report_link}`",
                },
            }
        )
    payload: dict[str, Any] = {"blocks": blocks}
    if thread_ts:
        payload["thread_ts"] = thread_ts
    return payload
