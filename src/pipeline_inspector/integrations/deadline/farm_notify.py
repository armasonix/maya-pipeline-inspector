"""Farm job completion notification context from Deadline payloads."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pipeline_inspector.integrations.deadline.job_payload import (
    job_name_from_payload,
    job_status_from_payload,
)
from pipeline_inspector.integrations.notify.dispatcher import FarmNotificationContext

_DEADLINE_MIN_DATE_PREFIX = "0001-01-01"


def _parse_deadline_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text or text.startswith(_DEADLINE_MIN_DATE_PREFIX):
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _format_timestamp(value: Any) -> str:
    parsed = _parse_deadline_timestamp(value)
    if parsed is None:
        return ""
    return parsed.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def _format_duration_seconds(total_seconds: int) -> str:
    seconds = max(0, int(total_seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {sec}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m {sec}s"


def _duration_text_from_payload(payload: dict[str, Any]) -> str:
    started = _parse_deadline_timestamp(payload.get("DateStart"))
    completed = _parse_deadline_timestamp(payload.get("DateComp"))
    if started is not None and completed is not None and completed >= started:
        return _format_duration_seconds(int((completed - started).total_seconds()))
    return ""


def _submitted_by_from_payload(payload: dict[str, Any]) -> str:
    props = payload.get("Props")
    if isinstance(props, dict):
        user = props.get("User")
        if user:
            return str(user)
    for key in ("User", "JobUserName"):
        value = payload.get(key)
        if value:
            return str(value)
    return ""


def farm_notification_context_from_job_payload(
    payload: dict[str, Any],
    *,
    fallback_job_id: str,
    fallback_job_name: str = "",
) -> FarmNotificationContext:
    """Build a farm notification context from a Deadline Web Service job record."""

    job_id = str(payload.get("_id") or fallback_job_id).strip() or fallback_job_id
    job_name = fallback_job_name or job_name_from_payload(payload, fallback_job_id=job_id)
    worker_machine = str(payload.get("Mach") or "").strip()
    try:
        error_count = int(payload.get("Errs") or 0)
    except (TypeError, ValueError):
        error_count = 0
    return FarmNotificationContext(
        job_id=job_id,
        job_name=job_name,
        status=job_status_from_payload(payload),
        worker_machine=worker_machine,
        submitted_by=_submitted_by_from_payload(payload),
        started_at=_format_timestamp(payload.get("DateStart")),
        completed_at=_format_timestamp(payload.get("DateComp")),
        duration_text=_duration_text_from_payload(payload),
        error_count=error_count,
    )
