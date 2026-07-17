"""Merge OpenUSD proxy stages from the active Maya scene into a GraphSnapshot."""
from __future__ import annotations

import json
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from pipeline_inspector.core.models import GraphSnapshot

_DEBUG_LOG = Path(__file__).resolve().parents[2] / "debug-618f4f.log"


def merge_usd_proxy_snapshots(
    snapshot: GraphSnapshot,
    cmds: Any,
) -> GraphSnapshot:
    """Append USD stage scans from ``mayaUsdProxyShape`` nodes."""

    paths = _collect_usd_proxy_paths(cmds)
    # #region agent log
    _debug_log(
        "usd_scene_scan.merge_usd_proxy_snapshots",
        "USD proxy discovery",
        {
            "proxy_count": len(paths),
            "proxy_paths": "|".join(str(path) for path in paths),
            "base_renderer": snapshot.renderer,
            "base_file_deps": len(snapshot.file_dependencies),
            "base_nodes": len(snapshot.nodes),
        },
        hypothesis_id="H1",
    )
    # #endregion
    if not paths:
        return snapshot

    from pipeline_inspector.usd.scanner import scan_usd_stage

    merged = snapshot
    merged_paths: list[str] = []
    for path in paths:
        try:
            usd_snapshot = scan_usd_stage(path, scan_scope="asset")
        except Exception as exc:  # noqa: BLE001
            # #region agent log
            _debug_log(
                "usd_scene_scan.merge_usd_proxy_snapshots",
                "USD proxy scan failed",
                {"path": str(path), "error": str(exc)},
                hypothesis_id="H1",
            )
            # #endregion
            continue
        merged = _merge_snapshots(merged, usd_snapshot, proxy_usd_path=path)
        merged_paths.append(str(path))

    # #region agent log
    _debug_log(
        "usd_scene_scan.merge_usd_proxy_snapshots",
        "USD proxy merge complete",
        {
            "merged_paths": "|".join(merged_paths),
            "merged_file_deps": len(merged.file_dependencies),
            "merged_nodes": len(merged.nodes),
            "shader_nodes_with_colorspace": sum(
                1
                for node in merged.nodes
                if node.type_name == "Shader" and node.attrs.get("colorSpace")
            ),
        },
        hypothesis_id="H1",
    )
    # #endregion
    return merged


def _collect_usd_proxy_paths(cmds: Any) -> list[Path]:
    shapes = cmds.ls(type="mayaUsdProxyShape", long=True) or []
    paths: list[Path] = []
    seen: set[str] = set()
    for shape in shapes:
        for attr in ("filePath", "fp"):
            try:
                raw_path = str(cmds.getAttr(f"{shape}.{attr}") or "").strip()
            except Exception:  # noqa: BLE001
                continue
            if not raw_path or raw_path in seen:
                continue
            candidate = Path(raw_path)
            if candidate.suffix.casefold() not in {".usd", ".usda", ".usdc"}:
                continue
            seen.add(raw_path)
            paths.append(candidate.resolve())
            break
    return paths


def _merge_snapshots(
    base: GraphSnapshot,
    usd: GraphSnapshot,
    *,
    proxy_usd_path: Path | None = None,
) -> GraphSnapshot:
    node_ids = {node.id for node in base.nodes}
    nodes = list(base.nodes)
    for node in usd.nodes:
        if node.id not in node_ids:
            nodes.append(node)
            node_ids.add(node.id)

    dep_keys = {(dep.node_id, dep.attr, dep.raw_path) for dep in base.file_dependencies}
    file_dependencies = list(base.file_dependencies)
    for dependency in usd.file_dependencies:
        key = (dependency.node_id, dependency.attr, dependency.raw_path)
        if key in dep_keys:
            continue
        file_dependencies.append(dependency)
        dep_keys.add(key)

    shape_ids = {shape.node_id for shape in base.shapes}
    shapes = list(base.shapes)
    for shape in usd.shapes:
        if shape.node_id not in shape_ids:
            shapes.append(shape)
            shape_ids.add(shape.node_id)

    material_ids = {material.node_id for material in base.materials}
    materials = list(base.materials)
    for material in usd.materials:
        if material.node_id not in material_ids:
            materials.append(material)
            material_ids.add(material.node_id)

    metadata = base.usd_stage_metadata
    usd_root_layer = str(
        proxy_usd_path
        or (usd.usd_stage_metadata.root_layer if usd.usd_stage_metadata is not None else "")
        or ""
    )
    if usd.usd_stage_metadata is not None:
        if metadata is None:
            metadata = usd.usd_stage_metadata
            if usd_root_layer:
                metadata = replace(metadata, root_layer=usd_root_layer)
        else:
            metadata = replace(
                metadata,
                root_layer=usd_root_layer or metadata.root_layer,
                unbound_mesh_count=metadata.unbound_mesh_count
                + usd.usd_stage_metadata.unbound_mesh_count,
                missing_reference_count=metadata.missing_reference_count
                + usd.usd_stage_metadata.missing_reference_count,
                unbound_mesh_paths=list(metadata.unbound_mesh_paths)
                + list(usd.usd_stage_metadata.unbound_mesh_paths),
                missing_reference_paths=list(metadata.missing_reference_paths)
                + list(usd.usd_stage_metadata.missing_reference_paths),
            )

    return replace(
        base,
        nodes=nodes,
        file_dependencies=file_dependencies,
        shapes=shapes,
        materials=materials,
        usd_stage_metadata=metadata,
    )


def _debug_log(
    location: str,
    message: str,
    data: dict[str, object],
    *,
    hypothesis_id: str,
) -> None:
    try:
        payload = {
            "sessionId": "618f4f",
            "timestamp": int(time.time() * 1000),
            "location": location,
            "message": message,
            "data": {key: str(value) for key, value in data.items()},
            "hypothesisId": hypothesis_id,
        }
        with _DEBUG_LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
    except OSError:
        return
