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

    return _job_epoch_from_payload(payload, ("DateComp", "CompDate", "DateCompleted", "CompletedDate"))


def job_start_epoch_seconds(payload: dict[str, Any]) -> float | None:
    """Return a job start timestamp when present in the payload."""

    return _job_epoch_from_payload(payload, ("DateStart", "StartDate"))


def job_submit_epoch_seconds(payload: dict[str, Any]) -> float | None:
    """Return a job submit timestamp when present in the payload."""

    return _job_epoch_from_payload(payload, ("DateSubmit", "SubmitDate"))


def job_pool_from_payload(payload: dict[str, Any]) -> str:
    """Return the pool name from a job payload."""

    return _job_field_from_payload(payload, ("Pool",))


def job_group_from_payload(payload: dict[str, Any]) -> str:
    """Return the worker group from a job payload."""

    return _job_field_from_payload(payload, ("Grp", "Group"))


def job_plugin_from_payload(payload: dict[str, Any]) -> str:
    """Return the Deadline plugin name from a job payload."""

    return _job_field_from_payload(payload, ("Plugin", "Plug"))


def job_user_from_payload(payload: dict[str, Any]) -> str:
    """Return the submitting user from a job payload."""

    return _job_field_from_payload(payload, ("UserName", "User", "JobUserName"))


def job_error_count(payload: dict[str, Any]) -> int:
    """Return the Deadline task error count for a job."""

    for source in _job_sources(payload):
        try:
            return max(0, int(source.get("Errs") or 0))
        except (TypeError, ValueError):
            continue
    return 0


def job_frame_count(payload: dict[str, Any]) -> int:
    """Return the number of frames represented by a job payload."""

    for source in _job_sources(payload):
        for key in ("NumFrames", "FrameCount"):
            try:
                count = int(source.get(key) or 0)
            except (TypeError, ValueError):
                continue
            if count > 0:
                return count
        frames = str(source.get("Frames") or "").strip()
        if frames:
            return _count_frames_spec(frames)
    return 0


def average_frame_render_seconds_from_statistics(statistics: dict[str, Any]) -> float | None:
    """Return average frame render time from job statistics when available."""

    for key in (
        "AverageFrameRenderTime",
        "AvgFrameRenderTime",
        "AverageTaskRenderTime",
        "AverageRenderTime",
    ):
        seconds = duration_seconds_from_value(statistics.get(key))
        if seconds is not None:
            return seconds
    return None


def task_render_time_seconds(task: dict[str, Any]) -> float | None:
    """Return render time in seconds from a Deadline task payload."""

    for key in ("RenderTime", "TaskRenderTime", "TotalRenderTime"):
        seconds = duration_seconds_from_value(task.get(key))
        if seconds is not None:
            return seconds
    return None


def task_frame_number(task: dict[str, Any]) -> int | None:
    """Return the frame number represented by a task payload."""

    for key in ("Frame", "TaskFrame", "Frames"):
        value = task.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def task_is_failed(task: dict[str, Any]) -> bool:
    """Return True when a task payload indicates failure."""

    status = str(task.get("TaskStatus", task.get("Status", ""))).casefold()
    if status in {"failed", "4"}:
        return True
    stat = task.get("Stat")
    if stat is not None:
        try:
            return int(stat) == 4
        except (TypeError, ValueError):
            return str(stat).casefold() in {"failed", "4"}
    return False


def task_is_completed(task: dict[str, Any]) -> bool:
    """Return True when a task payload indicates completion."""

    status = str(task.get("TaskStatus", task.get("Status", ""))).casefold()
    if status in {"completed", "3"}:
        return True
    stat = task.get("Stat")
    if stat is not None:
        try:
            return int(stat) == 3
        except (TypeError, ValueError):
            return str(stat).casefold() in {"completed", "3"}
    return False


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


def _job_epoch_from_payload(payload: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for source in _job_sources(payload):
        for key in keys:
            timestamp = _parse_deadline_datetime(source.get(key))
            if timestamp is not None:
                return timestamp
    return None


def _job_field_from_payload(payload: dict[str, Any], keys: tuple[str, ...]) -> str:
    for source in _job_sources(payload):
        for key in keys:
            value = source.get(key)
            if value:
                return str(value)
    return ""


def _job_sources(payload: dict[str, Any]) -> list[dict[str, Any]]:
    props = payload.get("Props")
    if isinstance(props, dict):
        return [payload, props]
    return [payload]


def _count_frames_spec(frames: str) -> int:
    total = 0
    for chunk in frames.split(","):
        part = chunk.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            try:
                start = int(start_text.strip())
                end = int(end_text.strip())
            except ValueError:
                continue
            total += max(0, end - start + 1)
            continue
        try:
            total += 1
        except ValueError:
            continue
    return total


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

