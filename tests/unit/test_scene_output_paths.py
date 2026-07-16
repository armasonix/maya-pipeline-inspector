from __future__ import annotations

from pathlib import Path

from pipeline_inspector.reports.scene_output_paths import (
    default_farm_html_report_path,
    default_scene_export_path,
    legacy_scene_export_path,
    resolve_existing_scene_export_path,
)


def test_default_scene_export_path_uses_reports_subfolders(tmp_path: Path):
    scene = tmp_path / "asset_shading.ma"
    resolved = default_scene_export_path(scene, suffix="report", extension="json")

    assert resolved == (
        tmp_path / "reports" / "validation" / "asset_shading_pipeline_inspector_report.json"
    )


def test_resolve_existing_scene_export_path_prefers_organized_layout(tmp_path: Path):
    scene = tmp_path / "asset_shading.ma"
    organized = default_scene_export_path(scene, suffix="manifest", extension="json")
    organized.parent.mkdir(parents=True, exist_ok=True)
    organized.write_text("{}", encoding="utf-8")

    assert (
        resolve_existing_scene_export_path(scene, suffix="manifest", extension="json")
        == organized
    )


def test_resolve_existing_scene_export_path_falls_back_to_legacy_layout(tmp_path: Path):
    scene = tmp_path / "asset_shading.ma"
    legacy = legacy_scene_export_path(scene, suffix="manifest", extension="json")
    legacy.write_text("{}", encoding="utf-8")

    assert resolve_existing_scene_export_path(scene, suffix="manifest", extension="json") == legacy


def test_default_farm_html_report_path_uses_reports_farm(tmp_path: Path):
    scene = tmp_path / "asset_shading.ma"
    assert default_farm_html_report_path(scene) == (
        tmp_path / "reports" / "farm" / "asset_shading_deadline_farm_report.html"
    )
