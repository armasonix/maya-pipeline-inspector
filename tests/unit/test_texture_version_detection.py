from __future__ import annotations

from pathlib import Path

from pipeline_inspector.maya.scanner import _latest_texture_version, _texture_version


def _write_udim_tiles(folder: Path, stem: str, tiles: list[int]) -> None:
    for tile in tiles:
        (folder / f"{stem}.{tile}.exr").write_bytes(b"tile")


def test_texture_version_returns_none_when_filename_has_no_version_token():
    assert _texture_version("albedo.<UDIM>.exr") is None
    assert _texture_version("/show/tex/hero_basecolor.1001.exr") is None


def test_texture_version_parses_case_insensitive_token():
    assert _texture_version("albedo_V012.<UDIM>.exr") == "012"


def test_latest_texture_version_returns_none_when_version_token_is_missing(tmp_path: Path):
    texture_dir = tmp_path / "tex"
    texture_dir.mkdir()
    path = str(texture_dir / "albedo.<UDIM>.exr")

    assert _latest_texture_version(path) is None


def test_latest_texture_version_returns_current_when_folder_has_single_version(
    tmp_path: Path,
):
    texture_dir = tmp_path / "tex"
    texture_dir.mkdir()
    _write_udim_tiles(texture_dir, "roughness_v001", [1001])
    path = str(texture_dir / "roughness_v001.<UDIM>.exr")

    assert _latest_texture_version(path) == "001"


def test_latest_texture_version_picks_highest_numeric_sibling(tmp_path: Path):
    texture_dir = tmp_path / "tex"
    texture_dir.mkdir()
    _write_udim_tiles(texture_dir, "albedo_v001", [1001, 1002])
    _write_udim_tiles(texture_dir, "albedo_v009", [1001])
    _write_udim_tiles(texture_dir, "albedo_v010", [1001, 1002])
    path = str(texture_dir / "albedo_v001.<UDIM>.exr")

    assert _latest_texture_version(path) == "010"


def test_latest_texture_version_ignores_unrelated_sibling_files(tmp_path: Path):
    texture_dir = tmp_path / "tex"
    texture_dir.mkdir()
    _write_udim_tiles(texture_dir, "albedo_v001", [1001])
    _write_udim_tiles(texture_dir, "albedo_v004", [1001])
    _write_udim_tiles(texture_dir, "roughness_v099", [1001])
    (texture_dir / "notes.txt").write_text("ignore me", encoding="utf-8")
    (texture_dir / "albedo_v005").mkdir()
    path = str(texture_dir / "albedo_v001.<UDIM>.exr")

    assert _latest_texture_version(path) == "004"


def test_latest_texture_version_preserves_zero_padding_width(tmp_path: Path):
    texture_dir = tmp_path / "tex"
    texture_dir.mkdir()
    _write_udim_tiles(texture_dir, "albedo_v01", [1001])
    _write_udim_tiles(texture_dir, "albedo_v02", [1001])
    _write_udim_tiles(texture_dir, "albedo_v010", [1001])
    path = str(texture_dir / "albedo_v01.<UDIM>.exr")

    assert _latest_texture_version(path) == "010"
