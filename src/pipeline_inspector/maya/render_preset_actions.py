"""Apply studio render-quality presets to the open Maya scene."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline_inspector.core.render_presets import (
    RENDER_QUALITY_DRAFT,
    RENDER_QUALITY_PRODUCTION,
    RenderSettings,
    apply_render_quality_preset,
)


@dataclass(frozen=True)
class ApplyRenderPresetResult:
    succeeded: bool
    message: str
    quality: str
    applied_attrs: tuple[str, ...] = ()


def apply_studio_render_quality_to_scene(
    render: RenderSettings,
    quality: str,
    *,
    cmds: Any | None = None,
) -> ApplyRenderPresetResult:
    """Push Draft/Production preset values into Maya Render Settings."""

    normalized_quality = str(quality or RENDER_QUALITY_DRAFT).strip().lower()
    if normalized_quality not in {RENDER_QUALITY_DRAFT, RENDER_QUALITY_PRODUCTION}:
        normalized_quality = RENDER_QUALITY_DRAFT

    maya_cmds = cmds or _maya_cmds()
    renderer = str(maya_cmds.getAttr("defaultRenderGlobals.currentRenderer") or "").strip()
    preset = render.preset_for_quality(normalized_quality)
    applied = apply_render_quality_preset(
        preset,
        renderer=renderer,
        cmds=maya_cmds,
        apply_timeline_frame_range=True,
    )
    if not applied:
        return ApplyRenderPresetResult(
            succeeded=False,
            message=(
                f"No {normalized_quality} render preset values were applied. "
                "Fill Width/Height or renderer sample fields first."
            ),
            quality=normalized_quality,
        )

    width = preset.common.width
    height = preset.common.height
    resolution_text = (
        f"{width}x{height}"
        if width > 0 and height > 0
        else "scene resolution unchanged"
    )
    return ApplyRenderPresetResult(
        succeeded=True,
        message=(
            f"Applied {normalized_quality} preset to Maya ({renderer or 'unknown renderer'}): "
            f"{resolution_text}; render frame range synced from timeline."
        ),
        quality=normalized_quality,
        applied_attrs=tuple(applied),
    )


def _maya_cmds() -> Any:
    import maya.cmds as cmds

    return cmds
