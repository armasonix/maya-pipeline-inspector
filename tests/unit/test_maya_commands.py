from __future__ import annotations

from typing import Any, Optional

from shader_health.maya import commands


class FakeCmds:
    def __init__(self, *, menu_exists: bool) -> None:
        self.menu_exists = menu_exists
        self.deleted: list[tuple[str, dict[str, Any]]] = []
        self.created_menu: Optional[tuple[str, dict[str, Any]]] = None
        self.created_items: list[dict[str, Any]] = []

    def menu(self, name: str, **kwargs: Any) -> object:
        if kwargs.get("query") and kwargs.get("exists"):
            return self.menu_exists
        self.created_menu = (name, dict(kwargs))
        self.menu_exists = True
        return name

    def menuItem(self, **kwargs: Any) -> None:
        self.created_items.append(dict(kwargs))

    def deleteUI(self, name: str, **kwargs: Any) -> None:
        self.deleted.append((name, dict(kwargs)))
        self.menu_exists = False


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
    assert cmds.created_items == [
        {
            "label": commands.MENU_ITEM_LABEL,
            "parent": commands.MENU_NAME,
            "command": commands.MENU_COMMAND,
        }
    ]


def test_uninstall_menu_deletes_existing_menu(monkeypatch: Any):
    cmds = FakeCmds(menu_exists=True)
    monkeypatch.setattr(commands, "_maya_cmds", lambda: cmds)

    commands.uninstall_menu()

    assert cmds.deleted == [(commands.MENU_NAME, {"menu": True})]
