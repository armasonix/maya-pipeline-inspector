from __future__ import annotations

from pipeline_inspector.core.render_presets import CommonRenderQualitySettings, RenderQualityPreset, RenderSettings
from pipeline_inspector.maya import render_preset_actions


class _FakeCmds:
    def __init__(self) -> None:
        self.nodes = {"defaultResolution", "defaultArnoldRenderOptions", "defaultRenderGlobals"}
        self.attrs: dict[str, int | float] = {}

    def objExists(self, node_name: str) -> bool:
        return node_name in self.nodes

    def setAttr(self, plug: str, value: int | float) -> None:
        self.attrs[plug] = value

    def getAttr(self, plug: str) -> str:
        _ = plug
        return "arnold"

    def playbackOptions(self, *, query: bool, min: bool = False, max: bool = False) -> float:
        _ = query
        if min:
            return 1.0
        if max:
            return 24.0
        return 0.0


def test_apply_studio_render_quality_to_scene_uses_production_resolution(monkeypatch):
    cmds = _FakeCmds()
    monkeypatch.setattr(render_preset_actions, "_maya_cmds", lambda: cmds)
    render = RenderSettings(
        production=RenderQualityPreset(
            common=CommonRenderQualitySettings(width=4096, height=2305),
        )
    )

    result = render_preset_actions.apply_studio_render_quality_to_scene(
        render,
        "production",
        cmds=cmds,
    )

    assert result.succeeded is True
    assert cmds.attrs["defaultResolution.width"] == 4096
    assert cmds.attrs["defaultRenderGlobals.endFrame"] == 24
