"""Poll Deadline farm jobs and dispatch completion notifications."""
from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from typing import Any

from pipeline_inspector.integrations.deadline.client import DeadlineClient, DeadlineConfig
from pipeline_inspector.integrations.deadline.farm_notify import (
    farm_notification_context_from_job_payload,
)
from pipeline_inspector.integrations.deadline.job_payload import (
    job_name_from_payload,
    job_status_from_payload,
)
from pipeline_inspector.integrations.notify.dispatcher import (
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
                    notify_context = farm_notification_context_from_job_payload(
                        payload,
                        fallback_job_id=normalized_job_id,
                        fallback_job_name=resolved_name,
                    )
                    dispatch_result = dispatch_farm_notifications(
                        studio_config,
                        notify_context,
                    )
                    # region agent log
                    _farm_monitor_debug_log(
                        "farm_job_monitor.py:_poll_loop",
                        "dispatched farm completion notifications",
                        {
                            "job_id": normalized_job_id,
                            "status": status,
                            "worker_machine": notify_context.worker_machine,
                            "duration_text": notify_context.duration_text,
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
    from pipeline_inspector.util.debug_log import write_debug_log

    write_debug_log(location, message, data, hypothesis_id=hypothesis_id)
