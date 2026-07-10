from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

from shader_health.core.manifest_gate import ManifestGatePolicy  # noqa: F401
from shader_health.maya import ui_launcher
from shader_health.ui import main_window


class FakePanel:
    def __init__(self) -> None:
        self.show_calls: list[dict[str, Any]] = []
        self.closed = False

    def show(self, **kwargs: Any) -> None:
        self.show_calls.append(dict(kwargs))

    def close(self) -> None:
        self.closed = True


class FakeCmds:
    def __init__(self, *, workspace_exists: bool) -> None:
        self.workspace_exists = workspace_exists
        self.deleted: list[tuple[str, dict[str, Any]]] = []
        self.restored: list[str] = []
        self.closed: list[str] = []

    def workspaceControl(self, name: str, **kwargs: Any) -> Optional[bool]:
        if kwargs.get("query") and kwargs.get("exists"):
            return self.workspace_exists
        if kwargs.get("edit") and kwargs.get("restore"):
            self.restored.append(name)
            return None
        if kwargs.get("edit") and kwargs.get("close"):
            self.closed.append(name)
            return None
        return None

    def deleteUI(self, name: str, **kwargs: Any) -> None:
        self.deleted.append((name, dict(kwargs)))
        self.workspace_exists = False


def test_show_panel_creates_dockable_panel(monkeypatch: Any):
    cmds = FakeCmds(workspace_exists=False)
    panel = FakePanel()
    monkeypatch.setattr(ui_launcher, "_PANEL", None)
    monkeypatch.setattr(ui_launcher, "_maya_cmds", lambda: cmds)
    monkeypatch.setattr(ui_launcher, "_create_dockable_panel", lambda: panel)

    result = ui_launcher.show_panel()

    assert result is panel
    assert panel.show_calls == [
        {
            "dockable": True,
            "area": "right",
            "floating": False,
            "retain": False,
        }
    ]


def test_show_panel_restores_existing_panel(monkeypatch: Any):
    cmds = FakeCmds(workspace_exists=True)
    panel = FakePanel()
    monkeypatch.setattr(ui_launcher, "_PANEL", panel)
    monkeypatch.setattr(ui_launcher, "_maya_cmds", lambda: cmds)

    result = ui_launcher.show_panel()

    assert result is panel
    assert cmds.restored == [ui_launcher.WORKSPACE_CONTROL_NAME]
    assert panel.show_calls == [{}]


def test_show_panel_recreates_stale_workspace_control(monkeypatch: Any):
    cmds = FakeCmds(workspace_exists=True)
    panel = FakePanel()
    monkeypatch.setattr(ui_launcher, "_PANEL", None)
    monkeypatch.setattr(ui_launcher, "_maya_cmds", lambda: cmds)
    monkeypatch.setattr(ui_launcher, "_create_dockable_panel", lambda: panel)

    result = ui_launcher.show_panel()

    assert result is panel
    assert cmds.deleted == [(ui_launcher.WORKSPACE_CONTROL_NAME, {"control": True})]
    assert panel.show_calls[0]["dockable"] is True


def test_show_farm_check_panel_selects_farm_tab_and_runs_preflight(monkeypatch: Any):
    panel = SimpleNamespace(_shader_health_content=object())
    calls: list[str] = []
    monkeypatch.setattr(ui_launcher, "show_panel", lambda: panel)
    monkeypatch.setattr(ui_launcher, "load_qt_widgets", lambda: object())
    monkeypatch.setattr(
        ui_launcher,
        "_select_farm_tab",
        lambda _content, _qt: calls.append("select"),
    )
    monkeypatch.setattr(
        ui_launcher,
        "_run_farm_preflight_from_ui",
        lambda _content, _qt: calls.append("preflight"),
    )

    result = ui_launcher.show_farm_check_panel()

    assert result is panel
    assert calls == ["select", "preflight"]


def test_close_panel_deletes_workspace_control(monkeypatch: Any):
    cmds = FakeCmds(workspace_exists=True)
    panel = FakePanel()
    monkeypatch.setattr(ui_launcher, "_PANEL", panel)
    monkeypatch.setattr(ui_launcher, "_maya_cmds", lambda: cmds)

    ui_launcher.close_panel()

    assert cmds.deleted == [(ui_launcher.WORKSPACE_CONTROL_NAME, {"control": True})]
    assert panel.closed is True
    assert ui_launcher._PANEL is None


def test_schedule_ui_validation_defers_validation_job(monkeypatch: Any):
    content = SimpleNamespace(_shader_health_validate_running=False)
    calls: list[str] = []

    class FakeCmds:
        def __init__(self) -> None:
            self.deferred: list[Any] = []

        def evalDeferred(self, fn: Any, lowestPriority: bool = True) -> None:
            _ = lowestPriority
            self.deferred.append(fn)

    cmds = FakeCmds()
    monkeypatch.setattr(ui_launcher, "_maya_cmds", lambda: cmds)
    monkeypatch.setattr(
        ui_launcher,
        "_set_validate_busy_state",
        lambda *_args, **_kwargs: calls.append("busy"),
    )
    monkeypatch.setattr(
        ui_launcher,
        "_run_validation_job",
        lambda *_args, **_kwargs: calls.append("run"),
    )

    ui_launcher._schedule_ui_validation(content, object(), scan_scope="scene")

    assert len(cmds.deferred) == 1
    cmds.deferred[0]()
    assert calls == ["busy", "run", "busy"]
    assert content._shader_health_validate_running is False


