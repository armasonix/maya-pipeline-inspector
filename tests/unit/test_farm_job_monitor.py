from __future__ import annotations

import time
from typing import Any

from pipeline_inspector.integrations.deadline.client import DeadlineClient, DeadlineConfig
from pipeline_inspector.integrations.telegram.notify import TelegramNotificationResult
from pipeline_inspector.integrations.deadline.job_payload import (
    job_name_from_payload,
    job_status_from_payload,
)
from pipeline_inspector.maya.farm_job_monitor import start_farm_job_notification_poll
from pipeline_inspector.studio_config import ConnectorSettings, StudioConfig, TelegramConnectorSettings
from pipeline_inspector.integrations.notification_triggers import NOTIFY_EVENT_ON_FARM_COMPLETE


def test_job_status_from_payload_prefers_job_status_key():
    assert job_status_from_payload({"JobStatus": "Completed"}) == "Completed"


def test_job_status_from_payload_maps_deadline_stat_field():
    assert job_status_from_payload({"Stat": 3}) == "Completed"
    assert job_status_from_payload({"Stat": 1}) == "Active"


def test_job_name_from_payload_reads_nested_props_name():
    assert (
        job_name_from_payload(
            {"Props": {"Name": "Pipeline Inspector | hero.ma"}},
            fallback_job_id="job-42",
        )
        == "Pipeline Inspector | hero.ma"
    )


def test_start_farm_job_notification_poll_dispatches_on_completed(monkeypatch):
    calls: list[str] = []

    class FakeClient:
        def get_job(self, job_id: str) -> dict[str, Any]:
            calls.append(job_id)
            return {"JobStatus": "Completed", "JobName": "hero_render"}

    def fake_factory(_config: DeadlineConfig) -> FakeClient:
        return FakeClient()

    dispatched: list[tuple[str, str]] = []

    monkeypatch.setattr(
        "pipeline_inspector.maya.farm_job_monitor.dispatch_farm_notifications",
        lambda _studio, context: (
            dispatched.append((context.job_id, context.status)),
            __import__(
                "pipeline_inspector.integrations.notify.dispatcher",
                fromlist=["ValidationNotificationDispatchResult"],
            ).ValidationNotificationDispatchResult(outcomes=()),
        )[1],
    )
    monkeypatch.setattr(
        "pipeline_inspector.maya.farm_job_monitor.report_validation_notification_outcomes",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr("pipeline_inspector.maya.farm_job_monitor.time.sleep", lambda _seconds: None)

    studio = StudioConfig(
        connectors=ConnectorSettings(
            telegram=TelegramConnectorSettings(
                enabled=True,
                bot_token="token",
                chat_id="123",
                notify_on=(NOTIFY_EVENT_ON_FARM_COMPLETE,),
            )
        )
    )
    start_farm_job_notification_poll(
        config=DeadlineConfig(),
        studio_config=studio,
        job_id="job-42",
        client_factory=fake_factory,
    )
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and not dispatched:
        time.sleep(0.05)
    assert calls == ["job-42"]
    assert dispatched == [("job-42", "Completed")]
