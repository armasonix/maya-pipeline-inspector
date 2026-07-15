"""Build tracker note content and optional HTML report artifacts."""
from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pipeline_inspector.core import GraphSnapshot, RuleResult
from pipeline_inspector.reports.html_report import write_html_report
from pipeline_inspector.reports.markdown_report import build_markdown_report


@dataclass(frozen=True)
class TrackerReportBundle:
    """Markdown note text plus an optional HTML report file for attachment."""

    markdown_note: str
    html_report_path: str = ""
    attachment_filename: str = "pipeline_inspector_report.html"


def build_tracker_report_bundle_from_run(
    result: Any,
    *,
    report_path: str = "",
    include_html: bool = True,
) -> TrackerReportBundle:
    """Build tracker note content and an optional HTML report file from a validation run."""


    snapshot = _snapshot_from_run(result)
    results = _results_from_run(result)
    markdown_note = build_markdown_report(snapshot, results)

    existing_path = str(report_path or "").strip()
    if existing_path and Path(existing_path).is_file():
        return TrackerReportBundle(
            markdown_note=markdown_note,
            html_report_path=existing_path,
        )

    if not include_html:
        return TrackerReportBundle(markdown_note=markdown_note)

    stem = _report_stem(snapshot)
    temp_dir = Path(tempfile.gettempdir()) / "pipeline_inspector_tracker_reports"
    temp_dir.mkdir(parents=True, exist_ok=True)
    html_path = temp_dir / f"{stem}_pipeline_inspector_report.html"
    write_html_report(html_path, snapshot, results)
    return TrackerReportBundle(
        markdown_note=markdown_note,
        html_report_path=str(html_path),
    )


def _snapshot_from_run(result: Any) -> GraphSnapshot:
    snapshot = getattr(result, "snapshot", None)
    if isinstance(snapshot, GraphSnapshot):
        return snapshot
    if snapshot is not None and hasattr(snapshot, "scene_path"):
        return GraphSnapshot(
            scene_path=str(getattr(snapshot, "scene_path", "") or ""),
            maya_version=str(getattr(snapshot, "maya_version", "") or ""),
            renderer=str(getattr(snapshot, "renderer", "") or ""),
            scan_scope=str(getattr(snapshot, "scan_scope", "") or "scene"),
            scanned_at_utc=str(getattr(snapshot, "scanned_at_utc", "") or ""),
        )
    raise TypeError("validation run result must expose a GraphSnapshot on .snapshot")


def _results_from_run(result: Any) -> tuple[RuleResult, ...]:
    raw_results = getattr(result, "results", ())
    if not isinstance(raw_results, (list, tuple)):
        return ()
    results: list[RuleResult] = []
    for item in raw_results:
        if isinstance(item, RuleResult):
            results.append(item)
    return tuple(results)


def _report_stem(snapshot: GraphSnapshot) -> str:
    scene_path = str(getattr(snapshot, "scene_path", "") or "").strip()
    if not scene_path:
        return "unsaved_scene"
    stem = Path(scene_path.replace("\\", "/")).stem
    return stem or "unsaved_scene"
