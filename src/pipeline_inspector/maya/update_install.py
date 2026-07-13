"""Maya-specific helpers for in-app update install and restart."""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

_PLUGIN_MARKERS = ("pipeline_inspector",)
_DEFAULT_RESTART_DELAY_SECONDS = 3.0


def prepare_maya_for_update_install() -> dict[str, object]:
    """Close UI and unload Pipeline Inspector so native binaries can be replaced."""

    errors: list[str] = []
    outcome: dict[str, object] = {
        "in_maya": False,
        "ui_uninstalled": False,
        "plugins_unloaded": [],
        "errors": errors,
    }
    try:
        import maya.cmds as cmds
    except ImportError:
        return outcome

    outcome["in_maya"] = True
    try:
        from pipeline_inspector.maya.commands import reset_ui_install_state, uninstall_ui

        uninstall_ui()
        reset_ui_install_state()
        outcome["ui_uninstalled"] = True
    except Exception as exc:
        errors.append(f"ui_uninstall: {exc}")

    unloaded: list[str] = []
    for plugin_name in _loaded_pipeline_inspector_plugins(cmds):
        try:
            cmds.unloadPlugin(plugin_name, force=True)
            unloaded.append(plugin_name)
        except Exception as exc:
            errors.append(f"unload:{plugin_name}: {exc}")
    outcome["plugins_unloaded"] = unloaded
    return outcome


def schedule_maya_restart(
    *,
    qt_widgets: Any | None = None,
    dialog: Any | None = None,
    delay_seconds: float = _DEFAULT_RESTART_DELAY_SECONDS,
) -> bool:
    """Close the update dialog and restart Maya on the Qt main thread."""

    try:
        import maya.cmds as cmds
        import maya.utils
    except ImportError:
        return False

    executable = resolve_maya_executable()
    if executable is None:
        return False

    single_shot = _qt_single_shot_callback(qt_widgets)
    if single_shot is None:
        return False

    if dialog is not None:
        _close_dialog(dialog)

    def _restart_maya() -> None:
        _launch_maya_and_quit(cmds, executable)

    def _arm_restart_timer() -> None:
        single_shot(int(delay_seconds * 1000), _restart_maya)

    maya.utils.executeDeferred(_arm_restart_timer)
    return True


def _qt_single_shot_callback(qt_widgets: Any | None) -> Any | None:
    timer_cls = getattr(qt_widgets, "QTimer", None) if qt_widgets is not None else None
    single_shot = getattr(timer_cls, "singleShot", None) if timer_cls is not None else None
    if single_shot is not None:
        return single_shot

    try:
        from pipeline_inspector.ui.qt import load_qt_core

        qt_core = load_qt_core()
    except RuntimeError:
        return None

    timer_cls = getattr(qt_core, "QTimer", None)
    return getattr(timer_cls, "singleShot", None) if timer_cls is not None else None


def resolve_maya_executable() -> Path | None:
    """Return the Maya GUI executable for the active session."""

    maya_location = os.environ.get("MAYA_LOCATION", "").strip()
    if maya_location:
        exe_name = "maya.exe" if sys.platform == "win32" else "maya"
        candidate = Path(maya_location) / "bin" / exe_name
        if candidate.is_file():
            return candidate

    argv0 = Path(sys.argv[0]).resolve()
    if argv0.is_file() and "maya" in argv0.name.lower():
        return argv0
    return None


def finalize_maya_plugin_registration(install_root: Path) -> dict[str, object]:
    """Re-enable autoload and load the canonical plug-in path after update install."""

    errors: list[str] = []
    outcome: dict[str, object] = {
        "install_root": str(install_root),
        "mod_exists": False,
        "canonical_path": "",
        "autoload_enabled": False,
        "loaded": False,
        "pending_applied": 0,
        "errors": errors,
    }
    mod_path = install_root / "maya_module" / "pipeline_inspector.mod"
    outcome["mod_exists"] = mod_path.is_file()
    try:
        import maya.cmds as cmds
    except ImportError:
        return outcome

    bootstrap_path = install_root / "maya_module" / "scripts" / "pipeline_inspector_bootstrap.py"
    if not bootstrap_path.is_file():
        errors.append(f"missing bootstrap: {bootstrap_path}")
        return outcome

    bootstrap = _load_bootstrap_module(bootstrap_path)
    outcome["pending_applied"] = bootstrap.apply_pending_native_plugin_binaries()
    maya_year = bootstrap.resolve_maya_year(lambda: cmds.about(version=True))
    canonical_path = bootstrap.canonical_plugin_path(maya_year)
    outcome["canonical_path"] = canonical_path or ""
    if not canonical_path:
        errors.append("canonical plug-in path not found on disk")
        return outcome

    outcome["autoload_enabled"] = bootstrap.enable_plugin_autoload(canonical_path, cmds)
    try:
        if not cmds.pluginInfo(bootstrap.PLUGIN_NAME, query=True, loaded=True):
            cmds.loadPlugin(canonical_path, quiet=True)
        outcome["loaded"] = True
    except Exception as exc:
        errors.append(f"loadPlugin: {exc}")
    return outcome


def _launch_maya_and_quit(cmds_module: Any, executable: Path) -> None:
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        [str(executable)],
        cwd=str(executable.parent),
        creationflags=creationflags,
        close_fds=True,
    )
    cmds_module.quit(force=True)


def _close_dialog(dialog: Any) -> None:
    for method_name in ("accept", "done", "close"):
        method = getattr(dialog, method_name, None)
        if not callable(method):
            continue
        try:
            method()
        except TypeError:
            method(0)
        return


def _loaded_pipeline_inspector_plugins(cmds_module: Any) -> tuple[str, ...]:
    try:
        plugin_names = cmds_module.pluginInfo(query=True, listPlugins=True) or []
    except Exception:
        return ()

    loaded: list[str] = []
    for plugin_name in plugin_names:
        text = str(plugin_name)
        if not any(marker in text.lower() for marker in _PLUGIN_MARKERS):
            continue
        try:
            if cmds_module.pluginInfo(text, query=True, loaded=True):
                loaded.append(text)
        except Exception:
            continue
    return tuple(loaded)


def _load_bootstrap_module(bootstrap_path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(
        "pipeline_inspector_bootstrap_update_install",
        bootstrap_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import bootstrap module: {bootstrap_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
