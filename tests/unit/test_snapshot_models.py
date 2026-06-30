import json

import pytest

from shader_health.core import (
    SNAPSHOT_SCHEMA_VERSION,
    ConnectionSnapshot,
    FileDependencySnapshot,
    GraphSnapshot,
    ImageInfo,
    MaterialSnapshot,
    NodeSnapshot,
    ReferenceSnapshot,
    ShadingEngineSnapshot,
)


def make_snapshot() -> GraphSnapshot:
    return GraphSnapshot(
        scene_path="D:/show/assets/char/demo/shading/demo_shading.ma",
        maya_version="2025",
        renderer="vray",
        scan_scope="scene",
        scanned_at_utc="2026-06-30T12:00:00Z",
        nodes=[
            NodeSnapshot(
                id="node:file_roughness",
                name="file_roughness",
                full_name="char_demo:file_roughness",
                type_name="file",
                renderer_family="common",
                namespace="char_demo",
                referenced=True,
                reference_path="D:/show/assets/char/demo/demo_rig.ma",
                locked=False,
                attrs={"colorSpace": "ACEScg", "fileTextureName": "roughness.<UDIM>.exr"},
                classification=["texture", "file"],
            ),
            NodeSnapshot(
                id="node:demo_mtl",
                name="demo_mtl",
                type_name="VRayMtl",
                renderer_family="vray",
                attrs={"reflectionGlossiness": 0.5},
                classification=["material"],
            ),
        ],
        connections=[
            ConnectionSnapshot(
                src_node="node:file_roughness",
                src_attr="outAlpha",
                dst_node="node:demo_mtl",
                dst_attr="reflectionGlossiness",
                semantic="roughness",
            )
        ],
        materials=[
            MaterialSnapshot(
                node_id="node:demo_mtl",
                name="demo_mtl",
                type_name="VRayMtl",
                renderer_family="vray",
                shading_engines=["node:demo_sg"],
                assigned_shapes=["mesh:demo_body"],
                texture_nodes=["node:file_roughness"],
                displacement_nodes=[],
                graph_node_count=2,
                graph_depth=1,
                graph_fingerprint="sha256:demo",
            )
        ],
        shading_engines=[
            ShadingEngineSnapshot(
                node_id="node:demo_sg",
                name="demo_sg",
                surface_shader="node:demo_mtl",
                members=["mesh:demo_body"],
            )
        ],
        file_dependencies=[
            FileDependencySnapshot(
                node_id="node:file_roughness",
                attr="fileTextureName",
                raw_path="$ASSET_ROOT/tex/roughness_v001.<UDIM>.exr",
                resolved_path="D:/show/assets/char/demo/tex/roughness_v001.<UDIM>.exr",
                exists=True,
                is_udim=True,
                udim_tiles=[1001, 1002],
                missing_udim_tiles=[1003],
                extension=".exr",
                version="001",
                latest_version="003",
                mtime_utc="2026-06-30T11:00:00Z",
                size_bytes=1024,
                image_info=ImageInfo(width=4096, height=4096, channels=1, bit_depth="16f"),
            )
        ],
        references=[
            ReferenceSnapshot(
                namespace="char_demo",
                path="D:/show/assets/char/demo/demo_rig.ma",
                loaded=True,
                locked=False,
                node_ids=["node:file_roughness"],
            )
        ],
    )


def test_graph_snapshot_dict_round_trip():
    snapshot = make_snapshot()

    data = snapshot.to_dict()
    restored = GraphSnapshot.from_dict(data)

    assert restored == snapshot
    assert data["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert data["nodes"][0]["attrs"]["colorSpace"] == "ACEScg"
    assert data["file_dependencies"][0]["image_info"]["width"] == 4096


def test_graph_snapshot_json_round_trip():
    snapshot = make_snapshot()

    text = snapshot.to_json()
    restored = GraphSnapshot.from_json(text)

    assert restored == snapshot
    assert json.loads(text)["renderer"] == "vray"


def test_graph_snapshot_compact_json_is_valid():
    snapshot = make_snapshot()

    text = snapshot.to_json(indent=None)

    assert "\n" not in text
    assert GraphSnapshot.from_json(text) == snapshot


def test_graph_snapshot_from_json_rejects_non_mapping_root():
    with pytest.raises(TypeError, match="GraphSnapshot JSON must be a mapping"):
        GraphSnapshot.from_json("[]")
