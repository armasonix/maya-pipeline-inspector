"""Self-contained HTML report writer for validation results."""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from html import escape
from pathlib import Path
from typing import Any

from pipeline_inspector.core import GraphSnapshot, RuleResult
from pipeline_inspector.reports.json_report import build_json_report

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
        f"<title>{_text('Maya Pipeline Inspector Report')}</title>",
        f"<style>{_stylesheet()}</style>",
        "</head>",
        "<body>",
        '<div class="page">',
        _render_header(payload),
        _render_summary(payload),
        _render_severity_groups(payload),
        _render_footer(payload),
        "</div>",
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
    summary = _mapping(payload.get("summary"))
    status = str(payload.get("status", "unknown")).lower()
    status_label = status.upper()
    scene_path = _text(snapshot.get("scene_path", ""))
    renderer = _text(snapshot.get("renderer", "common"))
    scanned_at = _text(snapshot.get("scanned_at_utc", ""))
    health_score = payload.get("health_score", 0)

    return "\n".join(
        [
            '<header class="hero">',
            '<div class="hero-top">',
            '<div class="hero-copy">',
            f"<h1>{_text('Maya Pipeline Inspector Report')}</h1>",
            '<p class="hero-subtitle">Material preflight summary for publish and render-farm readiness.</p>',
            "</div>",
            f'<div class="score-ring status-{_attr(status)}">',
            f'<span class="score-value">{_text(health_score)}</span>',
            '<span class="score-label">Health</span>',
            "</div>",
            "</div>",
            '<div class="hero-meta">',
            f'<span class="status-pill status-{_attr(status)}">{status_label}</span>',
            f'<span class="meta-chip">Renderer: <strong>{renderer}</strong></span>',
            f'<span class="meta-chip">Failed: <strong>{_text(summary.get("failed", 0))}</strong></span>',
            f'<span class="meta-chip">Total: <strong>{_text(summary.get("total", 0))}</strong></span>',
            "</div>",
            '<dl class="meta-list">',
            f"<div><dt>Scene</dt><dd>{scene_path}</dd></div>",
            f"<div><dt>Scan time (UTC)</dt><dd>{scanned_at or 'N/A'}</dd></div>",
            f"<div><dt>Report schema</dt><dd>{_text(payload.get('report_schema_version'))}</dd></div>",
            f"<div><dt>Snapshot schema</dt><dd>{_text(payload.get('snapshot_schema_version'))}</dd></div>",
            "</dl>",
            "</header>",
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
            '<div class="metric-grid">',
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
    sections = [
        '<section class="panel" id="severity-groups">',
        "<h2>Severity Groups</h2>",
        '<p class="panel-hint">Expand or collapse each severity group to jump directly to the issues you need.</p>',
    ]
    for severity in SEVERITY_ORDER:
        results = grouped.get(severity, [])
        sections.append(_render_severity_group(severity, results))
    sections.append("</section>")
    return "\n".join(sections)

def _severity_group_open_by_default(severity: str, results: list[JsonDict]) -> bool:
    if not results:
        return False
    return severity in ("critical", "error")

def _render_severity_group(severity: str, results: list[JsonDict]) -> str:
    label = severity.capitalize()
    count = len(results)
    open_attr = " open" if _severity_group_open_by_default(severity, results) else ""
    lines = [
        f'<details class="severity severity-{_attr(severity)}"{open_attr}>',
        '<summary class="severity-summary">',
        '<span class="severity-summary-main">',
        f'<span class="severity-title">{_text(label)} ({count})</span>',
        f'<span class="severity-badge">{count}</span>',
        "</span>",
        "</summary>",
        '<div class="severity-body">',
    ]
    if not results:
        lines.append(f'<p class="empty">No {_text(severity)} results.</p>')
    else:
        lines.extend(_render_results_table(results))
    lines.extend(["</div>", "</details>"])
    return "\n".join(lines)

def _render_results_table(results: list[JsonDict]) -> list[str]:
    lines = [
        '<div class="table-wrap">',
        '<table class="results">',
        "<thead>",
        "<tr>",
        "<th>Status</th>",
        "<th>Rule</th>",
        "<th>Target</th>",
        "<th>Issue</th>",
        "<th>Why</th>",
        "<th>Current</th>",
        "<th>Expected</th>",
        "<th>Owner</th>",
        "</tr>",
        "</thead>",
        "<tbody>",
    ]
    for result in results:
        lines.append(_render_result_row(result))
    lines.extend(["</tbody>", "</table>", "</div>"])
    return lines

def _render_result_row(result: JsonDict) -> str:
    target = result.get("target_id") or result.get("node") or result.get("material") or ""
    status = str(result.get("status", "")).lower()
    return "".join(
        [
            "<tr>",
            f'<td><span class="result-status status-{_attr(status)}">{_text(result.get("status"))}</span></td>',
            f'<td class="mono">{_text(result.get("rule_id"))}</td>',
            f'<td class="mono">{_text(target)}</td>',
            f"<td>{_text(result.get('message'))}</td>",
            f'<td class="muted">{_text(result.get("why"))}</td>',
            f'<td class="mono">{_text(_format_value(result.get("current_value")))}</td>',
            f'<td class="mono">{_text(_format_value(result.get("expected_value")))}</td>',
            f"<td>{_text(result.get('owner'))}</td>",
            "</tr>",
        ]
    )

def _render_footer(payload: JsonDict) -> str:
    snapshot = _mapping(payload.get("snapshot"))
    scan_scope = _text(snapshot.get("scan_scope", "scene"))
    return "\n".join(
        [
            '<footer class="report-footer">',
            f"<p>Generated by Maya Pipeline Inspector · scope: {scan_scope}</p>",
            "</footer>",
        ]
    )

def _metric_card(label: str, value: JsonValue) -> str:
    return "".join(
        [
            '<article class="metric">',
            f'<span class="metric-label">{_text(label)}</span>',
            f'<strong class="metric-value">{_text(_format_value(value))}</strong>',
            "</article>",
        ]
    )

def _block_card(label: str, value: JsonValue) -> str:
    blocked = bool(value)
    status = "YES" if blocked else "NO"
    state = "blocked" if blocked else "clear"
    return "".join(
        [
            f'<article class="block-card {state}">',
            f'<span class="metric-label">{_text(label)}</span>',
            f'<strong class="metric-value">{status}</strong>',
            "</article>",
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
:root {
  color-scheme: light dark;
  --bg: #f4f6f8;
  --surface: #ffffff;
  --surface-muted: #f8fafc;
  --text: #0f172a;
  --text-muted: #64748b;
  --border: #e2e8f0;
  --accent: #2563eb;
  --critical: #b91c1c;
  --error: #c2410c;
  --warning: #b45309;
  --info: #2563eb;
  --passed: #15803d;
  --failed: #b91c1c;
  --shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
  font-family: "Segoe UI", Inter, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0b1220;
    --surface: #111827;
    --surface-muted: #1f2937;
    --text: #e5e7eb;
    --text-muted: #94a3b8;
    --border: #334155;
    --shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
  }
}
* { box-sizing: border-box; }
body {
  background: linear-gradient(180deg, var(--bg) 0%, color-mix(in srgb, var(--bg) 80%, var(--accent) 20%) 100%);
  color: var(--text);
  margin: 0;
  min-height: 100vh;
}
.page {
  margin: 0 auto;
  max-width: none;
  padding: 24px clamp(16px, 2.5vw, 48px) 40px;
  width: 100%;
}
.hero, .panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 18px;
  box-shadow: var(--shadow);
  margin-bottom: 24px;
  padding: 24px;
}
.hero-top {
  align-items: center;
  display: flex;
  gap: 24px;
  justify-content: space-between;
}
.hero-copy h1 {
  font-size: clamp(1.5rem, 2vw, 2rem);
  letter-spacing: -0.02em;
  margin: 0 0 8px;
}
.hero-subtitle {
  color: var(--text-muted);
  margin: 0;
  max-width: 42rem;
}
.score-ring {
  align-items: center;
  border: 4px solid var(--border);
  border-radius: 999px;
  display: flex;
  flex-direction: column;
  height: 112px;
  justify-content: center;
  min-width: 112px;
  padding: 12px;
}
.score-ring.status-failed { border-color: var(--failed); }
.score-ring.status-passed { border-color: var(--passed); }
.score-value {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1;
}
.score-label {
  color: var(--text-muted);
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  margin-top: 6px;
  text-transform: uppercase;
}
.hero-meta {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 20px;
}
.status-pill, .meta-chip, .severity-badge, .result-status {
  border-radius: 999px;
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  padding: 6px 12px;
  text-transform: uppercase;
}
.status-pill.status-failed { background: color-mix(in srgb, var(--failed) 15%, transparent); color: var(--failed); }
.status-pill.status-passed { background: color-mix(in srgb, var(--passed) 15%, transparent); color: var(--passed); }
.meta-chip {
  background: var(--surface-muted);
  border: 1px solid var(--border);
  color: var(--text-muted);
  text-transform: none;
}
.meta-list {
  display: grid;
  gap: 12px 20px;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  margin: 20px 0 0;
}
.meta-list div {
  background: var(--surface-muted);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 14px;
}
.meta-list dt {
  color: var(--text-muted);
  font-size: 0.75rem;
  letter-spacing: 0.06em;
  margin-bottom: 6px;
  text-transform: uppercase;
}
.meta-list dd {
  margin: 0;
  overflow-wrap: anywhere;
}
h2, h3 { margin-top: 0; }
.metric-grid, .blocking-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
}
.metric, .block-card {
  background: var(--surface-muted);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 14px;
}
.metric-label {
  color: var(--text-muted);
  display: block;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.metric-value {
  display: block;
  font-size: 1.35rem;
  margin-top: 6px;
  overflow-wrap: anywhere;
}
.block-card.blocked {
  border-color: color-mix(in srgb, var(--failed) 40%, var(--border));
  color: var(--failed);
}
.block-card.clear {
  border-color: color-mix(in srgb, var(--passed) 40%, var(--border));
  color: var(--passed);
}
.panel-hint {
  color: var(--text-muted);
  margin: -4px 0 16px;
}
.severity {
  background: var(--surface-muted);
  border: 1px solid var(--border);
  border-radius: 14px;
  margin-top: 12px;
  overflow: hidden;
}
.severity-summary {
  align-items: center;
  cursor: pointer;
  display: flex;
  gap: 12px;
  justify-content: space-between;
  list-style: none;
  padding: 14px 16px;
  user-select: none;
}
.severity-summary::-webkit-details-marker { display: none; }
.severity-summary-main {
  align-items: center;
  display: flex;
  flex: 1;
  gap: 10px;
  justify-content: space-between;
  min-width: 0;
}
.severity-title {
  font-size: 1rem;
  font-weight: 700;
}
.severity-summary::before {
  color: var(--text-muted);
  content: "▸";
  flex: 0 0 auto;
  font-size: 0.95rem;
  line-height: 1;
  transition: transform 0.15s ease;
}
.severity[open] > .severity-summary::before {
  content: "▾";
}
.severity-body {
  border-top: 1px solid var(--border);
  padding: 0 16px 16px;
}
.severity-critical .severity-badge { background: color-mix(in srgb, var(--critical) 15%, transparent); color: var(--critical); }
.severity-error .severity-badge { background: color-mix(in srgb, var(--error) 15%, transparent); color: var(--error); }
.severity-warning .severity-badge { background: color-mix(in srgb, var(--warning) 15%, transparent); color: var(--warning); }
.severity-info .severity-badge { background: color-mix(in srgb, var(--info) 15%, transparent); color: var(--info); }
.table-wrap {
  border: 1px solid var(--border);
  border-radius: 14px;
  overflow-x: auto;
  width: 100%;
}
.results {
  border-collapse: collapse;
  table-layout: fixed;
  width: 100%;
}
.results th, .results td {
  border-bottom: 1px solid var(--border);
  overflow-wrap: anywhere;
  padding: 10px 12px;
  text-align: left;
  vertical-align: top;
  word-break: break-word;
}
.results th:nth-child(1), .results td:nth-child(1) { width: 7%; }
.results th:nth-child(2), .results td:nth-child(2) { width: 14%; }
.results th:nth-child(3), .results td:nth-child(3) { width: 12%; }
.results th:nth-child(4), .results td:nth-child(4) { width: 18%; }
.results th:nth-child(5), .results td:nth-child(5) { width: 18%; }
.results th:nth-child(6), .results td:nth-child(6) { width: 11%; }
.results th:nth-child(7), .results td:nth-child(7) { width: 11%; }
.results th:nth-child(8), .results td:nth-child(8) { width: 9%; }
.results th {
  background: var(--surface-muted);
  color: var(--text-muted);
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  position: sticky;
  top: 0;
  text-transform: uppercase;
  z-index: 1;
}
.results tbody tr:last-child td { border-bottom: 0; }
.results tbody tr:hover { background: color-mix(in srgb, var(--accent) 6%, transparent); }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.88rem; }
.muted { color: var(--text-muted); }
.result-status.status-failed { background: color-mix(in srgb, var(--failed) 15%, transparent); color: var(--failed); }
.result-status.status-passed { background: color-mix(in srgb, var(--passed) 15%, transparent); color: var(--passed); }
.result-status.status-skipped { background: color-mix(in srgb, var(--text-muted) 15%, transparent); color: var(--text-muted); }
.empty {
  color: var(--text-muted);
  font-style: italic;
  margin: 0;
}
.report-footer {
  color: var(--text-muted);
  font-size: 0.85rem;
  padding: 8px 4px 0;
  text-align: center;
}
@media (max-width: 720px) {
  .hero-top { align-items: flex-start; flex-direction: column; }
  .page { padding-inline: 14px; }
}
""".strip()
