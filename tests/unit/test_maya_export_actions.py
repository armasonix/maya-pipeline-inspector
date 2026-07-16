from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

import pytest
from tests.unit.test_manifest_diff_command import old_manifest

from pipeline_inspector.core import GraphSnapshot, MaterialSnapshot, RuleResult
from pipeline_inspector.maya import commands, export_actions
from pipeline_inspector.reports.manifest import build_shader_manifest
from pipeline_inspector.ui import main_window


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
    assert "Maya Pipeline Inspector Report" in output_path.read_text(encoding="utf-8")


def test_export_shader_manifest_writes_manifest_file(tmp_path: Path):
    output_path = tmp_path / "manifest.json"

    result = export_actions.export_shader_manifest(
        output_path,
        snapshot=make_snapshot(str(tmp_path / "demo.ma")),
    )

    assert result.succeeded is True
    assert Path(result.path) == output_path
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["manifest_schema_version"] == "1.1"


def test_build_shader_manifest_includes_health_score_and_material_issues():
    snapshot = GraphSnapshot(
        scene_path="D:/show/asset/shading/demo.ma",
        maya_version="2025",
        renderer="vray",
        scan_scope="scene",
        scanned_at_utc="2026-07-01T12:00:00Z",
        materials=[
            MaterialSnapshot(
                node_id="node:hero_mtl",
                name="hero_mtl",
                type_name="VRayMtl",
                graph_fingerprint="sha256:hero_graph",
            )
        ],
    )
    results = [
        RuleResult(
            rule_id="common.texture.missing",
            severity="error",
            status="failed",
            title="Missing texture",
            message="Texture file is missing.",
            why="Publish requires resolvable texture paths.",
            owner="lookdev",
            material="hero_mtl",
        ),
        RuleResult(
            rule_id="common.texture.path_policy",
            severity="warning",
            status="failed",
            title="Local texture path",
            message="Texture path is not publish-safe.",
            why="Farm machines cannot resolve local paths.",
            owner="pipeline",
            material="hero_mtl",
        ),
    ]

    manifest = build_shader_manifest(snapshot, results=results)

    assert manifest["manifest_schema_version"] == "1.1"
    assert manifest["health_score"] == 87
    issues = manifest["materials"][0]["issues"]
    assert issues["failed"] == 2
    assert issues["error"] == 1
    assert issues["warning"] == 1
    assert issues["rule_ids"] == ["common.texture.missing", "common.texture.path_policy"]


def test_build_shader_manifest_uses_explicit_health_score_override():
    snapshot = make_snapshot("demo.ma")

    manifest = build_shader_manifest(snapshot, health_score=42)

    assert manifest["health_score"] == 42
    assert manifest["materials"] == []


def test_export_fix_plan_writes_fix_plan_file(tmp_path: Path):
    from pipeline_inspector.core.fix_plan import FixPlan

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
    from pipeline_inspector.core.fix_plan import FixPlan

    scene_path = tmp_path / "asset_shading.ma"

    result = export_actions.export_fix_plan(
        fix_plan=FixPlan(),
        snapshot=make_snapshot(str(scene_path)),
        profile_id="artist_relaxed",
    )

    assert Path(result.path) == (
        tmp_path / "reports" / "fix_plans" / "asset_shading_pipeline_inspector_fix_plan.json"
    )


def test_export_json_report_uses_scene_based_default_path(tmp_path: Path):
    scene_path = tmp_path / "asset_shading.ma"

    result = export_actions.export_json_report(snapshot=make_snapshot(str(scene_path)))

    assert Path(result.path) == (
        tmp_path / "reports" / "validation" / "asset_shading_pipeline_inspector_report.json"
    )


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
    assert "Maya Pipeline Inspector Manifest Diff" in html


