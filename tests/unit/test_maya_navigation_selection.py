from __future__ import annotations

from typing import Any

import pytest

from shader_health.maya import commands, navigation


class FakeCmds:
    def __init__(self, *, existing_nodes: set[str], hypershade_open: bool = False) -> None:
        self.existing_nodes = existing_nodes
        self.selected: list[tuple[str, dict[str, Any]]] = []
        self.hyper_shade_calls: list[dict[str, Any]] = []
        self.hypershade_open = hypershade_open
        self.deferred_callbacks: list[Any] = []

    def objExists(self, node_name: str) -> bool:
        return node_name in self.existing_nodes

    def select(self, node_name: str, **kwargs: Any) -> None:
        self.selected.append((node_name, dict(kwargs)))

    def hyperShade(self, **kwargs: Any) -> None:
        self.hyper_shade_calls.append(dict(kwargs))

    def modelPanel(self, panel_name: str, *, exists: bool = False, **kwargs: Any) -> bool:
        if exists:
            return panel_name == "hyperShadePanel1" and self.hypershade_open
        return panel_name == "hyperShadePanel1"

    def HypershadeWindow(self) -> None:
        self.hypershade_open = True

    def evalDeferred(self, callback: Any) -> None:
        self.deferred_callbacks.append(callback)
        callback()


class FakeMel:
    def __init__(self) -> None:
        self.expressions: list[str] = []

    def eval(self, expression: str) -> str:
        self.expressions.append(expression)
        return ""


def test_select_node_selects_existing_node():
    cmds = FakeCmds(existing_nodes={"file1"})

    result = navigation.select_node("file1", cmds=cmds)

    assert result.succeeded is True
    assert result.action == "select_node"
    assert cmds.selected == [("file1", {"replace": True})]


def test_open_in_hypershade_opens_window_and_shows_shader_network():
    cmds = FakeCmds(existing_nodes={"demo_missing_texture_MTL"})
    mel = FakeMel()

    result = navigation.open_in_hypershade("demo_missing_texture_MTL", cmds=cmds, mel=mel)

    assert result.succeeded is True
    assert cmds.hypershade_open is True
    assert "HypershadeWindow" not in mel.expressions
    assert (
        'hyperShadePanelGraphCommand("hyperShadePanel1", "showUpAndDownstream")'
        in mel.expressions
    )
    assert cmds.selected == [("demo_missing_texture_MTL", {"replace": True})]
    assert cmds.hyper_shade_calls == [{"shaderNetwork": "demo_missing_texture_MTL"}]
    assert "input and output connections" in result.message


def test_open_in_hypershade_reuses_open_window_and_switches_material():
    cmds = FakeCmds(
        existing_nodes={"demo_missing_texture_MTL", "VRayMtl1"},
        hypershade_open=True,
    )
    mel = FakeMel()

    first = navigation.open_in_hypershade("demo_missing_texture_MTL", cmds=cmds, mel=mel)
    second = navigation.open_in_hypershade("VRayMtl1", cmds=cmds, mel=mel)

    assert first.succeeded is True
    assert second.succeeded is True
    assert cmds.hypershade_open is True
    assert mel.expressions.count("HypershadeWindow") == 0
    assert mel.expressions.count(
        'hyperShadePanelGraphCommand("hyperShadePanel1", "showUpAndDownstream")',
    ) == 2
    assert cmds.hyper_shade_calls == [
        {"shaderNetwork": "demo_missing_texture_MTL"},
        {"shaderNetwork": "VRayMtl1"},
    ]


def test_open_in_hypershade_falls_back_to_mel_shader_network():
    cmds = FakeCmds(existing_nodes={"VRayMtl1"})
    cmds.hyperShade = None  # type: ignore[method-assign]
    mel = FakeMel()

    result = navigation.open_in_hypershade("VRayMtl1", cmds=cmds, mel=mel)

    assert result.succeeded is True
    assert cmds.hypershade_open is True
    assert "HypershadeWindow" not in mel.expressions
    assert 'hyperShade -shaderNetwork "VRayMtl1"' in mel.expressions
    assert (
        'hyperShadePanelGraphCommand("hyperShadePanel1", "showUpAndDownstream")'
        in mel.expressions
    )


def test_open_in_hypershade_action_prefers_material_over_texture_node(monkeypatch: Any):
    cmds = FakeCmds(
        existing_nodes={"demo_missing_texture_MTL", "demo_albedo_v001_1"},
    )
    calls: list[str] = []

    def fake_open_in_hypershade(node_name: str) -> navigation.NavigationActionResult:
        calls.append(node_name)
        return navigation.NavigationActionResult(
            "open_in_hypershade",
            node_name,
            True,
            "ok",
        )

    monkeypatch.setattr(commands, "_maya_cmds", lambda: cmds)
    monkeypatch.setattr(commands, "open_in_hypershade", fake_open_in_hypershade)

    result = commands.open_in_hypershade_action(
        "node:demo_albedo_v001_1",
        material_name="demo_missing_texture_MTL",
    )

    assert result.succeeded is True
    assert calls == ["demo_missing_texture_MTL"]


def test_empty_navigation_target_is_rejected():
    with pytest.raises(ValueError, match="node_name must not be empty"):
        navigation.select_node("   ", cmds=FakeCmds(existing_nodes=set()))
