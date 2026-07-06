from __future__ import annotations

import json
from pathlib import Path

from shader_health.core import (
    ConnectionSnapshot,
    FileDependencySnapshot,
    GraphSnapshot,
    MaterialSnapshot,
    NodeSnapshot,
)
from shader_health.reports.manifest import (
    MANIFEST_SCHEMA_VERSION,
    build_shader_manifest,
    dumps_shader_manifest,
    write_shader_manifest,
)


def make_snapshot() -> GraphSnapshot:
    return GraphSnapshot(
        scene_path="D:/show/asset/shading/demo.ma",
        maya_version="2025",
        renderer="vray",
        scan_scope="asset",
        scanned_at_utc="2026-07-01T12:00:00Z",
        nodes=[
            NodeSnapshot(
                id="node:file_albedo",
                name="file_albedo",
                type_name="file",
                attrs={"semantic_slot": "base_color"},
                classification=["texture", "file"],
            ),
            NodeSnapshot(
                id="node:file_roughness",
                name="file_roughness",
                type_name="file",
                classification=["texture", "file"],
            ),
        ],
        connections=[
            ConnectionSnapshot(
                src_node="node:file_roughness",
                src_attr="outAlpha",
                dst_node="node:hero_mtl",
                dst_attr="reflectionGlossiness",
                semantic="roughness",
            )
        ],
        materials=[
            MaterialSnapshot(
                node_id="node:hero_mtl",
                name="hero_mtl",
                type_name="VRayMtl",
                renderer_family="vray",
                shading_engines=["node:hero_sg"],
                assigned_shapes=["mesh:hero_body"],
                texture_nodes=["node:file_roughness", "node:file_albedo"],
                graph_node_count=12,
                graph_depth=4,
                graph_fingerprint="sha256:hero_graph",
            )
        ],
        file_dependencies=[
            FileDependencySnapshot(
                node_id="node:file_albedo",
                attr="fileTextureName",
                raw_path="$ASSET_ROOT/tex/albedo_v003.1001.exr",
                resolved_path="P:/show/asset/tex/albedo_v003.1001.exr",
                exists=True,
                is_udim=True,
                udim_tiles=[1001, 1002],
                missing_udim_tiles=[],
                extension=".exr",
                version="003",
                latest_version="003",
                max_dimension=4096,
            ),
            FileDependencySnapshot(
                node_id="node:file_roughness",
                attr="fileTextureName",
                raw_path="$ASSET_ROOT/tex/roughness_v001.1001.exr",
                resolved_path="P:/show/asset/tex/roughness_v001.1001.exr",
                exists=True,
                extension=".exr",
                version="001",
                latest_version="004",
                max_dimension=2048,
            ),
        ],
    )


def test_shader_manifest_contains_materials_textures_versions_and_fingerprint():
    manifest = build_shader_manifest(make_snapshot())

    assert manifest["manifest_schema_version"] == MANIFEST_SCHEMA_VERSION
    assert manifest["snapshot_schema_version"] == "1.0"
    assert manifest["scene_path"] == "D:/show/asset/shading/demo.ma"
    assert manifest["renderer"] == "vray"

    materials = manifest["materials"]
    assert len(materials) == 1
    material = materials[0]
    assert material["name"] == "hero_mtl"
    assert material["type_name"] == "VRayMtl"
    assert material["graph_fingerprint"] == "sha256:hero_graph"
    assert material["graph_node_count"] == 12
    assert material["graph_depth"] == 4

    textures = {texture["node_id"]: texture for texture in material["textures"]}
    assert textures["node:file_albedo"]["semantic"] == "base_color"
    assert textures["node:file_albedo"]["version"] == "003"
    assert textures["node:file_albedo"]["latest_version"] == "003"
    assert textures["node:file_albedo"]["udim_tiles"] == [1001, 1002]
    assert textures["node:file_albedo"]["max_dimension"] == 4096

    assert textures["node:file_roughness"]["semantic"] == "roughness"
    assert textures["node:file_roughness"]["version"] == "001"
    assert textures["node:file_roughness"]["latest_version"] == "004"
    assert textures["node:file_roughness"]["max_dimension"] == 2048


def test_shader_manifest_output_is_deterministic():
    snapshot = make_snapshot()

    first = dumps_shader_manifest(snapshot)
    second = dumps_shader_manifest(snapshot)

    assert first == second
    assert first.endswith("\n")
    payload = json.loads(first)
    assert payload["materials"][0]["textures"][0]["node_id"] == "node:file_albedo"


def test_shader_manifest_writer_writes_utf8_file(tmp_path: Path):
    output_path = tmp_path / "nested" / "manifest.json"

    written_path = write_shader_manifest(output_path, make_snapshot())

    assert written_path == output_path
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["manifest_schema_version"] == MANIFEST_SCHEMA_VERSION
    assert payload["materials"][0]["graph_fingerprint"] == "sha256:hero_graph"
