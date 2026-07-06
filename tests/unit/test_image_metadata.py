from __future__ import annotations

import struct
from pathlib import Path

from shader_health.core.image_metadata import max_image_dimension, read_image_dimensions
from shader_health.core.models import FileDependencySnapshot, GraphSnapshot, NodeSnapshot
from shader_health.maya.snapshot_enrichment import enrich_snapshot


def _write_png(path: Path, width: int, height: int) -> None:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    chunk_type = b"IHDR"
    length = struct.pack(">I", len(ihdr))
    crc = struct.pack(">I", 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + length + chunk_type + ihdr + crc)


def test_read_png_dimensions(tmp_path: Path):
    image_path = tmp_path / "tile.png"
    _write_png(image_path, 2048, 1024)

    width, height = read_image_dimensions(image_path)

    assert width == 2048
    assert height == 1024
    assert max_image_dimension(image_path) == 2048


def test_read_image_dimensions_returns_none_for_missing_file(tmp_path: Path):
    width, height = read_image_dimensions(tmp_path / "missing.png")

    assert width is None
    assert height is None
    assert max_image_dimension(tmp_path / "missing.png") is None


def test_enrich_snapshot_sets_max_dimension_on_existing_texture(tmp_path: Path):
    texture_path = tmp_path / "albedo.png"
    _write_png(texture_path, 4096, 2048)
    snapshot = GraphSnapshot(
        scene_path=str(tmp_path / "scene.ma"),
        nodes=[
            NodeSnapshot(
                id="node:file_albedo",
                name="file_albedo",
                type_name="file",
                attrs={"fileTextureName": str(texture_path)},
            )
        ],
        file_dependencies=[
            FileDependencySnapshot(
                node_id="node:file_albedo",
                attr="fileTextureName",
                raw_path=str(texture_path),
            )
        ],
    )

    enriched = enrich_snapshot(snapshot)
    dependency = enriched.file_dependencies[0]

    assert dependency.exists is True
    assert dependency.max_dimension == 4096
    assert dependency.image_info is not None
    assert dependency.image_info.width == 4096
    assert dependency.image_info.height == 2048
