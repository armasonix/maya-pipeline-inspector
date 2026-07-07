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


def native_plugin_suffix() -> str:
    if sys.platform == "win32":
        return ".mll"
    if sys.platform == "darwin":
        return ".bundle"
    return ".so"


def native_plugin_path(maya_year: str) -> Path:
    """Absolute path to the year-specific native plug-in binary when packaged."""

    return (
        module_root()
        / "plug-ins"
        / maya_year
        / f"shader_health_inspector{native_plugin_suffix()}"
    )


def manager_native_plugin_path() -> Path:
    """Top-level native plug-in copy used by Plug-in Manager browsing."""

    return module_root() / "plug-ins" / f"shader_health_inspector{native_plugin_suffix()}"


def python_plugin_name() -> str:
    return "shader_health_inspector.py"


INSTALL_MODE_NATIVE_YEAR = "native_year"
INSTALL_MODE_NATIVE_MANAGER = "native_manager"
INSTALL_MODE_PYTHON = "python"
INSTALL_MODE_MODULE_ONLY = "module_only"


def detect_install_mode(maya_year: str | None = None) -> str:
    """Return which dual-install delivery path is available on disk."""

    if maya_year and native_plugin_path(maya_year).is_file():
        return INSTALL_MODE_NATIVE_YEAR
    if manager_native_plugin_path().is_file():
        return INSTALL_MODE_NATIVE_MANAGER
    if (module_root() / "plug-ins" / python_plugin_name()).is_file():
        return INSTALL_MODE_PYTHON
    return INSTALL_MODE_MODULE_ONLY


def plugin_load_candidates(maya_year: str | None = None) -> tuple[str, ...]:
    """Plug-in paths to try in load order (native binary first, then .py fallback)."""

    candidates: list[str] = []
    seen: set[str] = set()

    def add(path: Path | str) -> None:
        text = str(path)
        if text not in seen:
            seen.add(text)
            candidates.append(text)

    if maya_year:
        year_path = native_plugin_path(maya_year)
        if year_path.is_file():
            add(year_path)
    manager_path = manager_native_plugin_path()
    if manager_path.is_file():
        add(manager_path)
    add(python_plugin_name())
    return tuple(candidates)


def describe_dual_install(maya_year: str | None = None) -> dict[str, object]:
    """Summarize dual-install detection for troubleshooting and unit tests."""

    return {
        "maya_year": maya_year,
        "install_mode": detect_install_mode(maya_year),
        "load_candidates": list(plugin_load_candidates(maya_year)),
    }


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
