"""Management-facing HTML report for Deadline farm analytics."""
from __future__ import annotations

from datetime import datetime, timezone
from math import cos, radians, sin
from pathlib import Path

from pipeline_inspector.integrations.deadline.analytics import (
    FarmAnalyticsReport,
    FarmBreakdownRow,
    FarmFailedJobRow,
    FarmFrameEconomics,
    FarmOperationsMetrics,
    FarmShotIntelligence,
)
from pipeline_inspector.reports.html_report import _attr, _metric_card, _stylesheet, _text

_CHART_COLORS = {
    "completed": "#15803d",
    "failed": "#b91c1c",
    "active": "#2563eb",
    "pool": "#7c3aed",
    "throughput": "#0f766e",
}


def build_farm_html_report(
    report: FarmAnalyticsReport,
    *,
    api_url: str = "",
) -> str:
    """Build a self-contained management HTML report from farm analytics."""

    html = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{_text('Deadline Farm Intelligence Report')}</title>",
        f"<style>{_stylesheet()}</style>",
        f"<style>{_farm_chart_stylesheet()}</style>",
        "</head>",
        "<body>",
        '<div class="page">',
        _render_header(report, api_url=api_url),
        _render_kpi_section(report),
        _render_kpi_visual_dashboard(report),
        _render_operations_section(report.operations),
        _render_frame_economics_section(report.frame_economics),
        _render_shot_intelligence_section(report.shot_intelligence),
        _render_history_note(report),
        _render_footer(report),
        "</div>",
        "</body>",
        "</html>",
    ]
    return "\n".join(html) + "\n"


