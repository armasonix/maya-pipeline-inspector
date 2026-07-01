"""Self-contained HTML report writer for validation results."""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from html import escape
from pathlib import Path
from typing import Any

from shader_health.core import GraphSnapshot, RuleResult
from shader_health.reports.json_report import build_json_report

SEVERITY_ORDER = ("critical", "error", "warning", "info")

JsonDict = dict[str, Any]
JsonValue = Any


def build_html_report(snapshot: GraphSnapshot, results: Iterable[RuleResult]) -> str:
    """Build a deterministic self-contained HTML validation report."""

    payload = build_json_report(snapshot, results)
    html = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{_text('Maya Shader Health Report')}</title>",
        f"<style>{_stylesheet()}</style>",
        "</head>",
        "<body>",
        '<main class="report">',
        _render_header(payload),
        _render_summary(payload),
        _render_severity_groups(payload),
        "</main>",
        "</body>",
        "</html>",
    ]
    return "\n".join(html) + "\n"


def write_html_report(
    path: str | Path,
    snapshot: GraphSnapshot,
    results: Iterable[RuleResult],
) -> Path:
    """Write a self-contained HTML validation report and return the output path."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_html_report(snapshot, results), encoding="utf-8")
    return output_path


def _render_header(payload: JsonDict) -> str:
    snapshot = _mapping(payload.get("snapshot"))
    title = _text("Maya Shader Health Report")
    scene_path = _text(snapshot.get("scene_path", ""))
    renderer = _text(snapshot.get("renderer", ""))
    status = _text(str(payload.get("status", "unknown")).upper())

    return "\n".join(
        [
            '<section class="hero">',
            f"<h1>{title}</h1>",
            '<div class="meta-grid">',
            _metric_card("Status", status),
            _metric_card("Health Score", payload.get("health_score")),
            _metric_card("Renderer", renderer),
            _metric_card("Scene", scene_path),
            _metric_card("Report Schema Version", payload.get("report_schema_version")),
            _metric_card("Snapshot Schema Version", payload.get("snapshot_schema_version")),
            "</div>",
            "</section>",
        ]
    )


def _render_summary(payload: JsonDict) -> str:
    summary = _mapping(payload.get("summary"))
    score = _mapping(payload.get("score"))
    blocking = _mapping(payload.get("blocking"))

    return "\n".join(
        [
            '<section class="panel" id="summary">',
            "<h2>Summary</h2>",
            '<div class="summary-grid">',
            _metric_card("Total", summary.get("total")),
            _metric_card("Failed", summary.get("failed")),
            _metric_card("Passed", summary.get("passed")),
            _metric_card("Skipped", summary.get("skipped")),
            _metric_card("Auto-fixable", summary.get("auto_fixable")),
            _metric_card("Raw Score", score.get("raw_score")),
            "</div>",
            '<div class="blocking-grid">',
            _block_card("Publish Block", blocking.get("publish")),
            _block_card("Deadline Block", blocking.get("deadline")),
            _block_card("Any Block", blocking.get("any")),
            "</div>",
            "</section>",
        ]
    )


def _render_severity_groups(payload: JsonDict) -> str:
    grouped = _group_results_by_severity(payload)
    sections = ['<section class="panel" id="severity-groups">', "<h2>Severity Groups</h2>"]
    for severity in SEVERITY_ORDER:
        results = grouped.get(severity, [])
        sections.append(_render_severity_group(severity, results))
    sections.append("</section>")
    return "\n".join(sections)


def _render_severity_group(severity: str, results: list[JsonDict]) -> str:
    label = severity.capitalize()
    lines = [
        f'<section class="severity severity-{_attr(severity)}">',
        f"<h3>{_text(label)} ({len(results)})</h3>",
    ]
    if not results:
        lines.append(f'<p class="empty">No {_text(severity)} results.</p>')
    else:
        lines.extend(_render_results_table(results))
    lines.append("</section>")
    return "\n".join(lines)


def _render_results_table(results: list[JsonDict]) -> list[str]:
    lines = [
        '<table class="results">',
        "<thead>",
        "<tr>",
        "<th>Status</th>",
        "<th>Rule</th>",
        "<th>Target</th>",
        "<th>Issue</th>",
        "<th>Current</th>",
        "<th>Expected</th>",
        "<th>Owner</th>",
        "</tr>",
        "</thead>",
        "<tbody>",
    ]
    for result in results:
        lines.append(_render_result_row(result))
    lines.extend(["</tbody>", "</table>"])
    return lines


def _render_result_row(result: JsonDict) -> str:
    target = result.get("target_id") or result.get("node") or result.get("material") or ""
    return "".join(
        [
            "<tr>",
            f'<td class="status">{_text(result.get("status"))}</td>',
            f"<td>{_text(result.get('rule_id'))}</td>",
            f"<td>{_text(target)}</td>",
            f"<td>{_text(result.get('message'))}</td>",
            f"<td>{_text(_format_value(result.get('current_value')))}</td>",
            f"<td>{_text(_format_value(result.get('expected_value')))}</td>",
            f"<td>{_text(result.get('owner'))}</td>",
            "</tr>",
        ]
    )


def _metric_card(label: str, value: JsonValue) -> str:
    return "".join(
        [
            '<div class="metric">',
            f'<span class="metric-label">{_text(label)}</span>',
            f'<strong class="metric-value">{_text(_format_value(value))}</strong>',
            "</div>",
        ]
    )


def _block_card(label: str, value: JsonValue) -> str:
    blocked = bool(value)
    status = "YES" if blocked else "NO"
    state = "blocked" if blocked else "clear"
    return "".join(
        [
            f'<div class="block-card {state}">',
            f'<span class="metric-label">{_text(label)}</span>',
            f'<strong class="metric-value">{status}</strong>',
            "</div>",
        ]
    )


def _group_results_by_severity(payload: JsonDict) -> dict[str, list[JsonDict]]:
    grouped = {severity: [] for severity in SEVERITY_ORDER}
    for result in payload.get("results", []):
        if not isinstance(result, Mapping):
            continue
        severity = str(result.get("severity", "info")).lower()
        grouped.setdefault(severity, []).append(dict(result))
    return grouped


def _mapping(value: JsonValue) -> JsonDict:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _format_value(value: JsonValue) -> str:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True)
    if value is None:
        return ""
    return str(value)


def _text(value: JsonValue) -> str:
    return escape(_format_value(value), quote=False)


def _attr(value: JsonValue) -> str:
    return escape(_format_value(value), quote=True)


def _stylesheet() -> str:
    return """
