from __future__ import annotations

from typing import Any, Optional

from shader_health.maya import ui_launcher


class FakePanel:
    def __init__(self) -> None:
        self.show_calls: list[dict[str, Any]] = []
        self.closed = False

    def show(self, **kwargs: Any) -> None:
        self.show_calls.append(dict(kwargs))

    def close(self) -> None:
        self.closed = True


class FakeCmds:
    def __init__(self, *, workspace_exists: bool) -> None:
        self.workspace_exists = workspace_exists
        self.deleted: list[tuple[str, dict[str, Any]]] = []
        self.restored: list[str] = []
        self.closed: list[str] = []

    def workspaceControl(self, name: str, **kwargs: Any) -> Optional[bool]:
        if kwargs.get("query") and kwargs.get("exists"):
            return self.workspace_exists
        if kwargs.get("edit") and kwargs.get("restore"):
            self.restored.append(name)
            return None
        if kwargs.get("edit") and kwargs.get("close"):
            self.closed.append(name)
            return None
        return None

    def deleteUI(self, name: str, **kwargs: Any) -> None:
        self.deleted.append((name, dict(kwargs)))
        self.workspace_exists = False


def test_show_panel_creates_dockable_panel(monkeypatch: Any):
    cmds = FakeCmds(workspace_exists=False)
    panel = FakePanel()
    monkeypatch.setattr(ui_launcher, "_PANEL", None)
    monkeypatch.setattr(ui_launcher, "_maya_cmds", lambda: cmds)
    monkeypatch.setattr(ui_launcher, "_create_dockable_panel", lambda: panel)

    result = ui_launcher.show_panel()

    assert result is panel
    assert panel.show_calls == [
        {
            "dockable": True,
            "area": "right",
            "floating": False,
            "retain": False,
        }
    ]


def test_show_panel_restores_existing_panel(monkeypatch: Any):
    cmds = FakeCmds(workspace_exists=True)
    panel = FakePanel()
    monkeypatch.setattr(ui_launcher, "_PANEL", panel)
    monkeypatch.setattr(ui_launcher, "_maya_cmds", lambda: cmds)

    result = ui_launcher.show_panel()

    assert result is panel
    assert cmds.restored == [ui_launcher.WORKSPACE_CONTROL_NAME]
    assert panel.show_calls == [{}]


def test_show_panel_recreates_stale_workspace_control(monkeypatch: Any):
    cmds = FakeCmds(workspace_exists=True)
    panel = FakePanel()
    monkeypatch.setattr(ui_launcher, "_PANEL", None)
    monkeypatch.setattr(ui_launcher, "_maya_cmds", lambda: cmds)
    monkeypatch.setattr(ui_launcher, "_create_dockable_panel", lambda: panel)

    result = ui_launcher.show_panel()

    assert result is panel
    assert cmds.deleted == [(ui_launcher.WORKSPACE_CONTROL_NAME, {"control": True})]
    assert panel.show_calls[0]["dockable"] is True


def test_close_panel_deletes_workspace_control(monkeypatch: Any):
    cmds = FakeCmds(workspace_exists=True)
    panel = FakePanel()
    monkeypatch.setattr(ui_launcher, "_PANEL", panel)
    monkeypatch.setattr(ui_launcher, "_maya_cmds", lambda: cmds)

    ui_launcher.close_panel()

    assert cmds.deleted == [(ui_launcher.WORKSPACE_CONTROL_NAME, {"control": True})]
    assert panel.closed is True
    assert ui_launcher._PANEL is None
