from __future__ import annotations

import time

from pipeline_inspector.integrations.deadline.analytics import collect_farm_analytics
from pipeline_inspector.integrations.deadline.client import (
    DeadlineClient,
    DeadlineConfig,
    DeadlineResponse,
    HttpRequest,
)
from pipeline_inspector.integrations.deadline.job_payload import (
    duration_seconds_from_value,
    job_completion_epoch_seconds,
    render_time_seconds_from_statistics,
    worker_is_rendering,
)


def test_deadline_client_list_jobs_by_state():
    def transport(request: HttpRequest, timeout: float) -> DeadlineResponse:
        assert request.url == "http://farm:8082/api/jobs?States=Completed%2CFailed"
        return DeadlineResponse(
            status_code=200,
            body="[]",
            json_data=[
                {"_id": "job-1", "Stat": 3},
                {"_id": "job-2", "Stat": 4},
            ],
        )

    client = DeadlineClient(DeadlineConfig(api_url="http://farm:8082"), transport=transport)
    jobs = client.list_jobs(states=("Completed", "Failed"))
    assert len(jobs) == 2
    assert jobs[0]["_id"] == "job-1"


def test_deadline_client_get_job_statistics():
    def transport(request: HttpRequest, timeout: float) -> DeadlineResponse:
        assert request.url == "http://farm:8082/api/jobs?JobID=job-9&Statistics=true"
        return DeadlineResponse(
            status_code=200,
            body="{}",
            json_data={"TotalRenderTime": "00:10:00"},
        )

    client = DeadlineClient(DeadlineConfig(api_url="http://farm:8082"), transport=transport)
    stats = client.get_job_statistics("job-9")
    assert stats["TotalRenderTime"] == "00:10:00"


def test_deadline_client_list_pools_and_workers():
    calls: list[str] = []

    def transport(request: HttpRequest, timeout: float) -> DeadlineResponse:
        calls.append(request.url)
        if request.url.endswith("/api/pools"):
            return DeadlineResponse(status_code=200, body="[]", json_data=["lookdev", "utility"])
        if "Pool=lookdev" in request.url:
            return DeadlineResponse(
                status_code=200,
                body="[]",
                json_data=["worker-a", "worker-b"],
            )
        if "Data=info" in request.url:
            return DeadlineResponse(
                status_code=200,
                body="[]",
                json_data=[
                    {"Name": "worker-a", "SlaveRendering": True},
                    {"Name": "worker-b", "SlaveRendering": False},
                ],
            )
        raise AssertionError(request.url)

    client = DeadlineClient(DeadlineConfig(api_url="http://farm:8082"), transport=transport)
    assert client.list_pool_names() == ["lookdev", "utility"]
    assert client.list_pool_workers(["lookdev"]) == ["worker-a", "worker-b"]
    assert worker_is_rendering(client.list_workers_info()[0]) is True


def test_job_payload_parsers():
    assert duration_seconds_from_value("01:30:00") == 5400.0
    assert render_time_seconds_from_statistics({"TotalRenderTime": 120}) == 120.0
    completed_at = job_completion_epoch_seconds(
        {"Props": {"DateComp": "Jul 16 2026 10:00:00"}}
    )
    assert completed_at is not None


def test_collect_farm_analytics_aggregates_metrics(monkeypatch):
    now = time.time()

    def transport(request: HttpRequest, timeout: float) -> DeadlineResponse:
        if "States=Completed%2CFailed%2CActive" in request.url:
            return DeadlineResponse(
                status_code=200,
                body="[]",
                json_data=[
                    {
                        "_id": "job-ok",
                        "Stat": 3,
                        "Props": {
                            "DateComp": time.strftime(
                                "%b %d %Y %H:%M:%S",
                                time.gmtime(now - 1800),
                            )
                        },
                    },
                    {"_id": "job-bad", "Stat": 4},
                    {"_id": "job-live", "Stat": 1},
                ],
            )
        if "Statistics=true" in request.url and "job-ok" in request.url:
            return DeadlineResponse(
                status_code=200,
                body="{}",
                json_data={"TotalRenderTime": 600},
            )
        if request.url.endswith("/api/pools"):
            return DeadlineResponse(status_code=200, body="[]", json_data=["lookdev"])
        if "Pool=lookdev" in request.url:
            return DeadlineResponse(status_code=200, body="[]", json_data=["worker-a"])
        if "Data=info" in request.url:
            return DeadlineResponse(
                status_code=200,
                body="[]",
                json_data=[{"Name": "worker-a", "SlaveRendering": True}],
            )
        raise AssertionError(request.url)

    client = DeadlineClient(DeadlineConfig(api_url="http://farm:8082"), transport=transport)
    report = collect_farm_analytics(client, window_hours=1.0)

    assert report.job_totals.completed_jobs == 1
    assert report.job_totals.failed_jobs == 1
    assert report.job_totals.active_jobs == 1
    assert report.metrics.failure_rate == 0.5
    assert report.metrics.throughput_jobs_per_hour == 1.0
    assert report.throughput_estimated is False
    assert report.metrics.average_render_time_seconds == 600.0
    assert report.metrics.pool_utilization["lookdev"] == 1.0