def write_farm_html_report(
    path: str | Path,
    report: FarmAnalyticsReport,
    *,
    api_url: str = "",
) -> Path:
    """Write a management farm HTML report and return the output path."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        build_farm_html_report(report, api_url=api_url),
        encoding="utf-8",
    )
    return output_path


def sample_farm_analytics_report() -> FarmAnalyticsReport:
    """Return a deterministic sample report for docs and tests."""

    from pipeline_inspector.integrations.deadline.analytics import (
        FarmAnalyticsMetrics,
        FarmBreakdownRow,
        FarmFailedJobRow,
        FarmFrameEconomics,
        FarmJobTotals,
        FarmOperationsMetrics,
        FarmPassMixEntry,
        FarmRerenderWatchEntry,
        FarmShotIntelligence,
    )

    return FarmAnalyticsReport(
        metrics=FarmAnalyticsMetrics(
            throughput_jobs_per_hour=4.5,
            failure_rate=0.12,
            average_render_time_seconds=1860.0,
            pool_utilization={"lookdev": 0.67, "utility": 0.25},
        ),
        job_totals=FarmJobTotals(
            total_jobs=48,
            completed_jobs=32,
            failed_jobs=4,
            active_jobs=12,
        ),
        pools=("lookdev", "utility"),
        window_hours=24.0,
        throughput_estimated=False,
        statistics_sample_size=18,
        collected_at_epoch=datetime(2026, 7, 16, 9, 30, tzinfo=timezone.utc).timestamp(),
        operations=FarmOperationsMetrics(
            average_queue_wait_seconds=420.0,
            average_wall_clock_seconds=2100.0,
            render_efficiency=0.71,
            average_task_error_rate=0.03,
            pending_jobs=3,
            suspended_jobs=1,
            breakdowns={
                "pool": (
                    FarmBreakdownRow("lookdev", 30, 0.08, 1800.0),
                    FarmBreakdownRow("utility", 18, 0.18, 900.0),
                ),
                "plugin": (FarmBreakdownRow("MayaBatch", 40, 0.10, 1500.0),),
            },
            top_failed_jobs=(
                FarmFailedJobRow(
                    job_id="job-bad-1",
                    job_name="show_seq010_sh010_beauty",
                    pool="lookdev",
                    status="Failed",
                    error_count=6,
                ),
            ),
        ),
        frame_economics=FarmFrameEconomics(
            median_frame_render_seconds=92.0,
            p95_frame_render_seconds=184.0,
            failed_frame_count=2,
            completed_frame_count=118,
            sampled_job_count=6,
            slowest_frames=((1042, 312.0, "job-slow"), (1043, 288.0, "job-slow")),
        ),
        shot_intelligence=FarmShotIntelligence(
            pass_mix=(
                FarmPassMixEntry("beauty", 20, 28800.0),
                FarmPassMixEntry("matte", 8, 7200.0),
                FarmPassMixEntry("other", 4, 1800.0),
            ),
            rerender_watchlist=(
                FarmRerenderWatchEntry(
                    shot_key="show_seq010_sh010",
                    submit_count=3,
                    had_prior_failure=True,
                    latest_status="Completed",
                    scene_path_hint="show_seq010_sh010.ma",
                ),
            ),
            rerender_rate=0.25,
            validation_linked_jobs=5,
        ),
    )


def _render_header(report: FarmAnalyticsReport, *, api_url: str) -> str:
    collected = _format_timestamp(report.collected_at_epoch)
    health_label = _farm_health_label(report)
    return "\n".join(
        [
            '<header class="hero">',
            '<div class="hero-top">',
            '<div class="hero-copy">',
            f"<h1>{_text('Deadline Farm Intelligence Report')}</h1>",
            '<p class="hero-subtitle">Management summary of render-farm throughput, reliability, and pool usage.</p>',
            "</div>",
            f'<div class="score-ring status-{_attr(health_label)}">',
            f'<span class="score-value">{_text(_format_percent(report.metrics.failure_rate))}</span>',
            '<span class="score-label">Failure Rate</span>',
            "</div>",
            "</div>",
            '<div class="hero-meta">',
            f'<span class="status-pill status-{_attr(health_label)}">{_text(health_label.upper())}</span>',
            f'<span class="meta-chip">Window: <strong>{_text(report.window_hours)}h</strong></span>',
            f'<span class="meta-chip">Pools: <strong>{_text(len(report.pools))}</strong></span>',
            f'<span class="meta-chip">Jobs tracked: <strong>{_text(report.job_totals.total_jobs)}</strong></span>',
            "</div>",
            '<dl class="meta-list">',
            f"<div><dt>Collected (UTC)</dt><dd>{_text(collected)}</dd></div>",
            f"<div><dt>Deadline Web Service</dt><dd>{_text(api_url or 'Configured via studio settings')}</dd></div>",
            f"<div><dt>Throughput note</dt><dd>{_text(_throughput_note(report))}</dd></div>",
            f"<div><dt>Render-time sample</dt><dd>{_text(report.statistics_sample_size)} completed jobs</dd></div>",
            "</dl>",
            "</header>",
        ]
    )


def _render_kpi_section(report: FarmAnalyticsReport) -> str:
    metrics = report.metrics
    totals = report.job_totals
    return "\n".join(
        [
            '<section class="panel" id="farm-kpis">',
            "<h2>Key Metrics</h2>",
            '<p class="panel-hint">High-level indicators for supervisors and pipeline managers.</p>',
            '<div class="metric-grid">',
            _metric_card("Throughput (jobs/hour)", f"{metrics.throughput_jobs_per_hour:.2f}"),
            _metric_card("Failure Rate", _format_percent(metrics.failure_rate)),
            _metric_card("Avg Render Time", _format_duration(metrics.average_render_time_seconds)),
            _metric_card("Active Jobs", totals.active_jobs),
            _metric_card("Completed Jobs", totals.completed_jobs),
            _metric_card("Failed Jobs", totals.failed_jobs),
            "</div>",
            "</section>",
        ]
    )


def _render_kpi_visual_dashboard(report: FarmAnalyticsReport) -> str:
    """Render the primary visual KPI dashboard directly after metric cards."""

    metrics = report.metrics
    totals = report.job_totals
    operations = report.operations
    throughput_index = min(metrics.throughput_jobs_per_hour / 10.0, 1.0)

    charts = [
        '<div class="chart-card">',
        _svg_donut_chart(
            [
                ("Completed", float(totals.completed_jobs), _CHART_COLORS["completed"]),
                ("Failed", float(totals.failed_jobs), _CHART_COLORS["failed"]),
                ("Active", float(totals.active_jobs), _CHART_COLORS["active"]),
            ],
            title="Job state mix",
            center_value=str(totals.total_jobs),
            center_label="Jobs",
        ),
        "</div>",
        '<div class="chart-card">',
        _svg_donut_chart(
            [
                ("Reliable", float(totals.completed_jobs), _CHART_COLORS["completed"]),
                ("Failed", float(totals.failed_jobs), _CHART_COLORS["failed"]),
            ],
            title="Finished reliability",
            center_value=_format_percent(max(0.0, 1.0 - metrics.failure_rate)),
            center_label="Success",
        ),
        "</div>",
        '<div class="chart-card">',
        _svg_radial_gauge(
            "Throughput",
            throughput_index,
            caption=f"{metrics.throughput_jobs_per_hour:.2f} jobs/h",
            color=_CHART_COLORS["throughput"],
        ),
        "</div>",
        '<div class="chart-card">',
        _svg_radial_gauge(
            "Failure rate",
            metrics.failure_rate,
            caption=_format_percent(metrics.failure_rate),
            color=_CHART_COLORS["failed"],
            invert_health=True,
        ),
        "</div>",
    ]

    if operations is not None:
        charts.extend(
            [
                '<div class="chart-card">',
                _svg_radial_gauge(
                    "Render efficiency",
                    operations.render_efficiency,
                    caption=_format_percent(operations.render_efficiency),
                    color=_CHART_COLORS["completed"],
                ),
                "</div>",
                '<div class="chart-card">',
                _svg_vertical_bar_chart(
                    [
                        ("Pending", float(operations.pending_jobs), _CHART_COLORS["active"]),
                        ("Suspended", float(operations.suspended_jobs), _CHART_COLORS["pool"]),
                    ],
                    title="Backlog pressure",
                ),
                "</div>",
            ]
        )

    utilization = metrics.pool_utilization
    if utilization:
        entries = [
            (pool_name, float(rate), _CHART_COLORS["pool"])
            for pool_name, rate in sorted(utilization.items())
        ]
        charts.extend(
            [
                '<div class="chart-card chart-card-span-2">',
                _svg_horizontal_bar_chart(entries, title="Pool utilization", max_value=1.0),
                "</div>",
            ]
        )

    if report.frame_economics is not None:
        frame = report.frame_economics
        charts.extend(
            [
                '<div class="chart-card chart-card-span-2">',
                _svg_vertical_bar_chart(
                    [
                        ("Median sec/frame", frame.median_frame_render_seconds, _CHART_COLORS["throughput"]),
                        ("P95 sec/frame", frame.p95_frame_render_seconds, _CHART_COLORS["active"]),
                        ("Failed frames", float(frame.failed_frame_count), _CHART_COLORS["failed"]),
                    ],
                    title="Frame cost profile",
                ),
                "</div>",
            ]
        )

    if report.shot_intelligence is not None and report.shot_intelligence.pass_mix:
        charts.extend(
            [
                '<div class="chart-card chart-card-span-2">',
                _svg_vertical_bar_chart(
                    [
                        (entry.pass_label.title(), entry.total_render_seconds, _CHART_COLORS["pool"])
                        for entry in report.shot_intelligence.pass_mix
                    ],
                    title="Pass render time (seconds)",
                ),
                "</div>",
            ]
        )

    return "\n".join(
        [
            '<section class="panel" id="farm-kpi-visuals">',
            "<h2>Farm KPI Dashboard</h2>",
            '<p class="panel-hint">Visual snapshot of throughput, reliability, utilization, and render cost.</p>',
            '<div class="chart-grid">',
            *charts,
            "</div>",
            "</section>",
        ]
    )


def _render_operations_section(operations: FarmOperationsMetrics | None) -> str:
    if operations is None:
        return ""
    breakdown_sections = []
    for dimension, rows in operations.breakdowns.items():
        if not rows:
            continue
        breakdown_sections.append(
            "\n".join(
                [
                    f"<h3>{_text(dimension.title())} Breakdown</h3>",
                    _render_breakdown_table(rows),
                ]
            )
        )
    return "\n".join(
        [
            '<section class="panel" id="farm-operations">',
            "<h2>Farm Operations Detail</h2>",
            '<p class="panel-hint">Routing breakdowns and failed-job follow-up after the KPI dashboard.</p>',
            '<dl class="meta-list">',
            f"<div><dt>Avg queue wait</dt><dd>{_text(_format_duration(operations.average_queue_wait_seconds))}</dd></div>",
            f"<div><dt>Avg wall clock</dt><dd>{_text(_format_duration(operations.average_wall_clock_seconds))}</dd></div>",
            f"<div><dt>Task error rate</dt><dd>{_text(_format_percent(operations.average_task_error_rate))}</dd></div>",
            "</dl>",
            *breakdown_sections,
            "<h3>Top Failed Jobs</h3>",
            _render_failed_jobs_table(operations.top_failed_jobs),
            "</section>",
        ]
    )


def _render_frame_economics_section(frame: FarmFrameEconomics | None) -> str:
    if frame is None:
        return ""
    slowest_rows = "".join(
        (
            "<tr>"
            f"<td class='mono'>{_text(job_id)}</td>"
            f"<td class='mono'>{_text(frame_number)}</td>"
            f"<td>{_text(_format_duration(seconds))}</td>"
            "</tr>"
            for frame_number, seconds, job_id in frame.slowest_frames
        )
    ) or "<tr><td colspan='3' class='muted'>No slow-frame samples in this window.</td></tr>"
    return "\n".join(
        [
            '<section class="panel" id="frame-economics">',
            "<h2>Frame Economics Detail</h2>",
            '<p class="panel-hint">Slowest frames and per-task samples behind the dashboard chart.</p>',
            '<div class="metric-grid">',
            _metric_card("Median sec/frame", f"{frame.median_frame_render_seconds:.1f}"),
            _metric_card("P95 sec/frame", f"{frame.p95_frame_render_seconds:.1f}"),
            _metric_card("Sampled Jobs", frame.sampled_job_count),
            _metric_card("Failed Frames", frame.failed_frame_count),
            "</div>",
            '<div class="table-wrap"><table class="results">',
            "<thead><tr><th>Job</th><th>Frame</th><th>Render Time</th></tr></thead>",
            f"<tbody>{slowest_rows}</tbody>",
            "</table></div>",
            "</section>",
        ]
    )


def _render_shot_intelligence_section(shot: FarmShotIntelligence | None) -> str:
    if shot is None:
        return ""
    watchlist_rows = "".join(
        
            "<tr>"
            f"<td class='mono'>{_text(entry.shot_key)}</td>"
            f"<td>{_text(entry.submit_count)}</td>"
            f"<td>{_text('yes' if entry.had_prior_failure else 'no')}</td>"
            f"<td>{_text(entry.latest_status)}</td>"
            f"<td class='mono'>{_text(entry.scene_path_hint or 'n/a')}</td>"
            "</tr>"
            for entry in shot.rerender_watchlist
        
    ) or "<tr><td colspan='5' class='muted'>No repeated shot submits detected in this window.</td></tr>"
    return "\n".join(
        [
            '<section class="panel" id="shot-intelligence">',
            "<h2>Shot Intelligence Detail</h2>",
            '<p class="panel-hint">Repeated submits and validation-linked jobs behind the pass chart.</p>',
            '<div class="metric-grid">',
            _metric_card("Rerender Rate", _format_percent(shot.rerender_rate)),
            _metric_card("Watchlist Shots", len(shot.rerender_watchlist)),
            _metric_card("Validation-linked Jobs", shot.validation_linked_jobs),
            "</div>",
            '<div class="table-wrap"><table class="results">',
            "<thead><tr><th>Shot</th><th>Submits</th><th>Prior Fail</th><th>Latest</th><th>Scene Hint</th></tr></thead>",
            f"<tbody>{watchlist_rows}</tbody>",
            "</table></div>",
            "</section>",
        ]
    )


def _render_history_note(report: FarmAnalyticsReport) -> str:
    if not report.history_path:
        return ""
    return "\n".join(
        [
            '<section class="panel" id="analytics-history">',
            "<h2>History</h2>",
            '<p class="panel-hint">This snapshot was appended to the studio analytics history file for longer rerender trend analysis.</p>',
            f"<p class='mono'>{_text(report.history_path)}</p>",
            "</section>",
        ]
    )


def _render_breakdown_table(rows: tuple[FarmBreakdownRow, ...]) -> str:
    body = "".join(
        
            "<tr>"
            f"<td>{_text(row.label)}</td>"
            f"<td>{_text(row.job_count)}</td>"
            f"<td>{_text(_format_percent(row.failure_rate))}</td>"
            f"<td>{_text(_format_duration(row.average_render_seconds))}</td>"
            "</tr>"
            for row in rows
        
    )
    return "\n".join(
        [
            '<div class="table-wrap"><table class="results">',
            "<thead><tr><th>Label</th><th>Jobs</th><th>Failure Rate</th><th>Avg Render</th></tr></thead>",
            f"<tbody>{body}</tbody>",
            "</table></div>",
        ]
    )


def _render_failed_jobs_table(rows: tuple[FarmFailedJobRow, ...]) -> str:
    if not rows:
        return '<p class="empty">No failed or high-error jobs in this window.</p>'
    body = "".join(
        
            "<tr>"
            f"<td class='mono'>{_text(row.job_name)}</td>"
            f"<td>{_text(row.pool)}</td>"
            f"<td>{_text(row.status)}</td>"
            f"<td>{_text(row.error_count)}</td>"
            "</tr>"
            for row in rows
        
    )
    return "\n".join(
        [
            '<div class="table-wrap"><table class="results">',
            "<thead><tr><th>Job</th><th>Pool</th><th>Status</th><th>Errors</th></tr></thead>",
            f"<tbody>{body}</tbody>",
            "</table></div>",
        ]
    )


def _render_footer(report: FarmAnalyticsReport) -> str:
    return "\n".join(
        [
            '<footer class="report-footer">',
            f"<p>Generated by Maya Pipeline Inspector · Deadline farm analytics · {len(report.pools)} pools</p>",
            "</footer>",
        ]
    )


def _svg_donut_chart(
    entries: list[tuple[str, float, str]],
    *,
    title: str,
    center_value: str,
    center_label: str,
) -> str:
    if not entries:
        return '<p class="empty">No chart data available.</p>'

    width = 240
    height = 210
    cx = width / 2
    cy = 92
    radius = 52
    stroke = 20
    total = sum(max(value, 0.0) for _, value, _ in entries) or 1.0
    start_angle = -90.0
    arcs: list[str] = []
    legend: list[str] = []

    for index, (label, value, color) in enumerate(entries):
        if value <= 0:
            continue
        sweep = (value / total) * 360.0
        end_angle = start_angle + sweep
        arcs.append(
            _svg_arc_path(cx, cy, radius, start_angle, end_angle, color=color, stroke_width=stroke)
        )
        start_angle = end_angle
        legend_y = 158 + index * 14
        legend.extend(
            [
                f'<rect x="16" y="{legend_y - 9}" width="8" height="8" rx="2" fill="{color}" />',
                f'<text x="28" y="{legend_y}" class="chart-label chart-label-compact">{_text(label)} ({int(value)})</text>',
            ]
        )

    return "\n".join(
        [
            f'<svg class="chart-svg chart-svg-compact" viewBox="0 0 {width} {height}" role="img" aria-label="{_attr(title)}">',
            f'<text x="{width / 2:.1f}" y="20" text-anchor="middle" class="chart-title">{_text(title)}</text>',
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}" class="donut-track" fill="none" stroke-width="{stroke}" />',
            *arcs,
            f'<text x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" class="donut-center-value">{_text(center_value)}</text>',
            f'<text x="{cx:.1f}" y="{cy + 14:.1f}" text-anchor="middle" class="donut-center-label">{_text(center_label)}</text>',
            *legend,
            "</svg>",
        ]
    )


def _svg_radial_gauge(
    title: str,
    value: float,
    *,
    caption: str,
    color: str,
    invert_health: bool = False,
) -> str:
    width = 240
    height = 210
    cx = width / 2
    cy = 108
    radius = 58
    stroke = 14
    clamped = min(max(value, 0.0), 1.0)
    sweep = clamped * 180.0
    gauge_color = color
    if invert_health:
        if clamped >= 0.25:
            gauge_color = _CHART_COLORS["failed"]
        elif clamped >= 0.10:
            gauge_color = _CHART_COLORS["active"]
        else:
            gauge_color = _CHART_COLORS["completed"]

    return "\n".join(
        [
            f'<svg class="chart-svg chart-svg-compact" viewBox="0 0 {width} {height}" role="img" aria-label="{_attr(title)}">',
            f'<text x="{width / 2:.1f}" y="20" text-anchor="middle" class="chart-title">{_text(title)}</text>',
            f'<path d="{_svg_arc_path(cx, cy, radius, 180, 360)}" class="gauge-track" fill="none" stroke-width="{stroke}" />',
            _svg_arc_path(cx, cy, radius, 180, 180 + sweep, color=gauge_color, stroke_width=stroke),
            f'<text x="{cx:.1f}" y="{cy + 6:.1f}" text-anchor="middle" class="donut-center-value">{_text(caption)}</text>',
            f'<text x="{cx:.1f}" y="{cy + 22:.1f}" text-anchor="middle" class="donut-center-label">{_text(_format_percent(clamped))}</text>',
            "</svg>",
        ]
    )


def _svg_arc_path(
    cx: float,
    cy: float,
    radius: float,
    start_angle: float,
    end_angle: float,
    *,
    color: str = "",
    stroke_width: float = 0.0,
) -> str:
    start = _polar_to_cartesian(cx, cy, radius, end_angle)
    end = _polar_to_cartesian(cx, cy, radius, start_angle)
    large_arc = 1 if end_angle - start_angle > 180 else 0
    path = (
        f"M {start[0]:.1f} {start[1]:.1f} "
        f"A {radius:.1f} {radius:.1f} 0 {large_arc} 0 {end[0]:.1f} {end[1]:.1f}"
    )
    if color:
        return (
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{stroke_width:.1f}" '
            f'stroke-linecap="round" />'
        )
    return path


def _polar_to_cartesian(cx: float, cy: float, radius: float, angle_deg: float) -> tuple[float, float]:
    angle = radians(angle_deg)
    return cx + radius * cos(angle), cy + radius * sin(angle)


def _svg_vertical_bar_chart(
    entries: list[tuple[str, float, str]],
    *,
    title: str,
) -> str:
    if not entries:
        return '<p class="empty">No chart data available.</p>'

    width = 720
    height = 260
    margin_left = 48
    margin_bottom = 48
    margin_top = 28
    chart_height = height - margin_bottom - margin_top
    chart_width = width - margin_left - 24
    max_value = max(value for _, value, _ in entries) or 1.0
    bar_width = chart_width / max(len(entries), 1) * 0.55
    gap = chart_width / max(len(entries), 1)

    bars: list[str] = []
    labels: list[str] = []
    for index, (label, value, color) in enumerate(entries):
        bar_height = (value / max_value) * chart_height if max_value else 0.0
        x = margin_left + index * gap + (gap - bar_width) / 2
        y = margin_top + chart_height - bar_height
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" '
            f'rx="8" fill="{color}" />'
        )
        labels.append(
            f'<text x="{x + bar_width / 2:.1f}" y="{height - 16}" text-anchor="middle" '
            f'class="chart-label">{_text(label)}</text>'
        )
        labels.append(
            f'<text x="{x + bar_width / 2:.1f}" y="{y - 8:.1f}" text-anchor="middle" '
            f'class="chart-value">{_text(int(value) if value.is_integer() else round(value, 1))}</text>'
        )

    return "\n".join(
        [
            f'<svg class="chart-svg" viewBox="0 0 {width} {height}" role="img" aria-label="{_attr(title)}">',
            f'<text x="{margin_left}" y="18" class="chart-title">{_text(title)}</text>',
            *bars,
            *labels,
            "</svg>",
        ]
    )


def _svg_horizontal_bar_chart(
    entries: list[tuple[str, float, str]],
    *,
    title: str,
    max_value: float,
) -> str:
    if not entries:
        return '<p class="empty">No chart data available.</p>'

    width = 720
    row_height = 42
    margin_left = 140
    margin_top = 28
    height = margin_top + len(entries) * row_height + 16
    chart_width = width - margin_left - 24
    safe_max = max(max_value, 0.0001)

    rows: list[str] = []
    for index, (label, value, color) in enumerate(entries):
        y = margin_top + index * row_height
        bar_width = (max(value, 0.0) / safe_max) * chart_width
        rows.extend(
            [
                f'<text x="0" y="{y + 24}" class="chart-label">{_text(label)}</text>',
                f'<rect x="{margin_left}" y="{y + 8}" width="{chart_width}" height="18" rx="9" class="chart-track" />',
                f'<rect x="{margin_left}" y="{y + 8}" width="{bar_width:.1f}" height="18" rx="9" fill="{color}" />',
                f'<text x="{margin_left + chart_width + 8}" y="{y + 22}" class="chart-value">{_text(_format_percent(value))}</text>',
            ]
        )

    return "\n".join(
        [
            f'<svg class="chart-svg" viewBox="0 0 {width} {height}" role="img" aria-label="{_attr(title)}">',
            f'<text x="0" y="18" class="chart-title">{_text(title)}</text>',
            *rows,
            "</svg>",
        ]
    )


def _farm_health_label(report: FarmAnalyticsReport) -> str:
    failure_rate = report.metrics.failure_rate
    if failure_rate >= 0.25:
        return "critical"
    if failure_rate >= 0.10:
        return "warning"
    return "healthy"


def _throughput_note(report: FarmAnalyticsReport) -> str:
    if report.throughput_estimated:
        return "Throughput estimated from completed-job count (completion timestamps unavailable)."
    return "Throughput calculated from completed jobs inside the reporting window."


def _format_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _format_duration(seconds: float) -> str:
    total = max(int(seconds), 0)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def _format_timestamp(epoch_seconds: float) -> str:
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _farm_chart_stylesheet() -> str:
    return """