def test_export_manifest_diff_uses_scene_based_default_paths(tmp_path: Path):
    baseline_path = tmp_path / "baseline_manifest.json"
    baseline_path.write_text(json.dumps(old_manifest()), encoding="utf-8")
    scene_path = tmp_path / "asset_shading.ma"

    result = export_actions.export_manifest_diff(
        baseline_path,
        snapshot=make_snapshot(str(scene_path)),
    )

    assert result.succeeded is True
    assert Path(result.path) == (
        tmp_path / "reports" / "manifests" / "asset_shading_pipeline_inspector_manifest_diff.json"
    )
    assert (
        tmp_path / "reports" / "manifests" / "asset_shading_pipeline_inspector_manifest_diff.html"
    ).is_file()


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
    calls: list[tuple[str, Optional[str], dict[str, Any]]] = []
    result = export_actions.ExportActionResult("action", "path", True, "ok")

    monkeypatch.setattr(
        commands,
        "_export_json_report",
        lambda path: calls.append(("json", path, {})) or result,
    )
    monkeypatch.setattr(
        commands,
        "_export_html_report",
        lambda path: calls.append(("html", path, {})) or result,
    )
    monkeypatch.setattr(
        commands,
        "_export_shader_manifest",
        lambda path: calls.append(("manifest", path, {})) or result,
    )
    monkeypatch.setattr(
        commands,
        "_export_fix_plan",
        lambda path: calls.append(("fix_plan", path, {})) or result,
    )
    monkeypatch.setattr(
        commands,
        "_export_manifest_diff_with_snapshot",
        lambda snapshot, **kwargs: calls.append(("manifest_diff", snapshot, kwargs)) or result,
    )

    assert commands.export_json_report_action("report.json") is result
    assert commands.export_html_report_action("report.html") is result
    assert commands.export_shader_manifest_action("manifest.json") is result
    assert commands.export_fix_plan_action("fix_plan.json") is result
    assert commands.export_manifest_diff_action("baseline.json") is result
    assert commands.export_manifest_diff_action(prefer_approved_sidecar=True) is result
    assert calls == [
        ("json", "report.json", {}),
        ("html", "report.html", {}),
        ("manifest", "manifest.json", {}),
        ("fix_plan", "fix_plan.json", {}),
        (
            "manifest_diff",
            None,
            {
                "baseline_manifest_path": "baseline.json",
                "json_path": None,
                "html_path": None,
                "prefer_approved_sidecar": False,
            },
        ),
        (
            "manifest_diff",
            None,
            {
                "baseline_manifest_path": None,
                "json_path": None,
                "html_path": None,
                "prefer_approved_sidecar": True,
            },
        ),
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
        self.word_wrap = False

    def setWordWrap(self, enabled: bool) -> None:
        self.word_wrap = enabled


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

    def addWidget(self, widget: Any, stretch: Optional[int] = None) -> None:
        self.parent.children.append(widget)
        _ = stretch

    def addStretch(self, stretch: int) -> None:
        _ = stretch


class FakeHBoxLayout(FakeVBoxLayout):
    pass


class FakeGridLayout(FakeVBoxLayout):
    def addWidget(self, widget: Any, row: int = 0, column: int = 0, *_args: Any) -> None:
        self.parent.children.append(widget)
        _ = (row, column)


class FakeTableWidget(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.column_count = 0
        self.row_count = 0
        self.headers: list[str] = []

    def setColumnCount(self, count: int) -> None:
        self.column_count = count

    def setRowCount(self, count: int) -> None:
        self.row_count = count

    def setHorizontalHeaderLabels(self, headers: list[str]) -> None:
        self.headers = headers


class FakeTableWidgetItem:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeCheckBox(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.text = text
        self.checked = False
        self.stateChanged = FakeSignal()

    def setText(self, text: str) -> None:
        self.text = text

    def setChecked(self, checked: bool) -> None:
        self.checked = checked

    def isChecked(self) -> bool:
        return self.checked


class FakeQtWidgets:
    QWidget = FakeWidget
    QLabel = FakeLabel
    QPushButton = FakePushButton
    QVBoxLayout = FakeVBoxLayout
    QHBoxLayout = FakeHBoxLayout
    QGridLayout = FakeGridLayout
    QTableWidget = FakeTableWidget
    QTableWidgetItem = FakeTableWidgetItem
    QCheckBox = FakeCheckBox


def test_approved_manifest_sidecar_path_uses_scene_sidecar(tmp_path: Path):
    scene_path = tmp_path / "hero_shading.ma"
    sidecar = tmp_path / "reports" / "manifests" / "hero_shading_pipeline_inspector_manifest.json"
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text("{}", encoding="utf-8")
    snapshot = SimpleNamespace(scene_path=str(scene_path))

    resolved = commands._approved_manifest_sidecar_path(snapshot)

    assert resolved == str(sidecar)


def test_approved_manifest_sidecar_path_supports_legacy_sidecar(tmp_path: Path):
    scene_path = tmp_path / "hero_shading.ma"
    sidecar = tmp_path / "hero_shading_pipeline_inspector_manifest.json"
    sidecar.write_text("{}", encoding="utf-8")
    snapshot = SimpleNamespace(scene_path=str(scene_path))

    resolved = commands._approved_manifest_sidecar_path(snapshot)

    assert resolved == str(sidecar)


def test_approved_manifest_sidecar_path_returns_none_when_sidecar_missing(tmp_path: Path):
    snapshot = SimpleNamespace(scene_path=str(tmp_path / "hero_shading.ma"))

    assert commands._approved_manifest_sidecar_path(snapshot) is None


def test_export_manifest_diff_prefers_approved_sidecar_without_dialog(
    monkeypatch: Any,
    tmp_path: Path,
):
    scene_path = tmp_path / "hero_shading.ma"
    sidecar = tmp_path / "reports" / "manifests" / "hero_shading_pipeline_inspector_manifest.json"
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(json.dumps(old_manifest()), encoding="utf-8")
    snapshot = make_snapshot(str(scene_path))
    snapshot = GraphSnapshot(
        scene_path=str(scene_path),
        maya_version="2025",
        renderer="vray",
        scan_scope="scene",
        scanned_at_utc="2026-07-01T12:00:00Z",
        materials=[
            MaterialSnapshot(
                node_id="node:hero_mtl",
                name="hero_mtl",
                type_name="VRayMtl",
                renderer_family="vray",
            )
        ],
    )
    def fail_dialog() -> str:
        raise AssertionError("file picker should not open when approved sidecar exists")

    monkeypatch.setattr(commands, "_pick_baseline_manifest_json", fail_dialog)

    result = commands._export_manifest_diff_with_snapshot(
        snapshot,
        prefer_approved_sidecar=True,
    )

    assert result.succeeded is True
    assert Path(result.path).name == "hero_shading_pipeline_inspector_manifest_diff.json"
    assert (
        tmp_path / "reports" / "manifests" / "hero_shading_pipeline_inspector_manifest_diff.html"
    ).is_file()


def test_export_buttons_connect_to_callbacks():
    calls: list[str] = []
    callbacks = main_window.ExportActionCallbacks(
        on_export_json=lambda: calls.append("json"),
        on_export_html=lambda: calls.append("html"),
        on_export_manifest=lambda: calls.append("manifest"),
        on_export_manifest_diff=lambda: calls.append("manifest_diff"),
        on_compare_approved_manifest=lambda: calls.append("compare_approved_manifest"),
        on_send_to_tracker=lambda: calls.append("send_to_tracker"),
        on_export_farm_html=lambda: calls.append("farm_html"),
    )

    widget = main_window.build_export_actions(FakeQtWidgets, callbacks=callbacks)

    _find(widget, main_window.EXPORT_JSON_BUTTON_OBJECT_NAME).clicked.emit()
    _find(widget, main_window.EXPORT_HTML_BUTTON_OBJECT_NAME).clicked.emit()
    _find(widget, main_window.EXPORT_MANIFEST_BUTTON_OBJECT_NAME).clicked.emit()
    _find(widget, main_window.EXPORT_MANIFEST_DIFF_BUTTON_OBJECT_NAME).clicked.emit()
    _find(
        widget,
        main_window.EXPORT_COMPARE_APPROVED_MANIFEST_BUTTON_OBJECT_NAME,
    ).clicked.emit()
    _find(widget, main_window.EXPORT_SEND_TO_TRACKER_BUTTON_OBJECT_NAME).clicked.emit()
    _find(widget, main_window.EXPORT_FARM_HTML_BUTTON_OBJECT_NAME).clicked.emit()
    assert calls == [
        "json",
        "html",
        "manifest",
        "manifest_diff",
        "compare_approved_manifest",
        "send_to_tracker",
        "farm_html",
    ]


def test_reports_export_grid_includes_farm_html_button():
    widget = main_window.build_export_actions(FakeQtWidgets)

    button = _find(widget, main_window.EXPORT_FARM_HTML_BUTTON_OBJECT_NAME)
    assert button.text == "Export Farm HTML Report"


def test_reports_export_grid_includes_send_to_tracker_button():
    widget = main_window.build_export_actions(FakeQtWidgets)

    button = _find(widget, main_window.EXPORT_SEND_TO_TRACKER_BUTTON_OBJECT_NAME)
    assert button.text == "Send to Tracker"


def test_reports_export_grid_omits_manifest_gate_button():
    widget = main_window.build_export_actions(FakeQtWidgets)

    with pytest.raises(AssertionError):
        _find(widget, main_window.VALIDATE_MANIFEST_GATE_BUTTON_OBJECT_NAME)


def test_fix_queue_export_fix_plan_button_connects_to_callback():
    from pipeline_inspector.ui.fix_queue import (
        FIX_QUEUE_EXPORT_FIX_PLAN_BUTTON_OBJECT_NAME,
        FixQueueActionCallbacks,
        build_fix_queue,
    )

    calls: list[str] = []
    callbacks = FixQueueActionCallbacks(on_export_fix_plan=lambda: calls.append("fix_plan"))
    widget = build_fix_queue(FakeQtWidgets, callbacks=callbacks)

    _find(widget, FIX_QUEUE_EXPORT_FIX_PLAN_BUTTON_OBJECT_NAME).clicked.emit()
    assert calls == ["fix_plan"]


def _find(widget: Any, object_name: str) -> Any:
    stack = [widget]
    while stack:
        current = stack.pop()
        if getattr(current, "object_name", None) == object_name:
            return current
        stack.extend(getattr(current, "children", []))
    raise AssertionError(f"Could not find object named {object_name!r}")
