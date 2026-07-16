"""Studio render-quality presets for Draft and Production farm tiers."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

RENDER_QUALITY_DRAFT = "draft"
RENDER_QUALITY_PRODUCTION = "production"


@dataclass(frozen=True)
class CommonRenderQualitySettings:
    """Shared Maya output settings (defaultResolution)."""

    width: int = 0
    height: int = 0
    device_aspect_ratio: float = 0.0
    pixel_aspect: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "width": int(self.width),
            "height": int(self.height),
            "device_aspect_ratio": float(self.device_aspect_ratio),
            "pixel_aspect": float(self.pixel_aspect),
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> CommonRenderQualitySettings:
        if not data:
            return cls()
        return cls(
            width=_optional_int(data.get("width")),
            height=_optional_int(data.get("height")),
            device_aspect_ratio=_optional_float(data.get("device_aspect_ratio")),
            pixel_aspect=_optional_float(data.get("pixel_aspect")),
        )


@dataclass(frozen=True)
class VrayRenderQualitySettings:
    """V-Ray for Maya quality knobs (vraySettings node)."""

    image_sampler_type: int = 0
    min_subdivs: int = 0
    max_subdivs: int = 0
    ray_depth: int = 0
    gi_depth: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_sampler_type": int(self.image_sampler_type),
            "min_subdivs": int(self.min_subdivs),
            "max_subdivs": int(self.max_subdivs),
            "ray_depth": int(self.ray_depth),
            "gi_depth": int(self.gi_depth),
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> VrayRenderQualitySettings:
        if not data:
            return cls()
        return cls(
            image_sampler_type=_optional_int(data.get("image_sampler_type")),
            min_subdivs=_optional_int(data.get("min_subdivs")),
            max_subdivs=_optional_int(data.get("max_subdivs")),
            ray_depth=_optional_int(data.get("ray_depth")),
            gi_depth=_optional_int(data.get("gi_depth")),
        )


@dataclass(frozen=True)
class ArnoldRenderQualitySettings:
    """Arnold (MtoA) quality knobs (defaultArnoldRenderOptions)."""

    aa_samples: int = 0
    gi_diffuse_samples: int = 0
    gi_specular_samples: int = 0
    gi_transmission_samples: int = 0
    gi_sss_samples: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "aa_samples": int(self.aa_samples),
            "gi_diffuse_samples": int(self.gi_diffuse_samples),
            "gi_specular_samples": int(self.gi_specular_samples),
            "gi_transmission_samples": int(self.gi_transmission_samples),
            "gi_sss_samples": int(self.gi_sss_samples),
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> ArnoldRenderQualitySettings:
        if not data:
            return cls()
        return cls(
            aa_samples=_optional_int(data.get("aa_samples")),
            gi_diffuse_samples=_optional_int(data.get("gi_diffuse_samples")),
            gi_specular_samples=_optional_int(data.get("gi_specular_samples")),
            gi_transmission_samples=_optional_int(data.get("gi_transmission_samples")),
            gi_sss_samples=_optional_int(data.get("gi_sss_samples")),
        )


@dataclass(frozen=True)
class RenderQualityPreset:
    """One Draft or Production render-quality bundle."""

    common: CommonRenderQualitySettings = CommonRenderQualitySettings()
    vray: VrayRenderQualitySettings = VrayRenderQualitySettings()
    arnold: ArnoldRenderQualitySettings = ArnoldRenderQualitySettings()

    def to_dict(self) -> dict[str, Any]:
        return {
            "common": self.common.to_dict(),
            "vray": self.vray.to_dict(),
            "arnold": self.arnold.to_dict(),
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> RenderQualityPreset:
        if not data:
            return cls()
        common_raw = data.get("common")
        vray_raw = data.get("vray")
        arnold_raw = data.get("arnold")
        return cls(
            common=CommonRenderQualitySettings.from_mapping(
                common_raw if isinstance(common_raw, Mapping) else None
            ),
            vray=VrayRenderQualitySettings.from_mapping(
                vray_raw if isinstance(vray_raw, Mapping) else None
            ),
            arnold=ArnoldRenderQualitySettings.from_mapping(
                arnold_raw if isinstance(arnold_raw, Mapping) else None
            ),
        )


@dataclass(frozen=True)
class RenderSettings:
    """Draft and Production render-quality presets configured by the studio."""

    draft: RenderQualityPreset = RenderQualityPreset()
    production: RenderQualityPreset = RenderQualityPreset()

    def preset_for_quality(self, quality: str) -> RenderQualityPreset:
        if quality == RENDER_QUALITY_PRODUCTION:
            return self.production
        return self.draft

    def to_dict(self) -> dict[str, Any]:
        return {
            "draft": self.draft.to_dict(),
            "production": self.production.to_dict(),
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> RenderSettings:
        if not data:
            return cls()
        draft_raw = data.get("draft")
        production_raw = data.get("production")
        return cls(
            draft=RenderQualityPreset.from_mapping(
                draft_raw if isinstance(draft_raw, Mapping) else None
            ),
            production=RenderQualityPreset.from_mapping(
                production_raw if isinstance(production_raw, Mapping) else None
            ),
        )


def apply_render_quality_preset(
    preset: RenderQualityPreset,
    *,
    renderer: str,
    cmds: Any,
) -> list[str]:
    """Apply configured preset values to the open Maya scene.

    Zero values are treated as unset and skipped. Returns applied attr plugs.
    """

    applied: list[str] = []
    renderer_id = str(renderer or "").strip().lower()

    if preset.common.width > 0 and _node_exists(cmds, "defaultResolution"):
        _set_attr(cmds, "defaultResolution.width", preset.common.width)
        applied.append("defaultResolution.width")
    if preset.common.height > 0 and _node_exists(cmds, "defaultResolution"):
        _set_attr(cmds, "defaultResolution.height", preset.common.height)
        applied.append("defaultResolution.height")
    if preset.common.device_aspect_ratio > 0 and _node_exists(cmds, "defaultResolution"):
        _set_attr(cmds, "defaultResolution.deviceAspectRatio", preset.common.device_aspect_ratio)
        applied.append("defaultResolution.deviceAspectRatio")
    if preset.common.pixel_aspect > 0 and _node_exists(cmds, "defaultResolution"):
        _set_attr(cmds, "defaultResolution.pixelAspect", preset.common.pixel_aspect)
        applied.append("defaultResolution.pixelAspect")

    if renderer_id == "vray" and _node_exists(cmds, "vraySettings"):
        vray_attrs = (
            ("image_sampler_type", "imageSamplerType"),
            ("min_subdivs", "dmc_minSubdivs"),
            ("max_subdivs", "dmc_maxSubdivs"),
            ("ray_depth", "maxRayDepth"),
            ("gi_depth", "gi_depth"),
        )
        for field_name, attr_name in vray_attrs:
            value = getattr(preset.vray, field_name)
            if value > 0:
                plug = f"vraySettings.{attr_name}"
                _set_attr(cmds, plug, value)
                applied.append(plug)

    if renderer_id == "arnold" and _node_exists(cmds, "defaultArnoldRenderOptions"):
        arnold_attrs = (
            ("aa_samples", "AASamples"),
            ("gi_diffuse_samples", "GIDiffuseSamples"),
            ("gi_specular_samples", "GISpecularSamples"),
            ("gi_transmission_samples", "GITransmissionSamples"),
            ("gi_sss_samples", "GISssSamples"),
        )
        for field_name, attr_name in arnold_attrs:
            value = getattr(preset.arnold, field_name)
            if value > 0:
                plug = f"defaultArnoldRenderOptions.{attr_name}"
                _set_attr(cmds, plug, value)
                applied.append(plug)

    return applied


def _optional_int(value: Any) -> int:
    if value is None or value == "":
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _optional_float(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _node_exists(cmds: Any, node_name: str) -> bool:
    exists = getattr(cmds, "objExists", None)
    if exists is None:
        return False
    return bool(exists(node_name))


def _set_attr(cmds: Any, plug: str, value: int | float) -> None:
    set_attr = getattr(cmds, "setAttr", None)
    if set_attr is not None:
        set_attr(plug, value)
