"""Runtime snapshot enrichment for Maya validation.

The scanner records raw Maya graph data. This module normalizes common runtime
Maya details that rule packs depend on: semantic texture slots, UDIM metadata,
and displacement amount aliases.
"""
from __future__ import annotations

import glob
import os
import re
from dataclasses import replace
from pathlib import Path
from typing import Optional

from shader_health.adapters import (
    ArnoldAdapter,
    CommonMayaAdapter,
    RendererAdapterRegistry,
    SemanticTextureSlotResolver,
    VrayAdapter,
)
from shader_health.core import (
    ConnectionSnapshot,
    FileDependencySnapshot,
    GraphSnapshot,
    NodeSnapshot,
    RuleResult,
)
from shader_health.core.graph_fingerprint import (
    material_graph_content_fingerprint,
    material_graph_fingerprint,
)
from shader_health.core.image_metadata import read_image_dimensions
from shader_health.core.models import ImageInfo, MaterialSnapshot
from shader_health.maya.arnold_enrichment import enrich_arnold_metadata
from shader_health.maya.complexity_profiler import profile_material_complexity
from shader_health.maya.displacement_enrichment import enrich_displacement_metadata
from shader_health.maya.optimized_texture_enrichment import enrich_optimized_texture_metadata
from shader_health.maya.vray_enrichment import enrich_vray_metadata

_UDIM_TILE_RE = re.compile(r"(?<!\d)(1\d{3}|2\d{3})(?!\d)")
_UDIM_MODE_VALUES = {3, "3", "UDIM", "udim", "Mari", "mari"}
_DISPLACEMENT_NODE_TYPES = {"displacementShader", "VRayDisplacement", "VRayDisplacementTex"}


def prepare_snapshot_for_validation(snapshot: GraphSnapshot) -> GraphSnapshot:
    """Return a validation-ready snapshot with runtime semantics and UDIM metadata."""

    enriched = enrich_snapshot(snapshot)
    resolver = SemanticTextureSlotResolver(_default_adapter_registry())
    resolved = resolver.apply_to_snapshot(enriched)
    propagated = _with_propagated_semantic_slots(resolved)
    return enrich_displacement_metadata(
        enrich_arnold_metadata(enrich_vray_metadata(propagated))
    )


def enrich_rule_results(
    snapshot: GraphSnapshot,
    results: list[RuleResult],
) -> list[RuleResult]:
    """Attach owning material names to validation results when possible."""

    material_index = build_material_index(snapshot)
    enriched: list[RuleResult] = []
    for result in results:
        if result.material:
            enriched.append(result)
            continue
        material = _resolve_result_material(result, material_index)
        if material is None:
            enriched.append(result)
        else:
            enriched.append(replace(result, material=material))
    return enriched


def build_material_index(snapshot: GraphSnapshot) -> dict[str, str]:
    """Map node ids and short names to owning material names."""

    index: dict[str, str] = {}
    incoming: dict[str, list[str]] = {}
    for connection in snapshot.connections:
        incoming.setdefault(connection.dst_node, []).append(connection.src_node)

    texture_types = {"file", "VRayBitmap", "aiImage"}
    nodes_by_id = {node.id: node for node in snapshot.nodes}

    for material in snapshot.materials:
        index[material.node_id] = material.name
        index[material.name] = material.name
        for node_id in material.texture_nodes:
            index[node_id] = material.name
            index[_short_node_id(node_id)] = material.name
        for node_id in material.displacement_nodes:
            index[node_id] = material.name
            index[_short_node_id(node_id)] = material.name
            for texture_id in _upstream_texture_nodes(
                node_id,
                incoming,
                nodes_by_id,
                texture_types,
            ):
                index[texture_id] = material.name
                index[_short_node_id(texture_id)] = material.name
    return index


