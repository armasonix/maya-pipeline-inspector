from __future__ import annotations

from typing import Any

from shader_health.maya import commands, navigation


class FakeClipboard:
    def __init__(self) -> None:
        self.text = ""

    def setText(self, text: str) -> None:
        self.text = text


class FakeApplication:
    def __init__(self) -> None:
        self.clipboard_value = FakeClipboard()

    def clipboard(self) -> FakeClipboard:
        return self.clipboard_value


class FakeQtWidgets:
    application = FakeApplication()

    class QApplication:
        @staticmethod
        def instance() -> FakeApplication:
            return FakeQtWidgets.application


def test_copy_path_uses_injected_clipboard_setter():
    copied: list[str] = []

    result = navigation.copy_path("asset/path/hero.tx", clipboard_setter=copied.append)

    assert result.succeeded is True
    assert copied == ["asset/path/hero.tx"]


def test_copy_path_uses_qt_clipboard():
    result = navigation.copy_path("asset/path/hero.tx", qt_widgets=FakeQtWidgets)

    assert result.succeeded is True
    assert FakeQtWidgets.application.clipboard_value.text == "asset/path/hero.tx"


def test_reveal_file_reports_unsupported_platform_without_launching_process(tmp_path):
    launched: list[list[str]] = []
    texture = tmp_path / "hero.tx"
    texture.write_text("data", encoding="utf-8")

    result = navigation.reveal_file(
        str(texture),
        platform_name="UnknownPlatform",
        process_launcher=launched.append,
    )

    assert result.succeeded is False
    assert "Unsupported platform" in result.message
    assert launched == []


def test_reveal_file_fails_when_path_does_not_exist(tmp_path):
    launched: list[list[str]] = []
    missing = tmp_path / "missing" / "hero.tx"

    result = navigation.reveal_file(
        str(missing),
        platform_name="Windows",
        process_launcher=launched.append,
    )

    assert result.succeeded is False
    assert "does not exist" in result.message
    assert launched == []


def test_reveal_file_windows_selects_existing_file(tmp_path):
    launched: list[list[str]] = []
    texture = tmp_path / "hero.tx"
    texture.write_text("data", encoding="utf-8")

    result = navigation.reveal_file(
        str(texture),
        platform_name="Windows",
        process_launcher=launched.append,
    )

    assert result.succeeded is True
    assert launched == [["explorer", f"/select,{texture.resolve()}"]]


def test_reveal_file_windows_opens_parent_when_file_missing(tmp_path):
    launched: list[list[str]] = []
    missing = tmp_path / "hero.tx"

    result = navigation.reveal_file(
        str(missing),
        platform_name="Windows",
        process_launcher=launched.append,
    )

    assert result.succeeded is True
    assert launched == [["explorer", str(tmp_path.resolve())]]


def test_copy_and_reveal_command_wrappers_delegate(monkeypatch: Any):
    calls: list[tuple[str, str]] = []
    result = navigation.NavigationActionResult("action", "target", True, "ok")

    monkeypatch.setattr(
        commands,
        "copy_path",
        lambda path: calls.append(("copy", path)) or result,
    )
    monkeypatch.setattr(
        commands,
        "reveal_file",
        lambda path: calls.append(("reveal", path)) or result,
    )

    assert commands.copy_path_action("asset/path/hero.tx") is result
    assert commands.reveal_file_action("asset/path/hero.tx") is result
    assert calls == [("copy", "asset/path/hero.tx"), ("reveal", "asset/path/hero.tx")]
