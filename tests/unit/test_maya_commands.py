from __future__ import annotations

from typing import Any, Optional

from pipeline_inspector.core import GraphSnapshot
from pipeline_inspector.maya import commands


class FakeCmds:
    def __init__(self, *, menu_exists: bool, shelf_exists: bool = False) -> None:
        self.menu_exists = menu_exists
        self.shelf_exists = shelf_exists
        self.existing_buttons: set[str] = set()
        self.button_labels: dict[str, str] = {}
        self.deleted: list[tuple[str, dict[str, Any]]] = []
        self.created_menu: Optional[tuple[str, dict[str, Any]]] = None
        self.created_items: list[dict[str, Any]] = []
        self.created_shelf: Optional[tuple[str, dict[str, Any]]] = None
        self.created_buttons: list[tuple[str, dict[str, Any]]] = []
        self.edited_buttons: list[tuple[str, dict[str, Any]]] = []
        self.shelf_children: list[str] = []

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
        if kwargs.get("query") and kwargs.get("childArray"):
            return list(self.shelf_children)
        self.created_shelf = (name, dict(kwargs))
        self.shelf_exists = True
        return name

    def shelfButton(self, name: str, **kwargs: Any) -> object:
        if kwargs.get("query") and kwargs.get("exists"):
            return name in self.existing_buttons
        if kwargs.get("query") and kwargs.get("label"):
            return self.button_labels.get(name, "")
        if kwargs.get("edit"):
            fields = dict(kwargs)
            fields.pop("edit", None)
            if "label" in fields:
                self.button_labels[name] = str(fields["label"])
            self.edited_buttons.append((name, fields))
            return name
        fields = dict(kwargs)
        self.created_buttons.append((name, fields))
        self.existing_buttons.add(name)
        if "label" in fields:
            self.button_labels[name] = str(fields["label"])
        if name not in self.shelf_children:
            self.shelf_children.append(name)
        return name

    def deleteUI(self, name: str, **kwargs: Any) -> None:
        self.deleted.append((name, dict(kwargs)))
        if kwargs.get("menu"):
            self.menu_exists = False
        if kwargs.get("control"):
            self.existing_buttons.discard(name)
            self.button_labels.pop(name, None)
            if name in self.shelf_children:
                self.shelf_children.remove(name)


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


def test_show_farm_check_ui_delegates_to_farm_check_launcher(monkeypatch: Any):
    sentinel = object()
    monkeypatch.setattr(commands, "show_farm_check_panel", lambda: sentinel)

    assert commands.show_farm_check_ui() is sentinel


def test_validate_scene_action_runs_scanner_and_validator(monkeypatch: Any):
    from pipeline_inspector.maya import scanner

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
    from pipeline_inspector.maya import scanner

    monkeypatch.setattr(scanner, "selection_node_names", lambda: [])

    result = commands.validate_selection_action()

    assert result.succeeded is False
    assert "Nothing selected" in result.message


def test_validate_selection_action_reports_missing_shader_networks(monkeypatch: Any):
    from pipeline_inspector.maya import scanner

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
    assert cmds.created_items[1]["label"] == commands.FARM_CHECK_MENU_ITEM_LABEL
    assert callable(cmds.created_items[1]["command"])
    assert cmds.created_items[2] == {"divider": True, "parent": commands.MENU_NAME}
    assert cmds.created_items[3]["label"] == commands.CLOSE_MENU_ITEM_LABEL
    assert callable(cmds.created_items[3]["command"])


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
        ),
        (
            commands.FARM_CHECK_SHELF_BUTTON_NAME,
            {
                "parent": commands.SHELF_NAME,
                "label": commands.FARM_CHECK_SHELF_BUTTON_LABEL,
                "annotation": commands.FARM_CHECK_SHELF_BUTTON_ANNOTATION,
                "image1": "commandButton.png",
                "sourceType": "python",
                "command": commands.FARM_CHECK_UI_PYTHON_COMMAND,
            },
        ),
    ]


