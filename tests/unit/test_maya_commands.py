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


STANDALONE_MENU_LABELS = (
    commands.OPEN_MENU_ITEM_LABEL,
    commands.SETTINGS_MENU_ITEM_LABEL,
    commands.VALIDATE_SCENE_MENU_ITEM_LABEL,
    commands.REPORTS_MENU_ITEM_LABEL,
    commands.READINESS_CHECK_MENU_ITEM_LABEL,
    commands.FARM_CHECK_MENU_ITEM_LABEL,
    commands.DOCUMENTATION_MENU_ITEM_LABEL,
    commands.CHECK_FOR_UPDATES_MENU_ITEM_LABEL,
    commands.CLOSE_MENU_ITEM_LABEL,
)

STANDALONE_SHELF_LABELS = (
    commands.OPEN_MENU_ITEM_LABEL,
    commands.SETTINGS_MENU_ITEM_LABEL,
    commands.VALIDATE_SCENE_MENU_ITEM_LABEL,
    commands.REPORTS_MENU_ITEM_LABEL,
    commands.READINESS_CHECK_MENU_ITEM_LABEL,
    commands.FARM_CHECK_MENU_ITEM_LABEL,
    commands.DOCUMENTATION_MENU_ITEM_LABEL,
    commands.CHECK_FOR_UPDATES_MENU_ITEM_LABEL,
)


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


def test_show_settings_ui_delegates_to_settings_launcher(monkeypatch: Any):
    sentinel = object()
    monkeypatch.setattr(commands, "show_settings_panel", lambda: sentinel)

    assert commands.show_settings_ui() is sentinel


def test_show_validate_scene_ui_delegates_to_validate_launcher(monkeypatch: Any):
    sentinel = object()
    monkeypatch.setattr(commands, "show_validate_scene_panel", lambda: sentinel)

    assert commands.show_validate_scene_ui() is sentinel


def test_show_reports_ui_delegates_to_reports_launcher(monkeypatch: Any):
    sentinel = object()
    monkeypatch.setattr(commands, "show_reports_panel", lambda: sentinel)

    assert commands.show_reports_ui() is sentinel


def test_show_readiness_check_ui_delegates_to_readiness_launcher(monkeypatch: Any):
    sentinel = object()
    monkeypatch.setattr(commands, "show_readiness_check_panel", lambda: sentinel)

    assert commands.show_readiness_check_ui() is sentinel


def test_show_check_for_updates_ui_delegates_to_updates_launcher(monkeypatch: Any):
    sentinel = object()
    monkeypatch.setattr(commands, "show_check_for_updates_panel", lambda: sentinel)

    assert commands.show_check_for_updates_ui() is sentinel


def test_show_documentation_ui_delegates_to_documentation_action(monkeypatch: Any):
    monkeypatch.setattr(commands, "open_documentation_action", lambda: True)

    assert commands.show_documentation_ui() is True


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
    assert [item["label"] for item in cmds.created_items if "label" in item] == list(
        STANDALONE_MENU_LABELS
    )
    assert all(
        callable(item["command"]) for item in cmds.created_items if "command" in item
    )
    assert sum(1 for item in cmds.created_items if item.get("divider")) == 1
    assert cmds.created_items[-1]["label"] == commands.CLOSE_MENU_ITEM_LABEL
    assert cmds.created_items[0]["label"] == commands.OPEN_MENU_ITEM_LABEL


def test_uninstall_menu_deletes_existing_menu(monkeypatch: Any):
    cmds = FakeCmds(menu_exists=True)
    monkeypatch.setattr(commands, "_maya_cmds", lambda: cmds)

    commands.uninstall_menu()

    assert cmds.deleted == [(commands.MENU_NAME, {"menu": True})]


def test_install_shelf_creates_shelf_and_buttons(monkeypatch: Any):
    cmds = FakeCmds(menu_exists=False, shelf_exists=False)
    monkeypatch.setattr(commands, "_maya_cmds", lambda: cmds)
    monkeypatch.setattr(commands, "_maya_shelf_top_level", lambda: "ShelfLayout")

    shelf_name = commands.install_shelf()

    assert shelf_name == commands.SHELF_NAME
    assert cmds.created_shelf == (commands.SHELF_NAME, {"parent": "ShelfLayout"})
    assert len(cmds.created_buttons) == 8
    assert cmds.created_buttons[0][1]["label"] == commands.OPEN_MENU_ITEM_LABEL
    created_labels = [fields["label"] for _, fields in cmds.created_buttons]
    assert created_labels == list(STANDALONE_SHELF_LABELS)
    for _, fields in cmds.created_buttons:
        assert fields["sourceType"] == "python"
        assert "image1" in fields
        assert fields["parent"] == commands.SHELF_NAME


def test_install_shelf_updates_existing_button(monkeypatch: Any):
    cmds = FakeCmds(menu_exists=False, shelf_exists=True)
    for entry in commands._standalone_shelf_entries():
        cmds.existing_buttons.add(entry["name"])
        cmds.button_labels[entry["name"]] = entry["label"]
        cmds.shelf_children.append(entry["name"])
    monkeypatch.setattr(commands, "_maya_cmds", lambda: cmds)
    monkeypatch.setattr(commands, "_maya_shelf_top_level", lambda: "ShelfLayout")

    commands.install_shelf()

    assert cmds.deleted == []
    assert cmds.created_shelf is None
    assert len(cmds.created_buttons) == 0
    assert len(cmds.edited_buttons) == 8


def test_install_shelf_removes_legacy_duplicate_labels(monkeypatch: Any):
    cmds = FakeCmds(menu_exists=False, shelf_exists=True)
    legacy_names = {
        "shelfButton42": commands.LEGACY_SHELF_BUTTON_LABEL,
        commands.FARM_CHECK_SHELF_BUTTON_NAME: commands.FARM_CHECK_SHELF_BUTTON_LABEL,
        "shelfButton99": commands.LEGACY_FARM_CHECK_SHELF_BUTTON_LABEL,
    }
    cmds.existing_buttons.update(legacy_names)
    cmds.button_labels.update(legacy_names)
    cmds.shelf_children = list(legacy_names)
    monkeypatch.setattr(commands, "_maya_cmds", lambda: cmds)
    monkeypatch.setattr(commands, "_maya_shelf_top_level", lambda: "ShelfLayout")

    commands.install_shelf()

    assert ("shelfButton42", {"control": True}) in cmds.deleted
    assert ("shelfButton99", {"control": True}) in cmds.deleted
    assert len(cmds.created_buttons) == 7
    assert len(cmds.edited_buttons) == 1


def test_uninstall_shelf_deletes_existing_button(monkeypatch: Any):
    cmds = FakeCmds(menu_exists=False, shelf_exists=True)
    for entry in commands._standalone_shelf_entries():
        cmds.existing_buttons.add(entry["name"])
        cmds.button_labels[entry["name"]] = entry["label"]
        cmds.shelf_children.append(entry["name"])
    monkeypatch.setattr(commands, "_maya_cmds", lambda: cmds)

    commands.uninstall_shelf()

    for entry in commands._standalone_shelf_entries():
        assert (entry["name"], {"control": True}) in cmds.deleted


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
