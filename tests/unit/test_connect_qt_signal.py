from __future__ import annotations

from shader_health.ui.table_widgets import connect_qt_signal


class FakeSignal:
    def __init__(self) -> None:
        self.slots: list = []

    def connect(self, slot) -> None:
        self.slots.append(slot)


class FakeBrokenSignal:
    connect = lambda self, slot: (_ for _ in ()).throw(AttributeError("broken"))


def test_connect_qt_signal_connects_slot():
    signal = FakeSignal()
    seen: list[int] = []

    assert connect_qt_signal(signal, lambda value: seen.append(value)) is True
    signal.slots[0](42)

    assert seen == [42]


def test_connect_qt_signal_returns_false_for_missing_signal():
    assert connect_qt_signal(None, lambda: None) is False


def test_connect_qt_signal_returns_false_when_connect_fails():
    assert connect_qt_signal(FakeBrokenSignal(), lambda: None) is False
