from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

from pipeline_inspector.core.manifest_gate import ManifestGatePolicy  # noqa: F401
from pipeline_inspector.maya import ui_launcher
from pipeline_inspector.ui import main_window


class FakePanel:
    def __init__(self) -> None:
        self.show_calls: list[dict[str, Any]] = []
        self.closed = False

    def show(self, **kwargs: Any) -> None:
        self.show_calls.append(dict(kwargs))

    def close(self) -> None:
        self.closed = True


def _panel_that_creates_workspace(cmds: FakeCmds, panel: FakePanel | None = None) -> FakePanel:
    panel = panel or FakePanel()

    def show(**kwargs: Any) -> None:
        panel.show_calls.append(dict(kwargs))
        cmds.workspace_exists = True

    panel.show = show  # type: ignore[method-assign]
    return panel


class FakeCmds:
    def __init__(self, *, workspace_exists: bool) -> None:
        self.workspace_exists = workspace_exists
        self.deleted: list[tuple[str, dict[str, Any]]] = []
        self.restored: list[str] = []
        self.closed: list[str] = []
        self.docked: list[tuple[str, tuple[str, int]]] = []
        self.hidden: list[str] = []

    def workspaceControl(self, name: str, **kwargs: Any) -> Optional[bool]:
        if kwargs.get("query") and kwargs.get("exists"):
            return self.workspace_exists
        if kwargs.get("edit") and kwargs.get("visible") is False:
            self.hidden.append(name)
            return None
        if kwargs.get("edit") and kwargs.get("restore"):
            self.restored.append(name)
            return None
        if kwargs.get("edit") and kwargs.get("close"):
            self.closed.append(name)
            self.workspace_exists = False
            return None
        if kwargs.get("edit") and kwargs.get("dockToMainWindow"):
            self.docked.append((name, kwargs["dockToMainWindow"]))
            return None
        return None

    def deleteUI(self, name: str, **kwargs: Any) -> None:
        self.deleted.append((name, dict(kwargs)))
        self.workspace_exists = False

    def evalDeferred(self, callback: Any, *args: Any, **kwargs: Any) -> None:
        callback(*args, **kwargs)

    def scriptJob(self, **kwargs: Any) -> int:
        event = kwargs.get("event")
        if isinstance(event, (list, tuple)) and len(event) == 2 and event[0] == "idle":
            event[1]()
        return 1

    def workspaceControlState(self, name: str, **kwargs: Any) -> bool:
        if kwargs.get("query") and kwargs.get("exists"):
            return False
        return False


def test_show_panel_creates_dockable_panel(monkeypatch: Any):
    cmds = FakeCmds(workspace_exists=False)
    panel = _panel_that_creates_workspace(cmds)
    monkeypatch.setattr(ui_launcher, "_PANEL", None)
    monkeypatch.setattr(ui_launcher, "_maya_cmds", lambda: cmds)
    monkeypatch.setattr(ui_launcher, "_create_dockable_panel", lambda: panel)
    remembered: list[str] = []
    visible_flags: list[bool] = []
    monkeypatch.setattr(
        ui_launcher,
        "remember_plugin_version",
        lambda version: remembered.append(version),
    )
    monkeypatch.setattr(
        ui_launcher,
        "remember_panel_visible",
        lambda visible: visible_flags.append(visible),
    )

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
    assert remembered == [ui_launcher.__version__]
    assert visible_flags == [True]
    assert cmds.docked == []


def test_show_panel_restores_existing_panel(monkeypatch: Any):
    cmds = FakeCmds(workspace_exists=True)
    panel = FakePanel()
    monkeypatch.setattr(ui_launcher, "_PANEL", panel)
    monkeypatch.setattr(ui_launcher, "_maya_cmds", lambda: cmds)
    monkeypatch.setattr(ui_launcher, "_purge_obsolete_workspace_controls", lambda _cmds: None)
    monkeypatch.setattr(ui_launcher, "remember_plugin_version", lambda _version: None)
    monkeypatch.setattr(ui_launcher, "remember_panel_visible", lambda _visible: None)

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
    monkeypatch.setattr(ui_launcher, "_purge_obsolete_workspace_controls", lambda _cmds: None)
    monkeypatch.setattr(ui_launcher, "remember_plugin_version", lambda _version: None)
    monkeypatch.setattr(ui_launcher, "remember_panel_visible", lambda _visible: None)

    result = ui_launcher.show_panel()

    assert result is panel
    assert cmds.deleted == [(ui_launcher.WORKSPACE_CONTROL_NAME, {"control": True})]
    assert panel.show_calls[0]["dockable"] is True
    assert panel.show_calls[0]["area"] == "right"


