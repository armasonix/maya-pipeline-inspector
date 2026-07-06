"""Arnold-specific snapshot enrichment for validation policy rules."""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Optional

from shader_health.core.models import (
    ArnoldMaterialMetadata,
    ArnoldSceneMetadata,
    GraphSnapshot,
    MaterialSnapshot,
    NodeSnapshot,
    ShadingEngineSnapshot,
)

_ARNOLD_MATERIAL_TYPES = frozenset(
    {
        "aiStandardSurface",
        "aiToon",
        "aiCarPaint",
        "aiLayerShader",
        "aiMixShader",
        "standardSurface",
    }
)
_ARNOLD_PLUGIN_NODE_TYPES = frozenset({"aiOptions"})
_ARNOLD_STANDIN_NODE_TYPES = frozenset({"aiStandIn"})
_ARNOLD_KEY_ATTR_KEYS = (
    "specularRoughness",
    "metalness",
    "transmission",
    "transmissionDepth",
    "opacity",
    "emission",
    "subsurface",
    "specular",
    "diffuseRoughness",
    "specularIOR",
    "specularAnisotropy",
    "specularRotation",
)


def enrich_arnold_metadata(snapshot: GraphSnapshot) -> GraphSnapshot:
    """Attach Arnold scene and material metadata without failing on missing nodes."""

    nodes_by_id = {node.id: node for node in snapshot.nodes}
    engines_by_id = {engine.node_id: engine for engine in snapshot.shading_engines}
    materials = tuple(
        _enrich_arnold_material(material, nodes_by_id, engines_by_id)
        for material in snapshot.materials
    )
    return replace(
        snapshot,
        materials=list(materials),
        arnold_scene_metadata=_build_arnold_scene_metadata(snapshot, materials),
    )


def _build_arnold_scene_metadata(
    snapshot: GraphSnapshot,
    materials: tuple[MaterialSnapshot, ...],
) -> ArnoldSceneMetadata:
    plugin_node_ids = sorted(
        node.id
        for node in snapshot.nodes
        if node.type_name in _ARNOLD_PLUGIN_NODE_TYPES
    )
    stand_in_node_ids = sorted(
        node.id
        for node in snapshot.nodes
        if node.type_name in _ARNOLD_STANDIN_NODE_TYPES
    )
    arnold_material_count = sum(
        1 for material in materials if material.type_name in _ARNOLD_MATERIAL_TYPES
    )
    return ArnoldSceneMetadata(
        has_arnold_plugin=bool(plugin_node_ids),
        arnold_plugin_node_ids=plugin_node_ids,
        arnold_material_count=arnold_material_count,
        has_arnold_materials=arnold_material_count > 0,
        stand_in_node_ids=stand_in_node_ids,
        stand_in_count=len(stand_in_node_ids),
        has_stand_ins=bool(stand_in_node_ids),
    )


def _enrich_arnold_material(
    material: MaterialSnapshot,
    nodes_by_id: dict[str, NodeSnapshot],
    engines_by_id: dict[str, ShadingEngineSnapshot],
) -> MaterialSnapshot:
    if material.type_name not in _ARNOLD_MATERIAL_TYPES:
        return material

    node = nodes_by_id.get(material.node_id)
    key_attrs = _collect_key_attrs(node)
    return replace(
        material,
        arnold_metadata=ArnoldMaterialMetadata(
            texture_count=len(material.texture_nodes),
            displacement_linked=_material_has_displacement(material, engines_by_id),
            specular_roughness=_coerce_float(key_attrs.get("specular_roughness")),
            metalness=_coerce_float(key_attrs.get("metalness")),
            transmission_weight=_coerce_float(key_attrs.get("transmission_weight")),
            transmission_depth=_coerce_int(key_attrs.get("transmission_depth")),
            key_attrs=key_attrs,
        ),
    )


def _material_has_displacement(
    material: MaterialSnapshot,
    engines_by_id: dict[str, ShadingEngineSnapshot],
) -> bool:
    if material.displacement_nodes:
        return True
    for engine_id in material.shading_engines:
        engine = engines_by_id.get(engine_id)
        if engine is not None and engine.displacement_shader:
            return True
    return False


def _collect_key_attrs(node: Optional[NodeSnapshot]) -> dict[str, Any]:
    if node is None:
        return {}

    attrs = dict(node.attrs)
    key_attrs: dict[str, Any] = {}
    mapping = {
        "specularRoughness": "specular_roughness",
        "metalness": "metalness",
        "transmission": "transmission_weight",
        "transmissionDepth": "transmission_depth",
        "opacity": "opacity",
        "emission": "emission_weight",
        "subsurface": "subsurface_weight",
        "specular": "specular_weight",
        "diffuseRoughness": "diffuse_roughness",
        "specularIOR": "specular_ior",
        "specularAnisotropy": "specular_anisotropy",
        "specularRotation": "specular_rotation",
    }
    for source_key, target_key in mapping.items():
        if source_key in attrs:
            key_attrs[target_key] = attrs[source_key]
    for key in _ARNOLD_KEY_ATTR_KEYS:
        if key in attrs and key not in mapping:
            key_attrs[key] = attrs[key]
    return key_attrs


def _coerce_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return None
