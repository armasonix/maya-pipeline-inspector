"""Self-contained HTML report writer for shader manifest diffs."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pipeline_inspector.reports.html_report import _attr, _format_value, _stylesheet, _text

ISSUE_GROUP_ORDER = ("new", "resolved", "changed")
ISSUE_GROUP_LABELS = {
    "new": "New",
    "resolved": "Resolved",
    "changed": "Changed",
}

JsonDict = dict[str, Any]
JsonValue = Any

def build_html_manifest_diff(diff_payload: Mapping[str, Any]) -> str:
    """Build a deterministic self-contained HTML manifest diff report."""

    payload = dict(diff_payload)
    html = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{_text('Maya Pipeline Inspector Manifest Diff')}</title>",
        f"<style>{_stylesheet()}{_diff_stylesheet()}</style>",
        "</head>",
        "<body>",
        '<div class="page">',
        _render_header(payload),
        _render_summary(payload),
        _render_issue_groups(payload),
        _render_footer(),
        "</div>",
        "</body>",
        "</html>",
    ]
    return "\n".join(html) + "\n"

def write_html_manifest_diff(
    path: str | Path,
    diff_payload: Mapping[str, Any],
) -> Path:
    """Write a self-contained HTML manifest diff report and return the output path."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_html_manifest_diff(diff_payload), encoding="utf-8")
    return output_path

def _render_header(payload: JsonDict) -> str:
    summary = _mapping(payload.get("summary"))
    total_changes = sum(int(summary.get(key, 0) or 0) for key in ISSUE_GROUP_ORDER)
    status = "changed" if total_changes else "unchanged"
    status_label = "CHANGED" if total_changes else "UNCHANGED"
    new_count = _text(summary.get("new", 0))
    resolved_count = _text(summary.get("resolved", 0))
    changed_count = _text(summary.get("changed", 0))

    return "\n".join(
        [
            '<header class="hero">',
            '<div class="hero-top">',
            '<div class="hero-copy">',
            f"<h1>{_text('Maya Pipeline Inspector Manifest Diff')}</h1>",
            (
                '<p class="hero-subtitle">'
                "Before/after comparison of shader manifest materials and textures."
                "</p>"
            ),
            "</div>",
            f'<div class="score-ring status-{_attr(status)}">',
            f'<span class="score-value">{_text(total_changes)}</span>',
            '<span class="score-label">Changes</span>',
            "</div>",
            "</div>",
            '<div class="hero-meta">',
            f'<span class="status-pill status-{_attr(status)}">{status_label}</span>',
            f'<span class="meta-chip">New: <strong>{new_count}</strong></span>',
            f'<span class="meta-chip">Resolved: <strong>{resolved_count}</strong></span>',
            f'<span class="meta-chip">Changed: <strong>{changed_count}</strong></span>',
            "</div>",
            '<dl class="meta-list">',
            _meta_item("Old scene", payload.get("old_scene_path", "")),
            _meta_item("New scene", payload.get("new_scene_path", "")),
            _meta_item("Diff schema", payload.get("manifest_diff_schema_version")),
            _meta_item("Old manifest schema", payload.get("old_manifest_schema_version")),
            _meta_item("New manifest schema", payload.get("new_manifest_schema_version")),
            "</dl>",
            "</header>",
        ]
    )

def _render_summary(payload: JsonDict) -> str:
    summary = _mapping(payload.get("summary"))

    return "\n".join(
        [
            '<section class="panel" id="summary">',
            "<h2>Summary</h2>",
            '<div class="metric-grid">',
            _metric_card("New entries", summary.get("new")),
            _metric_card("Resolved entries", summary.get("resolved")),
            _metric_card("Changed entries", summary.get("changed")),
            "</div>",
            "</section>",
        ]
    )

def _render_issue_groups(payload: JsonDict) -> str:
    issues = _mapping(payload.get("issues"))
    sections = [
        '<section class="panel" id="issue-groups">',
        "<h2>Issue Groups</h2>",
        (
            '<p class="panel-hint">'
            "Expand or collapse each group to review new, resolved, and changed manifest entries."
            "</p>"
        ),
    ]
    for group_id in ISSUE_GROUP_ORDER:
        entries = _issue_entries(issues.get(group_id))
        sections.append(_render_issue_group(group_id, entries))
    sections.append("</section>")
    return "\n".join(sections)

