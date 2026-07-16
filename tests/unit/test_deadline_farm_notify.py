from __future__ import annotations

from pipeline_inspector.integrations.deadline.farm_notify import (
    farm_notification_context_from_job_payload,
)
from pipeline_inspector.integrations.notify.dispatcher import _format_farm_notification_message


def test_farm_notification_context_from_job_payload_extracts_worker_and_duration():
    payload = {
        "_id": "job-42",
        "Stat": 3,
        "Mach": "DESKTOP-C8KN1E3",
        "DateStart": "2026-07-15T21:37:25.000+03:00",
        "DateComp": "2026-07-15T21:39:40.000+03:00",
        "Errs": 0,
        "Props": {
            "Name": "Pipeline Inspector | hero.ma",
            "User": "ledorub3d",
        },
    }

    context = farm_notification_context_from_job_payload(
        payload,
        fallback_job_id="job-42",
    )

    assert context.status == "Completed"
    assert context.job_name == "Pipeline Inspector | hero.ma"
    assert context.worker_machine == "DESKTOP-C8KN1E3"
    assert context.submitted_by == "ledorub3d"
    assert context.duration_text == "2m 15s"
    assert context.started_at
    assert context.completed_at


def test_format_farm_notification_message_includes_worker_and_duration():
    from pipeline_inspector.integrations.notify.dispatcher import FarmNotificationContext

    message = _format_farm_notification_message(
        FarmNotificationContext(
            job_id="job-42",
            job_name="Pipeline Inspector | hero.ma",
            status="Completed",
            worker_machine="DESKTOP-C8KN1E3",
            submitted_by="ledorub3d",
            started_at="2026-07-15 21:37:25 MSK",
            completed_at="2026-07-15 21:39:40 MSK",
            duration_text="2m 15s",
        )
    )

    assert "Farm job completed successfully" in message
    assert "Worker: DESKTOP-C8KN1E3" in message
    assert "Duration: 2m 15s" in message
    assert "User: ledorub3d" in message
