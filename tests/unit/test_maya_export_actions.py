from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from shader_health.core import GraphSnapshot
from shader_health.maya import commands, export_actions
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


def test_export_json_report_uses_scene_based_default_path(tmp_path: Path):
    scene_path = tmp_path / "asset_shading.ma"

    result = export_actions.export_json_report(snapshot=make_snapshot(str(scene_path)))

    assert Path(result.path) == tmp_path / "asset_shading_shader_health_report.json"


def test_export_command_wrappers_delegate(monkeypatch: Any):
    calls: list[tuple[str, Optional[str]]] = []
    result = export_actions.ExportActionResult("action", "path", True, "ok")

    monkeypatch.setattr(
        commands,
        "export_json_report",
        lambda path=None: calls.append(("json", path)) or result,
    )
    monkeypatch.setattr(
        commands,
        "export_html_report",
        lambda path=None: calls.append(("html", path)) or result,
    )
    monkeypatch.setattr(
        commands,
        "export_shader_manifest",
        lambda path=None: calls.append(("manifest", path)) or result,
    )

    assert commands.export_json_report_action("report.json") is result
    assert commands.export_html_report_action("report.html") is result
    assert commands.export_shader_manifest_action("manifest.json") is result
    assert calls == [
        ("json", "report.json"),
        ("html", "report.html"),
        ("manifest", "manifest.json"),
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
    )

    widget = main_window.build_export_actions(FakeQtWidgets, callbacks=callbacks)

    _find(widget, main_window.EXPORT_JSON_BUTTON_OBJECT_NAME).clicked.emit()
    _find(widget, main_window.EXPORT_HTML_BUTTON_OBJECT_NAME).clicked.emit()
    _find(widget, main_window.EXPORT_MANIFEST_BUTTON_OBJECT_NAME).clicked.emit()
    assert calls == ["json", "html", "manifest"]


def _find(widget: Any, object_name: str) -> Any:
    stack = [widget]
    while stack:
        current = stack.pop()
        if getattr(current, "object_name", None) == object_name:
            return current
        stack.extend(getattr(current, "children", []))
    raise AssertionError(f"Could not find object named {object_name!r}")
