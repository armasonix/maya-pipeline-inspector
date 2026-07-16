"""Helpers for parsing Deadline Web Service job payloads."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

_DEADLINE_JOB_STAT_NAMES = {
    0: "Unknown",
    1: "Active",
    2: "Suspended",
    3: "Completed",
    4: "Failed",
    6: "Pending",
}


def job_status_from_payload(payload: dict[str, Any]) -> str:
    """Return a Deadline job status string from a Web Service payload."""

    for key in ("JobStatus", "Status", "JobState"):
        value = payload.get(key)
        if value:
            return str(value)
    stat = payload.get("Stat")
    if stat is not None:
        try:
            return _DEADLINE_JOB_STAT_NAMES.get(int(stat), str(stat))
        except (TypeError, ValueError):
            return str(stat)
    return ""


def job_name_from_payload(payload: dict[str, Any], *, fallback_job_id: str) -> str:
    """Return a human-readable job name from a Web Service payload."""

    props = payload.get("Props")
    if isinstance(props, dict):
        nested_name = props.get("Name")
        if nested_name:
            return str(nested_name)
    for key in ("JobName", "Name"):
        value = payload.get(key)
        if value:
            return str(value)
    return fallback_job_id


def duration_seconds_from_value(value: Any) -> float | None:
    """Parse Deadline duration values that may be seconds or HH:MM:SS strings."""

    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    if ":" in text:
        parts = text.split(":")
        try:
            if len(parts) == 3:
                hours, minutes, seconds = (float(part) for part in parts)
                return hours * 3600.0 + minutes * 60.0 + seconds
        except ValueError:
            return None
    try:
        return float(text)
    except ValueError:
        return None


def render_time_seconds_from_statistics(statistics: dict[str, Any]) -> float | None:
    """Return total render time in seconds from a job statistics payload."""

    for key in ("TotalRenderTime", "TotalTaskRenderTime", "JobRenderTime", "RenderTime"):
        seconds = duration_seconds_from_value(statistics.get(key))
        if seconds is not None:
            return seconds
    return None


def job_completion_epoch_seconds(payload: dict[str, Any]) -> float | None:
    """Return a job completion timestamp when present in the payload."""

    props = payload.get("Props")
    sources: list[dict[str, Any]] = [payload]
    if isinstance(props, dict):
        sources.append(props)
    for source in sources:
        for key in ("DateComp", "CompDate", "DateCompleted", "CompletedDate"):
            timestamp = _parse_deadline_datetime(source.get(key))
            if timestamp is not None:
                return timestamp
    return None


def worker_is_rendering(worker_info: dict[str, Any]) -> bool:
    """Return True when a worker info payload indicates an active render."""

    if worker_info.get("SlaveRendering") is True:
        return True
    state = str(
        worker_info.get("SlaveState", worker_info.get("State", ""))
    ).casefold()
    if state in {"rendering", "2"}:
        return True
    stat = worker_info.get("Stat")
    return stat is not None and str(stat).casefold() in {"rendering", "2"}


def _parse_deadline_datetime(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    formats = (
        "%b %d %Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    )
    for fmt in formats:
        try:
            parsed = datetime.strptime(text, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.timestamp()
        except ValueError:
            continue
    return None

