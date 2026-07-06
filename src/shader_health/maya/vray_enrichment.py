"""V-Ray-specific snapshot enrichment for validation policy rules."""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Optional

from shader_health.core.models import (
    GraphSnapshot,
    MaterialSnapshot,
    NodeSnapshot,
    ShadingEngineSnapshot,
    VrayMaterialMetadata,
    VraySceneMetadata,
)

_VRAY_MATERIAL_TYPES = frozenset(
    {
        "VRayMtl",
        "VRayMtl2",
        "VRayBlendMtl",
        "VRayBumpMtl",
        "VRayFastSSS2",
        "VRayAlSurface",
    }
)
_VRAY_PLUGIN_NODE_TYPES = frozenset({"VRaySettingsNode", "VRaySettings"})
_VRAY_LIMIT_ATTR_KEYS = (
    "rlmd",
    "reflectionMaxDepth",
    "rrmd",
    "refractionMaxDepth",
    "brdf",
    "omode",
    "gtrec",
    "cth",
    "and",
)
_SUBDIVISION_ATTR_KEYS = ("igi", "generateGi", "subdivs", "fde", "gfr", "ufs")


def enrich_vray_metadata(snapshot: GraphSnapshot) -> GraphSnapshot:
    """Attach V-Ray scene and material metadata without failing on missing nodes."""

    nodes_by_id = {node.id: node for node in snapshot.nodes}
    engines_by_id = {engine.node_id: engine for engine in snapshot.shading_engines}
    materials = tuple(
        _enrich_vray_material(material, nodes_by_id, engines_by_id)
        for material in snapshot.materials
    )
    return replace(
        snapshot,
        materials=list(materials),
        vray_scene_metadata=_build_vray_scene_metadata(snapshot, materials),
    )


def _build_vray_scene_metadata(
    snapshot: GraphSnapshot,
    materials: tuple[MaterialSnapshot, ...],
) -> VraySceneMetadata:
    plugin_node_ids = sorted(
        node.id
        for node in snapshot.nodes
        if node.type_name in _VRAY_PLUGIN_NODE_TYPES
    )
    vray_material_count = sum(
        1 for material in materials if material.type_name in _VRAY_MATERIAL_TYPES
    )
    return VraySceneMetadata(
        has_vray_plugin=bool(plugin_node_ids),
        vray_plugin_node_ids=plugin_node_ids,
        vray_material_count=vray_material_count,
        has_vray_materials=vray_material_count > 0,
    )


def _enrich_vray_material(
    material: MaterialSnapshot,
    nodes_by_id: dict[str, NodeSnapshot],
    engines_by_id: dict[str, ShadingEngineSnapshot],
) -> MaterialSnapshot:
    if material.type_name not in _VRAY_MATERIAL_TYPES:
        return material

    node = nodes_by_id.get(material.node_id)
    limit_attrs = _collect_limit_attrs(node)
    reflection_max_depth = _coerce_int(limit_attrs.get("reflection_max_depth"))
    refraction_max_depth = _coerce_int(limit_attrs.get("refraction_max_depth"))
    return replace(
        material,
        vray_metadata=VrayMaterialMetadata(
            texture_count=len(material.texture_nodes),
            displacement_linked=_material_has_displacement(material, engines_by_id),
            subdivision_enabled=_subdivision_enabled(node),
            reflection_max_depth=reflection_max_depth,
            refraction_max_depth=refraction_max_depth,
            limit_attrs=limit_attrs,
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


def _subdivision_enabled(node: Optional[NodeSnapshot]) -> bool:
    if node is None:
        return False
    for key in _SUBDIVISION_ATTR_KEYS:
        value = node.attrs.get(key)
        if isinstance(value, bool):
            if value:
                return True
            continue
        if _truthy(value):
            return True
    return False


def _collect_limit_attrs(node: Optional[NodeSnapshot]) -> dict[str, Any]:
    if node is None:
        return {}

    attrs = dict(node.attrs)
    limit_attrs: dict[str, Any] = {}
    mapping = {
        "rlmd": "reflection_max_depth",
        "reflectionMaxDepth": "reflection_max_depth",
        "rrmd": "refraction_max_depth",
        "refractionMaxDepth": "refraction_max_depth",
        "brdf": "brdf",
        "omode": "opacity_mode",
        "gtrec": "gi_technique",
        "cth": "cutoff_threshold",
        "and": "affect_all_nodes",
        "afs": "affect_shadows",
        "uf": "use_fresnel",
        "fde": "force_displacement",
        "gfr": "generate_gi_for_backfaces",
        "ufs": "use_subsurface_scattering",
    }
    for source_key, target_key in mapping.items():
        if source_key in attrs:
            limit_attrs[target_key] = attrs[source_key]
    for key in _VRAY_LIMIT_ATTR_KEYS:
        if key in attrs and key not in mapping:
            limit_attrs[key] = attrs[key]
    return limit_attrs


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


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized in {"1", "true", "yes", "on"}
    return False