def test_show_farm_check_panel_selects_farm_tab_and_runs_preflight(monkeypatch: Any):
    panel = SimpleNamespace(_pipeline_inspector_content=object())
    calls: list[str] = []
    monkeypatch.setattr(ui_launcher, "show_panel", lambda: panel)
    monkeypatch.setattr(ui_launcher, "load_qt_widgets", lambda: object())
    monkeypatch.setattr(ui_launcher, "_set_panel_view", lambda *_args, **_kwargs: None)
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
    content = SimpleNamespace(_pipeline_inspector_validate_running=False)
    calls: list[str] = []
    scheduled: list[Any] = []

    class FakeQtWidgets:
        class QTimer:
            @staticmethod
            def singleShot(_delay_ms: int, callback: Any) -> None:
                scheduled.append(callback)

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
    monkeypatch.setattr(ui_launcher, "_ui_agent_debug_log", lambda *_args, **_kwargs: None)

    ui_launcher._schedule_ui_validation(content, FakeQtWidgets(), scan_scope="scene")

    assert len(scheduled) == 1
    scheduled[0]()
    assert calls == ["busy", "run", "busy"]
    assert content._pipeline_inspector_validate_running is False


def test_schedule_ui_validation_falls_back_to_main_thread_schedule(monkeypatch: Any):
    content = SimpleNamespace(_pipeline_inspector_validate_running=False)
    runs: list[str] = []
    scheduled: list[Any] = []

    monkeypatch.setattr(
        ui_launcher,
        "_set_validate_busy_state",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        ui_launcher,
        "_run_validation_job",
        lambda *_args, **_kwargs: runs.append("run"),
    )
    monkeypatch.setattr(
        ui_launcher,
        "_schedule_on_main_thread",
        lambda callback: scheduled.append(callback),
    )
    monkeypatch.setattr(ui_launcher, "_ui_agent_debug_log", lambda *_args, **_kwargs: None)

    ui_launcher._schedule_ui_validation(content, object(), scan_scope="selection")

    assert len(scheduled) == 1
    scheduled[0]()
    assert runs == ["run"]
    assert content._pipeline_inspector_validate_running is False


def test_update_severity_filter_options_restores_saved_preference(monkeypatch: Any):
    from pipeline_inspector.ui.issues_triage import IssueFilterPrefs, write_issue_filter_prefs

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


def test_run_validation_job_notifies_connectors_after_successful_validation(monkeypatch: Any):
    from pipeline_inspector.core.scoring import HealthScore

    content = SimpleNamespace(
        _pipeline_inspector_studio_config=ui_launcher.StudioConfig.default(),
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
        "pipeline_inspector.maya.commands.validate_scene_action",
        lambda **_kwargs: result,
    )
    monkeypatch.setattr(ui_launcher, "_selected_asset_class_id", lambda *_args: "")
    monkeypatch.setattr(ui_launcher, "_populate_validation_result", lambda *_args: None)
    monkeypatch.setattr(ui_launcher, "_update_validation_chrome_labels", lambda *_args: None)
    monkeypatch.setattr(
        ui_launcher,
        "_maybe_notify_validation",
        lambda content_arg, _qt_widgets, result_arg: calls.append((content_arg, result_arg)),
    )

    ui_launcher._run_validation_job(
        content,
        object(),
        scan_scope="scene",
        profile_id="lookdev",
    )

    assert calls == [(content, result)]


def test_maybe_notify_validation_delegates_to_dispatcher(monkeypatch: Any):
    content = SimpleNamespace()
    result = SimpleNamespace()
    calls: list[tuple[Any, Any]] = []

    def _fake_dispatch(studio_config: Any, validation_result: Any, **kwargs: Any) -> Any:
        calls.append((studio_config, validation_result, kwargs))
        from pipeline_inspector.integrations.notify.dispatcher import (
            ValidationNotificationDispatchResult,
        )

        return ValidationNotificationDispatchResult(outcomes=())

    monkeypatch.setattr(
        "pipeline_inspector.integrations.notify.dispatcher.dispatch_validation_notifications",
        _fake_dispatch,
    )
    monkeypatch.setattr(
        "pipeline_inspector.integrations.notify.dispatcher.report_validation_notification_outcomes",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        ui_launcher,
        "_studio_config_for_content",
        lambda _content: ui_launcher.StudioConfig(),
    )
    monkeypatch.setattr(
        ui_launcher,
        "_permission_resolver_for_content",
        lambda _content: SimpleNamespace(effective_role="technical_artist"),
    )

    ui_launcher._maybe_notify_validation(content, object(), result)

    assert len(calls) == 1
    assert calls[0][0].__class__.__name__ == "StudioConfig"
    assert calls[0][1] is result
    assert calls[0][2].get("supervisor_route") is None
    assert calls[0][2].get("force_notify") is False


