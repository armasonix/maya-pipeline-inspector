"""Maya command entrypoints for Shader Health Inspector."""
from __future__ import annotations

import importlib
import json
from html import escape
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

from shader_health.maya.navigation import (
    NavigationActionResult,
    copy_path,
    open_attribute_editor,
    reveal_file,
    select_node,
)
from shader_health.maya.ui_launcher import close_panel, show_panel

MENU_NAME = "shaderHealthInspectorMenu"
MENU_LABEL = "Shader Health"
OPEN_MENU_ITEM_LABEL = "Open Shader Health Inspector"
CLOSE_MENU_ITEM_LABEL = "Close Shader Health Inspector"
SHELF_NAME = "ShaderHealth"
SHELF_BUTTON_NAME = "shaderHealthInspectorShelfButton"
SHELF_BUTTON_LABEL = "Shader Health"
SHELF_BUTTON_ANNOTATION = "Open Maya Shader Health Inspector"
MAYA_MAIN_WINDOW = "MayaWindow"
OPEN_UI_PYTHON_COMMAND = "from shader_health.maya.commands import show_ui\nshow_ui()"


def show_ui() -> Any:
    """Open the dockable Maya Shader Health Inspector panel from script/menu/shelf."""

    return show_panel()


def close_ui(*, delete: bool = True) -> None:
    """Close the dockable Maya Shader Health Inspector panel."""

    close_panel(delete=delete)


def validate_scene_action() -> Any:
    """Validate the current Maya scene and return a UI-friendly result object."""

    return _validate_scene()


def select_node_action(node_name: str) -> NavigationActionResult:
    """Select a Maya node from a UI action."""

    return select_node(node_name)


def open_attribute_editor_action(node_name: str) -> NavigationActionResult:
    """Open Maya Attribute Editor for a node from a UI action."""

    return open_attribute_editor(node_name)


def copy_path_action(path: str) -> NavigationActionResult:
    """Copy a path from a UI action."""

    return copy_path(path)


def reveal_file_action(path: str) -> NavigationActionResult:
    """Reveal a file from a UI action where the host OS supports it."""

    return reveal_file(path)


def export_json_report_action(path: Optional[str] = None) -> Any:
    """Export a JSON report artifact from the current Maya scene."""

    return _export_json_report(path)


def export_html_report_action(path: Optional[str] = None) -> Any:
    """Export an HTML report artifact from the current Maya scene."""

    return _export_html_report(path)


def export_shader_manifest_action(path: Optional[str] = None) -> Any:
    """Export a shader manifest artifact from the current Maya scene."""

    return _export_shader_manifest(path)


def install_menu(parent: Optional[str] = None) -> str:
    """Install Maya menu entries that open and close the dockable panel."""

    cmds = _maya_cmds()
    menu_parent = parent or MAYA_MAIN_WINDOW
    if cmds.menu(MENU_NAME, query=True, exists=True):
        cmds.deleteUI(MENU_NAME, menu=True)
    menu_name = cmds.menu(MENU_NAME, label=MENU_LABEL, parent=menu_parent, tearOff=True)
    cmds.menuItem(label=OPEN_MENU_ITEM_LABEL, parent=menu_name, command=lambda *_: show_ui())
    cmds.menuItem(divider=True, parent=menu_name)
    cmds.menuItem(label=CLOSE_MENU_ITEM_LABEL, parent=menu_name, command=lambda *_: close_ui())
    return str(menu_name)


def uninstall_menu() -> None:
    """Remove the Maya menu entry if it exists."""

    cmds = _maya_cmds()
    if cmds.menu(MENU_NAME, query=True, exists=True):
        cmds.deleteUI(MENU_NAME, menu=True)


def install_shelf(parent: Optional[str] = None) -> str:
    """Install a Maya shelf tab and button that opens the dockable panel."""

    cmds = _maya_cmds()
    shelf_parent = parent or _maya_shelf_top_level()

    if not cmds.shelfLayout(SHELF_NAME, query=True, exists=True):
        cmds.shelfLayout(SHELF_NAME, parent=shelf_parent)

    if cmds.shelfButton(SHELF_BUTTON_NAME, query=True, exists=True):
        cmds.deleteUI(SHELF_BUTTON_NAME, control=True)

    cmds.shelfButton(
        SHELF_BUTTON_NAME,
        parent=SHELF_NAME,
        label=SHELF_BUTTON_LABEL,
        annotation=SHELF_BUTTON_ANNOTATION,
        image1="commandButton.png",
        sourceType="python",
        command=OPEN_UI_PYTHON_COMMAND,
    )
    return SHELF_NAME


def uninstall_shelf() -> None:
    """Remove the Shader Health shelf button if it exists."""

    cmds = _maya_cmds()
    if cmds.shelfButton(SHELF_BUTTON_NAME, query=True, exists=True):
        cmds.deleteUI(SHELF_BUTTON_NAME, control=True)


