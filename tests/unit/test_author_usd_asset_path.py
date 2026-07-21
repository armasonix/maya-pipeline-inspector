from __future__ import annotations

from pathlib import Path

from pipeline_inspector.studio_config import StudioEnvironmentSettings
from pipeline_inspector.util.paths import author_usd_asset_path


def test_author_usd_asset_path_prefers_relative_to_anchor(tmp_path: Path) -> None:
    textures = tmp_path / "usd-asset" / ".." / "broken_scene" / "textures"
    textures.mkdir(parents=True)
    texture_path = textures / "t_demo_albedo_v002.1001.exr"
    texture_path.write_bytes(b"pixels")
    anchor = tmp_path / "usd-asset"
    anchor.mkdir()

    authored = author_usd_asset_path(
        str(texture_path.resolve()),
        anchor_dir=anchor,
    )

    assert authored == "../broken_scene/textures/t_demo_albedo_v002.1001.exr"


def test_author_usd_asset_path_expands_studio_tokens(tmp_path: Path) -> None:
    textures = tmp_path / "textures"
    textures.mkdir()
    texture_path = textures / "demo_albedo_v002.1001.exr"
    texture_path.write_bytes(b"pixels")
    anchor = tmp_path / "asset"
    anchor.mkdir()
    studio_environment = StudioEnvironmentSettings(
        asset_root=str(tmp_path),
        texture_root=str(textures),
    )

    authored = author_usd_asset_path(
        "${STUDIO_ASSET_ROOT}/textures/demo_albedo_v002.1001.exr",
        anchor_dir=anchor,
        studio_environment=studio_environment,
    )

    assert authored == "../textures/demo_albedo_v002.1001.exr"


def test_author_usd_asset_path_uses_fallback_when_tokens_unexpanded(tmp_path: Path) -> None:
    textures = tmp_path / "broken_scene" / "textures"
    textures.mkdir(parents=True)
    texture_path = textures / "t_demo_albedo_v002.1001.exr"
    texture_path.write_bytes(b"pixels")
    anchor = tmp_path / "usd-asset"
    anchor.mkdir()
    fallback = str(
        (tmp_path / "broken_scene" / "textures" / "demo_albedo_v002.1001.exr").resolve()
    )

    authored = author_usd_asset_path(
        "${STUDIO_ASSET_ROOT}/textures/t_demo_albedo_v002.1001.exr",
        anchor_dir=anchor,
        studio_environment=None,
        fallback_absolute=fallback,
    )

    assert authored == "../broken_scene/textures/t_demo_albedo_v002.1001.exr"
    assert "${" not in authored
