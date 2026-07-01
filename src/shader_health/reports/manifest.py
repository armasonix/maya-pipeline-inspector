"""Material Passport / Shader Manifest writer."""
from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Optional

from shader_health.core import (
    ConnectionSnapshot,
    FileDependencySnapshot,
    GraphSnapshot,
    MaterialSnapshot,
    NodeSnapshot,
)

MANIFEST_SCHEMA_VERSION = "1.0"

JsonDict = dict[str, Any]


def build_shader_manifest(snapshot: GraphSnapshot) -> JsonDict:
    """Build a deterministic material manifest from a graph snapshot."""

    nodes_by_id = {node.id: node for node in snapshot.nodes}
    dependencies_by_node_id = _dependencies_by_node_id(snapshot.file_dependencies)
    semantic_by_node_id = _semantic_by_node_id(snapshot.connections, nodes_by_id)

    materials = [
        _material_entry(
            material,
            nodes_by_id,
            dependencies_by_node_id,
            semantic_by_node_id,
        )
        for material in sorted(snapshot.materials, key=_material_sort_key)
    ]

    return {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "snapshot_schema_version": snapshot.schema_version,
        "scene_path": snapshot.scene_path,
        "renderer": snapshot.renderer,
        "scan_scope": snapshot.scan_scope,
        "scanned_at_utc": snapshot.scanned_at_utc,
        "materials": materials,
    }


def dumps_shader_manifest(snapshot: GraphSnapshot, *, indent: Optional[int] = 2) -> str:
    """Serialize a deterministic material manifest as JSON text."""

    return json.dumps(build_shader_manifest(snapshot), indent=indent, sort_keys=True) + "\n"


def write_shader_manifest(
    path: str | Path,
    snapshot: GraphSnapshot,
    *,
    indent: Optional[int] = 2,
) -> Path:
    """Write a material manifest and return the output path."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        dumps_shader_manifest(snapshot, indent=indent),
        encoding="utf-8",
    )
    return output_path


def _material_entry(
    material: MaterialSnapshot,
    nodes_by_id: dict[str, NodeSnapshot],
    dependencies_by_node_id: dict[str, list[FileDependencySnapshot]],
    semantic_by_node_id: dict[str, str],
) -> JsonDict:
    return {
        "node_id": material.node_id,
        "name": material.name,
        "type_name": material.type_name,
        "renderer_family": material.renderer_family,
        "shading_engines": sorted(material.shading_engines),
        "assigned_shapes": sorted(material.assigned_shapes),
        "graph_fingerprint": material.graph_fingerprint,
        "graph_node_count": material.graph_node_count,
        "graph_depth": material.graph_depth,
        "textures": _texture_entries(
            material.texture_nodes,
            nodes_by_id,
            dependencies_by_node_id,
            semantic_by_node_id,
        ),
    }


def _texture_entries(
    texture_node_ids: Iterable[str],
    nodes_by_id: dict[str, NodeSnapshot],
    dependencies_by_node_id: dict[str, list[FileDependencySnapshot]],
    semantic_by_node_id: dict[str, str],
) -> list[JsonDict]:
    entries: list[JsonDict] = []
    for node_id in sorted(texture_node_ids):
        dependencies = dependencies_by_node_id.get(node_id, [])
        if not dependencies:
            entries.append(_texture_entry(node_id, None, nodes_by_id, semantic_by_node_id))
            continue
        for dependency in sorted(dependencies, key=_dependency_sort_key):
            entries.append(_texture_entry(node_id, dependency, nodes_by_id, semantic_by_node_id))
    return entries


def _texture_entry(
    node_id: str,
    dependency: Optional[FileDependencySnapshot],
    nodes_by_id: dict[str, NodeSnapshot],
    semantic_by_node_id: dict[str, str],
) -> JsonDict:
    node = nodes_by_id.get(node_id)
    entry: JsonDict = {
        "node_id": node_id,
        "node_name": node.name if node else "",
        "type_name": node.type_name if node else "",
        "semantic": semantic_by_node_id.get(node_id),
    }
    if dependency is None:
        entry.update(
            {
                "attr": "",
                "raw_path": "",
                "resolved_path": None,
                "exists": False,
                "extension": None,
                "version": None,
                "latest_version": None,
                "is_udim": False,
                "udim_tiles": [],
                "missing_udim_tiles": [],
            }
        )
        return entry

    entry.update(
        {
            "attr": dependency.attr,
            "raw_path": dependency.raw_path,
            "resolved_path": dependency.resolved_path,
            "exists": dependency.exists,
            "extension": dependency.extension,
            "version": dependency.version,
            "latest_version": dependency.latest_version,
            "is_udim": dependency.is_udim,
            "udim_tiles": list(dependency.udim_tiles),
            "missing_udim_tiles": list(dependency.missing_udim_tiles),
        }
    )
    return entry


def _dependencies_by_node_id(
    dependencies: Iterable[FileDependencySnapshot],
) -> dict[str, list[FileDependencySnapshot]]:
    grouped: dict[str, list[FileDependencySnapshot]] = {}
    for dependency in dependencies:
        grouped.setdefault(dependency.node_id, []).append(dependency)
    return grouped


def _semantic_by_node_id(
    connections: Iterable[ConnectionSnapshot],
    nodes_by_id: dict[str, NodeSnapshot],
) -> dict[str, str]:
    semantics: dict[str, str] = {}
    for node_id, node in nodes_by_id.items():
        semantic = node.attrs.get("semantic_slot")
        if isinstance(semantic, str) and semantic:
            semantics[node_id] = semantic
    for connection in connections:
        if connection.semantic:
            semantics.setdefault(connection.src_node, connection.semantic)
    return semantics


def _material_sort_key(material: MaterialSnapshot) -> tuple[str, str]:
    return (material.name, material.node_id)


def _dependency_sort_key(dependency: FileDependencySnapshot) -> tuple[str, str, str]:
    return (
        dependency.raw_path,
        dependency.resolved_path or "",
        dependency.attr,
    )