def test_install_shelf_updates_existing_button(monkeypatch: Any):
    cmds = FakeCmds(menu_exists=False, shelf_exists=True)
    cmds.existing_buttons.update(
        {commands.SHELF_BUTTON_NAME, commands.FARM_CHECK_SHELF_BUTTON_NAME}
    )
    cmds.button_labels[commands.SHELF_BUTTON_NAME] = commands.SHELF_BUTTON_LABEL
    cmds.button_labels[commands.FARM_CHECK_SHELF_BUTTON_NAME] = (
        commands.FARM_CHECK_SHELF_BUTTON_LABEL
    )
    cmds.shelf_children = [
        commands.SHELF_BUTTON_NAME,
        commands.FARM_CHECK_SHELF_BUTTON_NAME,
    ]
    monkeypatch.setattr(commands, "_maya_cmds", lambda: cmds)
    monkeypatch.setattr(commands, "_maya_shelf_top_level", lambda: "ShelfLayout")

    commands.install_shelf()

    assert cmds.deleted == []
    assert cmds.created_shelf is None
    assert len(cmds.created_buttons) == 0
    assert len(cmds.edited_buttons) == 2


def test_install_shelf_removes_legacy_duplicate_labels(monkeypatch: Any):
    cmds = FakeCmds(menu_exists=False, shelf_exists=True)
    cmds.existing_buttons.update(
        {
            commands.SHELF_BUTTON_NAME,
            "shelfButton42",
            commands.FARM_CHECK_SHELF_BUTTON_NAME,
            "shelfButton99",
        }
    )
    cmds.button_labels[commands.SHELF_BUTTON_NAME] = commands.SHELF_BUTTON_LABEL
    cmds.button_labels["shelfButton42"] = commands.SHELF_BUTTON_LABEL
    cmds.button_labels[commands.FARM_CHECK_SHELF_BUTTON_NAME] = (
        commands.FARM_CHECK_SHELF_BUTTON_LABEL
    )
    cmds.button_labels["shelfButton99"] = commands.FARM_CHECK_SHELF_BUTTON_LABEL
    cmds.shelf_children = [
        commands.SHELF_BUTTON_NAME,
        "shelfButton42",
        commands.FARM_CHECK_SHELF_BUTTON_NAME,
        "shelfButton99",
    ]
    monkeypatch.setattr(commands, "_maya_cmds", lambda: cmds)
    monkeypatch.setattr(commands, "_maya_shelf_top_level", lambda: "ShelfLayout")

    commands.install_shelf()

    assert ("shelfButton42", {"control": True}) in cmds.deleted
    assert ("shelfButton99", {"control": True}) in cmds.deleted
    assert len(cmds.created_buttons) == 0
    assert len(cmds.edited_buttons) == 2


def test_uninstall_shelf_deletes_existing_button(monkeypatch: Any):
    cmds = FakeCmds(menu_exists=False, shelf_exists=True)
    cmds.existing_buttons.update(
        {commands.SHELF_BUTTON_NAME, commands.FARM_CHECK_SHELF_BUTTON_NAME}
    )
    cmds.button_labels[commands.SHELF_BUTTON_NAME] = commands.SHELF_BUTTON_LABEL
    cmds.button_labels[commands.FARM_CHECK_SHELF_BUTTON_NAME] = (
        commands.FARM_CHECK_SHELF_BUTTON_LABEL
    )
    cmds.shelf_children = [
        commands.SHELF_BUTTON_NAME,
        commands.FARM_CHECK_SHELF_BUTTON_NAME,
    ]
    monkeypatch.setattr(commands, "_maya_cmds", lambda: cmds)

    commands.uninstall_shelf()

    assert (commands.SHELF_BUTTON_NAME, {"control": True}) in cmds.deleted
    assert (commands.FARM_CHECK_SHELF_BUTTON_NAME, {"control": True}) in cmds.deleted


def test_install_ui_refreshes_menu_and_shelf(monkeypatch: Any):
    calls: list[str] = []
    monkeypatch.setattr(
        commands,
        "install_menu",
        lambda: calls.append("menu") or commands.MENU_NAME,
    )
    monkeypatch.setattr(
        commands,
        "install_shelf",
        lambda: calls.append("shelf") or commands.SHELF_NAME,
    )

    commands.install_ui()
    commands.install_ui()

    assert calls == ["menu", "shelf", "menu", "shelf"]
