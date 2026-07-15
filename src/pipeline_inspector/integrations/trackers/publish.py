"""Shared validation publish payload for task tracker connectors."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SLACK_THREAD_TS_METADATA_KEYS: tuple[str, ...] = ("thread_ts", "slack_thread_ts")


_MAYA_SCENE_SUFFIXES: tuple[str, ...] = (".ma", ".mb")


def scene_basename(scene_path: str) -> str:
    """Return a cross-platform scene filename from Maya/Windows or POSIX paths."""

    if not scene_path:
        return "unsaved scene"
    normalized = scene_path.replace("\\", "/").rstrip("/")
    name = Path(normalized).name
    return name or "unsaved scene"


def scene_task_lookup_name(scene_name: str) -> str:
    """Return a tracker task lookup name with Maya scene suffixes removed."""

    normalized = str(scene_name or "").strip()
    if not normalized:
        return normalized
    lower = normalized.lower()
    for suffix in _MAYA_SCENE_SUFFIXES:
        if lower.endswith(suffix):
            return normalized[: -len(suffix)]
    return normalized


def scene_task_lookup_candidates(scene_name: str) -> tuple[str, ...]:
    """Return scene names to try when resolving a tracker task from a Maya scene."""

    primary = str(scene_name or "").strip()
    if not primary:
        return ()
    stem = scene_task_lookup_name(primary)
    if stem and stem != primary:
        return (stem, primary)
    return (primary,)


@dataclass(frozen=True)
class ValidationPublishPayload:
    """Normalized validation payload for task tracker publish actions."""

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
    validated_at_utc: str
    report_path: str = ""
    metadata: Mapping[str, str] = field(default_factory=dict)

    def profile_label(self) -> str:
        """Return a display label for the active validation profile."""

        label = self.profile_id or "unknown"
        if self.asset_class_id:
            return f"{label}+{self.asset_class_id}"
        return label

    def block_status_label(self) -> str:
        """Return human-readable publish/deadline block flags."""

        flags: list[str] = []
        if self.block_publish:
            flags.append("Publish block")
        if self.block_deadline:
            flags.append("Deadline block")
        return ", ".join(flags) if flags else "No blocks"


def tracker_metadata_from_run(result: Any) -> dict[str, str]:
    """Return optional studio pipeline tracker metadata attached to a validation run."""

    raw_metadata = getattr(result, "tracker_metadata", None)
    if not isinstance(raw_metadata, Mapping):
        return {}

    metadata: dict[str, str] = {}
    for key, value in raw_metadata.items():
        normalized_key = str(key).strip()
        normalized_value = str(value or "").strip()
        if normalized_key and normalized_value:
            metadata[normalized_key] = normalized_value
    return metadata


def slack_thread_ts_from_tracker_metadata(metadata: Mapping[str, str]) -> str | None:
    """Return a Slack thread timestamp from optional tracker metadata."""

    for key in SLACK_THREAD_TS_METADATA_KEYS:
        thread_ts = str(metadata.get(key, "") or "").strip()
        if thread_ts:
            return thread_ts
    return None


def validation_publish_payload_from_run(
    result: Any,
    *,
    report_path: str = "",
    metadata: Mapping[str, str] | None = None,
) -> ValidationPublishPayload:
    """Build a publish payload from a validation run result object."""

    health = getattr(result, "health_score", None)
    snapshot = getattr(result, "snapshot", None)
    scene_path = str(getattr(snapshot, "scene_path", "") or "")
    merged_metadata = tracker_metadata_from_run(result)
    if metadata:
        merged_metadata.update(dict(metadata))
    return ValidationPublishPayload(
        scene_name=scene_basename(scene_path),
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
        validated_at_utc=str(getattr(snapshot, "scanned_at_utc", "") or ""),
        report_path=report_path,
        metadata=merged_metadata,
    )


def format_validation_publish_summary(payload: ValidationPublishPayload) -> str:
    """Format a tracker-neutral validation summary message."""

    from pipeline_inspector.integrations.messaging.validation_summary import (
        render_validation_summary_from_payload,
    )

    return render_validation_summary_from_payload(payload, platform="ftrack")


def format_tracker_note_content(
    payload: ValidationPublishPayload,
    *,
    markdown_note: str = "",
) -> str:
    """Return enriched Markdown note text with plain-summary fallback."""

    normalized_markdown = str(markdown_note or "").strip()
    if normalized_markdown:
        if payload.report_path:
            return (
                f"{normalized_markdown}\n\n"
                f"**Attached report path:** `{payload.report_path}`"
            )
        return normalized_markdown
    return format_validation_publish_summary(payload)