def _upstream_texture_nodes(
    start_node_id: str,
    incoming: dict[str, list[str]],
    nodes_by_id: dict[str, NodeSnapshot],
    texture_types: set[str],
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
        if node is not None and node.type_name in texture_types:
            found.add(node_id)
            continue
        stack.extend(incoming.get(node_id, ()))
    return found


def enrich_snapshot(snapshot: GraphSnapshot) -> GraphSnapshot:
    """Return a validation-ready snapshot enriched with runtime semantics."""

    base_nodes = tuple(_enrich_node(node) for node in snapshot.nodes)
    base_nodes_by_id = {node.id: node for node in base_nodes}
    connections = tuple(
        _enrich_connection(connection, base_nodes_by_id)
        for connection in snapshot.connections
    )
    node_semantics = _node_semantics_from_connections(connections)
    nodes = tuple(_apply_node_semantic(node, node_semantics.get(node.id)) for node in base_nodes)
    nodes_by_id = {node.id: node for node in nodes}
    scene_dir = Path(snapshot.scene_path).parent if snapshot.scene_path else Path.cwd()
    file_dependencies = tuple(
        _enrich_file_dependency(dependency, nodes_by_id.get(dependency.node_id), scene_dir)
        for dependency in snapshot.file_dependencies
    )
    materials = tuple(
        _enrich_material_fingerprint(
            profile_material_complexity(
                material,
                nodes_by_id=nodes_by_id,
                connections=connections,
                adapter_registry=_default_adapter_registry(),
            ),
            nodes=nodes,
            connections=connections,
            file_dependencies=file_dependencies,
        )
        for material in snapshot.materials
    )
    return replace(
        snapshot,
        nodes=list(nodes),
        connections=list(connections),
        file_dependencies=list(file_dependencies),
        materials=list(materials),
    )


def _enrich_node(node: NodeSnapshot) -> NodeSnapshot:
    attrs = dict(node.attrs)
    if _is_displacement_node(node) and "amount" not in attrs:
        for alias in ("scale", "displacement", "displacementAmount"):
            if alias in attrs:
                attrs["amount"] = attrs[alias]
                break
    return replace(node, attrs=attrs)


def _apply_node_semantic(node: NodeSnapshot, semantic: Optional[str]) -> NodeSnapshot:
    if not semantic:
        return node
    attrs = dict(node.attrs)
    attrs.setdefault("semantic_slot", semantic)
    return replace(node, attrs=attrs)


def _enrich_connection(
    connection: ConnectionSnapshot,
    nodes_by_id: dict[str, NodeSnapshot],
) -> ConnectionSnapshot:
    if connection.semantic:
        return connection
    dst_node = nodes_by_id.get(connection.dst_node)
    semantic = _semantic_from_destination(connection.dst_attr, dst_node)
    return replace(connection, semantic=semantic) if semantic else connection


def _node_semantics_from_connections(
    connections: tuple[ConnectionSnapshot, ...],
) -> dict[str, str]:
    semantics: dict[str, str] = {}
    for connection in connections:
        if connection.semantic:
            semantics.setdefault(connection.src_node, connection.semantic)
    return semantics


def _semantic_from_destination(
    dst_attr: str,
    dst_node: Optional[NodeSnapshot],
) -> Optional[str]:
    attr = dst_attr.lower()
    dst_type = (dst_node.type_name if dst_node else "").lower()
    if "displacement" in attr or "displacement" in dst_type:
        return "displacement"
    if attr in {"d", "disp", "displacement"}:
        return "displacement"
    roughness_attrs = {"rlg", "specular_roughness", "diffuse_roughness"}
    if "rough" in attr or "gloss" in attr or attr in roughness_attrs:
        return "roughness"
    if "metal" in attr:
        return "metalness"
    if "normal" in attr:
        return "normal"
    if "bump" in attr:
        return "bump"
    if "opacity" in attr or "transparency" in attr or attr.endswith("alpha"):
        return "opacity"
    if "emission" in attr or "incandescence" in attr:
        return "emission"
    if "specularcolor" in attr or "reflectioncolor" in attr:
        return "specular_color"
    if "basecolor" in attr or "diffuse" in attr or attr == "color":
        return "base_color"
    return None


def _enrich_file_dependency(
    dependency: FileDependencySnapshot,
    node: Optional[NodeSnapshot],
    scene_dir: Path,
) -> FileDependencySnapshot:
    udim_pattern = _udim_pattern(dependency.raw_path, node)
    resolved_path = _resolve_path(udim_pattern or dependency.raw_path, scene_dir)
    is_udim = bool(udim_pattern) or dependency.is_udim
    if not is_udim:
        enriched = replace(
            dependency,
            resolved_path=resolved_path,
            exists=Path(resolved_path).is_file(),
        )
        return _enrich_dependency_image_metadata(enriched)

    tiles = _existing_udim_tiles(resolved_path)
    enriched = replace(
        dependency,
        raw_path=udim_pattern or dependency.raw_path,
        resolved_path=resolved_path,
        exists=bool(tiles),
        is_udim=True,
        udim_tiles=tiles,
        missing_udim_tiles=_missing_udim_tiles(tiles),
    )
    return _enrich_dependency_image_metadata(enriched)


def _enrich_dependency_image_metadata(
    dependency: FileDependencySnapshot,
) -> FileDependencySnapshot:
    if not dependency.exists or not dependency.resolved_path:
        return dependency

    resolved = dependency.resolved_path
    if dependency.is_udim and "<UDIM>" in resolved:
        tiles = dependency.udim_tiles or _existing_udim_tiles(resolved)
        if tiles:
            first_tile = str(resolved).replace("<UDIM>", f"{tiles[0]:04d}").replace(
                "<udim>",
                f"{tiles[0]:04d}",
            )
            width, height = read_image_dimensions(first_tile)
        else:
            width, height = None, None
    else:
        width, height = read_image_dimensions(resolved)

    if width is None and height is None:
        return enrich_optimized_texture_metadata(dependency)

    max_dimension = max(width or 0, height or 0) or None
    image_info = ImageInfo(width=width, height=height)
    return enrich_optimized_texture_metadata(
        replace(
            dependency,
            image_info=image_info,
            max_dimension=max_dimension,
        )
    )


def _enrich_material_fingerprint(
    material: MaterialSnapshot,
    *,
    nodes: tuple[NodeSnapshot, ...],
    connections: tuple[ConnectionSnapshot, ...],
    file_dependencies: tuple[FileDependencySnapshot, ...],
) -> MaterialSnapshot:
    if material.graph_fingerprint and material.graph_content_fingerprint:
        return material

    nodes_by_id = {node.id: node for node in nodes}
    texture_paths = _material_texture_paths(material, file_dependencies)
    fingerprint = material.graph_fingerprint or material_graph_fingerprint(
        material,
        nodes_by_id=nodes_by_id,
        connections=connections,
        texture_paths=texture_paths,
    )
    content_fingerprint = material.graph_content_fingerprint or material_graph_content_fingerprint(
        material,
        nodes_by_id=nodes_by_id,
        connections=connections,
        texture_paths=texture_paths,
    )
    return replace(
        material,
        graph_fingerprint=fingerprint,
        graph_content_fingerprint=content_fingerprint,
    )


def _material_texture_paths(
    material: MaterialSnapshot,
    file_dependencies: tuple[FileDependencySnapshot, ...],
) -> tuple[str, ...]:
    deps_by_node = {dependency.node_id: dependency for dependency in file_dependencies}
    paths: list[str] = []
    for node_id in material.texture_nodes:
        dependency = deps_by_node.get(node_id)
        if dependency is None:
            continue
        path = dependency.resolved_path or dependency.raw_path
        if path:
            paths.append(path)
    return tuple(paths)


def _udim_pattern(raw_path: str, node: Optional[NodeSnapshot]) -> Optional[str]:
    if "<UDIM>" in raw_path or "<udim>" in raw_path:
        return raw_path
    if not _uses_maya_udim_mode(node):
        return None
    path = Path(raw_path.replace("\\", "/"))
    matches = list(_UDIM_TILE_RE.finditer(path.name))
    if not matches:
        return None
    match = matches[-1]
    name = path.name[: match.start()] + "<UDIM>" + path.name[match.end() :]
    return str(path.with_name(name)).replace("\\", "/")


def _uses_maya_udim_mode(node: Optional[NodeSnapshot]) -> bool:
    if node is None:
        return False
    return node.attrs.get("uvTilingMode") in _UDIM_MODE_VALUES


def _is_displacement_node(node: NodeSnapshot) -> bool:
    return node.type_name in _DISPLACEMENT_NODE_TYPES or "displacement" in node.type_name.lower()


def _resolve_path(raw_path: str, scene_dir: Path) -> str:
    expanded = os.path.expanduser(os.path.expandvars(raw_path)).replace("\\", "/")
    path = Path(expanded)
    if path.is_absolute():
        return str(path).replace("\\", "/")

    candidates = [Path(expanded), scene_dir / expanded]
    parts = Path(expanded).parts
    if "textures" in parts:
        index = parts.index("textures")
        candidates.append(scene_dir.joinpath(*parts[index:]))

    for candidate in candidates:
        if _path_or_udim_exists(candidate):
            return str(candidate).replace("\\", "/")
    return str(candidates[-1]).replace("\\", "/")


def _path_or_udim_exists(path: Path) -> bool:
    text = str(path).replace("\\", "/")
    if "<UDIM>" in text or "<udim>" in text:
        return bool(_udim_files(text))
    return path.exists()


def _udim_glob_pattern(path: str) -> str:
    return path.replace("<UDIM>", "[0-9][0-9][0-9][0-9]").replace(
        "<udim>",
        "[0-9][0-9][0-9][0-9]",
    )


def _udim_files(path: str) -> list[Path]:
    return sorted(Path(item) for item in glob.glob(_udim_glob_pattern(path)))


def _existing_udim_tiles(path: str) -> list[int]:
    tiles: set[int] = set()
    for file_path in _udim_files(path):
        matches = _UDIM_TILE_RE.findall(file_path.name)
        if matches:
            tiles.add(int(matches[-1]))
    return sorted(tiles)


def _missing_udim_tiles(existing_tiles: list[int]) -> list[int]:
    if len(existing_tiles) < 2:
        return []
    existing = set(existing_tiles)
    return [tile for tile in range(min(existing), max(existing) + 1) if tile not in existing]


def _default_adapter_registry() -> RendererAdapterRegistry:
    return RendererAdapterRegistry([CommonMayaAdapter(), VrayAdapter(), ArnoldAdapter()])


def _with_propagated_semantic_slots(snapshot: GraphSnapshot) -> GraphSnapshot:
    semantics_by_src: dict[str, str] = {}
    for connection in snapshot.connections:
        if connection.semantic:
            semantics_by_src[connection.src_node] = connection.semantic

    nodes: list[NodeSnapshot] = []
    for node in snapshot.nodes:
        semantic = semantics_by_src.get(node.id)
        if semantic and not node.attrs.get("semantic_slot"):
            attrs = dict(node.attrs)
            attrs["semantic_slot"] = semantic
            nodes.append(replace(node, attrs=attrs))
        else:
            nodes.append(node)
    return replace(snapshot, nodes=nodes)


def _resolve_result_material(
    result: RuleResult,
    material_index: dict[str, str],
) -> Optional[str]:
    if result.target_kind == "material":
        return result.node or material_index.get(result.target_id)

    for key in (result.target_id, result.node):
        if not key:
            continue
        material = material_index.get(str(key))
        if material:
            return material
        prefixed = f"node:{key}"
        material = material_index.get(prefixed)
        if material:
            return material
    return None


def _short_node_id(node_id: str) -> str:
    if node_id.startswith("node:"):
        return node_id.split(":", 1)[1]
    return node_id