def test_update_severity_filter_options_restores_saved_preference(monkeypatch: Any):
    from shader_health.ui.issues_triage import IssueFilterPrefs, write_issue_filter_prefs

    class FakeCombo:
        def __init__(self) -> None:
            self.items: list[str] = []
            self.current = ""

        def blockSignals(self, _enabled: bool) -> None:
            return

        def clear(self) -> None:
            self.items.clear()

        def addItems(self, items: list[str]) -> None:
            self.items.extend(items)

        def setCurrentText(self, text: str) -> None:
            self.current = text

    content = SimpleNamespace()
    write_issue_filter_prefs(
        content,
        IssueFilterPrefs(severity="critical"),
    )
    combo = FakeCombo()
    monkeypatch.setattr(
        ui_launcher,
        "_find_child",
        lambda _content, _qt, name: (
            combo if name == main_window.ISSUES_SEVERITY_FILTER_OBJECT_NAME else None
        ),
    )

    class FakeQt:
        QComboBox = object

    ui_launcher._update_severity_filter_options(
        content,
        FakeQt(),
        (
            main_window.IssueTableRow(
                severity="critical",
                material="Hero",
                node="file1",
                issue="Missing",
                owner="lookdev",
                rule="missing_texture",
            ),
        ),
    )

    assert combo.current == "critical"


class FakeSignal:
    def __init__(self) -> None:
        self.handlers: list[Any] = []

    def connect(self, handler: Any) -> None:
        self.handlers.append(handler)

    def emit(self, *args: Any) -> None:
        for handler in self.handlers:
            handler(*args)


class FakeSplitter:
    def __init__(self) -> None:
        self.object_name = main_window.VALIDATE_ISSUES_SPLITTER_OBJECT_NAME
        self._sizes = [640, 187]
        self.applied_sizes: list[list[int]] = []
        self.splitterMoved = FakeSignal()

    def setObjectName(self, object_name: str) -> None:
        self.object_name = object_name

    def sizes(self) -> list[int]:
        return list(self._sizes)

    def setSizes(self, sizes: list[int]) -> None:
        self.applied_sizes.append([int(size) for size in sizes])
        self._sizes = [int(size) for size in sizes]


class FakeContent:
    def __init__(self, splitter: FakeSplitter) -> None:
        self.splitter = splitter

    def findChild(self, widget_type: Any, object_name: str) -> Any:
        _ = widget_type
        if object_name == main_window.VALIDATE_ISSUES_SPLITTER_OBJECT_NAME:
            return self.splitter
        return None


def test_validate_splitter_persistence_restores_saved_sizes():
    splitter = FakeSplitter()
    content = FakeContent(splitter)

    setattr(content, ui_launcher.VALIDATE_SPLITTER_SIZES_ATTR, (700, 200))
    ui_launcher._wire_validate_splitter_persistence(content, SimpleNamespace(QWidget=object))

    assert splitter.applied_sizes == [[700, 200]]


def test_validate_splitter_persistence_saves_sizes_on_move():
    splitter = FakeSplitter()
    content = FakeContent(splitter)

    ui_launcher._wire_validate_splitter_persistence(content, SimpleNamespace(QWidget=object))
    splitter._sizes = [650, 210]
    splitter.splitterMoved.emit()

    assert getattr(content, ui_launcher.VALIDATE_SPLITTER_SIZES_ATTR) == (650, 210)


def test_run_validation_job_notifies_telegram_after_successful_validation(monkeypatch: Any):
    from shader_health.core.scoring import HealthScore

    content = SimpleNamespace(
        _shader_health_studio_config=ui_launcher.StudioConfig.default(),
    )
    result = SimpleNamespace(
        succeeded=True,
        message="Scene validated.",
        snapshot=SimpleNamespace(scene_path="hero.ma"),
        scan_scope="scene",
        profile_id="lookdev",
        asset_class_id="",
        health_score=HealthScore(score=80, raw_score=80, block_publish=True),
    )
    calls: list[tuple[Any, Any]] = []

    monkeypatch.setattr(
        "shader_health.maya.commands.validate_scene_action",
        lambda **_kwargs: result,
    )
    monkeypatch.setattr(ui_launcher, "_selected_asset_class_id", lambda *_args: "")
    monkeypatch.setattr(ui_launcher, "_populate_validation_result", lambda *_args: None)
    monkeypatch.setattr(ui_launcher, "_update_validation_chrome_labels", lambda *_args: None)
    monkeypatch.setattr(
        ui_launcher,
        "_maybe_notify_telegram_validation",
        lambda content_arg, result_arg: calls.append((content_arg, result_arg)),
    )

    ui_launcher._run_validation_job(
        content,
        object(),
        scan_scope="scene",
        profile_id="lookdev",
    )

    assert calls == [(content, result)]
