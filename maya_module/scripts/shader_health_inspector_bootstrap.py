"""Maya module bootstrap helpers for Shader Health Inspector."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


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


def _ensure_source_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    src_path = repo_root / "src"
    src_text = str(src_path)
    if src_path.exists() and src_text not in sys.path:
        sys.path.insert(0, src_text)
