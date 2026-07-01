"""Maya command entrypoints for Shader Health Inspector."""
from __future__ import annotations

import importlib
from typing import Any, Optional

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


def _maya_shelf_top_level() -> str:
    mel: Any = _maya_module("maya.mel")
    return str(mel.eval("$tmp = $gShelfTopLevel"))


def _maya_cmds() -> Any:
    return _maya_module("maya.cmds")


def _maya_module(module_name: str) -> Any:
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        raise RuntimeError("Maya commands can only run inside Autodesk Maya.") from exc
