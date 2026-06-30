"""Core snapshot data models.

These models are intentionally Maya-independent. Maya scanners, renderer adapters,
rule engines, reports, and tests should exchange scene data through these plain
Python data contracts.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Optional

JsonDict = dict[str, Any]
JsonValue = Any

SNAPSHOT_SCHEMA_VERSION = "1.0"


def _as_dict(value: Optional[Mapping[str, Any]]) -> JsonDict:
    return dict(value or {})


def _as_str_list(value: Optional[list[Any]]) -> list[str]:
    if value is None:
        return []
    return [str(item) for item in value]


def _as_int_list(value: Optional[list[Any]]) -> list[int]:
    if value is None:
        return []
    return [int(item) for item in value]


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping, got {type(value).__name__}")
    return value


@dataclass(frozen=True)
class ImageInfo:
    """Optional metadata about an image file dependency."""

    width: Optional[int] = None
    height: Optional[int] = None
    channels: Optional[int] = None
    bit_depth: Optional[str] = None
    color_space: Optional[str] = None
    compression: Optional[str] = None

    def to_dict(self) -> JsonDict:
        return {
            "width": self.width,
            "height": self.height,
            "channels": self.channels,
            "bit_depth": self.bit_depth,
            "color_space": self.color_space,
            "compression": self.compression,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ImageInfo:
        return cls(
            width=data.get("width"),
            height=data.get("height"),
            channels=data.get("channels"),
            bit_depth=data.get("bit_depth"),
            color_space=data.get("color_space"),
            compression=data.get("compression"),
        )


@dataclass(frozen=True)
class NodeSnapshot:
    """Renderer-agnostic representation of a Maya dependency node."""

    id: str
    name: str
    full_name: str = ""
    type_name: str = ""
    renderer_family: Optional[str] = None
    namespace: Optional[str] = None
    referenced: bool = False
    reference_path: Optional[str] = None
    locked: bool = False
    attrs: JsonDict = field(default_factory=dict)
    classification: list[str] = field(default_factory=list)

    def to_dict(self) -> JsonDict:
        return {
            "id": self.id,
            "name": self.name,
            "full_name": self.full_name,
            "type_name": self.type_name,
            "renderer_family": self.renderer_family,
            "namespace": self.namespace,
            "referenced": self.referenced,
            "reference_path": self.reference_path,
            "locked": self.locked,
            "attrs": dict(self.attrs),
            "classification": list(self.classification),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> NodeSnapshot:
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            full_name=str(data.get("full_name", "")),
            type_name=str(data.get("type_name", "")),
            renderer_family=data.get("renderer_family"),
            namespace=data.get("namespace"),
            referenced=bool(data.get("referenced", False)),
            reference_path=data.get("reference_path"),
            locked=bool(data.get("locked", False)),
            attrs=_as_dict(data.get("attrs")),
            classification=_as_str_list(data.get("classification")),
        )


@dataclass(frozen=True)
class ConnectionSnapshot:
    """Directed connection between two node attributes."""

    src_node: str
    src_attr: str
    dst_node: str
    dst_attr: str
    semantic: Optional[str] = None

    def to_dict(self) -> JsonDict:
        return {
            "src_node": self.src_node,
            "src_attr": self.src_attr,
            "dst_node": self.dst_node,
            "dst_attr": self.dst_attr,
            "semantic": self.semantic,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ConnectionSnapshot:
        return cls(
            src_node=str(data.get("src_node", "")),
            src_attr=str(data.get("src_attr", "")),
            dst_node=str(data.get("dst_node", "")),
            dst_attr=str(data.get("dst_attr", "")),
            semantic=data.get("semantic"),
        )


@dataclass(frozen=True)
class FileDependencySnapshot:
    """File dependency collected from a texture or renderer file node."""

    node_id: str
    attr: str
    raw_path: str
    resolved_path: Optional[str] = None
    exists: bool = False
    is_sequence: bool = False
    is_udim: bool = False
    udim_tiles: list[int] = field(default_factory=list)
    missing_udim_tiles: list[int] = field(default_factory=list)
    extension: Optional[str] = None
    version: Optional[str] = None
    latest_version: Optional[str] = None
    mtime_utc: Optional[str] = None
    size_bytes: Optional[int] = None
    image_info: Optional[ImageInfo] = None

    def to_dict(self) -> JsonDict:
        return {
            "node_id": self.node_id,
            "attr": self.attr,
            "raw_path": self.raw_path,
            "resolved_path": self.resolved_path,
            "exists": self.exists,
            "is_sequence": self.is_sequence,
            "is_udim": self.is_udim,
            "udim_tiles": list(self.udim_tiles),
            "missing_udim_tiles": list(self.missing_udim_tiles),
            "extension": self.extension,
            "version": self.version,
            "latest_version": self.latest_version,
            "mtime_utc": self.mtime_utc,
            "size_bytes": self.size_bytes,
            "image_info": self.image_info.to_dict() if self.image_info else None,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> FileDependencySnapshot:
        image_info_data = data.get("image_info")
        image_info = None
        if image_info_data is not None:
            image_info = ImageInfo.from_dict(_require_mapping(image_info_data, "image_info"))

        return cls(
            node_id=str(data.get("node_id", "")),
            attr=str(data.get("attr", "")),
            raw_path=str(data.get("raw_path", "")),
            resolved_path=data.get("resolved_path"),
            exists=bool(data.get("exists", False)),
            is_sequence=bool(data.get("is_sequence", False)),
            is_udim=bool(data.get("is_udim", False)),
            udim_tiles=_as_int_list(data.get("udim_tiles")),
            missing_udim_tiles=_as_int_list(data.get("missing_udim_tiles")),
            extension=data.get("extension"),
            version=data.get("version"),
            latest_version=data.get("latest_version"),
            mtime_utc=data.get("mtime_utc"),
            size_bytes=data.get("size_bytes"),
            image_info=image_info,
        )


@dataclass(frozen=True)
class MaterialSnapshot:
    """Material-level summary extracted from the shader graph."""

    node_id: str
    name: str
    type_name: str
    renderer_family: Optional[str] = None
    shading_engines: list[str] = field(default_factory=list)
    assigned_shapes: list[str] = field(default_factory=list)
    texture_nodes: list[str] = field(default_factory=list)
    displacement_nodes: list[str] = field(default_factory=list)
    graph_node_count: int = 0
    graph_depth: int = 0
    graph_fingerprint: str = ""

    def to_dict(self) -> JsonDict:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "type_name": self.type_name,
            "renderer_family": self.renderer_family,
            "shading_engines": list(self.shading_engines),
            "assigned_shapes": list(self.assigned_shapes),
            "texture_nodes": list(self.texture_nodes),
            "displacement_nodes": list(self.displacement_nodes),
            "graph_node_count": self.graph_node_count,
            "graph_depth": self.graph_depth,
            "graph_fingerprint": self.graph_fingerprint,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> MaterialSnapshot:
        return cls(
            node_id=str(data.get("node_id", "")),
            name=str(data.get("name", "")),
            type_name=str(data.get("type_name", "")),
            renderer_family=data.get("renderer_family"),
            shading_engines=_as_str_list(data.get("shading_engines")),
            assigned_shapes=_as_str_list(data.get("assigned_shapes")),
            texture_nodes=_as_str_list(data.get("texture_nodes")),
            displacement_nodes=_as_str_list(data.get("displacement_nodes")),
            graph_node_count=int(data.get("graph_node_count", 0)),
            graph_depth=int(data.get("graph_depth", 0)),
            graph_fingerprint=str(data.get("graph_fingerprint", "")),
        )


@dataclass(frozen=True)
class ShadingEngineSnapshot:
    """Shading engine assignment and material connection summary."""

    node_id: str
    name: str
    surface_shader: Optional[str] = None
    displacement_shader: Optional[str] = None
    volume_shader: Optional[str] = None
    members: list[str] = field(default_factory=list)

    def to_dict(self) -> JsonDict:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "surface_shader": self.surface_shader,
            "displacement_shader": self.displacement_shader,
            "volume_shader": self.volume_shader,
            "members": list(self.members),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ShadingEngineSnapshot:
        return cls(
            node_id=str(data.get("node_id", "")),
            name=str(data.get("name", "")),
            surface_shader=data.get("surface_shader"),
            displacement_shader=data.get("displacement_shader"),
            volume_shader=data.get("volume_shader"),
            members=_as_str_list(data.get("members")),
        )


@dataclass(frozen=True)
class ReferenceSnapshot:
    """Referenced Maya file metadata needed for reference-safe validation."""

    namespace: str
    path: str
    loaded: bool = True
    locked: bool = False
    node_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> JsonDict:
        return {
            "namespace": self.namespace,
            "path": self.path,
            "loaded": self.loaded,
            "locked": self.locked,
            "node_ids": list(self.node_ids),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ReferenceSnapshot:
        return cls(
            namespace=str(data.get("namespace", "")),
            path=str(data.get("path", "")),
            loaded=bool(data.get("loaded", True)),
            locked=bool(data.get("locked", False)),
            node_ids=_as_str_list(data.get("node_ids")),
        )


@dataclass(frozen=True)
class GraphSnapshot:
    """Complete renderer-agnostic snapshot of a scene, selection, or asset."""

    schema_version: str = SNAPSHOT_SCHEMA_VERSION
    scene_path: str = ""
    maya_version: str = ""
    renderer: Optional[str] = None
    scan_scope: str = "scene"
    scanned_at_utc: str = ""
    nodes: list[NodeSnapshot] = field(default_factory=list)
    connections: list[ConnectionSnapshot] = field(default_factory=list)
    materials: list[MaterialSnapshot] = field(default_factory=list)
    shading_engines: list[ShadingEngineSnapshot] = field(default_factory=list)
    file_dependencies: list[FileDependencySnapshot] = field(default_factory=list)
    references: list[ReferenceSnapshot] = field(default_factory=list)

    def to_dict(self) -> JsonDict:
        return {
            "schema_version": self.schema_version,
            "scene_path": self.scene_path,
            "maya_version": self.maya_version,
            "renderer": self.renderer,
            "scan_scope": self.scan_scope,
            "scanned_at_utc": self.scanned_at_utc,
            "nodes": [node.to_dict() for node in self.nodes],
            "connections": [connection.to_dict() for connection in self.connections],
            "materials": [material.to_dict() for material in self.materials],
            "shading_engines": [engine.to_dict() for engine in self.shading_engines],
            "file_dependencies": [dependency.to_dict() for dependency in self.file_dependencies],
            "references": [reference.to_dict() for reference in self.references],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> GraphSnapshot:
        return cls(
            schema_version=str(data.get("schema_version", SNAPSHOT_SCHEMA_VERSION)),
            scene_path=str(data.get("scene_path", "")),
            maya_version=str(data.get("maya_version", "")),
            renderer=data.get("renderer"),
            scan_scope=str(data.get("scan_scope", "scene")),
            scanned_at_utc=str(data.get("scanned_at_utc", "")),
            nodes=[
                NodeSnapshot.from_dict(_require_mapping(item, "nodes item"))
                for item in data.get("nodes", [])
            ],
            connections=[
                ConnectionSnapshot.from_dict(_require_mapping(item, "connections item"))
                for item in data.get("connections", [])
            ],
            materials=[
                MaterialSnapshot.from_dict(_require_mapping(item, "materials item"))
                for item in data.get("materials", [])
            ],
            shading_engines=[
                ShadingEngineSnapshot.from_dict(_require_mapping(item, "shading_engines item"))
                for item in data.get("shading_engines", [])
            ],
            file_dependencies=[
                FileDependencySnapshot.from_dict(_require_mapping(item, "file_dependencies item"))
                for item in data.get("file_dependencies", [])
            ],
            references=[
                ReferenceSnapshot.from_dict(_require_mapping(item, "references item"))
                for item in data.get("references", [])
            ],
        )

    def to_json(self, *, indent: Optional[int] = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> GraphSnapshot:
        data = json.loads(text)
        return cls.from_dict(_require_mapping(data, "GraphSnapshot JSON"))