def install_ui() -> None:
    """Install all Maya UI entrypoints for the current session."""

    install_menu()
    install_shelf()


def _validate_scene() -> Any:
    from shader_health.core import (
        ValidationEngine,
        compute_health_score,
        load_rule_stack,
        summarize_results,
    )
    from shader_health.maya.scanner import scan_scene

    snapshot = scan_scene()
    renderer_ids = (snapshot.renderer,) if snapshot.renderer else ()
    rules = load_rule_stack(renderer_ids=renderer_ids)
    results = tuple(ValidationEngine().validate(snapshot, rules))
    summary = summarize_results(results)
    health_score = compute_health_score(results)
    failed_count = sum(1 for result in results if result.status == "failed")
    message = (
        f"Scene validated. {failed_count} failed issue(s). "
        f"Health: {health_score.score}/100."
    )
    return SimpleNamespace(
        action="validate_scene",
        succeeded=True,
        snapshot=snapshot,
        results=results,
        summary=summary,
        health_score=health_score,
        message=message,
    )


def _export_json_report(path: Optional[str]) -> Any:
    scene = _runtime_scene_metadata()
    output_path = _runtime_output_path(path, scene["scene_path"], "report", "json")
    payload = {
        "report_schema_version": "maya-runtime-1.0",
        "status": "not_validated",
        "summary": {},
        "results": [],
        "snapshot": scene,
    }
    _write_json(output_path, payload)
    return _runtime_result("export_json_report", output_path, "JSON report exported.")


def _export_html_report(path: Optional[str]) -> Any:
    scene = _runtime_scene_metadata()
    output_path = _runtime_output_path(path, scene["scene_path"], "report", "html")
    lines = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        "<title>Maya Shader Health Report</title>",
        "</head>",
        "<body>",
        "<main>",
        "<h1>Maya Shader Health Report</h1>",
        "<h2>Runtime Export</h2>",
        f"<p><strong>Scene:</strong> {_html(scene['scene_path'])}</p>",
        f"<p><strong>Maya:</strong> {_html(scene['maya_version'])}</p>",
        f"<p><strong>Renderer:</strong> {_html(scene['renderer'])}</p>",
        "<p>Status: not_validated</p>",
        "</main>",
        "</body>",
        "</html>",
    ]
    _write_text(output_path, "\n".join(lines) + "\n")
    return _runtime_result("export_html_report", output_path, "HTML report exported.")


def _export_shader_manifest(path: Optional[str]) -> Any:
    scene = _runtime_scene_metadata()
    output_path = _runtime_output_path(path, scene["scene_path"], "manifest", "json")
    payload = {
        "manifest_schema_version": "maya-runtime-1.0",
        "scene_path": scene["scene_path"],
        "maya_version": scene["maya_version"],
        "renderer": scene["renderer"],
        "scan_scope": "scene",
        "materials": [],
    }
    _write_json(output_path, payload)
    return _runtime_result("export_shader_manifest", output_path, "Shader manifest exported.")


def _runtime_scene_metadata() -> dict[str, str]:
    cmds = _maya_cmds()
    scene_path = str(cmds.file(query=True, sceneName=True) or "")
    maya_version = str(cmds.about(version=True) or "")
    renderer = _runtime_renderer(cmds)
    return {
        "scene_path": scene_path,
        "maya_version": maya_version,
        "renderer": renderer,
        "scan_scope": "scene",
    }


def _runtime_renderer(cmds: Any) -> str:
    try:
        return str(cmds.getAttr("defaultRenderGlobals.currentRenderer") or "")
    except Exception:  # noqa: BLE001
        return ""


def _runtime_output_path(
    path: Optional[str],
    scene_path: str,
    suffix: str,
    extension: str,
) -> Path:
    if path:
        return Path(path)
    if scene_path:
        scene = Path(scene_path)
        output_dir = scene.parent
        scene_stem = scene.stem
    else:
        output_dir = Path.cwd()
        scene_stem = "untitled_scene"
    return output_dir / f"{scene_stem}_shader_health_{suffix}.{extension}"


def _write_json(path: Path, payload: Any) -> None:
    _write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _html(value: Any) -> str:
    return escape(str(value), quote=False)


def _runtime_result(action: str, path: Path, message: str) -> Any:
    return SimpleNamespace(
        action=action,
        path=str(path),
        succeeded=True,
        message=message,
    )


def _maya_shelf_top_level() -> str:
    mel = _maya_mel()
    shelf_top_level = mel.eval("$tmp=$gShelfTopLevel")
    return str(shelf_top_level)


def _maya_cmds() -> Any:
    try:
        return importlib.import_module("maya.cmds")
    except ImportError as exc:
        raise RuntimeError("Maya commands are available only inside Autodesk Maya.") from exc


def _maya_mel() -> Any:
    try:
        return importlib.import_module("maya.mel")
    except ImportError as exc:
        raise RuntimeError("Maya MEL is available only inside Autodesk Maya.") from exc
