from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pipeline_inspector.maya import ui_icons


def test_maya_module_icons_directory_points_at_maya_module_icons(tmp_path: Path, monkeypatch: Any):
    repo_root = tmp_path / "repo"
    icons_dir = repo_root / "maya_module" / "icons"
    icons_dir.mkdir(parents=True)
    monkeypatch.setattr(ui_icons, "repo_root", lambda: repo_root)

    assert ui_icons.maya_module_icons_directory() == icons_dir


def test_resolve_icon_path_uses_configured_basename(tmp_path: Path, monkeypatch: Any):
    repo_root = tmp_path / "repo"
    icons_dir = repo_root / "maya_module" / "icons"
    icons_dir.mkdir(parents=True)
    icon_path = icons_dir / "pipeline_inspector_settings.png"
    icon_path.write_bytes(b"png")
    monkeypatch.setattr(ui_icons, "repo_root", lambda: repo_root)

    assert ui_icons.resolve_icon_path(ui_icons.ICON_SETTINGS) == icon_path
    assert ui_icons.icon_path_exists(ui_icons.ICON_SETTINGS) is True


def test_shelf_and_menu_image_kwargs_use_basename_when_png_exists(
    tmp_path: Path,
    monkeypatch: Any,
):
    repo_root = tmp_path / "repo"
    icons_dir = repo_root / "maya_module" / "icons"
    icons_dir.mkdir(parents=True)
    (icons_dir / "pipeline_inspector_farm_check.png").write_bytes(b"png")
    monkeypatch.setattr(ui_icons, "repo_root", lambda: repo_root)

    assert ui_icons.shelf_button_image_kwargs(ui_icons.ICON_FARM_CHECK) == {
        "image1": "pipeline_inspector_farm_check.png",
    }
    assert ui_icons.menu_item_image_kwargs(ui_icons.ICON_FARM_CHECK) == {
        "image": "pipeline_inspector_farm_check.png",
    }


def test_shelf_and_menu_image_kwargs_fallback_when_png_missing(
    tmp_path: Path,
    monkeypatch: Any,
):
    repo_root = tmp_path / "repo"
    (repo_root / "maya_module" / "icons").mkdir(parents=True)
    monkeypatch.setattr(ui_icons, "repo_root", lambda: repo_root)

    assert ui_icons.shelf_button_image_kwargs(ui_icons.ICON_REPORTS) == {
        "image1": "commandButton.png",
    }
    assert ui_icons.menu_item_image_kwargs(ui_icons.ICON_REPORTS) == {}


def test_unknown_icon_id_raises_key_error():
    with pytest.raises(KeyError, match="Unknown Pipeline Inspector icon id"):
        ui_icons.icon_filename("missing")
