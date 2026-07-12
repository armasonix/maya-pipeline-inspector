"""Stable graph fingerprints for material passport manifests."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from pipeline_inspector.core.models import ConnectionSnapshot, MaterialSnapshot, NodeSnapshot

JsonValue = Any

def material_graph_fingerprint(
    material: MaterialSnapshot,
    *,
    nodes_by_id: Mapping[str, NodeSnapshot],
    connections: Sequence[ConnectionSnapshot],
    texture_paths: Sequence[str] = (),
) -> str:
    """Return a deterministic sha256 fingerprint for a material shading graph."""

    graph_node_ids = _graph_node_ids(material, connections)
    payload = {
        "material_id": material.node_id,
        "type_name": material.type_name,
        "nodes": [
            _node_fingerprint_entry(nodes_by_id[node_id])
            for node_id in sorted(graph_node_ids)
            if node_id in nodes_by_id
        ],
        "connections": [
            _connection_fingerprint_entry(connection)
            for connection in sorted(connections, key=_connection_sort_key)
            if connection.src_node in graph_node_ids
            and connection.dst_node in graph_node_ids
        ],
        "texture_paths": [_normalize_path(path) for path in sorted(texture_paths)],
    }
    return _fingerprint_digest(payload)

def material_graph_content_fingerprint(
    material: MaterialSnapshot,
    *,
    nodes_by_id: Mapping[str, NodeSnapshot],
    connections: Sequence[ConnectionSnapshot],
    texture_paths: Sequence[str] = (),
) -> str:
    """Return a content-only fingerprint that ignores Maya node names and material ids."""

    graph_node_ids = _graph_node_ids(material, connections)
    graph_nodes = [
        nodes_by_id[node_id] for node_id in sorted(graph_node_ids) if node_id in nodes_by_id
    ]
    canonical_ids = _canonical_node_ids(graph_nodes)
    payload = {
        "type_name": material.type_name,
        "nodes": [
            _node_content_fingerprint_entry(node, canonical_ids[node.id])
            for node in sorted(graph_nodes, key=_node_content_sort_key)
        ],
        "connections": [
            _connection_content_fingerprint_entry(connection, canonical_ids)
            for connection in sorted(connections, key=_connection_sort_key)
            if connection.src_node in canonical_ids
            and connection.dst_node in canonical_ids
        ],
        "texture_paths": [_normalize_path(path) for path in sorted(texture_paths)],
    }
    return _fingerprint_digest(payload)

def _fingerprint_digest(payload: Mapping[str, JsonValue]) -> str:
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"

def _graph_node_ids(
    material: MaterialSnapshot,
    connections: Sequence[ConnectionSnapshot],
) -> set[str]:
    seeds = {material.node_id, *material.texture_nodes, *material.displacement_nodes}
    graph_ids = set(seeds)
    changed = True
    while changed:
        changed = False
        for connection in connections:
            if connection.src_node in graph_ids or connection.dst_node in graph_ids:
                before = len(graph_ids)
                graph_ids.add(connection.src_node)
                graph_ids.add(connection.dst_node)
                if len(graph_ids) != before:
                    changed = True
    return graph_ids

def _node_fingerprint_entry(node: NodeSnapshot) -> dict[str, JsonValue]:
    attrs = {
        key: _json_safe(value)
        for key, value in sorted(node.attrs.items())
        if key in _FINGERPRINT_ATTRS
    }
    return {
        "id": node.id,
        "type_name": node.type_name,
        "attrs": attrs,
    }

def _node_content_fingerprint_entry(node: NodeSnapshot, canonical_id: str) -> dict[str, JsonValue]:
    attrs = {
        key: _json_safe(value)
        for key, value in sorted(node.attrs.items())
        if key in _FINGERPRINT_ATTRS
    }
    return {
        "id": canonical_id,
        "type_name": node.type_name,
        "attrs": attrs,
    }

def _connection_content_fingerprint_entry(
    connection: ConnectionSnapshot,
    canonical_ids: Mapping[str, str],
) -> dict[str, str]:
    return {
        "source": f"{canonical_ids[connection.src_node]}.{connection.src_attr}",
        "target": f"{canonical_ids[connection.dst_node]}.{connection.dst_attr}",
    }

def _canonical_node_ids(nodes: Sequence[NodeSnapshot]) -> dict[str, str]:
    ordered = sorted(nodes, key=_node_content_sort_key)
    return {node.id: f"n{index}" for index, node in enumerate(ordered)}

def _node_content_sort_key(node: NodeSnapshot) -> tuple[str, str]:
    attrs = {
        key: _json_safe(value)
        for key, value in sorted(node.attrs.items())
        if key in _FINGERPRINT_ATTRS
    }
    return (node.type_name, json.dumps(attrs, sort_keys=True, separators=(",", ":")))

def _connection_fingerprint_entry(connection: ConnectionSnapshot) -> dict[str, str]:
    return {
        "source": f"{connection.src_node}.{connection.src_attr}",
        "target": f"{connection.dst_node}.{connection.dst_attr}",
    }

def _connection_sort_key(connection: ConnectionSnapshot) -> tuple[str, str, str, str]:
    return (
        connection.src_node,
        connection.src_attr,
        connection.dst_node,
        connection.dst_attr,
    )

def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip()

def _json_safe(value: JsonValue) -> JsonValue:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)

_FINGERPRINT_ATTRS = frozenset(
    {
        "colorSpace",
        "fileTextureName",
        "defaultColor",
        "outColor",
        "outAlpha",
        "amount",
        "scale",
        "aiDispersion",
    }
)
