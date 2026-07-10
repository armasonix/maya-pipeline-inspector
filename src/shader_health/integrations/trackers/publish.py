"""Shared validation publish payload for task tracker connectors."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def scene_basename(scene_path: str) -> str:
    """Return a cross-platform scene filename from Maya/Windows or POSIX paths."""

    if not scene_path:
        return "unsaved scene"
    normalized = scene_path.replace("\\", "/").rstrip("/")
    name = Path(normalized).name
    return name or "unsaved scene"


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
        metadata=dict(metadata or {}),
    )


def format_validation_publish_summary(payload: ValidationPublishPayload) -> str:
    """Format a tracker-neutral validation summary message."""

    scope_label = payload.scan_scope.title() if payload.scan_scope else "Scene"
    lines = [
        f"Shader Health validation summary ({payload.block_status_label()})",
        f"Scene: {payload.scene_name}",
        f"Profile: {payload.profile_label()}",
        f"Scope: {scope_label}",
        f"Health: {payload.health_score}/100",
        (
            "Issues: "
            f"{payload.critical_count} critical, "
            f"{payload.error_count} error, "
            f"{payload.warning_count} warning, "
            f"{payload.info_count} info"
        ),
    ]
    if payload.validated_at_utc:
        lines.append(f"Validated at: {payload.validated_at_utc}")
    if payload.report_path:
        lines.append(f"Report: {payload.report_path}")
    return "\n".join(lines)
