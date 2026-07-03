"""Maya selection and navigation actions for Shader Health Inspector."""
from __future__ import annotations

import importlib
import platform
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from shader_health.ui.qt import load_qt_widgets


@dataclass(frozen=True)
class NavigationActionResult:
    """Outcome of a Maya navigation action."""

    action: str
    target: str
    succeeded: bool
    message: str


def select_node(node_name: str, *, cmds: Optional[Any] = None) -> NavigationActionResult:
    """Select a Maya node by name."""

    target = _require_text(node_name, field_name="node_name")
    maya_cmds = cmds or _maya_cmds()
    if not maya_cmds.objExists(target):
        return _result("select_node", target, False, "Node does not exist.")
    maya_cmds.select(target, replace=True)
    return _result("select_node", target, True, "Node selected.")


def open_in_hypershade(
    node_name: str,
    *,
    cmds: Optional[Any] = None,
    mel: Optional[Any] = None,
) -> NavigationActionResult:
    """Open Hypershade and show the shader network for a material node."""

    target = _require_text(node_name, field_name="node_name")
    maya_cmds = cmds or _maya_cmds()
    if not maya_cmds.objExists(target):
        return _result("open_in_hypershade", target, False, "Node does not exist.")
    maya_mel = mel or _maya_mel()

    hypershade_was_open = bool(_hypershade_panel_name(maya_cmds))
    if not hypershade_was_open:
        hypershade_window = getattr(maya_cmds, "HypershadeWindow", None)
        if hypershade_window is not None:
            hypershade_window()
        else:
            maya_mel.eval("HypershadeWindow")

    panel_name = _hypershade_panel_name(maya_cmds) or "hyperShadePanel1"
    maya_cmds.select(target, replace=True)
    hyper_shade = getattr(maya_cmds, "hyperShade", None)
    if hyper_shade is not None:
        hyper_shade(shaderNetwork=target)
    else:
        maya_mel.eval(f'hyperShade -shaderNetwork "{target}"')

    graph_command = f'hyperShadePanelGraphCommand("{panel_name}", "showUpAndDownstream")'

    def _apply_io_connections_view() -> None:
        maya_mel.eval(graph_command)

    if hypershade_was_open:
        _apply_io_connections_view()
    else:
        eval_deferred = getattr(maya_cmds, "evalDeferred", None)
        if eval_deferred is not None:
            eval_deferred(_apply_io_connections_view)
        else:
            _apply_io_connections_view()

    return _result(
        "open_in_hypershade",
        target,
        True,
        f"Hypershade focused on {target} (input and output connections).",
    )


def open_attribute_editor(
    node_name: str,
    *,
    cmds: Optional[Any] = None,
    mel: Optional[Any] = None,
) -> NavigationActionResult:
    """Select a Maya node and open the Attribute Editor."""

    target = _require_text(node_name, field_name="node_name")
    maya_cmds = cmds or _maya_cmds()
    if not maya_cmds.objExists(target):
        return _result("open_attribute_editor", target, False, "Node does not exist.")
    maya_cmds.select(target, replace=True)
    maya_mel = mel or _maya_mel()
    maya_mel.eval("openAEWindow")
    return _result("open_attribute_editor", target, True, "Attribute Editor opened.")


def copy_path(
    path: str,
    *,
    clipboard_setter: Optional[Callable[[str], None]] = None,
    qt_widgets: Optional[Any] = None,
) -> NavigationActionResult:
    """Copy a filesystem path to the Maya/Qt clipboard."""

    target = _require_text(path, field_name="path")
    if clipboard_setter is not None:
        clipboard_setter(target)
        return _result("copy_path", target, True, "Path copied to clipboard.")

    widgets = qt_widgets or load_qt_widgets()
    app = widgets.QApplication.instance()
    if app is None:
        return _result("copy_path", target, False, "No active Qt application found.")
    app.clipboard().setText(target)
    return _result("copy_path", target, True, "Path copied to clipboard.")


def reveal_file(
    path: str,
    *,
    platform_name: Optional[str] = None,
    process_launcher: Optional[Callable[[Sequence[str]], Any]] = None,
) -> NavigationActionResult:
    """Reveal a file or folder in the host OS file browser where supported."""

    target = _require_text(path, field_name="path")
    resolved_path = Path(target).expanduser()
    system_name = platform_name or platform.system()
    launcher = process_launcher or _launch_process
    command = _reveal_command(resolved_path, system_name)
    if command is None:
        return _result("reveal_file", target, False, f"Unsupported platform: {system_name}.")
    launcher(command)
    return _result("reveal_file", target, True, "Reveal command launched.")


def _reveal_command(path: Path, system_name: str) -> Optional[list[str]]:
    if system_name == "Windows":
        if path.is_dir():
            return ["explorer", str(path)]
        return ["explorer", f"/select,{path}"]
    if system_name == "Darwin":
        return ["open", "-R", str(path)]
    if system_name == "Linux":
        reveal_target = path if path.is_dir() else path.parent
        return ["xdg-open", str(reveal_target)]
    return None


def _launch_process(command: Sequence[str]) -> None:
    subprocess.Popen(list(command))  # noqa: S603


def _maya_cmds() -> Any:
    return _maya_module("maya.cmds")


def _maya_mel() -> Any:
    return _maya_module("maya.mel")


def _maya_module(module_name: str) -> Any:
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        raise RuntimeError("Maya navigation actions can only run inside Autodesk Maya.") from exc


def _require_text(value: str, *, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} must not be empty.")
    return stripped


def _hypershade_panel_name(maya_cmds: Any) -> str:
    """Return the active Hypershade model panel name, if Hypershade is open."""

    model_panel = getattr(maya_cmds, "modelPanel", None)
    if model_panel is not None:
        for candidate in ("hyperShadePanel1", "hypershadePrimaryPane"):
            try:
                if model_panel(candidate, exists=True):
                    return candidate
            except TypeError:
                continue

    get_panel = getattr(maya_cmds, "getPanel", None)
    model_editor = getattr(maya_cmds, "modelEditor", None)
    if get_panel is not None and model_editor is not None:
        try:
            panels = get_panel(type="modelPanel") or []
        except TypeError:
            panels = []
        for panel in panels:
            try:
                editor_name = model_editor(panel, query=True, editorName=True)
            except Exception:  # noqa: BLE001 - Maya query failures vary by panel state
                continue
            if editor_name == "hyperShadePanel":
                return str(panel)
    return ""


def _result(
    action: str,
    target: str,
    succeeded: bool,
    message: str,
) -> NavigationActionResult:
    return NavigationActionResult(
        action=action,
        target=target,
        succeeded=succeeded,
        message=message,
    )
