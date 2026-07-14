from __future__ import annotations

from types import SimpleNamespace

from pipeline_inspector.studio_config import GovernanceSettings, StudioConfig
from pipeline_inspector.ui.governance_section import (
    SETTINGS_TRACKER_ROLE_MAP_INPUT_OBJECT_NAME,
    read_governance_from_view,
    update_governance_view,
)


class FakePlainTextEdit:
    def __init__(self, text: str = "") -> None:
        self._text = text
        self._focus = False

    def toPlainText(self) -> str:
        return self._text

    def setPlainText(self, text: str) -> None:
        self._text = text

    def hasFocus(self) -> bool:
        return self._focus


class FakeQtWidgets:
    QPlainTextEdit = FakePlainTextEdit
    QWidget = object
    QLabel = object


def _patch_find_child(monkeypatch, tracker_input: FakePlainTextEdit) -> None:
    import pipeline_inspector.ui.governance_section as governance_section

    def _fake_find(view: object, cls: object, object_name: str) -> object | None:
        if object_name == SETTINGS_TRACKER_ROLE_MAP_INPUT_OBJECT_NAME:
            return tracker_input
        return None

    monkeypatch.setattr(governance_section, "find_child", _fake_find)


def test_read_governance_keeps_partial_tracker_text_without_fallback(monkeypatch):
    tracker_input = FakePlainTextEdit("Artist")
    _patch_find_child(monkeypatch, tracker_input)
    base = StudioConfig(
        governance=GovernanceSettings(tracker_role_map={"Old": "pipeline_td"}),
    )

    governance = read_governance_from_view(SimpleNamespace(), FakeQtWidgets(), base=base)

    assert governance.tracker_role_map == {}


def test_update_governance_skips_plain_text_reset_while_focused(monkeypatch):
    tracker_input = FakePlainTextEdit("Artist=technical_artist")
    tracker_input._focus = True
    _patch_find_child(monkeypatch, tracker_input)
    config = StudioConfig(
        governance=GovernanceSettings(tracker_role_map={"Old": "pipeline_td"}),
    )

    update_governance_view(SimpleNamespace(), FakeQtWidgets(), config)

    assert tracker_input.toPlainText() == "Artist=technical_artist"
