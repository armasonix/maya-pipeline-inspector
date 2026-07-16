"""Readable Markdown validation reports for task tracker notes."""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from pipeline_inspector.core import GraphSnapshot, RuleResult, summarize_results
from pipeline_inspector.integrations.messaging.validation_summary import format_block_status_label
from pipeline_inspector.reports.json_report import build_json_report

SEVERITY_ORDER = ("critical", "error", "warning", "info")


def build_markdown_report(snapshot: GraphSnapshot, results: Iterable[RuleResult]) -> str:
    """Build a readable Markdown validation report for tracker notes."""

    result_list = list(results)
    payload = build_json_report(snapshot, result_list)
    summary = summarize_results(result_list)
    snapshot_meta = payload.get("snapshot", {})
    scene_path = str(snapshot_meta.get("scene_path", "") or "unsaved scene")
    scanned_at = str(snapshot_meta.get("scanned_at_utc", "") or "")
    health_score = int(payload.get("health_score", 0) or 0)
    block_label = format_block_status_label(
        block_publish=bool(summary.block_publish),
        block_deadline=bool(summary.block_deadline),
    )

    lines = [
        "# Maya Pipeline Inspector Validation Report",
        "",
        f"- **Scene:** `{scene_path}`",
        f"- **Health score:** {health_score}/100",
        f"- **Blocks:** {block_label}",
        (
            "- **Issues:** "
            f"{summary.critical} critical, {summary.error} error, "
            f"{summary.warning} warning, {summary.info} info"
        ),
    ]
    if scanned_at:
        lines.append(f"- **Validated:** {scanned_at}")
    lines.extend(["", "## Failed issues", ""])

    failed = [result for result in result_list if result.status == "failed"]
    if not failed:
        lines.append("_No failed issues._")
    else:
        for severity in SEVERITY_ORDER:
            group = [result for result in failed if result.severity == severity]
            if not group:
                continue
            lines.append(f"### {severity.title()} ({len(group)})")
            lines.append("")
            for result in sorted(group, key=_issue_sort_key):
                lines.extend(_issue_markdown_lines(result))
                lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_markdown_report(
    path: str | Path,
    snapshot: GraphSnapshot,
    results: Iterable[RuleResult],
) -> Path:
    """Write a Markdown validation report and return the output path."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_markdown_report(snapshot, results), encoding="utf-8")
    return output_path


def _issue_sort_key(result: RuleResult) -> tuple[str, str, str]:
    return (result.rule_id, result.target_id, result.message)


def _issue_markdown_lines(result: RuleResult) -> list[str]:
    target = _issue_target_label(result)
    lines = [
        f"- **{result.rule_id}** — {result.message}",
        f"  - Target: `{target}`",
    ]
    if result.owner:
        lines.append(f"  - Owner: `{result.owner}`")
    if result.material:
        lines.append(f"  - Material: `{result.material}`")
    return lines


def _issue_target_label(result: RuleResult) -> str:
    if result.node:
        return str(result.node)
    if result.target_id:
        return str(result.target_id)
    return "scene"
