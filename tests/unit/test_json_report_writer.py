from __future__ import annotations

import json
from pathlib import Path

from shader_health.core import GraphSnapshot, RuleResult
from shader_health.reports import (
    REPORT_SCHEMA_VERSION,
    build_json_report,
    dumps_json_report,
    write_json_report,
)


def make_snapshot() -> GraphSnapshot:
    return GraphSnapshot(
        scene_path="D:/show/asset/shading/demo.ma",
        maya_version="2025",
        renderer="vray",
        scan_scope="scene",
        scanned_at_utc="2026-07-01T12:00:00Z",
    )


def make_result(
    rule_id: str,
    severity: str,
    *,
    status: str = "failed",
    block_publish: bool = False,
    block_deadline: bool = False,
) -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        severity=severity,
        status=status,
        title="Demo rule",
        message="Demo issue.",
        why="Demo explanation.",
        owner="shader_td",
        target_kind="node",
        target_id="node:file_demo",
        node="file_demo",
        plug="colorSpace",
        current_value="ACEScg",
        expected_value="Raw",
        block_publish=block_publish,
        block_deadline=block_deadline,
        auto_fix_available=True,
        fix_id="set_attr",
        graph_trace=["file_demo.outColor", "demo_mtl.baseColor"],
        evidence={"semantic_slot": "roughness"},
    )


def test_json_report_contains_schema_summary_score_block_status_and_results():
    snapshot = make_snapshot()
    results = [
        make_result("common.texture.colorspace.data_raw", "critical", block_publish=True),
        make_result("common.texture.path.local_drive", "warning"),
    ]

    report = build_json_report(snapshot, results)

    assert report["report_schema_version"] == REPORT_SCHEMA_VERSION
    assert report["snapshot_schema_version"] == "1.0"
    assert report["status"] == "failed"
    assert report["block_publish"] is True
    assert report["block_deadline"] is False
    assert report["blocking"] == {
        "any": True,
        "deadline": False,
        "publish": True,
    }
    assert report["summary"]["failed"] == 2
    assert report["summary"]["critical"] == 1
    assert report["summary"]["warning"] == 1
    assert report["score"]["score"] == 49
    assert report["health_score"] == 49
    assert report["snapshot"] == {
        "maya_version": "2025",
        "renderer": "vray",
        "scan_scope": "scene",
        "scene_path": "D:/show/asset/shading/demo.ma",
        "schema_version": "1.0",
        "scanned_at_utc": "2026-07-01T12:00:00Z",
    }
    assert report["results"][0]["rule_id"] == "common.texture.colorspace.data_raw"
    assert report["results"][0]["block_publish"] is True
    assert report["results"][0]["fix_id"] == "set_attr"


def test_json_report_output_is_deterministic():
    snapshot = make_snapshot()
    results = [
        make_result("z.rule", "warning"),
        make_result("a.rule", "error", block_deadline=True),
    ]

    first = dumps_json_report(snapshot, results)
    second = dumps_json_report(snapshot, list(reversed(results)))

    assert first == second
    assert first.endswith("\n")
    assert json.loads(first)["results"][0]["rule_id"] == "a.rule"


def test_json_report_writer_writes_utf8_file(tmp_path: Path):
    snapshot = make_snapshot()
    result = make_result("common.texture.colorspace.data_raw", "critical")
    output_path = tmp_path / "nested" / "report.json"

    written_path = write_json_report(output_path, snapshot, [result])

    assert written_path == output_path
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["report_schema_version"] == REPORT_SCHEMA_VERSION
    assert payload["results"][0]["rule_id"] == "common.texture.colorspace.data_raw"


def test_json_report_passed_status_without_failed_results():
    snapshot = make_snapshot()
    result = make_result(
        "common.texture.colorspace.data_raw",
        "critical",
        status="passed",
    )

    report = build_json_report(snapshot, [result])

    assert report["status"] == "passed"
    assert report["block_publish"] is False
    assert report["block_deadline"] is False
    assert report["summary"]["passed"] == 1
    assert report["score"]["score"] == 100
    assert "fix_audit" not in report


def test_json_report_includes_optional_fix_audit_section():
    snapshot = make_snapshot()
    fix_audit = {
        "applied_at_utc": "2026-07-03T12:00:00Z",
        "scene_path": snapshot.scene_path,
        "profile_id": "artist_relaxed",
        "undo_chunk_name": "Shader Health Apply Fixes",
        "total": 1,
        "applied_count": 1,
        "blocked_count": 0,
        "failed_count": 0,
        "records": [],
    }

    report = build_json_report(snapshot, [], fix_audit=fix_audit)

    assert report["fix_audit"] == fix_audit
