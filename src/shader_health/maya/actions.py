"""Maya UI navigation actions.

This module keeps Maya and Qt imports lazy so it can be imported by public CI
without Autodesk Maya installed.
"""
from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from shader_health.ui.qt import load_qt_widgets


@dataclass(frozen=True)
class MayaActionResult:
    """Result returned by Maya navigation actions."""

    success: bool
    message: str

def select_node(node_name: str) -> MayaActionResult:
    """Select a Maya dependency node by name."""

    normalized_node = node_name.strip()
    if not normalized_node:
        return MayaActionResult(False, "No Maya node was provided.")

    cmds = _maya_cmds()
    if not cmds.objExists(normalized_node):
        return MayaActionResult(False, f"Maya node does not exist: {normalized_node}")

    cmds.select(normalized_node, replace=True)
    return MayaActionResult(True, f"Selected Maya node: {normalized_node}")

def open_attribute_editor(node_name: str) -> MayaActionResult:
    """Select a Maya node and open the Attribute Editor."""

    selection_result = select_node(node_name)
    if not selection_result.success:
        return selection_result

    mel = _maya_mel()
    mel.eval("openAEWindow;")
    return MayaActionResult(True, f"Opened Attribute Editor for: {node_name.strip()}")

def copy_path_to_clipboard(path: str) -> MayaActionResult:
    """Copy a file path or dependency path to the active Qt clipboard."""

    normalized_path = path.strip()
    if not normalized_path:
        return MayaActionResult(False, "No path was provided.")

    qt_widgets = _qt_widgets()
    application = qt_widgets.QApplication.instance()
    if application is None:
        return MayaActionResult(False, "No active Qt application was found.")

    application.clipboard().setText(normalized_path)
    return MayaActionResult(True, f"Copied path: {normalized_path}")

def reveal_file(path: str) -> MayaActionResult:
    """Reveal a file in the OS file browser where the platform supports it."""

    normalized_path = path.strip()
    if not normalized_path:
        return MayaActionResult(False, "No file path was provided.")

    target = Path(normalized_path)
    reveal_target = _existing_reveal_target(target)
    if reveal_target is None:
        return MayaActionResult(False, f"File path does not exist: {normalized_path}")

    command = _reveal_command(reveal_target)
    if command is None:
        return MayaActionResult(False, f"Reveal file is not supported on: {sys.platform}")

    _popen(command)
    return MayaActionResult(True, f"Revealed file path: {normalized_path}")

def _existing_reveal_target(target: Path) -> Optional[Path]:
    if target.exists():
        return target
    parent = target.parent
    if parent.exists():
        return parent
    return None

def _reveal_command(target: Path) -> Optional[list[str]]:
    target_text = str(target)
    if sys.platform.startswith("win"):
        if target.is_file():
            return ["explorer", "/select,", target_text]
        return ["explorer", target_text]
    if sys.platform == "darwin":
        return ["open", "-R", target_text]
    if sys.platform.startswith("linux"):
        directory = target if target.is_dir() else target.parent
        return ["xdg-open", str(directory)]
    return None

def _maya_cmds() -> Any:
    return _maya_module("maya.cmds")

def _maya_mel() -> Any:
    return _maya_module("maya.mel")

def _maya_module(module_name: str) -> Any:
    import importlib

    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        raise RuntimeError("Maya navigation actions can only run inside Autodesk Maya.") from exc

def _qt_widgets() -> Any:
    return load_qt_widgets()

def _popen(command: Sequence[str]) -> None:
    subprocess.Popen(list(command))
