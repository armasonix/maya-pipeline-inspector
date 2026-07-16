"""Aggregate Deadline farm analytics from Web Service job and pool reads."""
from __future__ import annotations

import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pipeline_inspector.integrations.deadline.analytics_history import append_farm_analytics_history
from pipeline_inspector.integrations.deadline.client import DeadlineClient
from pipeline_inspector.integrations.deadline.job_keys import (
    pass_label_from_job,
    scene_path_hint_from_job,
    shot_key_from_job,
)
from pipeline_inspector.integrations.deadline.job_payload import (
    average_frame_render_seconds_from_statistics,
    job_completion_epoch_seconds,
    job_error_count,
    job_frame_count,
    job_group_from_payload,
    job_name_from_payload,
    job_plugin_from_payload,
    job_pool_from_payload,
    job_start_epoch_seconds,
    job_status_from_payload,
    job_submit_epoch_seconds,
    job_user_from_payload,
    render_time_seconds_from_statistics,
    task_frame_number,
    task_is_completed,
    task_is_failed,
    task_render_time_seconds,
    worker_is_rendering,
)

_DEFAULT_ANALYTICS_STATES = ("Completed", "Failed", "Active")
_BACKLOG_STATES = ("Pending", "Suspended")
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
class FarmBreakdownRow:
    """One row in a farm operations breakdown table."""

    label: str
    job_count: int
    failure_rate: float
    average_render_seconds: float


@dataclass(frozen=True)
class FarmFailedJobRow:
    """A failed or high-error job surfaced for supervisors."""

    job_id: str
    job_name: str
    pool: str
    status: str
    error_count: int


@dataclass(frozen=True)
class FarmOperationsMetrics:
    """Tier A operational farm metrics."""

    average_queue_wait_seconds: float
    average_wall_clock_seconds: float
    render_efficiency: float
    average_task_error_rate: float
    pending_jobs: int
    suspended_jobs: int
    breakdowns: Mapping[str, tuple[FarmBreakdownRow, ...]]
    top_failed_jobs: tuple[FarmFailedJobRow, ...]


@dataclass(frozen=True)
class FarmFrameEconomics:
    """Tier B per-frame render economics."""

    median_frame_render_seconds: float
    p95_frame_render_seconds: float
    failed_frame_count: int
    completed_frame_count: int
    sampled_job_count: int
    slowest_frames: tuple[tuple[int, float, str], ...]


@dataclass(frozen=True)
class FarmPassMixEntry:
    """Render-pass time grouped by studio naming convention."""

    pass_label: str
    job_count: int
    total_render_seconds: float


@dataclass(frozen=True)
class FarmRerenderWatchEntry:
    """Shot with multiple submits or a failed predecessor."""

    shot_key: str
    submit_count: int
    had_prior_failure: bool
    latest_status: str
    scene_path_hint: str


@dataclass(frozen=True)
class FarmShotIntelligence:
    """Tier C shot-centric intelligence derived from job metadata."""

    pass_mix: tuple[FarmPassMixEntry, ...]
    rerender_watchlist: tuple[FarmRerenderWatchEntry, ...]
    rerender_rate: float
    validation_linked_jobs: int


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
    operations: FarmOperationsMetrics | None = None
    frame_economics: FarmFrameEconomics | None = None
    shot_intelligence: FarmShotIntelligence | None = None
    history_path: str = ""


def collect_farm_analytics(
    client: DeadlineClient,
    *,
    pool_filter: str | None = None,
    states: Sequence[str] = _DEFAULT_ANALYTICS_STATES,
    window_hours: float = 24.0,
    max_statistics_jobs: int = 25,
    max_frame_sample_jobs: int = 10,
    max_tasks_per_job: int = 500,
    shot_key_pattern: str | None = None,
    history_path: str | Path | None = None,
) -> FarmAnalyticsReport:
    """Collect farm health, operations, frame, and shot-centric analytics."""

    pattern = re.compile(shot_key_pattern) if shot_key_pattern else None
    jobs = client.list_jobs(states=states)
    backlog_jobs = client.list_jobs(states=_BACKLOG_STATES)
    totals = _job_totals(jobs)
    completed_jobs = [job for job in jobs if _normalized_status(job) in _COMPLETED_STATUSES]
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
    operations = _collect_operations_metrics(jobs, backlog_jobs)
    frame_economics = _collect_frame_economics(
        client,
        completed_jobs,
        max_frame_sample_jobs=max_frame_sample_jobs,
        max_tasks_per_job=max_tasks_per_job,
    )
    shot_intelligence = _collect_shot_intelligence(
        jobs,
        completed_jobs,
        pattern=pattern,
    )

    report = FarmAnalyticsReport(
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
        operations=operations,
        frame_economics=frame_economics,
        shot_intelligence=shot_intelligence,
        history_path=str(history_path or ""),
    )
    if history_path:
        append_farm_analytics_history(history_path, farm_analytics_to_dict(report))
    return report


