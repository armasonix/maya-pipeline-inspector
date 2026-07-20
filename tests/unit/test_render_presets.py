from __future__ import annotations

from pipeline_inspector.core.render_presets import (
    ArnoldRenderQualitySettings,
    CommonRenderQualitySettings,
    RenderQualityPreset,
    RenderSettings,
    VrayRenderQualitySettings,
    apply_render_quality_preset,
)


class _FakeCmds:
    def __init__(self) -> None:
        self.nodes = {"defaultResolution", "vraySettings", "defaultArnoldRenderOptions", "defaultRenderGlobals"}
        self.attrs: dict[str, int | float] = {}

    def objExists(self, node_name: str) -> bool:
        return node_name in self.nodes

    def setAttr(self, plug: str, value: int | float) -> None:
        self.attrs[plug] = value

    def playbackOptions(self, *, query: bool, min: bool = False, max: bool = False) -> float:
        _ = query
        if min:
            return 1.0
        if max:
            return 24.0
        return 0.0


def test_render_settings_round_trip_dict():
    original = RenderSettings(
        draft=RenderQualityPreset(
            common=CommonRenderQualitySettings(width=960, height=540),
            vray=VrayRenderQualitySettings(max_subdivs=4),
            arnold=ArnoldRenderQualitySettings(aa_samples=2),
        ),
        production=RenderQualityPreset(
            common=CommonRenderQualitySettings(width=1920, height=1080),
            vray=VrayRenderQualitySettings(max_subdivs=16, ray_depth=8),
            arnold=ArnoldRenderQualitySettings(aa_samples=6, gi_diffuse_samples=3),
        ),
    )

    restored = RenderSettings.from_mapping(original.to_dict())

    assert restored.to_dict() == original.to_dict()


def test_apply_render_quality_preset_sets_maya_attrs_for_vray():
    cmds = _FakeCmds()
    preset = RenderQualityPreset(
        common=CommonRenderQualitySettings(width=1280, height=720),
        vray=VrayRenderQualitySettings(max_subdivs=12, ray_depth=6),
    )

    applied = apply_render_quality_preset(preset, renderer="vray", cmds=cmds)

    assert "defaultResolution.width" in applied
    assert "defaultResolution.height" in applied
    assert "vraySettings.dmc_maxSubdivs" in applied
    assert cmds.attrs["defaultResolution.width"] == 1280
    assert cmds.attrs["vraySettings.dmc_maxSubdivs"] == 12


def test_apply_render_quality_preset_sets_arnold_attrs():
    cmds = _FakeCmds()
    preset = RenderQualityPreset(
        arnold=ArnoldRenderQualitySettings(aa_samples=5, gi_specular_samples=3),
    )

    applied = apply_render_quality_preset(preset, renderer="arnold", cmds=cmds)

    assert "defaultArnoldRenderOptions.AASamples" in applied
    assert cmds.attrs["defaultArnoldRenderOptions.AASamples"] == 5


def test_apply_render_quality_preset_skips_zero_values():
    cmds = _FakeCmds()
    preset = RenderQualityPreset()

    applied = apply_render_quality_preset(preset, renderer="vray", cmds=cmds)

    assert applied == []


def test_apply_render_quality_preset_syncs_timeline_frame_range():
    cmds = _FakeCmds()
    preset = RenderQualityPreset(
        common=CommonRenderQualitySettings(width=4096, height=2305),
    )

    applied = apply_render_quality_preset(
        preset,
        renderer="arnold",
        cmds=cmds,
        apply_timeline_frame_range=True,
    )

    assert "defaultRenderGlobals.startFrame" in applied
    assert "defaultRenderGlobals.endFrame" in applied
    assert cmds.attrs["defaultRenderGlobals.startFrame"] == 1
    assert cmds.attrs["defaultRenderGlobals.endFrame"] == 24
    assert cmds.attrs["defaultResolution.width"] == 4096
