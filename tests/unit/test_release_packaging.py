from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from tools.build_release_package import (
    build_release_package,
    list_native_plugins_in_zip,
    release_zip_name,
    validate_native_plugins_present,
)

from pipeline_inspector.integrations.update.download import select_update_asset
from pipeline_inspector.integrations.update.github_releases import ReleaseAsset


def _write_native_plugins(repo_root: Path) -> None:
    plug_ins = repo_root / "maya_module" / "plug-ins"
    for year in (2024, 2025):
        target = plug_ins / str(year)
        target.mkdir(parents=True, exist_ok=True)
        (target / "pipeline_inspector.mll").write_bytes(b"mll")
    (plug_ins / "pipeline_inspector.mll").write_bytes(b"mll")


def test_release_zip_name_uses_project_version():
    assert release_zip_name("0.6.0") == "maya-pipeline-inspector-0.6.0.zip"


def test_build_release_package_writes_maya_module_and_src(tmp_path: Path):
    repo_root = tmp_path / "repo"
    maya_module = repo_root / "maya_module"
    package = repo_root / "src" / "pipeline_inspector"
    maya_module.mkdir(parents=True)
    package.mkdir(parents=True)
    (maya_module / "pipeline_inspector.mod").write_text(
        "+ pipeline_inspector 0.6 .\n",
        encoding="utf-8",
    )
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "version_marker.txt").write_text("0.6.0", encoding="utf-8")

    artifact = build_release_package(
        version="0.6.0",
        output_dir=tmp_path / "dist",
        repo_root=repo_root,
    )

    assert artifact.name == "maya-pipeline-inspector-0.6.0.zip"
    with zipfile.ZipFile(artifact) as archive:
        names = set(archive.namelist())
    assert "maya_module/pipeline_inspector.mod" in names
    assert "src/pipeline_inspector/version_marker.txt" in names


def test_build_release_package_bundles_native_plugins_when_present(tmp_path: Path):
    repo_root = tmp_path / "repo"
    maya_module = repo_root / "maya_module"
    package = repo_root / "src" / "pipeline_inspector"
    maya_module.mkdir(parents=True)
    package.mkdir(parents=True)
    (maya_module / "pipeline_inspector.mod").write_text(
        "+ pipeline_inspector 0.6 .\n",
        encoding="utf-8",
    )
    (package / "__init__.py").write_text("", encoding="utf-8")
    _write_native_plugins(repo_root)

    artifact = build_release_package(
        version="0.6.0",
        output_dir=tmp_path / "dist",
        repo_root=repo_root,
        require_native=True,
    )

    with zipfile.ZipFile(artifact) as archive:
        bundled = list_native_plugins_in_zip(archive)
    assert "maya_module/plug-ins/2024/pipeline_inspector.mll" in bundled
    assert "maya_module/plug-ins/2025/pipeline_inspector.mll" in bundled
    assert "maya_module/plug-ins/pipeline_inspector.mll" in bundled


def test_validate_native_plugins_present_requires_supported_years(tmp_path: Path):
    repo_root = tmp_path / "repo"
    plug_ins = repo_root / "maya_module" / "plug-ins"
    plug_ins.mkdir(parents=True)
    (plug_ins / "2024" / "pipeline_inspector.mll").parent.mkdir(parents=True, exist_ok=True)
    (plug_ins / "2024" / "pipeline_inspector.mll").write_bytes(b"mll")

    with pytest.raises(RuntimeError, match="2025"):
        validate_native_plugins_present(repo_root)


def test_build_release_package_requires_native_plugins_when_flag_set(tmp_path: Path):
    repo_root = tmp_path / "repo"
    maya_module = repo_root / "maya_module"
    package = repo_root / "src" / "pipeline_inspector"
    maya_module.mkdir(parents=True)
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")

    with pytest.raises(RuntimeError, match="native plug-ins"):
        build_release_package(
            version="0.6.0",
            output_dir=tmp_path / "dist",
            repo_root=repo_root,
            require_native=True,
        )


def test_select_update_asset_prefers_maya_pipeline_inspector_zip():
    assets = (
        ReleaseAsset("pipeline_inspector.mll", "https://x/mll", 1, "bin", 1),
        ReleaseAsset("maya-pipeline-inspector-0.5.0.zip", "https://x/zip", 2, "zip", 2),
    )

    selected = select_update_asset(assets)

    assert selected is not None
    assert selected.name == "maya-pipeline-inspector-0.5.0.zip"


def test_select_update_asset_rejects_legacy_shader_health_zip():
    assets = (
        ReleaseAsset("maya-shader-health-inspector-0.4.0.zip", "https://x/legacy", 1, "zip", 1),
        ReleaseAsset("other-package-0.5.0.zip", "https://x/other", 2, "zip", 2),
    )

    selected = select_update_asset(assets)

    assert selected is not None
    assert selected.name == "other-package-0.5.0.zip"


def test_select_update_asset_returns_none_when_only_non_zip_assets():
    assets = (
        ReleaseAsset("pipeline_inspector.mll", "https://x/mll", 1, "bin", 1),
    )

    assert select_update_asset(assets) is None


def test_select_update_asset_returns_none_when_only_legacy_zip_assets():
    assets = (
        ReleaseAsset("shader_health_inspector-0.4.0.zip", "https://x/legacy", 1, "zip", 1),
    )

    assert select_update_asset(assets) is None


def test_build_release_package_requires_payload_directories(tmp_path: Path):
    repo_root = tmp_path / "empty"
    repo_root.mkdir()

    with pytest.raises(FileNotFoundError, match="maya_module"):
        build_release_package(version="0.6.0", output_dir=tmp_path / "dist", repo_root=repo_root)
