"""Maya scene scanner entrypoints.

This module is intentionally safe to import outside Maya. Real Maya modules are
loaded lazily only when scan functions run without an injected ``cmds_module``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from shader_health.core import GraphSnapshot, NodeSnapshot


class MayaUnavailableError(RuntimeError):
    """Raised when Maya commands are required but unavailable."""


@dataclass(frozen=True)
class ScanOptions:
    """Options shared by scanner entrypoints.

    These flags are intentionally conservative placeholders for Milestone 2.
    Deeper traversal will be implemented by the following scanner issues.
    """

    include_references: bool = True
    include_file_dependencies: bool = True
    include_connections: bool = True


def scan_scene(
    options: Optional[ScanOptions] = None,
    cmds_module: Optional[Any] = None,
) -> GraphSnapshot:
    """Scan the current Maya scene and return a minimal GraphSnapshot.

    The MVP entrypoint captures scene metadata only. Shading engine traversal,
    node attribute collection, file dependencies, and reference metadata are
    implemented by later scanner issues.
    """

    cmds = _get_cmds(cmds_module)
    return _base_snapshot(cmds, scan_scope="scene", options=options or ScanOptions())


def scan_selection(
    options: Optional[ScanOptions] = None,
    cmds_module: Optional[Any] = None,
) -> GraphSnapshot:
    """Scan current Maya selection and return a selection-scoped snapshot.

    For the first scanner milestone this records selected nodes as lightweight
    NodeSnapshot entries. Full upstream material traversal is handled later.
    """

    cmds = _get_cmds(cmds_module)
    snapshot = _base_snapshot(cmds, scan_scope="selection", options=options or ScanOptions())
    selected_nodes = _selection_nodes(cmds)
    return GraphSnapshot(
        schema_version=snapshot.schema_version,
        scene_path=snapshot.scene_path,
        maya_version=snapshot.maya_version,
        renderer=snapshot.renderer,
        scan_scope=snapshot.scan_scope,
        scanned_at_utc=snapshot.scanned_at_utc,
        nodes=selected_nodes,
        connections=snapshot.connections,
        materials=snapshot.materials,
        shading_engines=snapshot.shading_engines,
        file_dependencies=snapshot.file_dependencies,
        references=snapshot.references,
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


def _base_snapshot(cmds: Any, *, scan_scope: str, options: ScanOptions) -> GraphSnapshot:
    del options  # Reserved for upcoming scanner traversal issues.
    return GraphSnapshot(
        scene_path=_scene_path(cmds),
        maya_version=_maya_version(cmds),
        renderer=_current_renderer(cmds),
        scan_scope=scan_scope,
        scanned_at_utc=_utc_now(),
    )


def _scene_path(cmds: Any) -> str:
    scene_path = _call_cmds(cmds, "file", "", query=True, sceneName=True)
    return str(scene_path or "")


def _maya_version(cmds: Any) -> str:
    version = _call_cmds(cmds, "about", "", version=True)
    return str(version or "")


def _current_renderer(cmds: Any) -> Optional[str]:
    renderer = _call_cmds(cmds, "getAttr", None, "defaultRenderGlobals.currentRenderer")
    return str(renderer) if renderer else None


def _selection_nodes(cmds: Any) -> list[NodeSnapshot]:
    selection = _call_cmds(cmds, "ls", [], selection=True, long=True) or []
    nodes: list[NodeSnapshot] = []
    for full_name in selection:
        full_name_text = str(full_name)
        nodes.append(
            NodeSnapshot(
                id=f"node:{full_name_text}",
                name=_short_name(full_name_text),
                full_name=full_name_text,
                type_name=_node_type(cmds, full_name_text),
                attrs={},
                classification=[],
            )
        )
    return nodes


def _node_type(cmds: Any, node: str) -> str:
    node_type = _call_cmds(cmds, "nodeType", "", node)
    return str(node_type or "")


def _short_name(full_name: str) -> str:
    if "|" in full_name:
        full_name = full_name.rsplit("|", 1)[-1]
    if ":" in full_name:
        return full_name.rsplit(":", 1)[-1]
    return full_name


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
