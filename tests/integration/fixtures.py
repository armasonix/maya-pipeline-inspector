"""Shared snapshot fixtures for integration tests."""

from __future__ import annotations

from pathlib import Path

from shader_health.core import (
    ConnectionSnapshot,
    FileDependencySnapshot,
    GraphSnapshot,
    MaterialSnapshot,
    NodeSnapshot,
)


def broken_scene_snapshot(tmp_path: Path) -> GraphSnapshot:
    """Build a broken-scene-like snapshot with common and renderer issues."""

    tile_1001 = tmp_path / "demo_roughness_v001.1001.exr"
    tile_1003 = tmp_path / "demo_roughness_v001.1003.exr"
    tile_1001.write_bytes(b"tile")
    tile_1003.write_bytes(b"tile")
    udim_path = str(tile_1001).replace("\\", "/")

    return GraphSnapshot(
        scene_path=str(tmp_path / "shader_health_demo_broken.ma"),
        maya_version="2024",
        renderer="vray",
        scan_scope="scene",
        scanned_at_utc="2026-07-01T12:00:00Z",
        nodes=[
            NodeSnapshot(
                id="node:demo_roughness_v001_1",
                name="demo_roughness_v001_1",
                type_name="file",
                attrs={"colorSpace": "sRGB"},
            ),
            NodeSnapshot(
                id="node:demo_roughness_v001_2",
                name="demo_roughness_v001_2",
                type_name="file",
                attrs={
                    "colorSpace": "Raw",
                    "uvTilingMode": 3,
                    "fileTextureName": udim_path,
                },
            ),
            NodeSnapshot(
                id="node:demo_wrong_colorspace_MTL",
                name="demo_wrong_colorspace_MTL",
                type_name="VRayMtl",
            ),
            NodeSnapshot(
                id="node:demo_untextured_MTL",
                name="demo_untextured_MTL",
                type_name="VRayMtl",
            ),
            NodeSnapshot(
                id="node:displacementShader1",
                name="displacementShader1",
                type_name="displacementShader",
                attrs={"scale": 18},
            ),
        ],
        connections=[
            ConnectionSnapshot(
                src_node="node:demo_roughness_v001_1",
                src_attr="outAlpha",
                dst_node="node:demo_wrong_colorspace_MTL",
                dst_attr="roughness",
            ),
            ConnectionSnapshot(
                src_node="node:demo_displacement_v001_1",
                src_attr="outAlpha",
                dst_node="node:displacementShader1",
                dst_attr="displacement",
            ),
        ],
        materials=[
            MaterialSnapshot(
                node_id="node:demo_wrong_colorspace_MTL",
                name="demo_wrong_colorspace_MTL",
                type_name="VRayMtl",
                texture_nodes=["node:demo_roughness_v001_1"],
            ),
            MaterialSnapshot(
                node_id="node:demo_untextured_MTL",
                name="demo_untextured_MTL",
                type_name="VRayMtl",
                texture_nodes=[],
            ),
            MaterialSnapshot(
                node_id="node:demo_displacement_MTL",
                name="demo_displacement_MTL",
                type_name="VRayMtl",
                texture_nodes=["node:demo_displacement_v001_1"],
                displacement_nodes=["node:displacementShader1"],
            ),
        ],
        file_dependencies=[
            FileDependencySnapshot(
                node_id="node:demo_roughness_v001_2",
                attr="fileTextureName",
                raw_path=udim_path,
                resolved_path=udim_path,
                exists=True,
                is_udim=False,
            )
        ],
    )


def arnold_policy_scene_snapshot(tmp_path: Path) -> GraphSnapshot:
    """Build an Arnold snapshot that triggers production policy rule failures."""

    return GraphSnapshot(
        scene_path=str(tmp_path / "arnold_policy_demo.ma"),
        renderer="arnold",
        scan_scope="scene",
        scanned_at_utc="2026-07-01T12:00:00Z",
        nodes=[
            NodeSnapshot(
                id="node:hero_mtl",
                name="hero_mtl",
                type_name="aiStandardSurface",
                attrs={"transmissionDepth": 16},
            ),
            NodeSnapshot(
                id="node:demo_displacement_MTL",
                name="demo_displacement_MTL",
                type_name="aiStandardSurface",
            ),
            NodeSnapshot(
                id="node:displacementShader1",
                name="displacementShader1",
                type_name="displacementShader",
                attrs={"scale": 12},
            ),
            NodeSnapshot(
                id="node:hero_proxyStandIn",
                name="hero_proxyStandIn",
                type_name="aiStandIn",
            ),
        ],
        materials=[
            MaterialSnapshot(
                node_id="node:hero_mtl",
                name="hero_mtl",
                type_name="aiStandardSurface",
                texture_nodes=["node:file_basecolor"],
            ),
            MaterialSnapshot(
                node_id="node:demo_displacement_MTL",
                name="demo_displacement_MTL",
                type_name="aiStandardSurface",
                texture_nodes=["node:file_disp"],
                displacement_nodes=["node:displacementShader1"],
            ),
        ],
    )


def arnold_scene_snapshot(tmp_path: Path) -> GraphSnapshot:
    """Build a minimal Arnold snapshot for renderer-pack integration checks."""

    return GraphSnapshot(
        scene_path=str(tmp_path / "arnold_demo.ma"),
        renderer="arnold",
        scan_scope="scene",
        scanned_at_utc="2026-07-01T12:00:00Z",
        nodes=[
            NodeSnapshot(
                id="node:aiStandardSurface1",
                name="aiStandardSurface1",
                type_name="aiStandardSurface",
            )
        ],
        materials=[
            MaterialSnapshot(
                node_id="node:aiStandardSurface1",
                name="aiStandardSurface1",
                type_name="aiStandardSurface",
                texture_nodes=[],
            )
        ],
    )
