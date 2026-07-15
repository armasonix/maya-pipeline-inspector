from __future__ import annotations

from pathlib import Path

from pipeline_inspector.core import GraphSnapshot, RuleResult
from pipeline_inspector.reports.markdown_report import build_markdown_report, write_markdown_report


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
    message: str = "Demo issue.",
) -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        severity=severity,
        status=status,
        title="Demo rule",
        message=message,
        why="Demo explanation.",
        owner="shader_td",
        target_kind="node",
        target_id="node:file_demo",
        node="file_demo",
        plug="colorSpace",
        current_value="ACEScg",
        expected_value="Raw",
    )


def test_build_markdown_report_includes_summary_and_failed_issues():
    markdown = build_markdown_report(
        make_snapshot(),
        [
            make_result("R001", "critical"),
            make_result("R002", "warning", status="passed"),
        ],
    )

    assert "# Maya Pipeline Inspector Validation Report" in markdown
    assert "**Scene:** `D:/show/asset/shading/demo.ma`" in markdown
    assert "**Health score:**" in markdown
    assert "### Critical (1)" in markdown
    assert "**R001**" in markdown
    assert "_No failed issues._" not in markdown


def test_build_markdown_report_shows_empty_failed_section():
    markdown = build_markdown_report(make_snapshot(), [])

    assert "## Failed issues" in markdown
    assert "_No failed issues._" in markdown


def test_write_markdown_report_writes_utf8_file(tmp_path: Path):
    output_path = tmp_path / "report.md"
    written_path = write_markdown_report(
        output_path,
        make_snapshot(),
        [make_result("R001", "error")],
    )

    assert written_path == output_path
    text = output_path.read_text(encoding="utf-8")
    assert "Maya Pipeline Inspector Validation Report" in text
