from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pipeline_inspector.integrations.update.install import (
    _copy_install_file,
    apply_install_payload,
)
from pipeline_inspector.maya.update_install import (
    prepare_maya_for_update_install,
    resolve_maya_executable,
    schedule_maya_restart,
)


def test_prepare_maya_for_update_install_unloads_loaded_plugin(monkeypatch):
    calls: list[tuple[str, bool]] = []

    class FakeCmds:
        @staticmethod
        def pluginInfo(*args, **kwargs):
            if kwargs.get("query") and kwargs.get("listPlugins"):
                return ["pipeline_inspector.mll", "other_plugin"]
            if kwargs.get("query") and kwargs.get("loaded"):
                return args[0] == "pipeline_inspector.mll"
            return None

        @staticmethod
        def unloadPlugin(name, force=True):
            calls.append((name, force))

    monkeypatch.setitem(__import__("sys").modules, "maya.cmds", FakeCmds())
    monkeypatch.setitem(__import__("sys").modules, "maya", type("Maya", (), {"cmds": FakeCmds})())
    monkeypatch.setattr(
        "pipeline_inspector.maya.commands.uninstall_ui",
        lambda: None,
    )
    monkeypatch.setattr(
        "pipeline_inspector.maya.commands.reset_ui_install_state",
        lambda: None,
    )

    outcome = prepare_maya_for_update_install()

    assert outcome["in_maya"] is True
    assert outcome["ui_uninstalled"] is True
    assert calls == [("pipeline_inspector.mll", True)]


def test_resolve_maya_executable_uses_maya_location(monkeypatch, tmp_path: Path):
    maya_root = tmp_path / "Maya2024"
    bin_dir = maya_root / "bin"
    bin_dir.mkdir(parents=True)
    exe = bin_dir / "maya.exe"
    exe.write_bytes(b"")
    monkeypatch.setenv("MAYA_LOCATION", str(maya_root))

    assert resolve_maya_executable() == exe


def test_schedule_maya_restart_uses_qtimer(monkeypatch):
    scheduled: list[int] = []
    closed: list[str] = []
    deferred: list[Any] = []

    class FakeDialog:
        def accept(self) -> None:
            closed.append("accept")

    class FakeTimer:
        @staticmethod
        def singleShot(delay_ms, callback):
            scheduled.append(delay_ms)
            callback()

    class FakeCmds:
        @staticmethod
        def quit(force=True):
            _ = force

    class FakeQtWidgets:
        QTimer = FakeTimer

    class FakeMayaUtils:
        @staticmethod
        def executeDeferred(callback):
            deferred.append(callback)
            callback()

    monkeypatch.setitem(__import__("sys").modules, "maya.cmds", FakeCmds())
    monkeypatch.setitem(__import__("sys").modules, "maya.utils", FakeMayaUtils())
    monkeypatch.setitem(
        __import__("sys").modules,
        "maya",
        type(
            "Maya",
            (),
            {"cmds": FakeCmds, "utils": FakeMayaUtils},
        )(),
    )
    monkeypatch.setattr(
        "pipeline_inspector.maya.update_install.resolve_maya_executable",
        lambda: Path("C:/Maya2024/bin/maya.exe"),
    )
    monkeypatch.setattr(
        "pipeline_inspector.maya.update_install.subprocess.Popen",
        lambda *args, **kwargs: None,
    )

    dialog = FakeDialog()
    assert (
        schedule_maya_restart(
            qt_widgets=FakeQtWidgets(),
            dialog=dialog,
            delay_seconds=2.5,
        )
        is True
    )
    assert deferred == [deferred[0]]
    assert scheduled == [2500]
    assert closed == ["accept"]


def test_qt_single_shot_falls_back_to_qt_core(monkeypatch):
    class FakeQtCore:
        class QTimer:
            @staticmethod
            def singleShot(delay_ms, callback):
                return ("qt_core", delay_ms, callback)

    monkeypatch.setattr(
        "pipeline_inspector.maya.update_install.load_qt_core",
        lambda: FakeQtCore(),
        raising=False,
    )
    monkeypatch.setattr(
        "pipeline_inspector.ui.qt.load_qt_core",
        lambda: FakeQtCore(),
    )

    from pipeline_inspector.maya.update_install import _qt_single_shot_callback

    callback = _qt_single_shot_callback(object())
    assert callback is FakeQtCore.QTimer.singleShot


def test_copy_install_file_stages_pending_native_binary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    source = tmp_path / "payload" / "pipeline_inspector.mll"
    destination = tmp_path / "install" / "pipeline_inspector.mll"
    source.parent.mkdir(parents=True)
    destination.parent.mkdir(parents=True)
    source.write_bytes(b"new-plugin")

    def _raise_permission(_src, dst):
        if str(dst).endswith(".pending"):
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(_src.read_bytes())
            return
        raise PermissionError("locked")

    monkeypatch.setattr(
        "pipeline_inspector.integrations.update.install.shutil.copy2",
        _raise_permission,
    )

    pending_count = _copy_install_file(source, destination)

    assert pending_count == 1
    assert Path(f"{destination}.pending").read_bytes() == b"new-plugin"


def test_apply_install_payload_returns_pending_count(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    payload_root = tmp_path / "payload"
    install_root = tmp_path / "install"
    native = payload_root / "maya_module" / "plug-ins" / "pipeline_inspector.mll"
    native.parent.mkdir(parents=True)
    native.write_bytes(b"native")
    (payload_root / "src" / "pipeline_inspector").mkdir(parents=True)
    (payload_root / "src" / "pipeline_inspector" / "marker.txt").write_text(
        "0.5.0",
        encoding="utf-8",
    )
    install_root.mkdir()

    def _copy(src: Path, dst: Path) -> None:
        if dst.suffix == ".mll":
            raise PermissionError("locked")
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())

    monkeypatch.setattr(
        "pipeline_inspector.integrations.update.install.shutil.copy2",
        _copy,
    )

    pending_count = apply_install_payload(payload_root, install_root)

    assert pending_count == 1
    assert (
        install_root / "src" / "pipeline_inspector" / "marker.txt"
    ).read_text(encoding="utf-8") == "0.5.0"
