from __future__ import annotations

from pathlib import Path

import pytest

from pipeline_inspector.maya.panel_session import (
    load_panel_session,
    remember_table_column_widths,
    remember_validate_splitter_sizes,
    save_panel_session,
)
from pipeline_inspector.ui.main_window import ISSUES_TABLE_OBJECT_NAME


def test_panel_session_persists_table_column_widths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))

    remember_table_column_widths(ISSUES_TABLE_OBJECT_NAME, (120, 180, 240, 300, 90, 110))

    session = load_panel_session()
    assert session.table_column_widths[ISSUES_TABLE_OBJECT_NAME] == (120, 180, 240, 300, 90, 110)


def test_panel_session_persists_validate_splitter_sizes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))

    remember_validate_splitter_sizes((640, 280))

    session = load_panel_session()
    assert session.validate_splitter_sizes == (640, 280)


def test_save_panel_session_preserves_layout_when_updating_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))

    remember_table_column_widths(ISSUES_TABLE_OBJECT_NAME, (90, 100))
    remember_validate_splitter_sizes((500, 320))
    save_panel_session(studio_config_path=tmp_path / "studio.json")

    session = load_panel_session()
    assert session.studio_config_path.endswith("studio.json")
    assert session.table_column_widths[ISSUES_TABLE_OBJECT_NAME] == (90, 100)
    assert session.validate_splitter_sizes == (500, 320)
