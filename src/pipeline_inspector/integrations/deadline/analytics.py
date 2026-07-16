"""Aggregate Deadline farm analytics from Web Service job and pool reads."""
from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from pipeline_inspector.integrations.deadline.client import DeadlineClient
from pipeline_inspector.integrations.deadline.job_payload import (
    job_completion_epoch_seconds,
    job_status_from_payload,
    render_time_seconds_from_statistics,
    worker_is_rendering,
)

_DEFAULT_ANALYTICS_STATES = ("Completed", "Failed", "Active")
_COMPLETED_STATUSES = frozenset({"completed", "3"})
_FAILED_STATUSES = frozenset({"failed", "4"})
_ACTIVE_STATUSES = frozenset({"active", "1", "queued", "rendering"})


@dataclass(frozen=True)
class FarmJobTotals:
    """Raw job counts used to derive farm analytics."""

    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    active_jobs: int


@dataclass(frozen=True)
class FarmAnalyticsMetrics:
    """Derived farm analytics metrics."""

    throughput_jobs_per_hour: float
    failure_rate: float
    average_render_time_seconds: float
    pool_utilization: Mapping[str, float]


@dataclass(frozen=True)
class FarmAnalyticsReport:
    """Snapshot of Deadline farm analytics."""

    metrics: FarmAnalyticsMetrics
    job_totals: FarmJobTotals
    pools: tuple[str, ...]
    window_hours: float
    throughput_estimated: bool
    statistics_sample_size: int
    collected_at_epoch: float = field(default_factory=lambda: time.time())


def collect_farm_analytics(
    client: DeadlineClient,
    *,
    pool_filter: str | None = None,
    states: Sequence[str] = _DEFAULT_ANALYTICS_STATES,
    window_hours: float = 24.0,
    max_statistics_jobs: int = 25,
) -> FarmAnalyticsReport:
    """Collect throughput, failure, render-time, and pool utilization metrics."""

    jobs = client.list_jobs(states=states)
    totals = _job_totals(jobs)
    completed_jobs = [
        job
        for job in jobs
        if _normalized_status(job) in _COMPLETED_STATUSES
    ]
    throughput, throughput_estimated = _throughput_jobs_per_hour(
        completed_jobs,
        window_hours=window_hours,
        fallback_completed_count=totals.completed_jobs,
    )
    failure_rate = _failure_rate(totals.completed_jobs, totals.failed_jobs)
    average_render_time, sample_size = _average_render_time_seconds(
        client,
        completed_jobs,
        max_statistics_jobs=max_statistics_jobs,
    )
    pool_names = _resolve_pool_names(client, pool_filter=pool_filter)
    pool_utilization = _pool_utilization(client, pool_names)

    return FarmAnalyticsReport(
        metrics=FarmAnalyticsMetrics(
            throughput_jobs_per_hour=throughput,
            failure_rate=failure_rate,
            average_render_time_seconds=average_render_time,
            pool_utilization=pool_utilization,
        ),
        job_totals=totals,
        pools=tuple(pool_names),
        window_hours=window_hours,
        throughput_estimated=throughput_estimated,
        statistics_sample_size=sample_size,
    )


def format_farm_analytics_summary(report: FarmAnalyticsReport) -> str:
    """Return a compact human-readable analytics summary."""

    totals = report.job_totals
    metrics = report.metrics
    throughput_note = " (estimated)" if report.throughput_estimated else ""
    pool_lines = ", ".join(
        f"{name}={metrics.pool_utilization.get(name, 0.0):.0%}"
        for name in report.pools
    ) or "n/a"
    return (
        f"Farm analytics ({totals.total_jobs} jobs): "
        f"throughput={metrics.throughput_jobs_per_hour:.2f}/h{throughput_note}, "
        f"failure_rate={metrics.failure_rate:.1%}, "
        f"avg_render={metrics.average_render_time_seconds:.1f}s "
        f"(n={report.statistics_sample_size}), "
        f"pools=[{pool_lines}]"
    )


