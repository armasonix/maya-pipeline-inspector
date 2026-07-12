"""Semantic texture slot resolution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from shader_health.adapters.base import RendererAdapterRegistry
from shader_health.core import ConnectionSnapshot, GraphSnapshot, NodeSnapshot

_COLOR_SEMANTICS = frozenset({"base_color", "specular_color", "emission"})
_DATA_SEMANTICS = frozenset(
    {"roughness", "metalness", "normal", "bump", "displacement", "mask", "opacity"}
)

@dataclass(frozen=True)
class SemanticSlotResolution:
    """Resolved semantic label for a graph connection destination."""

    connection: ConnectionSnapshot
    semantic: str
    status: str
    data_kind: str
    adapter_id: Optional[str] = None
    reason: str = ""

    @property
    def is_resolved(self) -> bool:
        return self.status == "resolved"

class SemanticTextureSlotResolver:
    """Resolve connection destination plugs to semantic texture slots."""

    def __init__(self, registry: RendererAdapterRegistry) -> None:
        self.registry = registry

    def resolve_all(self, snapshot: GraphSnapshot) -> list[SemanticSlotResolution]:
        return [self.resolve_connection(snapshot, item) for item in snapshot.connections]

    def resolve_connection(
        self,
        snapshot: GraphSnapshot,
        connection: ConnectionSnapshot,
    ) -> SemanticSlotResolution:
        destination_node = _node_by_id(snapshot).get(connection.dst_node)
        if destination_node is None:
            return _semantic_resolution(
                connection,
                semantic="unknown",
                status="unknown",
                reason=f"destination node not found: {connection.dst_node}",
            )

        plug_key = f"{destination_node.type_name}.{connection.dst_attr}"
        matches = self._matching_semantics(plug_key)
        if not matches:
            return _semantic_resolution(
                connection,
                semantic="unknown",
                status="unknown",
                reason=f"no semantic mapping for {plug_key}",
            )

        unique_semantics = sorted({semantic for _, semantic in matches})
        if len(unique_semantics) > 1:
            return _semantic_resolution(
                connection,
                semantic="unknown",
                status="ambiguous",
                reason=f"ambiguous semantic mapping for {plug_key}",
            )

        adapter_ids = ",".join(adapter_id for adapter_id, _ in matches)
        semantic = unique_semantics[0]
        return _semantic_resolution(
            connection,
            semantic=semantic,
            status="resolved",
            adapter_id=adapter_ids,
        )

    def apply_to_snapshot(self, snapshot: GraphSnapshot) -> GraphSnapshot:
        resolved_connections = []
        for connection in snapshot.connections:
            resolution = self.resolve_connection(snapshot, connection)
            resolved_connections.append(_with_connection_semantic(connection, resolution.semantic))

        return GraphSnapshot(
            schema_version=snapshot.schema_version,
            scene_path=snapshot.scene_path,
            maya_version=snapshot.maya_version,
            renderer=snapshot.renderer,
            scan_scope=snapshot.scan_scope,
            scanned_at_utc=snapshot.scanned_at_utc,
            nodes=snapshot.nodes,
            connections=resolved_connections,
            materials=snapshot.materials,
            shading_engines=snapshot.shading_engines,
            file_dependencies=snapshot.file_dependencies,
            references=snapshot.references,
        )

    def _matching_semantics(self, plug_key: str) -> list[tuple[str, str]]:
        matches: list[tuple[str, str]] = []
        for adapter in self.registry.available_adapters():
            semantic = adapter.texture_slot_semantics().get(plug_key)
            if semantic is not None:
                matches.append((adapter.id, semantic))
        return matches

def classify_semantic_data_kind(semantic: str) -> str:
    """Classify semantic texture slot as color, data, material, or unknown."""

    if semantic in _COLOR_SEMANTICS:
        return "color"
    if semantic in _DATA_SEMANTICS:
        return "data"
    if semantic == "material":
        return "material"
    return "unknown"

def _node_by_id(snapshot: GraphSnapshot) -> dict[str, NodeSnapshot]:
    return {node.id: node for node in snapshot.nodes}

def _semantic_resolution(
    connection: ConnectionSnapshot,
    *,
    semantic: str,
    status: str,
    adapter_id: Optional[str] = None,
    reason: str = "",
) -> SemanticSlotResolution:
    return SemanticSlotResolution(
        connection=connection,
        semantic=semantic,
        status=status,
        data_kind=classify_semantic_data_kind(semantic),
        adapter_id=adapter_id,
        reason=reason,
    )

def _with_connection_semantic(
    connection: ConnectionSnapshot,
    semantic: str,
) -> ConnectionSnapshot:
    return ConnectionSnapshot(
        src_node=connection.src_node,
        src_attr=connection.src_attr,
        dst_node=connection.dst_node,
        dst_attr=connection.dst_attr,
        semantic=semantic,
    )
