"""Displacement risk profiling for snapshot enrichment."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import replace
from typing import Any, Optional

from pipeline_inspector.core import (
    ConnectionSnapshot,
    FileDependencySnapshot,
    GraphSnapshot,
    MaterialSnapshot,
    NodeSnapshot,
    ShadingEngineSnapshot,
)
from pipeline_inspector.core.models import DisplacementRiskMetadata

_DISPLACEMENT_NODE_TYPES = frozenset(
    {
        "displacementShader",
        "VRayDisplacement",
        "VRayDisplacementTex",
        "aiDisplacement",
        "aiVectorDisplacement",
    }
)
_TEXTURE_NODE_TYPES = frozenset({"file", "VRayBitmap", "aiImage"})
_AMOUNT_ATTR_KEYS = ("amount", "scale", "displacement", "displacementAmount")
_BOUNDS_MIN_KEYS = ("boundsMin", "minBound", "minValue", "displacementBoundsMin")
_BOUNDS_MAX_KEYS = ("boundsMax", "maxBound", "maxValue", "displacementBoundsMax")
_RISK_HINT_BANDS = (
    ("low", 3.0),
    ("medium", 6.0),
    ("high", 10.0),
)

def enrich_displacement_metadata(snapshot: GraphSnapshot) -> GraphSnapshot:
    """Attach displacement risk metadata to every material in the snapshot."""

    nodes_by_id = {node.id: node for node in snapshot.nodes}
    engines_by_id = {engine.node_id: engine for engine in snapshot.shading_engines}
    incoming = _incoming_by_destination(snapshot.connections)
    materials = [
        _profile_material_displacement(
            material,
            nodes_by_id=nodes_by_id,
            engines_by_id=engines_by_id,
            incoming=incoming,
            file_dependencies=snapshot.file_dependencies,
        )
        for material in snapshot.materials
    ]
    return replace(snapshot, materials=materials)

def _profile_material_displacement(
    material: MaterialSnapshot,
    *,
    nodes_by_id: Mapping[str, NodeSnapshot],
    engines_by_id: Mapping[str, ShadingEngineSnapshot],
    incoming: Mapping[str, list[str]],
    file_dependencies: Iterable[FileDependencySnapshot],
) -> MaterialSnapshot:
    displacement_node_ids = _collect_displacement_node_ids(material, engines_by_id)
    has_displacement = bool(displacement_node_ids)
    max_amount = _max_displacement_amount(displacement_node_ids, nodes_by_id)
    texture_linked = _displacement_texture_linked(
        displacement_node_ids,
        incoming=incoming,
        nodes_by_id=nodes_by_id,
        file_dependencies=file_dependencies,
    )
    bounds_min, bounds_max = _aggregate_bounds(displacement_node_ids, nodes_by_id)
    bounds_span = None
    if bounds_min is not None and bounds_max is not None:
        bounds_span = round(bounds_max - bounds_min, 4)

    subdivision_enabled = _material_subdivision_enabled(material, nodes_by_id)
    renderer_flags = _renderer_flags(material, nodes_by_id)
    risk_score, risk_hint = _risk_score(
        has_displacement=has_displacement,
        max_amount=max_amount,
        texture_linked=texture_linked,
        subdivision_enabled=subdivision_enabled,
        bounds_span=bounds_span,
        renderer_flags=renderer_flags,
    )

    return replace(
        material,
        displacement_metadata=DisplacementRiskMetadata(
            has_displacement=has_displacement,
            displacement_node_ids=displacement_node_ids,
            max_amount=max_amount,
            texture_linked=texture_linked,
            subdivision_enabled=subdivision_enabled,
            bounds_min=bounds_min,
            bounds_max=bounds_max,
            bounds_span=bounds_span,
            renderer_flags=renderer_flags,
            force_displacement=bool(renderer_flags.get("force_displacement", False)),
            vector_displacement=bool(renderer_flags.get("vector_displacement", False)),
            risk_score=risk_score,
            risk_hint=risk_hint,
        ),
    )

def _incoming_by_destination(
    connections: Iterable[ConnectionSnapshot],
) -> dict[str, list[str]]:
    incoming: dict[str, list[str]] = {}
    for connection in connections:
        incoming.setdefault(connection.dst_node, []).append(connection.src_node)
    return incoming

def _collect_displacement_node_ids(
    material: MaterialSnapshot,
    engines_by_id: Mapping[str, ShadingEngineSnapshot],
) -> list[str]:
    node_ids: list[str] = []
    seen: set[str] = set()
    for node_id in material.displacement_nodes:
        if node_id not in seen:
            seen.add(node_id)
            node_ids.append(node_id)
    for engine_id in material.shading_engines:
        engine = engines_by_id.get(engine_id)
        if engine is None or not engine.displacement_shader:
            continue
        displacement_id = engine.displacement_shader
        if displacement_id not in seen:
            seen.add(displacement_id)
            node_ids.append(displacement_id)
    return node_ids

def _max_displacement_amount(
    displacement_node_ids: list[str],
    nodes_by_id: Mapping[str, NodeSnapshot],
) -> Optional[float]:
    amounts: list[float] = []
    for node_id in displacement_node_ids:
        node = nodes_by_id.get(node_id)
        if node is None:
            continue
        amount = _read_amount(node.attrs)
        if amount is not None:
            amounts.append(amount)
    if not amounts:
        return None
    return max(amounts)

def _read_amount(attrs: Mapping[str, Any]) -> Optional[float]:
    for key in _AMOUNT_ATTR_KEYS:
        value = attrs.get(key)
        if isinstance(value, bool) or value is None:
            continue
        if isinstance(value, (int, float)):
            return float(value)
    return None

def _displacement_texture_linked(
    displacement_node_ids: list[str],
    *,
    incoming: Mapping[str, list[str]],
    nodes_by_id: Mapping[str, NodeSnapshot],
    file_dependencies: Iterable[FileDependencySnapshot],
) -> bool:
    if not displacement_node_ids:
        return False

    deps_by_node = {dependency.node_id: dependency for dependency in file_dependencies}
    for node_id in displacement_node_ids:
        for texture_id in _upstream_texture_nodes(node_id, incoming, nodes_by_id):
            dependency = deps_by_node.get(texture_id)
            if dependency is not None and dependency.exists:
                return True
            node = nodes_by_id.get(texture_id)
            if node is not None and node.type_name in _TEXTURE_NODE_TYPES:
                return True
    return False

def _upstream_texture_nodes(
    start_node_id: str,
    incoming: Mapping[str, list[str]],
    nodes_by_id: Mapping[str, NodeSnapshot],
) -> set[str]:
    found: set[str] = set()
    stack = list(incoming.get(start_node_id, ()))
    visited: set[str] = set()
    while stack:
        node_id = stack.pop()
        if node_id in visited:
            continue
        visited.add(node_id)
        node = nodes_by_id.get(node_id)
        if node is not None and node.type_name in _TEXTURE_NODE_TYPES:
            found.add(node_id)
            continue
        stack.extend(incoming.get(node_id, ()))
    return found

def _aggregate_bounds(
    displacement_node_ids: list[str],
    nodes_by_id: Mapping[str, NodeSnapshot],
) -> tuple[Optional[float], Optional[float]]:
    mins: list[float] = []
    maxes: list[float] = []
    for node_id in displacement_node_ids:
        node = nodes_by_id.get(node_id)
        if node is None:
            continue
        bounds_min = _read_attr_float(node.attrs, _BOUNDS_MIN_KEYS)
        bounds_max = _read_attr_float(node.attrs, _BOUNDS_MAX_KEYS)
        if bounds_min is not None:
            mins.append(bounds_min)
        if bounds_max is not None:
            maxes.append(bounds_max)
    if not mins and not maxes:
        return None, None
    return (
        min(mins) if mins else None,
        max(maxes) if maxes else None,
    )

def _read_attr_float(attrs: Mapping[str, Any], keys: tuple[str, ...]) -> Optional[float]:
    for key in keys:
        value = attrs.get(key)
        if isinstance(value, bool) or value is None:
            continue
        if isinstance(value, (int, float)):
            return float(value)
    return None

def _material_subdivision_enabled(
    material: MaterialSnapshot,
    nodes_by_id: Mapping[str, NodeSnapshot],
) -> bool:
    if material.vray_metadata is not None and material.vray_metadata.subdivision_enabled:
        return True

    material_node = nodes_by_id.get(material.node_id)
    if material_node is None:
        return False

    for key in ("igi", "generateGi", "subdivs", "fde", "gfr", "ufs", "subdivision"):
        value = material_node.attrs.get(key)
        if isinstance(value, bool) and value:
            return True
        if isinstance(value, (int, float)) and value != 0:
            return True
        if isinstance(value, str) and value.strip().lower() in {"1", "true", "yes", "on"}:
            return True
    return False

def _renderer_flags(
    material: MaterialSnapshot,
    nodes_by_id: Mapping[str, NodeSnapshot],
) -> dict[str, Any]:
    flags: dict[str, Any] = {}
    if material.vray_metadata is not None:
        limit_attrs = material.vray_metadata.limit_attrs
        if limit_attrs.get("force_displacement"):
            flags["force_displacement"] = True
        if material.vray_metadata.subdivision_enabled:
            flags["subdivision_enabled"] = True
    if material.arnold_metadata is not None:
        flags["displacement_linked"] = material.arnold_metadata.displacement_linked

    material_node = nodes_by_id.get(material.node_id)
    if material_node is not None:
        vector_displacement = material_node.attrs.get("vectorDisplacement")
        if vector_displacement:
            flags["vector_displacement"] = True

    for node_id in material.displacement_nodes:
        node = nodes_by_id.get(node_id)
        if node is None:
            continue
        if node.type_name.startswith("VRay"):
            flags.setdefault("renderer_family", "vray")
        elif node.type_name.startswith("ai"):
            flags.setdefault("renderer_family", "arnold")
    return flags

def _risk_score(
    *,
    has_displacement: bool,
    max_amount: Optional[float],
    texture_linked: bool,
    subdivision_enabled: bool,
    bounds_span: Optional[float],
    renderer_flags: Mapping[str, Any],
) -> tuple[float, str]:
    if not has_displacement:
        return 0.0, "low"

    score = 0.0
    if max_amount is not None:
        score += min(max_amount, 10.0) * 1.5
    if subdivision_enabled:
        score += 2.5
    if not texture_linked:
        score += 1.0
    if renderer_flags.get("force_displacement"):
        score += 1.5
    if bounds_span is not None and bounds_span > 1.0:
        score += min(bounds_span, 4.0) * 0.75

    rounded = round(score, 2)
    return rounded, _risk_hint(rounded)

def _risk_hint(score: float) -> str:
    for hint, upper_bound in _RISK_HINT_BANDS:
        if score < upper_bound:
            return hint
    return "critical"
