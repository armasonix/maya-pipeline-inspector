"""Shader graph complexity profiling for snapshot enrichment."""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from contextlib import suppress
from dataclasses import replace
from typing import Optional

from shader_health.adapters import RendererAdapterRegistry
from shader_health.adapters.base import RendererAdapterError
from shader_health.core import ConnectionSnapshot, MaterialSnapshot, NodeSnapshot
from shader_health.core.models import ShaderComplexityMetadata

_DEFAULT_NODE_WEIGHT = 1.0
_EXPENSIVE_NODE_WEIGHT_THRESHOLD = 1.5
_FARM_COST_HINT_BANDS = (
    ("low", 8.0),
    ("medium", 16.0),
    ("high", 28.0),
)

def profile_material_complexity(
    material: MaterialSnapshot,
    *,
    nodes_by_id: Mapping[str, NodeSnapshot],
    connections: Iterable[ConnectionSnapshot],
    adapter_registry: RendererAdapterRegistry,
) -> MaterialSnapshot:
    """Return material with graph metrics and complexity metadata populated."""

    incoming = _incoming_by_destination(connections)
    graph_node_ids = _collect_material_graph_node_ids(material, incoming)
    depths = _depths_from_roots(
        roots=_material_roots(material),
        graph_node_ids=graph_node_ids,
        incoming=incoming,
    )
    histogram = _depth_histogram(depths)
    graph_depth = max(depths.values(), default=0)
    graph_node_count = len(graph_node_ids)

    weights = _merged_complexity_weights(material.renderer_family, adapter_registry)
    expensive_node_types: dict[str, int] = {}
    farm_cost_score = 0.0
    for node_id in sorted(graph_node_ids):
        node = nodes_by_id.get(node_id)
        if node is None:
            continue
        weight = weights.get(node.type_name, _DEFAULT_NODE_WEIGHT)
        farm_cost_score += weight
        if weight >= _EXPENSIVE_NODE_WEIGHT_THRESHOLD:
            expensive_node_types[node.type_name] = (
                expensive_node_types.get(node.type_name, 0) + 1
            )

    complexity_metadata = ShaderComplexityMetadata(
        depth_histogram=histogram,
        expensive_node_count=sum(expensive_node_types.values()),
        expensive_node_types=expensive_node_types,
        farm_cost_score=round(farm_cost_score, 2),
        farm_cost_hint=_farm_cost_hint(farm_cost_score),
    )
    return replace(
        material,
        graph_node_count=graph_node_count,
        graph_depth=graph_depth,
        complexity_metadata=complexity_metadata,
    )

def _incoming_by_destination(
    connections: Iterable[ConnectionSnapshot],
) -> dict[str, list[str]]:
    incoming: dict[str, list[str]] = {}
    for connection in connections:
        incoming.setdefault(connection.dst_node, []).append(connection.src_node)
    return incoming

def _material_roots(material: MaterialSnapshot) -> list[str]:
    roots = [material.node_id]
    for node_id in material.displacement_nodes:
        if node_id not in roots:
            roots.append(node_id)
    return roots

def _collect_material_graph_node_ids(
    material: MaterialSnapshot,
    incoming: Mapping[str, list[str]],
) -> set[str]:
    graph_node_ids: set[str] = set(_material_roots(material))
    stack = list(_material_roots(material))
    while stack:
        node_id = stack.pop()
        for src_node in incoming.get(node_id, ()):
            if src_node in graph_node_ids:
                continue
            graph_node_ids.add(src_node)
            stack.append(src_node)
    return graph_node_ids

def _depths_from_roots(
    *,
    roots: list[str],
    graph_node_ids: set[str],
    incoming: Mapping[str, list[str]],
) -> dict[str, int]:
    depths: dict[str, int] = {root: 0 for root in roots}
    queue = list(roots)
    while queue:
        node_id = queue.pop(0)
        current_depth = depths[node_id]
        for src_node in incoming.get(node_id, ()):
            if src_node not in graph_node_ids:
                continue
            next_depth = current_depth + 1
            if src_node not in depths or next_depth < depths[src_node]:
                depths[src_node] = next_depth
                queue.append(src_node)
    return depths

def _depth_histogram(depths: Mapping[str, int]) -> dict[str, int]:
    counts = Counter(str(depth) for depth in depths.values())
    return {key: counts[key] for key in sorted(counts, key=int)}

def _merged_complexity_weights(
    renderer_family: Optional[str],
    adapter_registry: RendererAdapterRegistry,
) -> dict[str, float]:
    weights = dict(adapter_registry.get("common").complexity_weights())
    if renderer_family:
        with suppress(RendererAdapterError):
            weights.update(adapter_registry.get(renderer_family).complexity_weights())
    return weights

def _farm_cost_hint(score: float) -> str:
    for hint, upper_bound in _FARM_COST_HINT_BANDS:
        if score < upper_bound:
            return hint
    return "critical"