def format_farm_analytics_summary(report: FarmAnalyticsReport) -> str:
    """Return a compact human-readable analytics summary."""

    totals = report.job_totals
    metrics = report.metrics
    throughput_note = " (estimated)" if report.throughput_estimated else ""
    pool_lines = ", ".join(
        f"{name}={metrics.pool_utilization.get(name, 0.0):.0%}"
        for name in report.pools
    ) or "n/a"
    parts = [
        f"Farm analytics ({totals.total_jobs} jobs): "
        f"throughput={metrics.throughput_jobs_per_hour:.2f}/h{throughput_note}, "
        f"failure_rate={metrics.failure_rate:.1%}, "
        f"avg_render={metrics.average_render_time_seconds:.1f}s "
        f"(n={report.statistics_sample_size}), "
        f"pools=[{pool_lines}]",
    ]
    if report.operations is not None:
        parts.append(
            "ops="
            f"queue={report.operations.average_queue_wait_seconds:.0f}s, "
            f"eff={report.operations.render_efficiency:.0%}, "
            f"pending={report.operations.pending_jobs}, "
            f"suspended={report.operations.suspended_jobs}"
        )
    if report.frame_economics is not None:
        frame = report.frame_economics
        parts.append(
            "frames="
            f"p50={frame.median_frame_render_seconds:.1f}s, "
            f"p95={frame.p95_frame_render_seconds:.1f}s"
        )
    if report.shot_intelligence is not None:
        shot = report.shot_intelligence
        parts.append(
            f"rerender_rate={shot.rerender_rate:.0%}, "
            f"watchlist={len(shot.rerender_watchlist)}"
        )
    return " ".join(parts)


