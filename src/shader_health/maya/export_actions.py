"""Maya UI report export actions."""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from shader_health.core import GraphSnapshot, RuleResult
from shader_health.core.fix_plan import FixPlan
from shader_health.maya.scanner import scan_scene
from shader_health.reports import write_json_report
from shader_health.reports.fix_plan_export import write_fix_plan_export
from shader_health.reports.html_report import write_html_report
from shader_health.reports.manifest import build_shader_manifest, write_shader_manifest
from shader_health.reports.manifest_diff_cli import (
    ManifestDiffInputError,
    load_manifest_json,
    write_manifest_diff_outputs,
)

SnapshotProvider = Callable[[], GraphSnapshot]


@dataclass(frozen=True)
class ExportActionResult:
    """Result returned by report export actions."""

    action: str
    path: str
    succeeded: bool
    message: str


def export_json_report(
    path: Optional[str | Path] = None,
    *,
    snapshot: Optional[GraphSnapshot] = None,
    snapshot_provider: Optional[SnapshotProvider] = None,
    results: Iterable[RuleResult] = (),
    fix_audit: Optional[dict[str, Any]] = None,
) -> ExportActionResult:
    """Export the current shader health JSON report."""

    export_snapshot = _snapshot(snapshot, snapshot_provider)
    output_path = _output_path(path, export_snapshot, suffix="report", extension="json")
    written_path = write_json_report(
        output_path,
        export_snapshot,
        results,
        fix_audit=fix_audit,
    )
    return _result("export_json_report", written_path, "JSON report exported.")


def export_html_report(
    path: Optional[str | Path] = None,
    *,
    snapshot: Optional[GraphSnapshot] = None,
    snapshot_provider: Optional[SnapshotProvider] = None,
    results: Iterable[RuleResult] = (),
) -> ExportActionResult:
    """Export the current shader health HTML report."""

    export_snapshot = _snapshot(snapshot, snapshot_provider)
    output_path = _output_path(path, export_snapshot, suffix="report", extension="html")
    written_path = write_html_report(output_path, export_snapshot, results)
    return _result("export_html_report", written_path, "HTML report exported.")


def export_shader_manifest(
    path: Optional[str | Path] = None,
    *,
    snapshot: Optional[GraphSnapshot] = None,
    snapshot_provider: Optional[SnapshotProvider] = None,
    results: Iterable[RuleResult] = (),
    health_score: Optional[int] = None,
) -> ExportActionResult:
    """Export the current Material Passport / Shader Manifest."""

    export_snapshot = _snapshot(snapshot, snapshot_provider)
    output_path = _output_path(path, export_snapshot, suffix="manifest", extension="json")
    written_path = write_shader_manifest(
        output_path,
        export_snapshot,
        results=results,
        health_score=health_score,
    )
    return _result("export_shader_manifest", written_path, "Shader manifest exported.")


def export_fix_plan(
    path: Optional[str | Path] = None,
    *,
    fix_plan: FixPlan,
    snapshot: Optional[GraphSnapshot] = None,
    snapshot_provider: Optional[SnapshotProvider] = None,
    profile_id: str = "",
) -> ExportActionResult:
    """Export the current planned fix actions without mutating the scene."""

    export_snapshot = _snapshot(snapshot, snapshot_provider)
    output_path = _output_path(path, export_snapshot, suffix="fix_plan", extension="json")
    written_path = write_fix_plan_export(
        output_path,
        fix_plan,
        snapshot=export_snapshot,
        profile_id=profile_id,
    )
    return _result("export_fix_plan", written_path, "Fix plan exported.")


def export_manifest_diff(
    baseline_manifest_path: str | Path,
    *,
    json_path: Optional[str | Path] = None,
    html_path: Optional[str | Path] = None,
    snapshot: Optional[GraphSnapshot] = None,
    snapshot_provider: Optional[SnapshotProvider] = None,
) -> ExportActionResult:
    """Export JSON and HTML diffs between a baseline manifest and the current scene."""

    export_snapshot = _snapshot(snapshot, snapshot_provider)
    try:
        old_manifest = load_manifest_json(Path(baseline_manifest_path))
    except ManifestDiffInputError as exc:
        return ExportActionResult(
            action="export_manifest_diff",
            path=str(baseline_manifest_path),
            succeeded=False,
            message=str(exc),
        )

    new_manifest = build_shader_manifest(export_snapshot)
    output_json_path = _output_path(
        json_path,
        export_snapshot,
        suffix="manifest_diff",
        extension="json",
    )
    output_html_path = (
        Path(html_path)
        if html_path is not None
        else output_json_path.with_suffix(".html")
    )
    write_manifest_diff_outputs(
        old_manifest,
        new_manifest,
        json_path=output_json_path,
        html_path=output_html_path,
    )
    return ExportActionResult(
        action="export_manifest_diff",
        path=str(output_json_path),
        succeeded=True,
        message=(
            "Manifest diff exported. "
            f"JSON: {output_json_path.name} HTML: {output_html_path.name}"
        ),
    )


def _snapshot(
    snapshot: Optional[GraphSnapshot],
    snapshot_provider: Optional[SnapshotProvider],
) -> GraphSnapshot:
    if snapshot is not None:
        return snapshot
    if snapshot_provider is not None:
        return snapshot_provider()
    return scan_scene()


def _output_path(
    path: Optional[str | Path],
    snapshot: GraphSnapshot,
    *,
    suffix: str,
    extension: str,
) -> Path:
    if path is not None:
        return Path(path)

    scene_path = Path(snapshot.scene_path) if snapshot.scene_path else None
    if scene_path is not None and scene_path.name:
        output_dir = scene_path.parent
        scene_stem = scene_path.stem
    else:
        output_dir = Path.cwd()
        scene_stem = "untitled_scene"
    return output_dir / f"{scene_stem}_shader_health_{suffix}.{extension}"


def _result(action: str, path: Path, message: str) -> ExportActionResult:
    return ExportActionResult(
        action=action,
        path=str(path),
        succeeded=True,
        message=message,
    )
