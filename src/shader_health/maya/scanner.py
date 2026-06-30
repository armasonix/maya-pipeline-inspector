"""Maya scene scanner entrypoints.

This module is intentionally safe to import outside Maya. Real Maya modules are
loaded lazily only when scan functions run without an injected ``cmds_module``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from shader_health.core import (
    ConnectionSnapshot,
    GraphSnapshot,
    MaterialSnapshot,
    NodeSnapshot,
    ShadingEngineSnapshot,
)

log = logging.getLogger(__name__)

_ATTRS_BY_TYPE = {
    "file": ("fileTextureName", "colorSpace", "uvTilingMode"),
    "VRayBitmap": ("file", "colorSpace"),
    "aiImage": ("filename", "colorSpace"),
    "VRayMtl": ("diffuseColor", "reflectionGlossiness", "reflectionColor"),
    "aiStandardSurface": ("baseColor", "specularRoughness", "metalness"),
    "standardSurface": ("baseColor", "specularRoughness", "metalness"),
    "lambert": ("color", "transparency"),
}


class MayaUnavailableError(RuntimeError):
    """Raised when Maya commands are required but unavailable."""


@dataclass(frozen=True)
class ScanOptions:
    """Options shared by scanner entrypoints."""

    include_references: bool = True
    include_file_dependencies: bool = True
    include_connections: bool = True


def scan_scene(
    options: Optional[ScanOptions] = None,
    cmds_module: Optional[Any] = None,
) -> GraphSnapshot:
    """Scan the current Maya scene and return a GraphSnapshot."""

    cmds = _get_cmds(cmds_module)
    return _scan_snapshot(cmds, scan_scope="scene", options=options or ScanOptions())


def scan_selection(
    options: Optional[ScanOptions] = None,
    cmds_module: Optional[Any] = None,
) -> GraphSnapshot:
    """Scan current Maya selection and return a selection-scoped snapshot."""

    cmds = _get_cmds(cmds_module)
    selection = _selection_names(cmds)
    return _scan_snapshot(
        cmds,
        scan_scope="selection",
        options=options or ScanOptions(),
        selected_nodes=selection,
    )


def _get_cmds(cmds_module: Optional[Any]) -> Any:
    if cmds_module is not None:
        return cmds_module

    try:
        import maya.cmds as cmds  # type: ignore[import-not-found]
    except ImportError as exc:
        raise MayaUnavailableError(
            "maya.cmds is unavailable. Run this scanner inside Maya or pass "
            "cmds_module for tests."
        ) from exc
    return cmds


def _scan_snapshot(
    cmds: Any,
    *,
    scan_scope: str,
    options: ScanOptions,
    selected_nodes: Optional[list[str]] = None,
) -> GraphSnapshot:
    graph = _collect_shader_graph(cmds, options=options, selected_nodes=selected_nodes)
    return GraphSnapshot(
        scene_path=_scene_path(cmds),
        maya_version=_maya_version(cmds),
        renderer=_current_renderer(cmds),
        scan_scope=scan_scope,
        scanned_at_utc=_utc_now(),
        nodes=list(graph.nodes.values()),
        connections=graph.connections,
        materials=graph.materials,
        shading_engines=graph.shading_engines,
    )


@dataclass
class _GraphBuildResult:
    nodes: dict[str, NodeSnapshot]
    connections: list[ConnectionSnapshot]
    materials: list[MaterialSnapshot]
    shading_engines: list[ShadingEngineSnapshot]


def _collect_shader_graph(
    cmds: Any,
    *,
    options: ScanOptions,
    selected_nodes: Optional[list[str]] = None,
) -> _GraphBuildResult:
    nodes: dict[str, NodeSnapshot] = {}
    connections: list[ConnectionSnapshot] = []
    materials: list[MaterialSnapshot] = []
    shading_engines: list[ShadingEngineSnapshot] = []

    for selected in selected_nodes or []:
        _add_node_snapshot(cmds, nodes, selected)

    for engine_name in _shading_engine_names(cmds, selected_nodes):
        engine_id = _node_id(engine_name)
        _add_node_snapshot(cmds, nodes, engine_name)

        surface_shader = _connected_node(cmds, f"{engine_name}.surfaceShader")
        displacement_shader = _connected_node(cmds, f"{engine_name}.displacementShader")
        volume_shader = _connected_node(cmds, f"{engine_name}.volumeShader")
        members = _set_members(cmds, engine_name)

        shading_engines.append(
            ShadingEngineSnapshot(
                node_id=engine_id,
                name=_short_name(engine_name),
                surface_shader=_node_id(surface_shader) if surface_shader else None,
                displacement_shader=_node_id(displacement_shader) if displacement_shader else None,
                volume_shader=_node_id(volume_shader) if volume_shader else None,
                members=members,
            )
        )

        for shader_attr, shader_name in (
            ("surfaceShader", surface_shader),
            ("displacementShader", displacement_shader),
            ("volumeShader", volume_shader),
        ):
            if shader_name is None:
                continue
            connections.append(
                ConnectionSnapshot(
                    src_node=_node_id(shader_name),
                    src_attr="outColor",
                    dst_node=engine_id,
                    dst_attr=shader_attr,
                )
            )

        if surface_shader:
            graph_nodes, graph_connections = _walk_upstream_graph(cmds, surface_shader)
            for node_name in graph_nodes:
                _add_node_snapshot(cmds, nodes, node_name)
            if options.include_connections:
                connections.extend(graph_connections)
            materials.append(
                _material_snapshot(
                    cmds,
                    material_name=surface_shader,
                    shading_engine_id=engine_id,
                    members=members,
                    graph_nodes=graph_nodes,
                    displacement_shader=displacement_shader,
                )
            )

        if displacement_shader:
            displacement_nodes = _walk_upstream_graph(cmds, displacement_shader)[0]
            for node_name in displacement_nodes:
                _add_node_snapshot(cmds, nodes, node_name)

    return _GraphBuildResult(
        nodes=nodes,
        connections=_dedupe_connections(connections),
        materials=materials,
        shading_engines=shading_engines,
    )


def _shading_engine_names(cmds: Any, selected_nodes: Optional[list[str]]) -> list[str]:
    if selected_nodes is None:
        scene_engines = _call_cmds(cmds, "ls", [], type="shadingEngine", long=True) or []
        return [str(item) for item in scene_engines]

    selected_engines: list[str] = []
    for node_name in selected_nodes:
        if _node_type(cmds, node_name) == "shadingEngine":
            selected_engines.append(node_name)
        connected = _call_cmds(cmds, "listConnections", [], node_name, type="shadingEngine")
        selected_engines.extend(str(item) for item in connected or [])
    return _dedupe_strings(selected_engines)


def _walk_upstream_graph(cmds: Any, root_node: str) -> tuple[list[str], list[ConnectionSnapshot]]:
    visited: set[str] = set()
    ordered_nodes: list[str] = []
    connections: list[ConnectionSnapshot] = []

    def visit(node_name: str) -> None:
        if node_name in visited:
            return
        visited.add(node_name)
        ordered_nodes.append(node_name)
        for connection in _input_connections(cmds, node_name):
            connections.append(connection)
            visit(_node_name_from_id(connection.src_node))

    visit(root_node)
    return ordered_nodes, _dedupe_connections(connections)


def _input_connections(cmds: Any, node_name: str) -> list[ConnectionSnapshot]:
    raw_connections = _call_cmds(
        cmds,
        "listConnections",
        [],
        node_name,
        source=True,
        destination=False,
        plugs=True,
        connections=True,
    ) or []
    if len(raw_connections) % 2 != 0:
        return []

    connections: list[ConnectionSnapshot] = []
    for index in range(0, len(raw_connections), 2):
        first = str(raw_connections[index])
        second = str(raw_connections[index + 1])
        if _plug_node(first) == node_name:
            dst_plug = first
            src_plug = second
        else:
            src_plug = first
            dst_plug = second
        connections.append(
            ConnectionSnapshot(
                src_node=_node_id(_plug_node(src_plug)),
                src_attr=_plug_attr(src_plug),
                dst_node=_node_id(_plug_node(dst_plug)),
                dst_attr=_plug_attr(dst_plug),
            )
        )
    return connections


def _material_snapshot(
    cmds: Any,
    *,
    material_name: str,
    shading_engine_id: str,
    members: list[str],
    graph_nodes: list[str],
    displacement_shader: Optional[str],
) -> MaterialSnapshot:
    texture_nodes = [
        _node_id(node_name)
        for node_name in graph_nodes
        if "texture" in _classify_node(_node_type(cmds, node_name))
    ]
    displacement_nodes = []
    if displacement_shader:
        displacement_nodes.append(_node_id(displacement_shader))

    return MaterialSnapshot(
        node_id=_node_id(material_name),
        name=_short_name(material_name),
        type_name=_node_type(cmds, material_name),
        renderer_family=_renderer_family(_node_type(cmds, material_name)),
        shading_engines=[shading_engine_id],
        assigned_shapes=members,
        texture_nodes=texture_nodes,
        displacement_nodes=displacement_nodes,
        graph_node_count=len(graph_nodes),
        graph_depth=max(len(graph_nodes) - 1, 0),
        graph_fingerprint="",
    )


def _add_node_snapshot(cmds: Any, nodes: dict[str, NodeSnapshot], node_name: str) -> None:
    node_id = _node_id(node_name)
    if node_id in nodes:
        return
    type_name = _node_type(cmds, node_name)
    referenced = _is_referenced(cmds, node_name)
    nodes[node_id] = NodeSnapshot(
        id=node_id,
        name=_short_name(node_name),
        full_name=node_name,
        type_name=type_name,
        renderer_family=_renderer_family(type_name),
        namespace=_namespace(node_name),
        referenced=referenced,
        reference_path=_reference_path(cmds, node_name) if referenced else None,
        locked=_is_locked(cmds, node_name),
        attrs=_collect_attrs(cmds, node_name, type_name),
        classification=_classify_node(type_name),
    )


def _collect_attrs(cmds: Any, node_name: str, type_name: str) -> dict[str, Any]:
    attrs: dict[str, Any] = {}
    for attr_name in _attrs_for_type(type_name):
        value = _safe_get_attr(cmds, node_name, attr_name)
        if value is not None:
            attrs[attr_name] = value
    return attrs


def _attrs_for_type(type_name: str) -> tuple[str, ...]:
    return _ATTRS_BY_TYPE.get(type_name, ())


def _safe_get_attr(cmds: Any, node_name: str, attr_name: str) -> Any:
    plug = f"{node_name}.{attr_name}"
    command = getattr(cmds, "getAttr", None)
    if command is None:
        return None
    try:
        return command(plug)
    except Exception as exc:
        log.debug("Skipping unreadable Maya attribute %s: %s", plug, exc)
        return None


def _is_referenced(cmds: Any, node_name: str) -> bool:
    value = _call_cmds(cmds, "referenceQuery", False, node_name, isNodeReferenced=True)
    return bool(value)


def _reference_path(cmds: Any, node_name: str) -> Optional[str]:
    value = _call_cmds(cmds, "referenceQuery", None, node_name, filename=True)
    return str(value) if value else None


def _is_locked(cmds: Any, node_name: str) -> bool:
    value = _call_cmds(cmds, "lockNode", False, node_name, query=True, lock=True)
    if isinstance(value, list):
        return bool(value[0]) if value else False
    return bool(value)


def _namespace(node_name: str) -> Optional[str]:
    short_path = node_name.rsplit("|", 1)[-1]
    if ":" not in short_path:
        return None
    return short_path.rsplit(":", 1)[0]


def _connected_node(cmds: Any, plug: str) -> Optional[str]:
    connected = _call_cmds(cmds, "listConnections", [], plug, source=True, destination=False) or []
    if not connected:
        return None
    return _plug_node(str(connected[0]))


def _set_members(cmds: Any, shading_engine: str) -> list[str]:
    members = _call_cmds(cmds, "sets", [], shading_engine, query=True) or []
    return [str(item) for item in members]


def _scene_path(cmds: Any) -> str:
    scene_path = _call_cmds(cmds, "file", "", query=True, sceneName=True)
    return str(scene_path or "")


def _maya_version(cmds: Any) -> str:
    version = _call_cmds(cmds, "about", "", version=True)
    return str(version or "")


def _current_renderer(cmds: Any) -> Optional[str]:
    renderer = _call_cmds(cmds, "getAttr", None, "defaultRenderGlobals.currentRenderer")
    return str(renderer) if renderer else None


def _selection_names(cmds: Any) -> list[str]:
    selection = _call_cmds(cmds, "ls", [], selection=True, long=True) or []
    return [str(item) for item in selection]


def _node_type(cmds: Any, node: str) -> str:
    node_type = _call_cmds(cmds, "nodeType", "", node)
    return str(node_type or "")


def _classify_node(type_name: str) -> list[str]:
    lowered = type_name.lower()
    if type_name == "shadingEngine":
        return ["shading_engine"]
    if type_name in {"file", "VRayBitmap", "aiImage"}:
        return ["texture", "file"]
    if "displacement" in lowered:
        return ["displacement"]
    if type_name.startswith("VRay") or type_name in {"aiStandardSurface", "lambert"}:
        return ["material"]
    if type_name == "standardSurface":
        return ["material"]
    return ["utility"]


def _renderer_family(type_name: str) -> Optional[str]:
    if type_name.startswith("VRay"):
        return "vray"
    if type_name.startswith("ai"):
        return "arnold"
    if type_name in {"file", "shadingEngine", "lambert", "standardSurface"}:
        return "common"
    return None


def _node_id(node_name: str) -> str:
    return f"node:{node_name}"


def _node_name_from_id(node_id: str) -> str:
    return node_id[5:] if node_id.startswith("node:") else node_id


def _plug_node(plug: str) -> str:
    return plug.split(".", 1)[0]


def _plug_attr(plug: str) -> str:
    if "." not in plug:
        return ""
    return plug.split(".", 1)[1]


def _short_name(full_name: str) -> str:
    if "|" in full_name:
        full_name = full_name.rsplit("|", 1)[-1]
    if ":" in full_name:
        return full_name.rsplit(":", 1)[-1]
    return full_name


def _dedupe_strings(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _dedupe_connections(connections: list[ConnectionSnapshot]) -> list[ConnectionSnapshot]:
    result: list[ConnectionSnapshot] = []
    seen: set[tuple[str, str, str, str]] = set()
    for connection in connections:
        key = (connection.src_node, connection.src_attr, connection.dst_node, connection.dst_attr)
        if key in seen:
            continue
        seen.add(key)
        result.append(connection)
    return result


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _call_cmds(cmds: Any, name: str, default: Any, *args: Any, **kwargs: Any) -> Any:
    command = getattr(cmds, name, None)
    if command is None:
        return default
    try:
        return command(*args, **kwargs)
    except Exception:
        return default
