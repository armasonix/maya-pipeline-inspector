"""Poll Deadline farm jobs and dispatch completion notifications."""
from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from typing import Any

from pipeline_inspector.integrations.deadline.client import DeadlineClient, DeadlineConfig
from pipeline_inspector.integrations.notify.dispatcher import (
    FarmNotificationContext,
    dispatch_farm_notifications,
    report_validation_notification_outcomes,
)
from pipeline_inspector.studio_config import StudioConfig

FARM_JOB_TERMINAL_STATUSES = frozenset(
    {
        "Completed",
        "Failed",
        "Suspended",
    }
)
DEFAULT_POLL_INTERVAL_SECONDS = 5.0
MAX_POLL_DURATION_SECONDS = 6 * 60 * 60

DeadlineClientFactory = Callable[[DeadlineConfig], DeadlineClient]

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


def start_farm_job_notification_poll(
    *,
    config: DeadlineConfig,
    studio_config: StudioConfig | None,
    job_id: str,
    job_name: str = "",
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    client_factory: DeadlineClientFactory | None = None,
) -> None:
    """Poll a submitted farm job until it reaches a terminal status, then notify."""

    normalized_job_id = str(job_id).strip()
    if not normalized_job_id:
        return

    factory = client_factory or (lambda cfg: DeadlineClient(cfg))
    # region agent log
    _farm_monitor_debug_log(
        "farm_job_monitor.py:start_farm_job_notification_poll",
        "scheduled farm job notification poll",
        {
            "job_id": normalized_job_id,
            "job_name": job_name,
            "poll_interval_seconds": poll_interval_seconds,
        },
        hypothesis_id="H3",
    )
    # endregion

    def _poll_loop() -> None:
        client = factory(config)
        deadline = time.monotonic() + MAX_POLL_DURATION_SECONDS
        while time.monotonic() < deadline:
            try:
                payload = client.get_job(normalized_job_id)
                status = job_status_from_payload(payload)
                resolved_name = job_name or job_name_from_payload(
                    payload,
                    fallback_job_id=normalized_job_id,
                )
                # region agent log
                _farm_monitor_debug_log(
                    "farm_job_monitor.py:_poll_loop",
                    "polled farm job status",
                    {
                        "job_id": normalized_job_id,
                        "status": status,
                        "terminal": status in FARM_JOB_TERMINAL_STATUSES,
                    },
                    hypothesis_id="H3",
                )
                # endregion
                if status in FARM_JOB_TERMINAL_STATUSES:
                    dispatch_result = dispatch_farm_notifications(
                        studio_config,
                        FarmNotificationContext(
                            job_id=normalized_job_id,
                            job_name=resolved_name,
                            status=status,
                        ),
                    )
                    # region agent log
                    _farm_monitor_debug_log(
                        "farm_job_monitor.py:_poll_loop",
                        "dispatched farm completion notifications",
                        {
                            "job_id": normalized_job_id,
                            "status": status,
                            "outcomes": [
                                {
                                    "connector": outcome.connector_id,
                                    "sent": outcome.sent,
                                    "skipped_reason": outcome.skipped_reason,
                                    "error_message": outcome.error_message,
                                }
                                for outcome in dispatch_result.outcomes
                            ],
                        },
                        hypothesis_id="H4",
                    )
                    # endregion
                    report_validation_notification_outcomes(dispatch_result)
                    return
            except Exception as exc:  # noqa: BLE001
                # region agent log
                _farm_monitor_debug_log(
                    "farm_job_monitor.py:_poll_loop",
                    "farm job poll error",
                    {"job_id": normalized_job_id, "error": str(exc)},
                    hypothesis_id="H3",
                )
                # endregion
            time.sleep(max(1.0, float(poll_interval_seconds)))

    threading.Thread(target=_poll_loop, daemon=True, name="pi-farm-job-monitor").start()


def _farm_monitor_debug_log(
    location: str,
    message: str,
    data: dict[str, Any],
    *,
    hypothesis_id: str,
) -> None:
    try:
        payload = {
            "sessionId": "618f4f",
            "timestamp": int(time.time() * 1000),
            "location": location,
            "message": message,
            "data": data,
            "hypothesisId": hypothesis_id,
        }
        log_path = __import__("pathlib").Path(__file__).resolve().parents[2] / "debug-618f4f.log"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
    except OSError:
        return