def _render_issue_group(group_id: str, entries: list[JsonDict]) -> str:
    label = ISSUE_GROUP_LABELS[group_id]
    count = len(entries)
    open_attr = " open" if count else ""
    lines = [
        f'<details class="severity category-{_attr(group_id)}"{open_attr}>',
        '<summary class="severity-summary">',
        '<span class="severity-summary-main">',
        f'<span class="severity-title">{_text(label)} ({count})</span>',
        f'<span class="severity-badge">{count}</span>',
        "</span>",
        "</summary>",
        '<div class="severity-body">',
    ]
    if not entries:
        lines.append(f'<p class="empty">No {_text(label.lower())} entries.</p>')
    elif group_id == "changed":
        lines.extend(_render_changed_table(entries))
    else:
        lines.extend(_render_entry_table(entries))
    lines.extend(["</div>", "</details>"])
    return "\n".join(lines)

def _render_entry_table(entries: list[JsonDict]) -> list[str]:
    lines = [
        '<div class="table-wrap">',
        '<table class="results entry-table">',
        "<thead>",
        "<tr>",
        "<th>Kind</th>",
        "<th>Label</th>",
        "<th>ID</th>",
        "<th>Material</th>",
        "<th>Fields</th>",
        "</tr>",
        "</thead>",
        "<tbody>",
    ]
    for entry in entries:
        lines.append(_render_entry_row(entry))
    lines.extend(["</tbody>", "</table>", "</div>"])
    return lines

def _render_entry_row(entry: JsonDict) -> str:
    fields = entry.get("fields")
    return "".join(
        [
            "<tr>",
            _kind_cell(entry.get("kind")),
            f"<td>{_text(entry.get('label'))}</td>",
            f'<td class="mono">{_text(entry.get("id"))}</td>',
            f'<td class="mono">{_text(entry.get("material_id", ""))}</td>',
            f'<td class="mono muted">{_text(_format_value(fields))}</td>',
            "</tr>",
        ]
    )

def _render_changed_table(entries: list[JsonDict]) -> list[str]:
    lines = [
        '<div class="table-wrap">',
        '<table class="results changed-table">',
        "<thead>",
        "<tr>",
        "<th>Kind</th>",
        "<th>Label</th>",
        "<th>ID</th>",
        "<th>Material</th>",
        "<th>Field</th>",
        "<th>Old</th>",
        "<th>New</th>",
        "</tr>",
        "</thead>",
        "<tbody>",
    ]
    for entry in entries:
        lines.extend(_render_changed_rows(entry))
    lines.extend(["</tbody>", "</table>", "</div>"])
    return lines

def _render_changed_rows(entry: JsonDict) -> list[str]:
    changes = entry.get("changes")
    if not isinstance(changes, list) or not changes:
        return [
            "".join(
                [
                    "<tr>",
                    _kind_cell(entry.get("kind")),
                    f"<td>{_text(entry.get('label'))}</td>",
                    f'<td class="mono">{_text(entry.get("id"))}</td>',
                    f'<td class="mono">{_text(entry.get("material_id", ""))}</td>',
                    '<td colspan="3" class="muted">No field changes recorded.</td>',
                    "</tr>",
                ]
            )
        ]

    rows: list[str] = []
    for index, change in enumerate(changes):
        if not isinstance(change, Mapping):
            continue
        material_cell = (
            f'<td class="mono">{_text(entry.get("material_id", ""))}</td>'
            if index == 0
            else "<td></td>"
        )
        kind_cell = (
            _kind_cell(entry.get("kind"))
            if index == 0
            else '<td class="row-span-muted">↳</td>'
        )
        rows.append(
            "".join(
                [
                    "<tr>",
                    kind_cell,
                    f"<td>{_text(entry.get('label')) if index == 0 else ''}</td>",
                    f'<td class="mono">{_text(entry.get("id")) if index == 0 else ""}</td>',
                    material_cell,
                    f'<td class="mono">{_text(change.get("field"))}</td>',
                    f'<td class="mono muted">{_text(_format_value(change.get("old")))}</td>',
                    f'<td class="mono">{_text(_format_value(change.get("new")))}</td>',
                    "</tr>",
                ]
            )
        )
    return rows

