from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
USD_ASSET = ROOT / "examples" / "usd-asset" / "char-usd-2-asset.usd"


@pytest.mark.skipif(not USD_ASSET.is_file(), reason="example USD asset missing")
def test_arnold_image_shader_prefers_filename_input_over_file() -> None:
    pytest.importorskip("pxr")
    from pipeline_inspector.usd.scanner import scan_usd_stage

    snapshot = scan_usd_stage(USD_ASSET, scan_scope="asset")
    albedo_deps = [
        dependency
        for dependency in snapshot.file_dependencies
        if "t_demo_albedo_v002" in dependency.node_id
    ]
    attrs = {dependency.attr for dependency in albedo_deps}
    raw_paths = {dependency.raw_path for dependency in albedo_deps}

    assert attrs == {"filename"}
    assert all(not path.startswith("D:/") and not path.startswith("d:/") for path in raw_paths)
    assert any("../broken_scene/textures/" in path for path in raw_paths)
