from __future__ import annotations

from pathlib import Path

from pipeline_inspector.studio_config import StudioEnvironmentSettings
from pipeline_inspector.util.paths import (
    author_maya_texture_path,
    author_maya_texture_path_for_fix,
)


def test_author_maya_texture_path_prefers_scene_relative(tmp_path: Path) -> None:
    scene = tmp_path / "broken_scene" / "scene.ma"
    scene.parent.mkdir(parents=True)
    textures = scene.parent / "textures"
    textures.mkdir()
    texture_path = textures / "demo_albedo_v002.1001.exr"
    texture_path.write_bytes(b"pixels")
    env = StudioEnvironmentSettings(
        asset_root=str(scene.parent),
        texture_root=str(textures),
    )

    authored = author_maya_texture_path(
        "${STUDIO_ASSET_ROOT}/textures/demo_albedo_v002.1001.exr",
        scene_path=str(scene),
        studio_environment=env,
        fallback_absolute=str(texture_path),
    )

    assert authored == "textures/demo_albedo_v002.1001.exr"
    assert "${" not in authored


def test_author_maya_texture_path_uses_absolute_for_parent_relative(tmp_path: Path) -> None:
    scene = tmp_path / "arnold_policy" / "scene.ma"
    scene.parent.mkdir(parents=True)
    textures = tmp_path / "broken_scene" / "textures"
    textures.mkdir(parents=True)
    texture_path = textures / "demo_albedo_v002.1001.exr"
    texture_path.write_bytes(b"pixels")
    env = StudioEnvironmentSettings(
        asset_root=str(tmp_path / "broken_scene"),
        texture_root=str(textures),
    )

    authored = author_maya_texture_path(
        "${STUDIO_ASSET_ROOT}/textures/demo_albedo_v002.1001.exr",
        scene_path=str(scene),
        studio_environment=env,
        fallback_absolute=str(texture_path),
    )

    assert authored == str(texture_path.resolve()).replace("\\", "/")
    assert ".." not in authored


def test_author_maya_texture_path_for_fix_prefers_studio_tokens(tmp_path: Path) -> None:
    scene = tmp_path / "arnold_policy" / "scene.ma"
    scene.parent.mkdir(parents=True)
    textures = tmp_path / "broken_scene" / "textures"
    textures.mkdir(parents=True)
    texture_path = textures / "demo_albedo_v002.1001.exr"
    texture_path.write_bytes(b"pixels")
    env = StudioEnvironmentSettings(
        asset_root=str(tmp_path / "broken_scene"),
        texture_root=str(textures),
    )

    authored = author_maya_texture_path_for_fix(
        str(texture_path.resolve()).replace("\\", "/"),
        scene_path=str(scene),
        studio_environment=env,
        fallback_absolute=str(texture_path),
    )

    assert authored == "${STUDIO_TEXTURE_ROOT}/demo_albedo_v002.1001.exr"
