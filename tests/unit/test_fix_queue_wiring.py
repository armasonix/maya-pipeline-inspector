from __future__ import annotations

from pipeline_inspector.ui.fix_queue import _connect_button


class _FakeClicked:
    def __init__(self) -> None:
        self.slots: list[object] = []

    def connect(self, slot: object) -> None:
        self.slots.append(slot)

    def emit(self) -> None:
        for slot in self.slots:
            slot()


class _FakeButton:
    def __init__(self) -> None:
        self.clicked = _FakeClicked()


def test_fix_queue_button_wires_single_handler_per_click() -> None:
    calls: list[str] = []
    button = _FakeButton()
    _connect_button(button, lambda: calls.append("handler"))
    button.clicked.emit()
    assert calls == ["handler"]


def test_duplicate_fix_queue_wiring_invokes_handler_twice() -> None:
    """Regression guard: duplicate clicked.connect caused double permission dialogs."""
    calls: list[str] = []
    button = _FakeButton()
    _connect_button(button, lambda: calls.append("callback"))
    _connect_button(button, lambda: calls.append("redundant"))
    button.clicked.emit()
    assert calls == ["callback", "redundant"]


def test_ui_launcher_no_longer_double_wires_fix_queue_actions() -> None:
    from pipeline_inspector.maya import ui_launcher

    assert not hasattr(ui_launcher, "_wire_fix_queue_actions")
