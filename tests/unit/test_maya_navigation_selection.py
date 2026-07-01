from __future__ import annotations

from typing import Any

import pytest

from shader_health.maya import commands, navigation


class FakeCmds:
    def __init__(self, *, existing_nodes: set[str]) -> None:
        self.existing_nodes = existing_nodes
        self.selected: list[tuple[str, dict[str, Any]]] = []

    def objExists(self, node_name: str) -> bool:
        return node_name in self.existing_nodes

    def select(self, node_name: str, **kwargs: Any) -> None:
        self.selected.append((node_name, dict(kwargs)))


class FakeMel:
    def __init__(self) -> None:
        self.expressions: list[str] = []

    def eval(self, expression: str) -> None:
        self.expressions.append(expression)


def test_select_node_selects_existing_node():
    cmds = FakeCmds(existing_nodes={"file1"})

    result = navigation.select_node("file1", cmds=cmds)

    assert result.succeeded is True
    assert result.action == "select_node"
    assert cmds.selected == [("file1", {"replace": True})]


def test_select_node_reports_missing_node():
    cmds = FakeCmds(existing_nodes=set())

    result = navigation.select_node("missingNode", cmds=cmds)

    assert result.succeeded is False
    assert result.message == "Node does not exist."
    assert cmds.selected == []


def test_open_attribute_editor_selects_node_and_runs_mel_command():
    cmds = FakeCmds(existing_nodes={"VRayMtl1"})
    mel = FakeMel()

    result = navigation.open_attribute_editor("VRayMtl1", cmds=cmds, mel=mel)

    assert result.succeeded is True
    assert cmds.selected == [("VRayMtl1", {"replace": True})]
    assert mel.expressions == ["openAEWindow"]


def test_empty_navigation_target_is_rejected():
    with pytest.raises(ValueError, match="node_name must not be empty"):
        navigation.select_node("   ", cmds=FakeCmds(existing_nodes=set()))


def test_command_wrappers_delegate_to_navigation_actions(monkeypatch: Any):
    calls: list[tuple[str, str]] = []
    result = navigation.NavigationActionResult("action", "target", True, "ok")

    monkeypatch.setattr(
        commands,
        "select_node",
        lambda node_name: calls.append(("select", node_name)) or result,
    )
    monkeypatch.setattr(
        commands,
        "open_attribute_editor",
        lambda node_name: calls.append(("ae", node_name)) or result,
    )

    assert commands.select_node_action("file1") is result
    assert commands.open_attribute_editor_action("file1") is result
    assert calls == [("select", "file1"), ("ae", "file1")]
