from __future__ import annotations

from typing import Any, Optional

from shader_health.core import GraphSnapshot
from shader_health.maya import commands


class FakeCmds:
    def __init__(self, *, menu_exists: bool, shelf_exists: bool = False) -> None:
        self.menu_exists = menu_exists
        self.shelf_exists = shelf_exists
        self.button_exists = False
        self.deleted: list[tuple[str, dict[str, Any]]] = []
        self.created_menu: Optional[tuple[str, dict[str, Any]]] = None
        self.created_items: list[dict[str, Any]] = []
        self.created_shelf: Optional[tuple[str, dict[str, Any]]] = None
        self.created_buttons: list[tuple[str, dict[str, Any]]] = []

    def menu(self, name: str, **kwargs: Any) -> object:
        if kwargs.get("query") and kwargs.get("exists"):
            return self.menu_exists
        self.created_menu = (name, dict(kwargs))
        self.menu_exists = True
        return name

    def menuItem(self, **kwargs: Any) -> None:
        self.created_items.append(dict(kwargs))

    def shelfLayout(self, name: str, **kwargs: Any) -> object:
        if kwargs.get("query") and kwargs.get("exists"):
            return self.shelf_exists
        self.created_shelf = (name, dict(kwargs))
        self.shelf_exists = True
        return name

    def shelfButton(self, name: str, **kwargs: Any) -> object:
        if kwargs.get("query") and kwargs.get("exists"):
            return self.button_exists
        self.created_buttons.append((name, dict(kwargs)))
        self.button_exists = True
        return name

    def deleteUI(self, name: str, **kwargs: Any) -> None:
        self.deleted.append((name, dict(kwargs)))
        if kwargs.get("menu"):
            self.menu_exists = False
        if kwargs.get("control") and name == commands.SHELF_BUTTON_NAME:
            self.button_exists = False


def test_show_ui_delegates_to_panel_launcher(monkeypatch: Any):
    sentinel = object()
    monkeypatch.setattr(commands, "show_panel", lambda: sentinel)

    assert commands.show_ui() is sentinel


def test_close_ui_delegates_to_panel_launcher(monkeypatch: Any):
    calls: list[dict[str, Any]] = []

    def fake_close_panel(**kwargs: Any) -> None:
        calls.append(dict(kwargs))

    monkeypatch.setattr(commands, "close_panel", fake_close_panel)

    commands.close_ui(delete=False)

    assert calls == [{"delete": False}]


def test_validate_scene_action_runs_scanner_and_validator(monkeypatch: Any):
    from shader_health.maya import scanner

    monkeypatch.setattr(
        scanner,
        "scan_scene",
        lambda: GraphSnapshot(scene_path="demo.ma", renderer="common"),
    )

    result = commands.validate_scene_action()

    assert result.action == "validate_scene"
    assert result.succeeded is True
    assert result.snapshot.scene_path == "demo.ma"
    assert result.health_score.score == 100
    assert "Scene validated" in result.message or "validated with profile" in result.message


def test_validate_selection_action_reports_empty_selection(monkeypatch: Any):
    from shader_health.maya import scanner

    monkeypatch.setattr(scanner, "selection_node_names", lambda: [])

    result = commands.validate_selection_action()

    assert result.succeeded is False
    assert "Nothing selected" in result.message


def test_validate_selection_action_reports_missing_shader_networks(monkeypatch: Any):
    from shader_health.maya import scanner

    monkeypatch.setattr(scanner, "selection_node_names", lambda: ["pCube1"])
    monkeypatch.setattr(
        scanner,
        "scan_selection",
        lambda: GraphSnapshot(scene_path="demo.ma", renderer="common"),
    )

    result = commands.validate_selection_action()

    assert result.succeeded is False
    assert "no assigned shader networks" in result.message.casefold()


def test_install_menu_replaces_existing_menu(monkeypatch: Any):
    cmds = FakeCmds(menu_exists=True)
    monkeypatch.setattr(commands, "_maya_cmds", lambda: cmds)

    menu_name = commands.install_menu()

    assert menu_name == commands.MENU_NAME
    assert cmds.deleted == [(commands.MENU_NAME, {"menu": True})]
    assert cmds.created_menu == (
        commands.MENU_NAME,
        {
            "label": commands.MENU_LABEL,
            "parent": commands.MAYA_MAIN_WINDOW,
            "tearOff": True,
        },
    )
    assert cmds.created_items[0]["label"] == commands.OPEN_MENU_ITEM_LABEL
    assert callable(cmds.created_items[0]["command"])
    assert cmds.created_items[1] == {"divider": True, "parent": commands.MENU_NAME}
    assert cmds.created_items[2]["label"] == commands.CLOSE_MENU_ITEM_LABEL
    assert callable(cmds.created_items[2]["command"])


def test_uninstall_menu_deletes_existing_menu(monkeypatch: Any):
    cmds = FakeCmds(menu_exists=True)
    monkeypatch.setattr(commands, "_maya_cmds", lambda: cmds)

    commands.uninstall_menu()

    assert cmds.deleted == [(commands.MENU_NAME, {"menu": True})]


def test_install_shelf_creates_shelf_and_button(monkeypatch: Any):
    cmds = FakeCmds(menu_exists=False, shelf_exists=False)
    monkeypatch.setattr(commands, "_maya_cmds", lambda: cmds)
    monkeypatch.setattr(commands, "_maya_shelf_top_level", lambda: "ShelfLayout")

    shelf_name = commands.install_shelf()

    assert shelf_name == commands.SHELF_NAME
    assert cmds.created_shelf == (commands.SHELF_NAME, {"parent": "ShelfLayout"})
    assert cmds.created_buttons == [
        (
            commands.SHELF_BUTTON_NAME,
            {
                "parent": commands.SHELF_NAME,
                "label": commands.SHELF_BUTTON_LABEL,
                "annotation": commands.SHELF_BUTTON_ANNOTATION,
                "image1": "commandButton.png",
                "sourceType": "python",
                "command": commands.OPEN_UI_PYTHON_COMMAND,
            },
        )
    ]


def test_install_shelf_replaces_existing_button(monkeypatch: Any):
    cmds = FakeCmds(menu_exists=False, shelf_exists=True)
    cmds.button_exists = True
    monkeypatch.setattr(commands, "_maya_cmds", lambda: cmds)
    monkeypatch.setattr(commands, "_maya_shelf_top_level", lambda: "ShelfLayout")

    commands.install_shelf()

    assert cmds.deleted == [(commands.SHELF_BUTTON_NAME, {"control": True})]
    assert cmds.created_shelf is None
    assert len(cmds.created_buttons) == 1


def test_uninstall_shelf_deletes_existing_button(monkeypatch: Any):
    cmds = FakeCmds(menu_exists=False, shelf_exists=True)
    cmds.button_exists = True
    monkeypatch.setattr(commands, "_maya_cmds", lambda: cmds)

    commands.uninstall_shelf()

    assert cmds.deleted == [(commands.SHELF_BUTTON_NAME, {"control": True})]


def test_install_ui_installs_menu_and_shelf(monkeypatch: Any):
    calls: list[str] = []
    monkeypatch.setattr(commands, "install_menu", lambda: calls.append("menu"))
    monkeypatch.setattr(commands, "install_shelf", lambda: calls.append("shelf"))

    commands.install_ui()

    assert calls == ["menu", "shelf"]
