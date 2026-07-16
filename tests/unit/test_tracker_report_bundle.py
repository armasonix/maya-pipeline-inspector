from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from pipeline_inspector.core import GraphSnapshot, RuleResult
from pipeline_inspector.integrations.trackers.report_bundle import (
    TrackerReportBundle,
    build_tracker_report_bundle_from_run,
)


def _run_result(*, report_path: str = "") -> SimpleNamespace:
    return SimpleNamespace(
        snapshot=GraphSnapshot(
            scene_path="D:/shots/hero.ma",
            maya_version="2025",
            renderer="arnold",
            scan_scope="scene",
            scanned_at_utc="2026-07-10T12:00:00Z",
        ),
        results=(
            RuleResult(
                rule_id="R001",
                severity="critical",
                status="failed",
                title="Demo",
                message="Broken rule.",
                why="Because.",
                owner="td",
                target_kind="scene",
                target_id="scene",
            ),
        ),
        report_path=report_path,
    )


def test_build_tracker_report_bundle_from_run_writes_temp_html(tmp_path: Path, monkeypatch):
    temp_root = tmp_path / "tracker_reports"
    monkeypatch.setattr(
        "pipeline_inspector.integrations.trackers.report_bundle.tempfile.gettempdir",
        lambda: str(temp_root),
    )

    bundle = build_tracker_report_bundle_from_run(_run_result())

    assert isinstance(bundle, TrackerReportBundle)
    assert "Maya Pipeline Inspector Validation Report" in bundle.markdown_note
    assert bundle.html_report_path
    assert Path(bundle.html_report_path).is_file()
    assert "hero_pipeline_inspector_report.html" in bundle.html_report_path.replace("\\", "/")


def test_build_tracker_report_bundle_can_skip_html_generation(tmp_path: Path, monkeypatch):
    temp_root = tmp_path / "tracker_reports"
    monkeypatch.setattr(
        "pipeline_inspector.integrations.trackers.report_bundle.tempfile.gettempdir",
        lambda: str(temp_root),
    )

    bundle = build_tracker_report_bundle_from_run(_run_result(), include_html=False)

    assert bundle.markdown_note
    assert bundle.html_report_path == ""
    assert not any(temp_root.iterdir()) if temp_root.exists() else True


def test_build_tracker_report_bundle_reuses_existing_report_path(tmp_path: Path):
    existing = tmp_path / "existing_report.html"
    existing.write_text("<html>report</html>", encoding="utf-8")

    bundle = build_tracker_report_bundle_from_run(
        _run_result(),
        report_path=str(existing),
    )

    assert bundle.html_report_path == str(existing)
    assert "Broken rule." in bundle.markdown_note