.chart-svg {
  display: block;
  max-width: 100%;
  width: 100%;
}
.chart-title {
  fill: var(--text);
  font-size: 14px;
  font-weight: 700;
}
.chart-label {
  fill: var(--text-muted);
  font-size: 12px;
}
.chart-value {
  fill: var(--text);
  font-size: 12px;
  font-weight: 600;
}
.chart-track {
  fill: color-mix(in srgb, var(--border) 70%, transparent);
}
.chart-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
.chart-card {
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: color-mix(in srgb, var(--surface) 92%, var(--bg));
}
.chart-card-span-2 {
  grid-column: span 2;
}
.chart-svg-compact {
  min-height: 200px;
}
.chart-svg-compact .chart-title {
  font-size: 12px;
}
.chart-label-compact {
  font-size: 10px;
}
.donut-track,
.gauge-track {
  stroke: color-mix(in srgb, var(--border) 75%, transparent);
}
.chart-svg-compact .donut-center-value {
  font-size: 17px;
  font-weight: 700;
}
.donut-center-value {
  fill: var(--text);
  font-size: 24px;
  font-weight: 700;
}
.donut-center-label {
  fill: var(--text-muted);
  font-size: 11px;
  font-weight: 600;
}
@media (max-width: 1200px) {
  .chart-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .chart-card-span-2 {
    grid-column: span 2;
  }
}
@media (max-width: 720px) {
  .chart-grid {
    grid-template-columns: 1fr;
  }
  .chart-card-span-2 {
    grid-column: span 1;
  }
}
.score-ring.status-healthy { border-color: var(--passed); }
.score-ring.status-warning { border-color: var(--warning); }
.score-ring.status-critical { border-color: var(--failed); }
.status-pill.status-healthy { background: color-mix(in srgb, var(--passed) 15%, transparent); color: var(--passed); }
.status-pill.status-warning { background: color-mix(in srgb, var(--warning) 15%, transparent); color: var(--warning); }
.status-pill.status-critical { background: color-mix(in srgb, var(--failed) 15%, transparent); color: var(--failed); }
""".strip()