:root { color-scheme: light; font-family: Arial, sans-serif; }
body { background: #f5f5f5; color: #1f2933; margin: 0; }
.report { margin: 0 auto; max-width: 1200px; padding: 32px; }
.hero, .panel { background: #ffffff; border: 1px solid #d9e2ec; border-radius: 12px; margin: 0 0 24px; padding: 24px; }
h1, h2, h3 { margin-top: 0; }
.meta-grid, .summary-grid, .blocking-grid { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }
.metric, .block-card { background: #f8fafc; border: 1px solid #d9e2ec; border-radius: 10px; padding: 12px; }
.metric-label { color: #52606d; display: block; font-size: 12px; text-transform: uppercase; }
.metric-value { display: block; font-size: 18px; margin-top: 4px; overflow-wrap: anywhere; }
.block-card.blocked { border-color: #c0392b; }
.block-card.clear { border-color: #2f855a; }
.severity { border-top: 4px solid #bcccdc; margin-top: 20px; padding-top: 16px; }
.severity-critical { border-top-color: #9b1c1c; }
.severity-error { border-top-color: #c2410c; }
.severity-warning { border-top-color: #b7791f; }
.severity-info { border-top-color: #2563eb; }
.results { border-collapse: collapse; width: 100%; }
.results th, .results td { border-bottom: 1px solid #d9e2ec; padding: 10px; text-align: left; vertical-align: top; }
.results th { background: #f8fafc; color: #334e68; font-size: 12px; text-transform: uppercase; }
.empty { color: #52606d; font-style: italic; }
""".strip()
