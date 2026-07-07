"""Maya module bootstrap helpers for Shader Health Inspector."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable


def resolve_maya_year(version_provider: Callable[[], Any]) -> str | None:
    """Return a four-digit Maya year from cmds.about(version=True) or similar."""

    try:
        return maya_year_from_version(str(version_provider()))
    except Exception:
        return None


def maya_year_from_version(version_string: str) -> str | None:
    """Extract a Maya release year from a version string."""

    text = version_string.strip()
    if text.isdigit() and len(text) == 4 and text.startswith("20"):
        return text
    for token in text.replace(",", " ").split():
        if token.isdigit() and len(token) == 4 and token.startswith("20"):
            return token
    return None


def module_root() -> Path:
    """Return the `maya_module/` directory that owns this bootstrap script."""

    return Path(__file__).resolve().parents[1]


def native_plugin_path(maya_year: str) -> Path:
    """Absolute path to the year-specific native plug-in binary when packaged."""

    if sys.platform == "win32":
        suffix = ".mll"
    elif sys.platform == "darwin":
        suffix = ".bundle"
    else:
        suffix = ".so"
    return module_root() / "plug-ins" / maya_year / f"shader_health_inspector{suffix}"


def plugin_load_candidates(maya_year: str | None = None) -> tuple[str, ...]:
    """Plug-in paths to try in load order (native binary first, then .py fallback)."""

    candidates: list[str] = []
    if maya_year:
        native_path = native_plugin_path(maya_year)
        if native_path.is_file():
            candidates.append(str(native_path))
        # region agent log
        try:
            import json
            import time

            log_path = module_root().parent / "debug-ee1eca.log"
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "sessionId": "ee1eca",
                            "runId": "plugin-load",
                            "hypothesisId": "H-PATH",
                            "location": "shader_health_inspector_bootstrap.py",
                            "message": "native_plugin_candidate",
                            "data": {
                                "maya_year": maya_year,
                                "native_path": str(native_path),
                                "exists": native_path.is_file(),
                            },
                            "timestamp": int(time.time() * 1000),
                        }
                    )
                    + "\n"
                )
        except OSError:
            pass
        # endregion
    candidates.append("shader_health_inspector.py")
    return tuple(candidates)


PLUGIN_NAME = "shader_health_inspector"


def show() -> Any:
    """Open the dockable Shader Health Inspector panel."""

    _ensure_source_path()
    from shader_health.maya.commands import show_ui

    return show_ui()


def close() -> None:
    """Close the dockable Shader Health Inspector panel."""

    _ensure_source_path()
    from shader_health.maya.commands import close_ui

    close_ui()


def install_menu() -> str:
    """Install the Maya menu entry that opens the panel."""

    _ensure_source_path()
    from shader_health.maya.commands import install_menu as _install_menu

    return _install_menu()


def install_shelf() -> str:
    """Install the Maya shelf tab and button that opens the panel."""

    _ensure_source_path()
    from shader_health.maya.commands import install_shelf as _install_shelf

    return _install_shelf()


def uninstall_ui() -> None:
    """Remove menu, shelf, and panel for plugin unload."""

    _ensure_source_path()
    from shader_health.maya.commands import reset_ui_install_state
    from shader_health.maya.commands import uninstall_ui as _uninstall_ui

    _uninstall_ui()
    reset_ui_install_state()


def install_ui() -> None:
    """Install all Maya UI entrypoints for this session."""

    _ensure_source_path()
    from shader_health.maya.commands import install_ui as _install_ui

    _install_ui()


def _ensure_source_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    src_path = repo_root / "src"
    src_text = str(src_path)
    if src_path.exists() and src_text not in sys.path:
        sys.path.insert(0, src_text)
