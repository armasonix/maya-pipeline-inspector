"""Helpers for parsing Deadline Web Service job payloads."""
from __future__ import annotations

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
