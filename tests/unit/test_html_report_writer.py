from __future__ import annotations

from pathlib import Path

from shader_health.core import GraphSnapshot, RuleResult
from shader_health.reports.html_report import build_html_report, write_html_report


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
        block_publish=block_publish,
        block_deadline=block_deadline,
    )


def test_html_report_is_self_contained_and_shows_blocking_status():
    html = build_html_report(
        make_snapshot(),
        [
            make_result(
                "common.texture.colorspace.data_raw",
                "critical",
                block_publish=True,
            ),
            make_result("common.texture.path.local_drive", "warning"),
        ],
    )

    assert html.startswith("<!doctype html>")
    assert "<style>" in html
    assert "href=" not in html
    assert "http://" not in html
    assert "https://" not in html
    assert "Publish Block" in html
    assert "Deadline Block" in html
    assert "Any Block" in html
    assert "YES" in html
    assert "NO" in html


def test_html_report_shows_severity_groups_and_results():
    html = build_html_report(
        make_snapshot(),
        [
            make_result("z.rule", "warning"),
            make_result("a.rule", "critical", block_deadline=True),
        ],
    )

    assert "Severity Groups" in html
    assert "Critical (1)" in html
    assert "Error (0)" in html
    assert "Warning (1)" in html
    assert "Info (0)" in html
    assert "a.rule" in html
    assert "z.rule" in html
    assert html.index("a.rule") < html.index("z.rule")


def test_html_report_escapes_user_controlled_text():
    html = build_html_report(
        make_snapshot(),
        [
            make_result(
                "common.texture.bad_value",
                "error",
                message="Bad <texture> & unsafe value.",
            )
        ],
    )

    assert "Bad &lt;texture&gt; &amp; unsafe value." in html
    assert "Bad <texture> & unsafe value." not in html


def test_html_report_writer_writes_utf8_file(tmp_path: Path):
    output_path = tmp_path / "nested" / "report.html"

    written_path = write_html_report(
        output_path,
        make_snapshot(),
        [make_result("common.texture.colorspace.data_raw", "critical")],
    )

    assert written_path == output_path
    assert output_path.exists()
    html = output_path.read_text(encoding="utf-8")
    assert "Maya Shader Health Report" in html
    assert "common.texture.colorspace.data_raw" in html
