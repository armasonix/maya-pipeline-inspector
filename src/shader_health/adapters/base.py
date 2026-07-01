"""Renderer adapter protocol, registry, and renderer adapters."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from shader_health.core import NodeSnapshot

TextureSlotSemantics = dict[str, str]
ComplexityWeights = dict[str, float]

_COMMON_MAYA_NODE_TYPES = {
    "file",
    "shadingEngine",
    "lambert",
    "standardSurface",
    "displacementShader",
    "bump2d",
    "place2dTexture",
    "blendColors",
    "condition",
    "clamp",
    "layeredTexture",
    "multiplyDivide",
    "plusMinusAverage",
    "remapValue",
    "reverse",
}

_COMMON_MAYA_TEXTURE_SLOTS = {
    "lambert.color": "base_color",
    "lambert.transparency": "opacity",
    "standardSurface.baseColor": "base_color",
    "standardSurface.specularRoughness": "roughness",
    "standardSurface.metalness": "metalness",
    "standardSurface.normalCamera": "normal",
    "standardSurface.emissionColor": "emission",
    "standardSurface.opacity": "opacity",
    "displacementShader.displacement": "displacement",
    "bump2d.bumpValue": "bump",
    "bump2d.normalCamera": "normal",
}

_COMMON_MAYA_COMPLEXITY_WEIGHTS = {
    "shadingEngine": 0.25,
    "file": 1.0,
    "lambert": 1.0,
    "standardSurface": 1.0,
    "displacementShader": 1.25,
    "bump2d": 1.0,
    "place2dTexture": 0.25,
    "blendColors": 0.75,
    "condition": 0.75,
    "clamp": 0.5,
    "layeredTexture": 2.0,
    "multiplyDivide": 0.5,
    "plusMinusAverage": 0.5,
    "remapValue": 0.75,
    "reverse": 0.5,
}

_VRAY_NODE_TYPES = {
    "VRayMtl",
    "VRayBlendMtl",
    "VRayBumpMtl",
    "VRayFastSSS2",
    "VRayAlSurface",
    "VRayBitmap",
    "VRayNormalMap",
    "VRayDisplacement",
    "VRayTriplanarTex",
    "VRayColor",
    "VRayDirt",
    "VRayFresnel",
    "VRayLayeredTex",
    "VRayMultiSubTex",
    "VRayRemap",
}

_VRAY_TEXTURE_SLOTS = {
    "VRayMtl.diffuseColor": "base_color",
    "VRayMtl.reflectionGlossiness": "roughness",
    "VRayMtl.reflectionColor": "specular_color",
    "VRayMtl.metalness": "metalness",
    "VRayMtl.bumpMap": "bump",
    "VRayMtl.normalMap": "normal",
    "VRayMtl.opacityMap": "opacity",
    "VRayMtl.selfIllumination": "emission",
    "VRayBlendMtl.baseMtl": "material",
    "VRayBlendMtl.coatMtl": "material",
    "VRayBlendMtl.blendAmount": "mask",
    "VRayBumpMtl.bumpMap": "bump",
    "VRayBumpMtl.normalMap": "normal",
    "VRayNormalMap.normalMap": "normal",
    "VRayDisplacement.displacement": "displacement",
    "VRayFastSSS2.diffuseColor": "base_color",
    "VRayFastSSS2.specularGlossiness": "roughness",
    "VRayAlSurface.diffuseColor": "base_color",
}

_VRAY_COMPLEXITY_WEIGHTS = {
    "VRayMtl": 1.25,
    "VRayBlendMtl": 3.0,
    "VRayBumpMtl": 1.25,
    "VRayFastSSS2": 2.0,
    "VRayAlSurface": 2.0,
    "VRayBitmap": 1.0,
    "VRayNormalMap": 1.0,
    "VRayDisplacement": 1.75,
    "VRayTriplanarTex": 1.5,
    "VRayColor": 0.25,
    "VRayDirt": 1.25,
    "VRayFresnel": 0.75,
    "VRayLayeredTex": 2.0,
    "VRayMultiSubTex": 2.0,
    "VRayRemap": 0.75,
}

_ARNOLD_NODE_TYPES = {
    "aiStandardSurface",
    "aiImage",
    "aiNormalMap",
    "aiBump2d",
    "aiLayerShader",
    "aiMixShader",
    "aiColorCorrect",
    "aiRange",
    "aiMultiply",
    "aiNoise",
    "aiTriplanar",
    "aiUserDataColor",
    "aiUserDataFloat",
    "aiUtility",
}

_ARNOLD_TEXTURE_SLOTS = {
    "aiStandardSurface.baseColor": "base_color",
    "aiStandardSurface.specularRoughness": "roughness",
    "aiStandardSurface.metalness": "metalness",
    "aiStandardSurface.normalCamera": "normal",
    "aiStandardSurface.opacity": "opacity",
    "aiStandardSurface.emissionColor": "emission",
    "aiStandardSurface.transmission": "transmission",
    "aiImage.filename": "texture_file",
    "aiNormalMap.input": "normal",
    "aiBump2d.bumpMap": "bump",
    "aiLayerShader.input": "material",
    "aiLayerShader.mix": "mask",
    "aiMixShader.mix": "mask",
    "displacementShader.displacement": "displacement",
}

_ARNOLD_COMPLEXITY_WEIGHTS = {
    "aiStandardSurface": 1.25,
    "aiImage": 1.0,
    "aiNormalMap": 1.0,
    "aiBump2d": 1.0,
    "aiLayerShader": 2.5,
    "aiMixShader": 2.0,
    "aiColorCorrect": 0.75,
    "aiRange": 0.75,
    "aiMultiply": 0.5,
    "aiNoise": 1.25,
    "aiTriplanar": 1.5,
    "aiUserDataColor": 0.5,
    "aiUserDataFloat": 0.5,
    "aiUtility": 0.75,
}


class RendererAdapterError(ValueError):
    """Raised when renderer adapter registration or lookup fails."""


@runtime_checkable
class RendererAdapter(Protocol):
    """Protocol implemented by renderer-specific adapter classes."""

    id: str
    display_name: str

    def is_available(self) -> bool:
        """Return whether this renderer adapter can run in the current environment."""

    def supported_node_types(self) -> set[str]:
        """Return Maya node types understood by this adapter."""

    def classify_node(self, node: NodeSnapshot) -> list[str]:
        """Return semantic classification tags for a snapshot node."""

    def texture_slot_semantics(self) -> TextureSlotSemantics:
        """Map renderer-specific destination plugs to semantic texture slots."""

    def displacement_slots(self) -> list[str]:
        """Return renderer-specific displacement-related destination plugs."""

    def complexity_weights(self) -> ComplexityWeights:
        """Return per-node-type graph complexity weights."""

    def default_rule_packs(self) -> list[str]:
        """Return default rule pack identifiers for this adapter."""


@dataclass(frozen=True)
class BaseRendererAdapter:
    """Small base implementation for simple renderer adapters and tests."""

    id: str
    display_name: str

    def is_available(self) -> bool:
        return True

    def supported_node_types(self) -> set[str]:
        return set()

    def classify_node(self, node: NodeSnapshot) -> list[str]:
        del node
        return []

    def texture_slot_semantics(self) -> TextureSlotSemantics:
        return {}

    def displacement_slots(self) -> list[str]:
        return []

    def complexity_weights(self) -> ComplexityWeights:
        return {}

    def default_rule_packs(self) -> list[str]:
        return []


@dataclass(frozen=True)
class CommonMayaAdapter(BaseRendererAdapter):
    """Adapter for renderer-agnostic Maya shading graph concepts."""

    id: str = "common"
    display_name: str = "Common Maya"

    def supported_node_types(self) -> set[str]:
        return set(_COMMON_MAYA_NODE_TYPES)

    def classify_node(self, node: NodeSnapshot) -> list[str]:
        type_name = node.type_name
        if type_name not in _COMMON_MAYA_NODE_TYPES:
            return []
        if type_name == "shadingEngine":
            return ["shading_engine"]
        if type_name == "file":
            return ["texture", "file"]
        if type_name in {"lambert", "standardSurface"}:
            return ["material"]
        if type_name == "displacementShader":
            return ["displacement"]
        if type_name == "bump2d":
            return ["bump", "utility"]
        if type_name == "place2dTexture":
            return ["placement", "utility"]
        return ["utility"]

    def texture_slot_semantics(self) -> TextureSlotSemantics:
        return dict(_COMMON_MAYA_TEXTURE_SLOTS)

    def displacement_slots(self) -> list[str]:
        return ["displacementShader.displacement"]

    def complexity_weights(self) -> ComplexityWeights:
        return dict(_COMMON_MAYA_COMPLEXITY_WEIGHTS)

    def default_rule_packs(self) -> list[str]:
        return ["common"]


@dataclass(frozen=True)
class VrayAdapter(BaseRendererAdapter):
    """Adapter for V-Ray for Maya material and texture graph concepts."""

    id: str = "vray"
    display_name: str = "V-Ray"

    def supported_node_types(self) -> set[str]:
        return set(_VRAY_NODE_TYPES)

    def classify_node(self, node: NodeSnapshot) -> list[str]:
        type_name = node.type_name
        if type_name not in _VRAY_NODE_TYPES:
            return []
        if type_name == "VRayBitmap":
            return ["texture", "file"]
        if type_name in {"VRayMtl", "VRayBlendMtl", "VRayFastSSS2", "VRayAlSurface"}:
            return ["material"]
        if type_name in {"VRayBumpMtl", "VRayNormalMap"}:
            return ["bump", "normal", "utility"]
        if type_name == "VRayDisplacement":
            return ["displacement"]
        return ["utility"]

    def texture_slot_semantics(self) -> TextureSlotSemantics:
        return dict(_VRAY_TEXTURE_SLOTS)

    def displacement_slots(self) -> list[str]:
        return ["VRayDisplacement.displacement"]

    def complexity_weights(self) -> ComplexityWeights:
        return dict(_VRAY_COMPLEXITY_WEIGHTS)

    def default_rule_packs(self) -> list[str]:
        return ["common", "vray"]


@dataclass(frozen=True)
class ArnoldAdapter(BaseRendererAdapter):
    """Adapter for Arnold for Maya material and texture graph concepts."""

    id: str = "arnold"
    display_name: str = "Arnold"

    def supported_node_types(self) -> set[str]:
        return set(_ARNOLD_NODE_TYPES)

    def classify_node(self, node: NodeSnapshot) -> list[str]:
        type_name = node.type_name
        if type_name not in _ARNOLD_NODE_TYPES:
            return []
        if type_name == "aiImage":
            return ["texture", "file"]
        if type_name in {"aiStandardSurface", "aiLayerShader", "aiMixShader"}:
            return ["material"]
        if type_name == "aiNormalMap":
            return ["normal", "utility"]
        if type_name == "aiBump2d":
            return ["bump", "utility"]
        if type_name in {"aiNoise", "aiTriplanar"}:
            return ["texture", "procedural", "utility"]
        return ["utility"]

    def texture_slot_semantics(self) -> TextureSlotSemantics:
        return dict(_ARNOLD_TEXTURE_SLOTS)

    def displacement_slots(self) -> list[str]:
        return ["displacementShader.displacement"]

    def complexity_weights(self) -> ComplexityWeights:
        return dict(_ARNOLD_COMPLEXITY_WEIGHTS)

    def default_rule_packs(self) -> list[str]:
        return ["common", "arnold"]


class RendererAdapterRegistry:
    """Deterministic in-memory registry for renderer adapters."""

    def __init__(self, adapters: Iterable[RendererAdapter] = ()) -> None:
        self._adapters: dict[str, RendererAdapter] = {}
        for adapter in adapters:
            self.register(adapter)

    def register(self, adapter: RendererAdapter, *, replace: bool = False) -> None:
        adapter_id = adapter.id.strip().lower()
        if not adapter_id:
            raise RendererAdapterError("renderer adapter id is required")

        if adapter_id in self._adapters and not replace:
            raise RendererAdapterError(f"renderer adapter already registered: {adapter_id}")

        self._adapters[adapter_id] = adapter

    def get(self, adapter_id: str) -> RendererAdapter:
        normalized_id = adapter_id.strip().lower()
        try:
            return self._adapters[normalized_id]
        except KeyError as exc:
            raise RendererAdapterError(f"unknown renderer adapter: {normalized_id}") from exc

    def ids(self) -> list[str]:
        return sorted(self._adapters)

    def adapters(self) -> list[RendererAdapter]:
        return [self._adapters[adapter_id] for adapter_id in self.ids()]

    def available_adapters(self) -> list[RendererAdapter]:
        return [adapter for adapter in self.adapters() if adapter.is_available()]

    def classify_node(self, node: NodeSnapshot) -> list[str]:
        tags: list[str] = []
        for adapter in self.available_adapters():
            if node.type_name not in adapter.supported_node_types():
                continue
            tags.extend(adapter.classify_node(node))
        return _dedupe(tags)


def _dedupe(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
