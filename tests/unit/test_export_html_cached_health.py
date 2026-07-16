from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from pipeline_inspector.core import GraphSnapshot, RuleResult
from pipeline_inspector.core.scoring import compute_health_score
from pipeline_inspector.maya import ui_launcher


def _make_snapshot(scene_path: str) -> GraphSnapshot:
    return GraphSnapshot(
        scene_path=scene_path,
        maya_version="2025",
        renderer="vray",
        scan_scope="scene",
        scanned_at_utc="2026-07-01T12:00:00Z",
    )


def _failed_error() -> RuleResult:
    return RuleResult(
        rule_id="texture.missing",
        status="failed",
        severity="error",
        title="Missing texture",
        message="Missing texture",
        why="Publish requires resolvable texture paths.",
        owner="lookdev",
        target_kind="file",
        target_id="file:hero_baseColor",
    )


def test_export_html_from_ui_uses_cached_validation_results(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    results = (_failed_error(),)
    cached_health = compute_health_score(results).score
    scene_path = str(tmp_path / "hero.ma")
    content = SimpleNamespace(
        _pipeline_inspector_snapshot=_make_snapshot(scene_path),
        _pipeline_inspector_results=results,
        _pipeline_inspector_profile_id="publish_strict",
        _pipeline_inspector_scan_scope="scene",
        _pipeline_inspector_last_validated_at="",
        _pipeline_inspector_scene_path=scene_path,
    )

    def _fail_revalidate() -> None:
        raise AssertionError("HTML export should not revalidate when cached state exists")

    monkeypatch.setattr(ui_launcher, "_active_panel_content", lambda: content)
    monkeypatch.setattr(ui_launcher, "load_qt_widgets", lambda: SimpleNamespace())
    monkeypatch.setattr(ui_launcher, "_set_reports_status_label", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "pipeline_inspector.maya.commands.export_html_report_action",
        _fail_revalidate,
    )

    captured: list[Path] = []

    def _capture_export(result: object) -> None:
        captured.append(Path(result.path))

    monkeypatch.setattr(ui_launcher, "_print_export_result", _capture_export)

    ui_launcher._export_html_from_ui()

    assert len(captured) == 1
    html = captured[0].read_text(encoding="utf-8")
    match = re.search(r'<span class="score-value">(\d+)</span>', html)
    assert match is not None
    assert int(match.group(1)) == cached_health
