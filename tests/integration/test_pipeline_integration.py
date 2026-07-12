"""Integration tests for the shared validation and reporting pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from tests.integration.fixtures import broken_scene_snapshot

from pipeline_inspector import cli
from pipeline_inspector.maya.validation_pipeline import run_validation
from pipeline_inspector.reports.html_report import build_html_report, write_html_report
from pipeline_inspector.reports.json_report import write_json_report


def test_packaged_pipeline_produces_failed_results_and_reports(tmp_path: Path):
    snapshot = broken_scene_snapshot(tmp_path)
    run = run_validation(snapshot, profile_id="publish_strict", scan_scope="scene")

    assert run.profile_id == "publish_strict"
    failed = [item for item in run.results if item.status == "failed"]
    assert failed
    assert run.health_score.score < 100

    json_path = tmp_path / "report.json"
    html_path = tmp_path / "report.html"
    write_json_report(json_path, run.snapshot, run.results)
    write_html_report(html_path, run.snapshot, run.results)

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    html = html_path.read_text(encoding="utf-8")
    assert payload["status"] == "failed"
    assert payload["health_score"] == run.health_score.score
    assert "<!doctype html>" in html.casefold()
    assert "Severity Groups" in html
    assert "Publish Block" in html
    assert "common.texture.colorspace.data_raw" in html


def test_ci_headless_profile_runs_through_cli_on_snapshot(tmp_path: Path):
    snapshot = broken_scene_snapshot(tmp_path)
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(snapshot.to_json(), encoding="utf-8")
    report_path = tmp_path / "ci_report.json"

    exit_code = cli.main(
        [
            "validate",
            str(snapshot_path),
            "--input-kind",
            "snapshot",
            "--profile-id",
            "ci_headless",
            "--report",
            str(report_path),
        ]
    )

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert report_path.exists()
    assert payload["summary"]["total"] >= 1
    assert exit_code in {
        cli.EXIT_OK,
        cli.EXIT_PUBLISH_BLOCK,
        cli.EXIT_DEADLINE_BLOCK,
    }


def test_html_report_is_self_contained_and_includes_enriched_fields(tmp_path: Path):
    snapshot = broken_scene_snapshot(tmp_path)
    run = run_validation(snapshot, profile_id="artist_relaxed", scan_scope="scene")
    html = build_html_report(run.snapshot, run.results)

    assert "href=" not in html
    assert "http://" not in html
    assert "https://" not in html
    assert "table-wrap" in html
    assert "score-ring" in html
    assert any(item.material for item in run.results if item.status == "failed")