def _render_footer() -> str:
    return "\n".join(
        [
            '<footer class="report-footer">',
            "<p>Generated by Maya Pipeline Inspector · manifest diff report</p>",
            "</footer>",
        ]
    )

def _meta_item(label: str, value: JsonValue) -> str:
    return f"<div><dt>{_text(label)}</dt><dd>{_text(value)}</dd></div>"

def _kind_cell(kind: JsonValue) -> str:
    return (
        f'<td><span class="kind-pill kind-{_attr(kind)}">{_text(kind)}</span></td>'
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

def _issue_entries(value: JsonValue) -> list[JsonDict]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]

def _mapping(value: JsonValue) -> JsonDict:
    if isinstance(value, Mapping):
        return dict(value)
    return {}

def _diff_stylesheet() -> str:
    return "\n".join(
        [
            ".score-ring.status-changed { border-color: var(--warning); }",
            ".score-ring.status-unchanged { border-color: var(--passed); }",
            (
                ".status-pill.status-changed {"
                " background: color-mix(in srgb, var(--warning) 15%, transparent);"
                " color: var(--warning); }"
            ),
            (
                ".status-pill.status-unchanged {"
                " background: color-mix(in srgb, var(--passed) 15%, transparent);"
                " color: var(--passed); }"
            ),
            (
                ".category-new .severity-badge {"
                " background: color-mix(in srgb, var(--info) 15%, transparent);"
                " color: var(--info); }"
            ),
            (
                ".category-resolved .severity-badge {"
                " background: color-mix(in srgb, var(--passed) 15%, transparent);"
                " color: var(--passed); }"
            ),
            (
                ".category-changed .severity-badge {"
                " background: color-mix(in srgb, var(--warning) 15%, transparent);"
                " color: var(--warning); }"
            ),
            ".kind-pill {",
            "  border-radius: 999px;",
            "  display: inline-block;",
            "  font-size: 0.72rem;",
            "  font-weight: 600;",
            "  letter-spacing: 0.04em;",
            "  padding: 4px 10px;",
            "  text-transform: uppercase;",
            "}",
            (
                ".kind-material {"
                " background: color-mix(in srgb, var(--accent) 12%, transparent);"
                " color: var(--accent); }"
            ),
            (
                ".kind-texture {"
                " background: color-mix(in srgb, var(--info) 12%, transparent);"
                " color: var(--info); }"
            ),
            ".entry-table th:nth-child(1), .entry-table td:nth-child(1) { width: 10%; }",
            ".entry-table th:nth-child(2), .entry-table td:nth-child(2) { width: 14%; }",
            ".entry-table th:nth-child(3), .entry-table td:nth-child(3) { width: 18%; }",
            ".entry-table th:nth-child(4), .entry-table td:nth-child(4) { width: 14%; }",
            ".entry-table th:nth-child(5), .entry-table td:nth-child(5) { width: 44%; }",
            ".changed-table th:nth-child(1), .changed-table td:nth-child(1) { width: 8%; }",
            ".changed-table th:nth-child(2), .changed-table td:nth-child(2) { width: 12%; }",
            ".changed-table th:nth-child(3), .changed-table td:nth-child(3) { width: 16%; }",
            ".changed-table th:nth-child(4), .changed-table td:nth-child(4) { width: 12%; }",
            ".changed-table th:nth-child(5), .changed-table td:nth-child(5) { width: 12%; }",
            ".changed-table th:nth-child(6), .changed-table td:nth-child(6) { width: 20%; }",
            ".changed-table th:nth-child(7), .changed-table td:nth-child(7) { width: 20%; }",
            ".row-span-muted { color: var(--text-muted); text-align: center; }",
        ]
    )
