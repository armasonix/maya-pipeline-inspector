"""Discord embed formatter for Pipeline Inspector validation summaries."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline_inspector.studio_config import (
    DISCORD_NOTIFY_EVENT_BLOCK_DEADLINE,
    DISCORD_NOTIFY_EVENT_BLOCK_PUBLISH,
)

_EVENT_LABELS = {
    DISCORD_NOTIFY_EVENT_BLOCK_PUBLISH: "Publish block",
    DISCORD_NOTIFY_EVENT_BLOCK_DEADLINE: "Deadline block",
}

_COLOR_PUBLISH_BLOCK = 0xE74C3C
_COLOR_DEADLINE_BLOCK = 0xF39C12
_COLOR_MIXED_BLOCK = 0xC0392B


@dataclass(frozen=True)
class ValidationEmbedContext:
    """Normalized validation payload for Discord embed messages."""

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


def validation_embed_context_from_mapping(context: Any) -> ValidationEmbedContext:
    """Build an embed context from a generic validation context object."""

    return ValidationEmbedContext(
        scene_name=str(getattr(context, "scene_name", "") or "unsaved scene"),
        scan_scope=str(getattr(context, "scan_scope", "") or "scene"),
        profile_id=str(getattr(context, "profile_id", "") or ""),
        asset_class_id=str(getattr(context, "asset_class_id", "") or ""),
        health_score=int(getattr(context, "health_score", 0) or 0),
        critical_count=int(getattr(context, "critical_count", 0) or 0),
        error_count=int(getattr(context, "error_count", 0) or 0),
        warning_count=int(getattr(context, "warning_count", 0) or 0),
        info_count=int(getattr(context, "info_count", 0) or 0),
        block_publish=bool(getattr(context, "block_publish", False)),
        block_deadline=bool(getattr(context, "block_deadline", False)),
    )


def format_validation_embed(
    context: ValidationEmbedContext,
    *,
    matched_events: tuple[str, ...],
) -> dict[str, Any]:
    """Format a Discord embed payload for a validation summary."""

    from pipeline_inspector.integrations.messaging.validation_summary import (
        render_validation_summary_text,
        validation_summary_from_context,
    )

    event_labels = ", ".join(_EVENT_LABELS.get(event, event) for event in matched_events)
    data = validation_summary_from_context(context, event_labels=event_labels)
    text = render_validation_summary_text(data, platform="chat")
    title, _, body = text.partition("\n")
    return {
        "title": title,
        "description": body.strip(),
        "color": _embed_color(matched_events),
    }


def _embed_color(matched_events: tuple[str, ...]) -> int:
    events = set(matched_events)
    if (
        DISCORD_NOTIFY_EVENT_BLOCK_PUBLISH in events
        and DISCORD_NOTIFY_EVENT_BLOCK_DEADLINE in events
    ):
        return _COLOR_MIXED_BLOCK
    if DISCORD_NOTIFY_EVENT_BLOCK_PUBLISH in events:
        return _COLOR_PUBLISH_BLOCK
    return _COLOR_DEADLINE_BLOCK
