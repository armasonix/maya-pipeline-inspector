from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from tests.unit.test_manifest_diff_command import old_manifest

from shader_health.core import GraphSnapshot
from shader_health.maya import commands, export_actions
from shader_health.reports.manifest import build_shader_manifest
from shader_health.ui import main_window


def make_snapshot(scene_path: str) -> GraphSnapshot:
    return GraphSnapshot(
        scene_path=scene_path,
        maya_version="2025",
        renderer="vray",
        scan_scope="scene",
        scanned_at_utc="2026-07-01T12:00:00Z",
    )


def test_export_json_report_writes_report_file(tmp_path: Path):
    output_path = tmp_path / "report.json"

    result = export_actions.export_json_report(
        output_path,
        snapshot=make_snapshot(str(tmp_path / "demo.ma")),
    )

    assert result.succeeded is True
    assert result.action == "export_json_report"
    assert Path(result.path) == output_path
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["report_schema_version"] == "1.0"


def test_export_html_report_writes_report_file(tmp_path: Path):
    output_path = tmp_path / "report.html"

    result = export_actions.export_html_report(
        output_path,
        snapshot=make_snapshot(str(tmp_path / "demo.ma")),
    )

    assert result.succeeded is True
    assert Path(result.path) == output_path
    assert "Maya Shader Health Report" in output_path.read_text(encoding="utf-8")


def test_export_shader_manifest_writes_manifest_file(tmp_path: Path):
    output_path = tmp_path / "manifest.json"

    result = export_actions.export_shader_manifest(
        output_path,
        snapshot=make_snapshot(str(tmp_path / "demo.ma")),
    )

    assert result.succeeded is True
    assert Path(result.path) == output_path
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["manifest_schema_version"] == "1.0"


def test_export_fix_plan_writes_fix_plan_file(tmp_path: Path):
    from shader_health.core.fix_plan import FixPlan

    output_path = tmp_path / "fix_plan.json"
    fix_plan = FixPlan()

    result = export_actions.export_fix_plan(
        output_path,
        fix_plan=fix_plan,
        snapshot=make_snapshot(str(tmp_path / "demo.ma")),
        profile_id="artist_relaxed",
    )

    assert result.succeeded is True
    assert result.action == "export_fix_plan"
    assert Path(result.path) == output_path
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["fix_plan_schema_version"] == "1.0"
    assert payload["profile_id"] == "artist_relaxed"
    assert payload["actions"] == []


def test_export_fix_plan_uses_scene_based_default_path(tmp_path: Path):
    from shader_health.core.fix_plan import FixPlan

    scene_path = tmp_path / "asset_shading.ma"

    result = export_actions.export_fix_plan(
        fix_plan=FixPlan(),
        snapshot=make_snapshot(str(scene_path)),
        profile_id="artist_relaxed",
    )

    assert Path(result.path) == tmp_path / "asset_shading_shader_health_fix_plan.json"


def test_export_json_report_uses_scene_based_default_path(tmp_path: Path):
    scene_path = tmp_path / "asset_shading.ma"

    result = export_actions.export_json_report(snapshot=make_snapshot(str(scene_path)))

    assert Path(result.path) == tmp_path / "asset_shading_shader_health_report.json"


def test_export_manifest_diff_writes_json_and_html_outputs(tmp_path: Path):
    baseline_path = tmp_path / "baseline_manifest.json"
    baseline_path.write_text(json.dumps(old_manifest()), encoding="utf-8")
    snapshot = make_snapshot(str(tmp_path / "asset_shading.ma"))
    json_path = tmp_path / "manifest_diff.json"
    html_path = tmp_path / "manifest_diff.html"

    result = export_actions.export_manifest_diff(
        baseline_path,
        json_path=json_path,
        html_path=html_path,
        snapshot=snapshot,
    )

    assert result.succeeded is True
    assert result.action == "export_manifest_diff"
    assert Path(result.path) == json_path
    assert json.loads(json_path.read_text(encoding="utf-8"))["summary"]["changed"] >= 0
    html = html_path.read_text(encoding="utf-8")
    assert "Maya Shader Health Manifest Diff" in html


def test_export_manifest_diff_uses_scene_based_default_paths(tmp_path: Path):
    baseline_path = tmp_path / "baseline_manifest.json"
    baseline_path.write_text(json.dumps(old_manifest()), encoding="utf-8")
    scene_path = tmp_path / "asset_shading.ma"

    result = export_actions.export_manifest_diff(
        baseline_path,
        snapshot=make_snapshot(str(scene_path)),
    )

    assert result.succeeded is True
    assert Path(result.path) == tmp_path / "asset_shading_shader_health_manifest_diff.json"
    assert (tmp_path / "asset_shading_shader_health_manifest_diff.html").is_file()


def test_export_manifest_diff_reports_invalid_baseline(tmp_path: Path):
    missing_baseline = tmp_path / "missing_baseline.json"

    result = export_actions.export_manifest_diff(
        missing_baseline,
        snapshot=make_snapshot(str(tmp_path / "asset_shading.ma")),
    )

    assert result.succeeded is False
    assert result.action == "export_manifest_diff"
    assert "does not exist" in result.message