def farm_analytics_to_dict(report: FarmAnalyticsReport) -> dict[str, Any]:
    """Serialize a farm analytics report for JSON APIs and CLI output."""

    metrics = report.metrics
    totals = report.job_totals
    payload: dict[str, Any] = {
        "collected_at_epoch": report.collected_at_epoch,
        "window_hours": report.window_hours,
        "throughput_estimated": report.throughput_estimated,
        "statistics_sample_size": report.statistics_sample_size,
        "history_path": report.history_path,
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
    if report.operations is not None:
        payload["operations"] = _operations_to_dict(report.operations)
    if report.frame_economics is not None:
        payload["frame_economics"] = _frame_economics_to_dict(report.frame_economics)
    if report.shot_intelligence is not None:
        payload["shot_intelligence"] = _shot_intelligence_to_dict(report.shot_intelligence)
    return payload


def _operations_to_dict(operations: FarmOperationsMetrics) -> dict[str, Any]:
    return {
        "average_queue_wait_seconds": operations.average_queue_wait_seconds,
        "average_wall_clock_seconds": operations.average_wall_clock_seconds,
        "render_efficiency": operations.render_efficiency,
        "average_task_error_rate": operations.average_task_error_rate,
        "pending_jobs": operations.pending_jobs,
        "suspended_jobs": operations.suspended_jobs,
        "breakdowns": {
            key: [
                {
                    "label": row.label,
                    "job_count": row.job_count,
                    "failure_rate": row.failure_rate,
                    "average_render_seconds": row.average_render_seconds,
                }
                for row in rows
            ]
            for key, rows in operations.breakdowns.items()
        },
        "top_failed_jobs": [
            {
                "job_id": row.job_id,
                "job_name": row.job_name,
                "pool": row.pool,
                "status": row.status,
                "error_count": row.error_count,
            }
            for row in operations.top_failed_jobs
        ],
    }


def _frame_economics_to_dict(frame: FarmFrameEconomics) -> dict[str, Any]:
    return {
        "median_frame_render_seconds": frame.median_frame_render_seconds,
        "p95_frame_render_seconds": frame.p95_frame_render_seconds,
        "failed_frame_count": frame.failed_frame_count,
        "completed_frame_count": frame.completed_frame_count,
        "sampled_job_count": frame.sampled_job_count,
        "slowest_frames": [
            {"frame": frame_number, "seconds": seconds, "job_id": job_id}
            for frame_number, seconds, job_id in frame.slowest_frames
        ],
    }


def _shot_intelligence_to_dict(shot: FarmShotIntelligence) -> dict[str, Any]:
    return {
        "pass_mix": [
            {
                "pass_label": entry.pass_label,
                "job_count": entry.job_count,
                "total_render_seconds": entry.total_render_seconds,
            }
            for entry in shot.pass_mix
        ],
        "rerender_watchlist": [
            {
                "shot_key": entry.shot_key,
                "submit_count": entry.submit_count,
                "had_prior_failure": entry.had_prior_failure,
                "latest_status": entry.latest_status,
                "scene_path_hint": entry.scene_path_hint,
            }
            for entry in shot.rerender_watchlist
        ],
        "rerender_rate": shot.rerender_rate,
        "validation_linked_jobs": shot.validation_linked_jobs,
    }


def _collect_operations_metrics(
    jobs: Sequence[dict[str, Any]],
    backlog_jobs: Sequence[dict[str, Any]],
) -> FarmOperationsMetrics:
    queue_waits: list[float] = []
    wall_clocks: list[float] = []
    render_totals: list[float] = []
    task_error_rates: list[float] = []

    for job in jobs:
        submit_at = job_submit_epoch_seconds(job)
        start_at = job_start_epoch_seconds(job)
        complete_at = job_completion_epoch_seconds(job)
        if submit_at is not None and start_at is not None and start_at >= submit_at:
            queue_waits.append(start_at - submit_at)
        if start_at is not None and complete_at is not None and complete_at >= start_at:
            wall = complete_at - start_at
            wall_clocks.append(wall)
            render_seconds = duration_fallback_from_job(job)
            if render_seconds is not None and wall > 0:
                render_totals.append(min(render_seconds, wall))
        frame_count = max(job_frame_count(job), 1)
        task_error_rates.append(job_error_count(job) / frame_count)

    pending = sum(1 for job in backlog_jobs if _normalized_status(job) in {"pending", "6"})
    suspended = sum(1 for job in backlog_jobs if _normalized_status(job) in {"suspended", "2"})
    avg_queue = _average(queue_waits)
    avg_wall = _average(wall_clocks)
    avg_render = _average(render_totals)
    efficiency = (avg_render / avg_wall) if avg_wall > 0 else 0.0

    return FarmOperationsMetrics(
        average_queue_wait_seconds=avg_queue,
        average_wall_clock_seconds=avg_wall,
        render_efficiency=min(max(efficiency, 0.0), 1.0),
        average_task_error_rate=_average(task_error_rates),
        pending_jobs=pending,
        suspended_jobs=suspended,
        breakdowns=_build_breakdowns(jobs),
        top_failed_jobs=_top_failed_jobs(jobs),
    )


def _collect_frame_economics(
    client: DeadlineClient,
    completed_jobs: Sequence[dict[str, Any]],
    *,
    max_frame_sample_jobs: int,
    max_tasks_per_job: int,
) -> FarmFrameEconomics:
    frame_times: list[float] = []
    slowest: list[tuple[int, float, str]] = []
    failed_frames = 0
    completed_frames = 0
    sampled_jobs = 0

    for job in completed_jobs[: max(max_frame_sample_jobs, 0)]:
        job_id = str(job.get("_id") or job.get("JobID") or "").strip()
        if not job_id:
            continue
        sampled_jobs += 1
        try:
            statistics = client.get_job_statistics(job_id)
        except Exception:
            statistics = {}
        average_frame = average_frame_render_seconds_from_statistics(statistics)
        if average_frame is not None:
            frame_times.append(average_frame)
        try:
            tasks = client.list_tasks(job_id)
        except Exception:
            tasks = []
        for task in tasks[: max(max_tasks_per_job, 0)]:
            if task_is_failed(task):
                failed_frames += 1
            elif task_is_completed(task):
                completed_frames += 1
            seconds = task_render_time_seconds(task)
            frame_number = task_frame_number(task)
            if seconds is None or frame_number is None:
                continue
            frame_times.append(seconds)
            slowest.append((frame_number, seconds, job_id))

    slowest.sort(key=lambda item: item[1], reverse=True)
    return FarmFrameEconomics(
        median_frame_render_seconds=_percentile(frame_times, 0.5),
        p95_frame_render_seconds=_percentile(frame_times, 0.95),
        failed_frame_count=failed_frames,
        completed_frame_count=completed_frames,
        sampled_job_count=sampled_jobs,
        slowest_frames=tuple(slowest[:5]),
    )


def _collect_shot_intelligence(
    jobs: Sequence[dict[str, Any]],
    completed_jobs: Sequence[dict[str, Any]],
    *,
    pattern: re.Pattern[str] | None,
) -> FarmShotIntelligence:
    pass_totals: dict[str, tuple[int, float]] = {}
    shot_groups: dict[str, list[dict[str, Any]]] = {}
    validation_linked = 0

    render_lookup = {
        str(job.get("_id") or job.get("JobID") or ""): render_time_seconds_from_statistics(job)
        or duration_fallback_from_job(job)
        or 0.0
        for job in completed_jobs
    }

    for job in jobs:
        pass_label = pass_label_from_job(job)
        job_id = str(job.get("_id") or job.get("JobID") or "")
        render_seconds = render_lookup.get(job_id, 0.0)
        count, total = pass_totals.get(pass_label, (0, 0.0))
        pass_totals[pass_label] = (count + 1, total + render_seconds)

        shot_key = shot_key_from_job(job, pattern=pattern)
        if shot_key:
            shot_groups.setdefault(shot_key, []).append(job)

        haystack = job_name_from_payload(job, fallback_job_id=job_id).casefold()
        if "pipeline inspector" in haystack or scene_path_hint_from_job(job):
            validation_linked += 1

    pass_mix = tuple(
        FarmPassMixEntry(pass_label=label, job_count=count, total_render_seconds=total)
        for label, (count, total) in sorted(pass_totals.items())
    )

    watchlist: list[FarmRerenderWatchEntry] = []
    keyed_jobs = 0
    rerender_jobs = 0
    for shot_key, group in sorted(shot_groups.items()):
        ordered = sorted(
            group,
            key=lambda job: job_submit_epoch_seconds(job) or job_completion_epoch_seconds(job) or 0.0,
        )
        keyed_jobs += len(ordered)
        if len(ordered) < 2:
            continue
        rerender_jobs += len(ordered)
        statuses = [job_status_from_payload(job) for job in ordered]
        had_prior_failure = any(status.casefold() == "failed" for status in statuses[:-1])
        latest_status = statuses[-1]
        watchlist.append(
            FarmRerenderWatchEntry(
                shot_key=shot_key,
                submit_count=len(ordered),
                had_prior_failure=had_prior_failure,
                latest_status=latest_status,
                scene_path_hint=scene_path_hint_from_job(ordered[-1]),
            )
        )

    rerender_rate = (rerender_jobs / keyed_jobs) if keyed_jobs else 0.0
    watchlist.sort(key=lambda entry: entry.submit_count, reverse=True)
    return FarmShotIntelligence(
        pass_mix=pass_mix,
        rerender_watchlist=tuple(watchlist[:10]),
        rerender_rate=rerender_rate,
        validation_linked_jobs=validation_linked,
    )


def duration_fallback_from_job(job: dict[str, Any]) -> float | None:
    """Estimate render seconds from job timestamps when statistics are absent."""

    start_at = job_start_epoch_seconds(job)
    complete_at = job_completion_epoch_seconds(job)
    if start_at is None or complete_at is None or complete_at < start_at:
        return None
    return complete_at - start_at


def _build_breakdowns(jobs: Sequence[dict[str, Any]]) -> dict[str, tuple[FarmBreakdownRow, ...]]:
    breakdowns: dict[str, tuple[FarmBreakdownRow, ...]] = {}
    resolvers = {
        "pool": job_pool_from_payload,
        "group": job_group_from_payload,
        "plugin": job_plugin_from_payload,
        "user": job_user_from_payload,
    }
    for dimension, resolver in resolvers.items():
        grouped: dict[str, list[dict[str, Any]]] = {}
        for job in jobs:
            label = resolver(job) or "unknown"
            grouped.setdefault(label, []).append(job)
        rows = []
        for label, group in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
            completed = sum(1 for job in group if _normalized_status(job) in _COMPLETED_STATUSES)
            failed = sum(1 for job in group if _normalized_status(job) in _FAILED_STATUSES)
            render_seconds = [
                value
                for value in (duration_fallback_from_job(job) for job in group)
                if value is not None
            ]
            rows.append(
                FarmBreakdownRow(
                    label=label,
                    job_count=len(group),
                    failure_rate=_failure_rate(completed, failed),
                    average_render_seconds=_average(render_seconds),
                )
            )
        breakdowns[dimension] = tuple(rows[:8])
    return breakdowns


def _top_failed_jobs(jobs: Sequence[dict[str, Any]]) -> tuple[FarmFailedJobRow, ...]:
    candidates: list[FarmFailedJobRow] = []
    for job in jobs:
        status = job_status_from_payload(job)
        errors = job_error_count(job)
        if status.casefold() != "failed" and errors <= 0:
            continue
        job_id = str(job.get("_id") or job.get("JobID") or "")
        candidates.append(
            FarmFailedJobRow(
                job_id=job_id,
                job_name=job_name_from_payload(job, fallback_job_id=job_id),
                pool=job_pool_from_payload(job) or "unknown",
                status=status,
                error_count=errors,
            )
        )
    candidates.sort(key=lambda row: (row.error_count, row.job_name), reverse=True)
    return tuple(candidates[:8])


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


def _average(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * percentile))
    return ordered[max(0, min(index, len(ordered) - 1))]