def farm_analytics_to_dict(report: FarmAnalyticsReport) -> dict[str, Any]:
    """Serialize a farm analytics report for JSON APIs and CLI output."""

    metrics = report.metrics
    totals = report.job_totals
    return {
        "collected_at_epoch": report.collected_at_epoch,
        "window_hours": report.window_hours,
        "throughput_estimated": report.throughput_estimated,
        "statistics_sample_size": report.statistics_sample_size,
        "pools": list(report.pools),
        "job_totals": {
            "total_jobs": totals.total_jobs,
            "completed_jobs": totals.completed_jobs,
            "failed_jobs": totals.failed_jobs,
            "active_jobs": totals.active_jobs,
        },
        "metrics": {
            "throughput_jobs_per_hour": metrics.throughput_jobs_per_hour,
            "failure_rate": metrics.failure_rate,
            "average_render_time_seconds": metrics.average_render_time_seconds,
            "pool_utilization": dict(metrics.pool_utilization),
        },
    }


def _job_totals(jobs: Sequence[dict[str, Any]]) -> FarmJobTotals:
    completed = failed = active = 0
    for job in jobs:
        status = _normalized_status(job)
        if status in _COMPLETED_STATUSES:
            completed += 1
        elif status in _FAILED_STATUSES:
            failed += 1
        elif status in _ACTIVE_STATUSES:
            active += 1
    return FarmJobTotals(
        total_jobs=len(jobs),
        completed_jobs=completed,
        failed_jobs=failed,
        active_jobs=active,
    )


def _normalized_status(job: dict[str, Any]) -> str:
    return job_status_from_payload(job).casefold()


def _throughput_jobs_per_hour(
    completed_jobs: Sequence[dict[str, Any]],
    *,
    window_hours: float,
    fallback_completed_count: int,
) -> tuple[float, bool]:
    safe_window = max(window_hours, 0.01)
    now = time.time()
    window_seconds = safe_window * 3600.0
    recent = 0
    dated = 0
    for job in completed_jobs:
        completed_at = job_completion_epoch_seconds(job)
        if completed_at is None:
            continue
        dated += 1
        if now - completed_at <= window_seconds:
            recent += 1
    if dated > 0:
        return recent / safe_window, False
    return fallback_completed_count / safe_window, True


def _failure_rate(completed_jobs: int, failed_jobs: int) -> float:
    denominator = completed_jobs + failed_jobs
    if denominator <= 0:
        return 0.0
    return failed_jobs / denominator


def _average_render_time_seconds(
    client: DeadlineClient,
    completed_jobs: Sequence[dict[str, Any]],
    *,
    max_statistics_jobs: int,
) -> tuple[float, int]:
    sample_limit = max(max_statistics_jobs, 0)
    if sample_limit == 0 or not completed_jobs:
        return 0.0, 0

    render_times: list[float] = []
    for job in completed_jobs[:sample_limit]:
        job_id = str(job.get("_id") or job.get("JobID") or "").strip()
        if not job_id:
            continue
        try:
            statistics = client.get_job_statistics(job_id)
        except Exception:
            continue
        render_seconds = render_time_seconds_from_statistics(statistics)
        if render_seconds is not None and render_seconds >= 0:
            render_times.append(render_seconds)

    if not render_times:
        return 0.0, 0
    return sum(render_times) / len(render_times), len(render_times)


def _resolve_pool_names(
    client: DeadlineClient,
    *,
    pool_filter: str | None,
) -> list[str]:
    if pool_filter:
        normalized = pool_filter.strip()
        return [normalized] if normalized else []
    return client.list_pool_names()


def _pool_utilization(
    client: DeadlineClient,
    pool_names: Sequence[str],
) -> dict[str, float]:
    if not pool_names:
        return {}

    worker_infos = {
        str(info.get("Name") or info.get("SlaveName") or ""): info
        for info in client.list_workers_info()
    }
    utilization: dict[str, float] = {}
    for pool_name in pool_names:
        workers = client.list_pool_workers([pool_name])
        if not workers:
            utilization[pool_name] = 0.0
            continue
        rendering = sum(
            1
            for worker_name in workers
            if worker_is_rendering(worker_infos.get(worker_name, {}))
        )
        utilization[pool_name] = rendering / len(workers)
    return utilization