def test_export_manifest_diff_does_not_mutate_scene_snapshot(tmp_path: Path):
    baseline_path = tmp_path / "baseline_manifest.json"
    baseline_path.write_text(json.dumps(old_manifest()), encoding="utf-8")
    snapshot = make_snapshot(str(tmp_path / "asset_shading.ma"))
    before = build_shader_manifest(snapshot)

    export_actions.export_manifest_diff(baseline_path, snapshot=snapshot)

    assert build_shader_manifest(snapshot) == before


def test_export_command_wrappers_delegate(monkeypatch: Any):
    calls: list[tuple[str, Optional[str]]] = []
    result = export_actions.ExportActionResult("action", "path", True, "ok")

    monkeypatch.setattr(
        commands,
        "_export_json_report",
        lambda path: calls.append(("json", path)) or result,
    )
    monkeypatch.setattr(
        commands,
        "_export_html_report",
        lambda path: calls.append(("html", path)) or result,
    )
    monkeypatch.setattr(
        commands,
        "_export_shader_manifest",
        lambda path: calls.append(("manifest", path)) or result,
    )
    monkeypatch.setattr(
        commands,
        "_export_fix_plan",
        lambda path: calls.append(("fix_plan", path)) or result,
    )
    monkeypatch.setattr(
        commands,
        "_export_manifest_diff_with_snapshot",
        lambda snapshot, **kwargs: calls.append(("manifest_diff", snapshot)) or result,
    )

    assert commands.export_json_report_action("report.json") is result
    assert commands.export_html_report_action("report.html") is result
    assert commands.export_shader_manifest_action("manifest.json") is result
    assert commands.export_fix_plan_action("fix_plan.json") is result
    assert commands.export_manifest_diff_action("baseline.json") is result
    assert calls == [
        ("json", "report.json"),
        ("html", "report.html"),
        ("manifest", "manifest.json"),
        ("fix_plan", "fix_plan.json"),
        ("manifest_diff", None),
    ]


class FakeSignal:
    def __init__(self) -> None:
        self.callback: Optional[Any] = None

    def connect(self, callback: Any) -> None:
        self.callback = callback

    def emit(self) -> None:
        assert self.callback is not None
        self.callback()


class FakeWidget:
    def __init__(self) -> None:
        self.object_name: Optional[str] = None
        self.children: list[Any] = []

    def setObjectName(self, object_name: str) -> None:
        self.object_name = object_name


class FakeLabel(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.text = text


class FakePushButton(FakeLabel):
    def __init__(self, text: str = "") -> None:
        super().__init__(text)
        self.clicked = FakeSignal()
        self.tooltip = ""

    def setToolTip(self, text: str) -> None:
        self.tooltip = text


class FakeVBoxLayout:
    def __init__(self, parent: FakeWidget) -> None:
        self.parent = parent

    def setContentsMargins(self, left: int, top: int, right: int, bottom: int) -> None:
        _ = (left, top, right, bottom)

    def setSpacing(self, spacing: int) -> None:
        _ = spacing

    def addWidget(self, widget: Any) -> None:
        self.parent.children.append(widget)


class FakeQtWidgets:
    QWidget = FakeWidget
    QLabel = FakeLabel
    QPushButton = FakePushButton
    QVBoxLayout = FakeVBoxLayout


def test_export_buttons_connect_to_callbacks():
    calls: list[str] = []
    callbacks = main_window.ExportActionCallbacks(
        on_export_json=lambda: calls.append("json"),
        on_export_html=lambda: calls.append("html"),
        on_export_manifest=lambda: calls.append("manifest"),
        on_export_manifest_diff=lambda: calls.append("manifest_diff"),
        on_export_fix_plan=lambda: calls.append("fix_plan"),
    )

    widget = main_window.build_export_actions(FakeQtWidgets, callbacks=callbacks)

    _find(widget, main_window.EXPORT_JSON_BUTTON_OBJECT_NAME).clicked.emit()
    _find(widget, main_window.EXPORT_HTML_BUTTON_OBJECT_NAME).clicked.emit()
    _find(widget, main_window.EXPORT_MANIFEST_BUTTON_OBJECT_NAME).clicked.emit()
    _find(widget, main_window.EXPORT_MANIFEST_DIFF_BUTTON_OBJECT_NAME).clicked.emit()
    _find(widget, main_window.EXPORT_FIX_PLAN_BUTTON_OBJECT_NAME).clicked.emit()
    assert calls == ["json", "html", "manifest", "manifest_diff", "fix_plan"]


def _find(widget: Any, object_name: str) -> Any:
    stack = [widget]
    while stack:
        current = stack.pop()
        if getattr(current, "object_name", None) == object_name:
            return current
        stack.extend(getattr(current, "children", []))
    raise AssertionError(f"Could not find object named {object_name!r}")
