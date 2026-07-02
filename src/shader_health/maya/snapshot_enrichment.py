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

from shader_health.core import (
    ConnectionSnapshot,
    FileDependencySnapshot,
    GraphSnapshot,
    NodeSnapshot,
)

_UDIM_TILE_RE = re.compile(r"(?<!\d)(1\d{3}|2\d{3})(?!\d)")
_UDIM_MODE_VALUES = {3, "3", "UDIM", "udim", "Mari", "mari"}


def enrich_snapshot(snapshot: GraphSnapshot) -> GraphSnapshot:
    """Return a validation-ready snapshot enriched with runtime semantics."""

    nodes = tuple(_enrich_node(node) for node in snapshot.nodes)
    nodes_by_id = {node.id: node for node in nodes}
    connections = tuple(_enrich_connection(item, nodes_by_id) for item in snapshot.connections)
    scene_dir = Path(snapshot.scene_path).parent if snapshot.scene_path else Path.cwd()
    file_dependencies = tuple(
        _enrich_file_dependency(item, nodes_by_id.get(item.node_id), scene_dir)
        for item in snapshot.file_dependencies
    )
    return replace(
        snapshot,
        nodes=list(nodes),
        connections=list(connections),
        file_dependencies=list(file_dependencies),
    )


def _enrich_node(node: NodeSnapshot) -> NodeSnapshot:
    attrs = dict(node.attrs)
    if node.type_name == "displacementShader" and "amount" not in attrs:
        for alias in ("scale", "displacement", "displacementAmount"):
            if alias in attrs:
                attrs["amount"] = attrs[alias]
                break
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


def _semantic_from_destination(
    dst_attr: str,
    dst_node: Optional[NodeSnapshot],
) -> Optional[str]:
    attr = dst_attr.lower()
    dst_type = (dst_node.type_name if dst_node else "").lower()
    if "displacement" in attr or "displacement" in dst_type:
        return "displacement"
    if "rough" in attr or "gloss" in attr:
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
        return replace(
            dependency,
            resolved_path=resolved_path,
            exists=Path(resolved_path).is_file(),
        )

    tiles = _existing_udim_tiles(resolved_path)
    return replace(
        dependency,
        raw_path=udim_pattern or dependency.raw_path,
        resolved_path=resolved_path,
        exists=bool(tiles),
        is_udim=True,
        udim_tiles=tiles,
        missing_udim_tiles=_missing_udim_tiles(tiles),
    )


def _udim_pattern(raw_path: str, node: Optional[NodeSnapshot]) -> Optional[str]:
    if "<UDIM>" in raw_path or "<udim>" in raw_path:
        return raw_path
    if not _uses_maya_udim_mode(node):
        return None
    path = Path(raw_path.replace("\\", "/"))
    match = None
    for match in _UDIM_TILE_RE.finditer(path.name):
        pass
    if match is None:
        return None
    name = path.name[: match.start()] + "<UDIM>" + path.name[match.end() :]
    return str(path.with_name(name)).replace("\\", "/")


def _uses_maya_udim_mode(node: Optional[NodeSnapshot]) -> bool:
    if node is None:
        return False
    return node.attrs.get("uvTilingMode") in _UDIM_MODE_VALUES


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
