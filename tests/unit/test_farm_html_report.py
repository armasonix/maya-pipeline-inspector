from __future__ import annotations

from pathlib import Path

from pipeline_inspector.reports.farm_html_report import (
    build_farm_html_report,
    sample_farm_analytics_report,
    write_farm_html_report,
)


def test_farm_html_report_is_self_contained_with_kpis_and_svg_charts():
    report = sample_farm_analytics_report()
    html = build_farm_html_report(report, api_url="")

    assert html.startswith("<!doctype html>")
    assert "<style>" in html
    assert "metric-grid" in html
    assert "Key Metrics" in html
    assert "Farm KPI Dashboard" in html
    assert "chart-grid" in html
    assert "repeat(4" in html or "grid-template-columns: repeat(4" in html
    assert "donut-center-value" in html
    assert "Throughput (jobs/hour)" in html
    assert "4.50" in html
    assert "12.0%" in html
    assert '<svg class="chart-svg"' in html
    assert "Job Mix" not in html
    assert "Pool Utilization" not in html or "Pool utilization" in html
    assert "Farm Operations" in html
    assert "Frame Economics" in html
    assert "Shot Intelligence" in html
    assert "beauty" in html
    assert "href=" not in html
    assert "http://" not in html
    assert "https://" not in html
    assert '"failure_rate"' not in html
    assert '"job_totals"' not in html


def test_write_farm_html_report_writes_file(tmp_path: Path):
    report = sample_farm_analytics_report()
    output = tmp_path / "farm_report.html"

    written = write_farm_html_report(output, report)

    assert written == output
    assert output.is_file()
    content = output.read_text(encoding="utf-8")
    assert "Deadline Farm Intelligence Report" in content
    assert "<svg" in content


def test_sample_fixture_matches_writer_output(tmp_path: Path):
    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "deadline_farm_report_sample.html"
    )
    report = sample_farm_analytics_report()
    expected = build_farm_html_report(report, api_url="")

    assert fixture_path.is_file()
    assert fixture_path.read_text(encoding="utf-8") == expected
