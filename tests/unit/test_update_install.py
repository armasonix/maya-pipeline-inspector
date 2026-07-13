from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from pipeline_inspector.integrations.update.install import (
    ensure_maya_module_descriptor,
    install_staged_update,
)
from pipeline_inspector.studio_config import STUDIO_CONFIG_FILENAME
from pipeline_inspector.user_config import USER_CONFIG_DIRNAME, USER_CONFIG_FILENAME


def _write_install_tree(root: Path, *, version: str) -> None:
    maya_module = root / "maya_module"
    package = root / "src" / "pipeline_inspector"
    maya_module.mkdir(parents=True)
    package.mkdir(parents=True)
    (maya_module / "pipeline_inspector.mod").write_text(
        f"+ pipeline_inspector {version} .\n",
        encoding="utf-8",
    )
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "version_marker.txt").write_text(version, encoding="utf-8")


def _write_zip_from_payload(zip_path: Path, payload_root: Path) -> None:
    with zipfile.ZipFile(zip_path, "w") as archive:
        for path in payload_root.rglob("*"):
            if path.is_file():
                archive.write(path, arcname=str(path.relative_to(payload_root.parent)))


def _configure_home(monkeypatch: pytest.MonkeyPatch, home: Path) -> None:
    monkeypatch.setattr("pathlib.Path.home", lambda: home)
    config_dir = home / USER_CONFIG_DIRNAME
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / STUDIO_CONFIG_FILENAME).write_text(
        '{"studio_name":"keep-me"}',
        encoding="utf-8",
    )
    (config_dir / USER_CONFIG_FILENAME).write_text('{"theme":"dark"}', encoding="utf-8")


def test_install_staged_update_replaces_payload_and_preserves_config_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    home = tmp_path / "home"
    home.mkdir()
    _configure_home(monkeypatch, home)

    install_root = tmp_path / "install"
    _write_install_tree(install_root, version="0.4.0")

    payload_root = tmp_path / "package" / "maya-pipeline-inspector"
    _write_install_tree(payload_root, version="0.5.0")
    zip_path = tmp_path / "package" / "maya-pipeline-inspector-0.5.0.zip"
    _write_zip_from_payload(zip_path, payload_root)

    result = install_staged_update(
        zip_path,
        tag_name="v0.5.0",
        install_root=install_root,
        backup_root=tmp_path / "backups",
    )

    assert result.success is True
    assert (install_root / "src" / "pipeline_inspector" / "version_marker.txt").read_text(
        encoding="utf-8"
    ) == "0.5.0"
    assert (home / USER_CONFIG_DIRNAME / STUDIO_CONFIG_FILENAME).read_text(
        encoding="utf-8"
    ) == '{"studio_name":"keep-me"}'
    assert (home / USER_CONFIG_DIRNAME / USER_CONFIG_FILENAME).read_text(
        encoding="utf-8"
    ) == '{"theme":"dark"}'


def test_install_staged_update_rolls_back_when_apply_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    install_root = tmp_path / "install"
    _write_install_tree(install_root, version="0.4.0")

    payload_root = tmp_path / "package" / "maya-pipeline-inspector"
    _write_install_tree(payload_root, version="0.5.0")
    zip_path = tmp_path / "package" / "maya-pipeline-inspector-0.5.0.zip"
    _write_zip_from_payload(zip_path, payload_root)

    def _raise_copy_error(*_args: object, **_kwargs: object) -> None:
        raise OSError("copy failed")

    monkeypatch.setattr(
        "pipeline_inspector.integrations.update.install.apply_install_payload",
        _raise_copy_error,
    )

    result = install_staged_update(
        zip_path,
        tag_name="v0.5.0",
        install_root=install_root,
        backup_root=tmp_path / "backups",
    )

    assert result.success is False
    assert result.rolled_back is True
    assert (
        install_root / "src" / "pipeline_inspector" / "version_marker.txt"
    ).read_text(encoding="utf-8") == "0.4.0"


def test_ensure_maya_module_descriptor_writes_mod_file(tmp_path: Path):
    install_root = tmp_path / "install"

    mod_path = ensure_maya_module_descriptor(install_root, "v0.5.0")

    assert mod_path.is_file()
    text = mod_path.read_text(encoding="utf-8")
    assert "+ pipeline_inspector 0.5.0 ." in text
    assert "plug-ins: plug-ins" in text


def test_install_staged_update_returns_failure_for_invalid_package(tmp_path: Path):
    install_root = tmp_path / "install"
    _write_install_tree(install_root, version="0.4.0")
    zip_path = tmp_path / "broken.zip"
    zip_path.write_bytes(b"not-a-zip")

    result = install_staged_update(
        zip_path,
        tag_name="v0.5.0",
        install_root=install_root,
        backup_root=tmp_path / "backups",
    )

    assert result.success is False
    assert result.rolled_back is False
    assert (
        install_root / "src" / "pipeline_inspector" / "version_marker.txt"
    ).read_text(encoding="utf-8") == "0.4.0"
