"""Maya command entrypoints for Shader Health Inspector."""
from __future__ import annotations

from typing import Any, Optional

from shader_health.maya.ui_launcher import close_panel, show_panel

MENU_NAME = "shaderHealthInspectorMenu"
MENU_LABEL = "Shader Health"
MENU_ITEM_LABEL = "Open Shader Health Inspector"
MAYA_MAIN_WINDOW = "MayaWindow"
MENU_COMMAND = "from shader_health.maya.commands import show_ui; show_ui()"


def show_ui() -> Any:
    """Open the dockable Maya Shader Health Inspector panel from script/menu/shelf."""

    return show_panel()


def close_ui(*, delete: bool = True) -> None:
    """Close the dockable Maya Shader Health Inspector panel."""

    close_panel(delete=delete)


def install_menu(parent: Optional[str] = None) -> str:
    """Install a simple Maya menu entry that opens the dockable panel."""

    cmds = _maya_cmds()
    menu_parent = parent or MAYA_MAIN_WINDOW
    if cmds.menu(MENU_NAME, query=True, exists=True):
        cmds.deleteUI(MENU_NAME, menu=True)
    menu_name = cmds.menu(MENU_NAME, label=MENU_LABEL, parent=menu_parent, tearOff=True)
    cmds.menuItem(label=MENU_ITEM_LABEL, parent=menu_name, command=MENU_COMMAND)
    return str(menu_name)


def uninstall_menu() -> None:
    """Remove the Maya menu entry if it exists."""

    cmds = _maya_cmds()
    if cmds.menu(MENU_NAME, query=True, exists=True):
        cmds.deleteUI(MENU_NAME, menu=True)


def _maya_cmds() -> Any:
    try:
        from maya import cmds  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("Maya commands can only run inside Autodesk Maya.") from exc
    return cmds
