from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP_PATH = ROOT / "maya_module" / "scripts" / "shader_health_inspector_bootstrap.py"
USER_SETUP_PATH = ROOT / "maya_module" / "scripts" / "userSetup.py"
PLUGIN_PATH = ROOT / "maya_module" / "plug-ins" / "shader_health_inspector.py"


def load_module(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bootstrap_repo_root_resolves_to_repository_root():
    load_module(BOOTSTRAP_PATH, "shader_health_inspector_bootstrap_root")

    repo_root = BOOTSTRAP_PATH.resolve().parents[2]

    assert repo_root == ROOT
    assert (repo_root / "src" / "shader_health").is_dir()


def test_ensure_source_path_adds_repo_src_directory():
    bootstrap = load_module(BOOTSTRAP_PATH, "shader_health_inspector_bootstrap_path")
    src_path = str((ROOT / "src").resolve())
    original_sys_path = list(sys.path)

    try:
        sys.path[:] = [entry for entry in sys.path if entry != src_path]
        bootstrap._ensure_source_path()
        assert sys.path[0] == src_path
    finally:
        sys.path[:] = original_sys_path


def test_bootstrap_install_ui_delegates_to_shader_health_commands(monkeypatch):
    bootstrap = load_module(BOOTSTRAP_PATH, "shader_health_inspector_bootstrap_install")
    calls: list[str] = []

    class FakeCommands:
        @staticmethod
        def install_ui() -> None:
            calls.append("install_ui")

    monkeypatch.setitem(
        sys.modules,
        "shader_health.maya.commands",
        FakeCommands(),
    )
    monkeypatch.setattr(bootstrap, "_ensure_source_path", lambda: None)

    bootstrap.install_ui()

    assert calls == ["install_ui"]


def test_bootstrap_uninstall_ui_delegates_to_shader_health_commands(monkeypatch):
    bootstrap = load_module(BOOTSTRAP_PATH, "shader_health_inspector_bootstrap_uninstall")
    calls: list[str] = []

    class FakeCommands:
        @staticmethod
        def uninstall_ui() -> None:
            calls.append("uninstall_ui")

        @staticmethod
        def reset_ui_install_state() -> None:
            calls.append("reset_ui_install_state")

    monkeypatch.setitem(
        sys.modules,
        "shader_health.maya.commands",
        FakeCommands(),
    )
    monkeypatch.setattr(bootstrap, "_ensure_source_path", lambda: None)

    bootstrap.uninstall_ui()

    assert calls == ["uninstall_ui", "reset_ui_install_state"]


def test_user_setup_import_is_harmless_outside_maya():
    load_module(USER_SETUP_PATH, "shader_health_user_setup_outside_maya")


def test_user_setup_prefers_plugin_load(monkeypatch):
    deferred: list[str] = []

    class FakeCmds:
        @staticmethod
        def evalDeferred(callback):
            deferred.append("deferred")
            callback()
            return None

        @staticmethod
        def pluginInfo(plugin_name, query=True, loaded=True):
            _ = plugin_name, query, loaded
            return False

        @staticmethod
        def loadPlugin(plugin_name, quiet=True):
            deferred.append(f"load:{plugin_name}:{quiet}")
            return "shader_health_inspector"

        @staticmethod
        def warning(message: str):
            _ = message

    fake_maya = ModuleType("maya")
    fake_maya.cmds = FakeCmds

    monkeypatch.setitem(sys.modules, "maya", fake_maya)
    monkeypatch.setitem(sys.modules, "maya.cmds", FakeCmds)

    load_module(USER_SETUP_PATH, "shader_health_user_setup_plugin")

    assert deferred == ["deferred", "load:shader_health_inspector.py:True"]


def test_user_setup_falls_back_to_bootstrap_install(monkeypatch):
    deferred: list[str] = []

    class FakeCmds:
        @staticmethod
        def evalDeferred(callback):
            deferred.append("deferred")
            callback()
            return None

        @staticmethod
        def pluginInfo(plugin_name, query=True, loaded=True):
            _ = plugin_name, query, loaded
            return False

        @staticmethod
        def loadPlugin(plugin_name, quiet=True):
            _ = plugin_name, quiet
            raise RuntimeError("plugin missing")

        @staticmethod
        def warning(message: str):
            _ = message

    fake_bootstrap = ModuleType("shader_health_inspector_bootstrap")

    def install_ui() -> None:
        deferred.append("install_ui")

    fake_bootstrap.install_ui = install_ui

    fake_maya = ModuleType("maya")
    fake_maya.cmds = FakeCmds

    monkeypatch.setitem(sys.modules, "maya", fake_maya)
    monkeypatch.setitem(sys.modules, "maya.cmds", FakeCmds)
    monkeypatch.setitem(sys.modules, "shader_health_inspector_bootstrap", fake_bootstrap)

    load_module(USER_SETUP_PATH, "shader_health_user_setup_fallback")

    assert deferred == ["deferred", "install_ui"]


def test_plugin_initialize_deferred_install(monkeypatch):
    calls: list[str] = []

    class FakeBootstrap:
        @staticmethod
        def install_ui() -> None:
            calls.append("install_ui")

    class FakeCmds:
        @staticmethod
        def evalDeferred(callback):
            callback()

    class FakePlugin:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

    fake_mpx = ModuleType("OpenMayaMPx")
    fake_mpx.MFnPlugin = FakePlugin
    fake_maya = ModuleType("maya")
    fake_maya.cmds = FakeCmds

    monkeypatch.setitem(sys.modules, "shader_health_inspector_bootstrap", FakeBootstrap())
    monkeypatch.setitem(sys.modules, "maya", fake_maya)
    monkeypatch.setitem(sys.modules, "maya.cmds", FakeCmds)
    monkeypatch.setitem(sys.modules, "maya.OpenMayaMPx", fake_mpx)

    plugin = load_module(PLUGIN_PATH, "shader_health_inspector_plugin_fresh")
    plugin.initializePlugin(object())

    assert calls == ["install_ui"]


def test_plugin_uninitialize_calls_uninstall(monkeypatch):
    calls: list[str] = []

    class FakeBootstrap:
        @staticmethod
        def uninstall_ui() -> None:
            calls.append("uninstall_ui")

    class FakePlugin:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

    fake_mpx = ModuleType("OpenMayaMPx")
    fake_mpx.MFnPlugin = FakePlugin
    fake_maya = ModuleType("maya")

    monkeypatch.setitem(sys.modules, "shader_health_inspector_bootstrap", FakeBootstrap())
    monkeypatch.setitem(sys.modules, "maya", fake_maya)
    monkeypatch.setitem(sys.modules, "maya.OpenMayaMPx", fake_mpx)

    plugin = load_module(PLUGIN_PATH, "shader_health_inspector_plugin_uninit_fresh")
    plugin.uninitializePlugin(object())

    assert calls == ["uninstall_ui"]
