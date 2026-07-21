"""Poll Deadline farm jobs and dispatch completion notifications."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

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

FARM_JOB_TERMINAL_STATUSES = frozenset({"Completed", "Failed", "Suspended"})
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

    def _poll_loop() -> None:
        client = factory(config)
        deadline = time.monotonic() + MAX_POLL_DURATION_SECONDS
        while time.monotonic() < deadline:
            try:
                payload = client.get_job(normalized_job_id)
                status = job_status_from_payload(payload)
                resolved_name = job_name or job_name_from_payload(
                    payload, fallback_job_id=normalized_job_id
                )
                if status in FARM_JOB_TERMINAL_STATUSES:
                    notify_context = farm_notification_context_from_job_payload(
                        payload, fallback_job_id=normalized_job_id, fallback_job_name=resolved_name
                    )
                    dispatch_result = dispatch_farm_notifications(studio_config, notify_context)
                    report_validation_notification_outcomes(dispatch_result)
                    return
            except Exception:
                pass
            time.sleep(max(1.0, float(poll_interval_seconds)))

    threading.Thread(target=_poll_loop, daemon=True, name="pi-farm-job-monitor").start()