def test_show_check_for_updates_shows_info_when_up_to_date(monkeypatch: Any):
    content = SimpleNamespace(_pipeline_inspector_studio_config=None)
    wizard_calls: list[dict[str, Any]] = []
    info_calls: list[tuple[str, str]] = []

    class FakeResult:
        up_to_date = True
        completed = True
        update_available = False
        skipped_reason = ""
        error_message = ""
        installed_version = "0.5.0"
        latest_version = "0.5.0"
        tag_name = "v0.5.0"
        staging_path = ""

    def _fake_run_update_check_only(**_kwargs: Any) -> FakeResult:
        return FakeResult()

    def _fake_show_update_modal_shell(_qt_widgets: Any, **kwargs: Any) -> object:
        wizard_calls.append(kwargs)
        raise AssertionError("wizard should not open when up to date")

    monkeypatch.setattr(
        "pipeline_inspector.ui.update_wizard.run_update_check_only",
        _fake_run_update_check_only,
    )
    monkeypatch.setattr(
        "pipeline_inspector.ui.update_modal.show_update_modal_shell",
        _fake_show_update_modal_shell,
    )
    monkeypatch.setattr(ui_launcher, "_maya_main_window_widget", lambda _qt: "main-window")
    monkeypatch.setattr(ui_launcher, "_set_label_text", lambda *_args: None)
    monkeypatch.setattr(
        ui_launcher,
        "_show_information_dialog",
        lambda _qt, title, message, **kwargs: info_calls.append((title, message)),
    )

    ui_launcher._show_check_for_updates_modal_from_ui(content, object())

    assert wizard_calls == []
    assert len(info_calls) == 1
    assert info_calls[0][0] == "Check for Updates"
    assert "already up to date" in info_calls[0][1]


def test_show_check_for_updates_opens_wizard_when_update_available(monkeypatch: Any):
    content = SimpleNamespace(_pipeline_inspector_studio_config=None)
    wizard_calls: list[dict[str, Any]] = []
    info_calls: list[tuple[str, str]] = []

    class FakeResult:
        up_to_date = False
        completed = True
        update_available = True
        skipped_reason = ""
        error_message = ""
        installed_version = "0.4.0"
        latest_version = "0.5.0"
        tag_name = "v0.5.0"
        staging_path = ""

    class FakeSession:
        result = FakeResult()

    def _fake_run_update_check_only(**_kwargs: Any) -> FakeResult:
        return FakeResult()

    def _fake_show_update_modal_shell(_qt_widgets: Any, **kwargs: Any) -> FakeSession:
        wizard_calls.append(kwargs)
        return FakeSession()

    monkeypatch.setattr(
        "pipeline_inspector.ui.update_wizard.run_update_check_only",
        _fake_run_update_check_only,
    )
    monkeypatch.setattr(
        "pipeline_inspector.ui.update_modal.show_update_modal_shell",
        _fake_show_update_modal_shell,
    )
    monkeypatch.setattr(ui_launcher, "_maya_main_window_widget", lambda _qt: "main-window")
    monkeypatch.setattr(ui_launcher, "_set_label_text", lambda *_args: None)
    monkeypatch.setattr(
        ui_launcher,
        "_show_information_dialog",
        lambda _qt, title, message, **kwargs: info_calls.append((title, message)),
    )

    ui_launcher._show_check_for_updates_modal_from_ui(content, object())

    assert info_calls == []
    assert len(wizard_calls) == 1
    assert wizard_calls[0]["parent"] == "main-window"
    assert wizard_calls[0]["installed_version"] == "0.5.0"


def test_maybe_run_startup_update_check_skips_when_pref_disabled(monkeypatch: Any):
    from pipeline_inspector.user_config import UserPreferences

    calls: list[tuple[Any, Any]] = []
    monkeypatch.setattr(
        ui_launcher,
        "_run_startup_update_check",
        lambda content, qt_widgets: calls.append((content, qt_widgets)),
    )

    ui_launcher._maybe_run_startup_update_check(
        SimpleNamespace(),
        object(),
        UserPreferences(),
    )

    assert calls == []


def test_run_startup_update_check_sets_status_when_update_available(monkeypatch: Any):
    content = SimpleNamespace()
    status_calls: list[str] = []

    class FakeResult:
        up_to_date = False
        skipped_reason = ""
        update_available = True
        completed = True
        error_message = ""
        installed_version = "0.4.0"
        latest_version = "0.5.0"
        tag_name = "v0.5.0"
        staging_path = ""

    monkeypatch.setattr(
        "pipeline_inspector.ui.update_wizard.run_update_check_only",
        lambda **_kwargs: FakeResult(),
    )
    monkeypatch.setattr(
        ui_launcher,
        "_set_label_text",
        lambda _content, _qt, _name, message: status_calls.append(message),
    )

    ui_launcher._run_startup_update_check(
        content,
        object(),
    )

    assert status_calls
    assert "0.5.0" in status_calls[0]
