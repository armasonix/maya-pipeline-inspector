"""Shared validation summary formatting for notifications and trackers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

SummaryPlatform = Literal["chat", "ftrack"]

CHAT_SEPARATOR = "---------------------"
CHAT_HEADLINE_BASE = "Health Validation"
FTRACK_HEADLINE = "Health Validation Result"
# BMP symbol in the same range as ❌ ⚠️ ℹ️ — avoids Ftrack ???? on supplementary-plane emoji.
FTRACK_CRITICAL_EMOJI = "⛔"


@dataclass(frozen=True)
class ValidationSummaryData:
    """Normalized validation summary content shared by all outbound channels."""

    headline: str
    scene_name: str
    profile_label: str
    scope_label: str
    health_score: int
    critical_count: int
    error_count: int
    warning_count: int
    info_count: int
    block_label: str
    event_labels: str = ""
    validated_at_utc: str = ""
    report_path: str = ""


def format_block_status_label(*, block_publish: bool, block_deadline: bool) -> str:
    flags: list[str] = []
    if block_publish:
        flags.append("Publish block")
    if block_deadline:
        flags.append("Deadline block")
    return ", ".join(flags) if flags else "No blocks"


def build_chat_headline(*, event_labels: str = "") -> str:
    suffix = event_labels.strip() or "Notification"
    return f"{CHAT_HEADLINE_BASE} · {suffix}"


def build_validation_summary_headline(*, event_labels: str = "") -> str:
    return build_chat_headline(event_labels=event_labels)


def _health_emoji(score: int) -> str:
    if score >= 80:
        return "🟢"
    if score >= 50:
        return "🟡"
    return "🔴"


def _blocks_emoji(block_label: str) -> str:
    if block_label == "No blocks":
        return "✅"
    return "🚫"


def _block_bullet_lines(block_label: str) -> list[str]:
    if block_label == "No blocks":
        return ["- No blocks"]
    return [f"- {part.strip()}" for part in block_label.split(", ")]


def _chat_issue_lines(data: ValidationSummaryData) -> list[str]:
    return [
        f"🚨 {data.critical_count} critical",
        f"❌ {data.error_count} error",
        f"⚠️ {data.warning_count} warning",
        f"ℹ️ {data.info_count} info",
    ]


def _ftrack_issues_inline(data: ValidationSummaryData) -> str:
    return (
        f"Issues: {data.critical_count} critical {FTRACK_CRITICAL_EMOJI} "
        f"{data.error_count} error ❌ "
        f"{data.warning_count} warning ⚠️ "
        f"{data.info_count} info ℹ️"
    )


def validation_summary_from_fields(
    *,
    scene_name: str,
    profile_label: str,
    scope_label: str,
    health_score: int,
    critical_count: int,
    error_count: int,
    warning_count: int,
    info_count: int,
    block_publish: bool,
    block_deadline: bool,
    validated_at_utc: str = "",
    report_path: str = "",
    event_labels: str = "",
) -> ValidationSummaryData:
    return ValidationSummaryData(
        headline=build_chat_headline(event_labels=event_labels),
        scene_name=scene_name or "unsaved scene",
        profile_label=profile_label or "unknown",
        scope_label=scope_label or "Scene",
        health_score=health_score,
        critical_count=critical_count,
        error_count=error_count,
        warning_count=warning_count,
        info_count=info_count,
        block_label=format_block_status_label(
            block_publish=block_publish,
            block_deadline=block_deadline,
        ),
        event_labels=event_labels,
        validated_at_utc=validated_at_utc,
        report_path=report_path,
    )


def validation_summary_from_payload(
    payload: Any,
    *,
    event_labels: str = "",
) -> ValidationSummaryData:
    profile_label = str(getattr(payload, "profile_label", lambda: "")() or "")
    if not profile_label:
        profile_label = str(getattr(payload, "profile_id", "") or "unknown")
    scope_label = str(getattr(payload, "scan_scope", "") or "scene").title()
    return validation_summary_from_fields(
        scene_name=str(getattr(payload, "scene_name", "") or "unsaved scene"),
        profile_label=profile_label,
        scope_label=scope_label,
        health_score=int(getattr(payload, "health_score", 0) or 0),
        critical_count=int(getattr(payload, "critical_count", 0) or 0),
        error_count=int(getattr(payload, "error_count", 0) or 0),
        warning_count=int(getattr(payload, "warning_count", 0) or 0),
        info_count=int(getattr(payload, "info_count", 0) or 0),
        block_publish=bool(getattr(payload, "block_publish", False)),
        block_deadline=bool(getattr(payload, "block_deadline", False)),
        validated_at_utc=str(getattr(payload, "validated_at_utc", "") or ""),
        report_path=str(getattr(payload, "report_path", "") or ""),
        event_labels=event_labels,
    )


def validation_summary_from_context(
    context: Any,
    *,
    event_labels: str = "",
) -> ValidationSummaryData:
    profile_label = str(getattr(context, "profile_id", "") or "unknown")
    asset_class_id = str(getattr(context, "asset_class_id", "") or "")
    if asset_class_id:
        profile_label = f"{profile_label}+{asset_class_id}"
    scope_label = str(getattr(context, "scan_scope", "") or "scene").title()
    return validation_summary_from_fields(
        scene_name=str(getattr(context, "scene_name", "") or "unsaved scene"),
        profile_label=profile_label,
        scope_label=scope_label,
        health_score=int(getattr(context, "health_score", 0) or 0),
        critical_count=int(getattr(context, "critical_count", 0) or 0),
        error_count=int(getattr(context, "error_count", 0) or 0),
        warning_count=int(getattr(context, "warning_count", 0) or 0),
        info_count=int(getattr(context, "info_count", 0) or 0),
        block_publish=bool(getattr(context, "block_publish", False)),
        block_deadline=bool(getattr(context, "block_deadline", False)),
        event_labels=event_labels,
    )


def render_validation_summary_text(
    data: ValidationSummaryData,
    *,
    platform: SummaryPlatform = "chat",
) -> str:
    """Render a multi-line summary using one shared layout for all platforms."""

    if platform == "ftrack":
        lines = [
            FTRACK_HEADLINE,
            f"Scene: {data.scene_name}",
            f"Profile: {data.profile_label}",
            f"Scope: {data.scope_label}",
            "",
            f"Health score: {data.health_score}/100",
            _ftrack_issues_inline(data),
            "",
            f"Blocks: {data.block_label}",
        ]
        if data.validated_at_utc:
            lines.append(f"Validated: {data.validated_at_utc}")
        if data.report_path:
            lines.append(f"Report: {data.report_path}")
    else:
        lines = [
            f"🔍 {data.headline}",
            f"{_health_emoji(data.health_score)} Health score: {data.health_score}/100",
            f"📁 Scene: {data.scene_name}",
            f"🎬 Profile: {data.profile_label}",
            f"🎯 Scope: {data.scope_label}",
            CHAT_SEPARATOR,
            "📊 Actual Issue list:",
            *_chat_issue_lines(data),
            CHAT_SEPARATOR,
            "🚫 Current Blocks:",
            *_block_bullet_lines(data.block_label),
        ]
        if data.validated_at_utc:
            lines.extend(["", f"🕒 Validated: {data.validated_at_utc}"])
        if data.report_path:
            lines.extend(["", f"📎 Report: {data.report_path}"])

    text = "\n".join(lines)
    return text


def render_validation_summary_from_payload(
    payload: Any,
    *,
    platform: SummaryPlatform = "chat",
    event_labels: str = "",
) -> str:
    data = validation_summary_from_payload(payload, event_labels=event_labels)
    return render_validation_summary_text(data, platform=platform)


def render_validation_summary_from_context(
    context: Any,
    *,
    platform: SummaryPlatform = "chat",
    event_labels: str = "",
) -> str:
    data = validation_summary_from_context(context, event_labels=event_labels)
    return render_validation_summary_text(data, platform=platform)


def chat_title_prefix() -> str:
    return "🔍 "


def blocks_emoji(block_label: str) -> str:
    return _blocks_emoji(block_label)


def chat_field_labels() -> dict[str, str]:
    return {
        "scene": "📁 Scene",
        "profile": "🎬 Profile",
        "scope": "🎯 Scope",
        "issues": "📊 Actual Issue list",
        "blocks": "Current Blocks",
    }


def format_health_score_line(data: ValidationSummaryData, *, platform: SummaryPlatform) -> str:
    if platform == "ftrack":
        return f"Health score: {data.health_score}/100"
    return f"{_health_emoji(data.health_score)} Health score: {data.health_score}/100"


def format_issues_block(data: ValidationSummaryData, *, platform: SummaryPlatform) -> str:
    if platform == "ftrack":
        return _ftrack_issues_inline(data)
    return "\n".join(_chat_issue_lines(data))


# Backward-compatible aliases used by tracker publish helpers.
format_validation_summary_from_payload = render_validation_summary_from_payload
format_validation_summary_from_context = render_validation_summary_from_context
