"""Maya UI report export actions."""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from shader_health.core import GraphSnapshot, RuleResult
from shader_health.maya.scanner import scan_scene
from shader_health.reports import write_json_report
from shader_health.reports.html_report import write_html_report
from shader_health.reports.manifest import write_shader_manifest

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
) -> ExportActionResult:
    """Export the current Material Passport / Shader Manifest."""

    export_snapshot = _snapshot(snapshot, snapshot_provider)
    output_path = _output_path(path, export_snapshot, suffix="manifest", extension="json")
    written_path = write_shader_manifest(output_path, export_snapshot)
    return _result("export_shader_manifest", written_path, "Shader manifest exported.")


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
