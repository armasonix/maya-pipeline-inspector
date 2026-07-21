from __future__ import annotations

from pipeline_inspector.ui.documentation_actions import (
    DEFAULT_DOCUMENTATION_URL,
    is_valid_http_url,
    normalize_documentation_url,
    open_documentation_url,
    resolve_documentation_url,
)


class FakeQUrl:
    def __init__(self, url: str) -> None:
        self.url = url


class FakeQDesktopServices:
    opened: list[str] = []

    @classmethod
    def openUrl(cls, url: FakeQUrl) -> bool:
        cls.opened.append(url.url)
        return True


class FakeQtGui:
    QUrl = FakeQUrl
    QDesktopServices = FakeQDesktopServices


def setup_function() -> None:
    FakeQDesktopServices.opened.clear()


def test_normalize_documentation_url_uses_default_for_blank_values():
    assert normalize_documentation_url("") == DEFAULT_DOCUMENTATION_URL
    assert normalize_documentation_url("   ") == DEFAULT_DOCUMENTATION_URL


def test_is_valid_http_url_accepts_http_and_https_only():
    assert is_valid_http_url("https://github.com/armasonix/maya-pipeline-inspector/wiki")
    assert is_valid_http_url("http://localhost/docs")
    assert not is_valid_http_url("ftp://example.test/docs")
    assert not is_valid_http_url("not-a-url")


def test_open_documentation_url_uses_qdesktop_services():
    opened = open_documentation_url(
        "https://example.test/docs",
        qt_gui=FakeQtGui,
    )

    assert opened is True
    assert FakeQDesktopServices.opened == ["https://example.test/docs"]


def test_open_documentation_url_falls_back_to_default_when_blank():
    opened = open_documentation_url("", qt_gui=FakeQtGui)

    assert opened is True
    assert FakeQDesktopServices.opened == [DEFAULT_DOCUMENTATION_URL]


def test_open_documentation_url_rejects_invalid_urls():
    assert open_documentation_url("not-a-url", qt_gui=FakeQtGui) is False
    assert FakeQDesktopServices.opened == []


def test_resolve_documentation_url_prefers_user_then_studio_then_default():
    assert resolve_documentation_url(
        user_docs_url="https://user.test/docs",
        studio_documentation_url="https://studio.test/docs",
    ) == "https://user.test/docs"
    assert resolve_documentation_url(
        user_docs_url="not-a-url",
        studio_documentation_url="https://studio.test/docs",
    ) == "https://studio.test/docs"
    assert resolve_documentation_url(
        user_docs_url="",
        studio_documentation_url="",
    ) == DEFAULT_DOCUMENTATION_URL


def test_open_documentation_url_falls_back_to_webbrowser(monkeypatch):
    class BrokenQtGui:
        QUrl = FakeQUrl
        QDesktopServices = type(
            "BrokenDesktop",
            (),
            {"openUrl": classmethod(lambda cls, url: False)},
        )

    opened: list[str] = []

    def fake_open(url: str, new: int = 0) -> bool:
        opened.append(url)
        return True

    monkeypatch.setattr(
        "pipeline_inspector.ui.documentation_actions.webbrowser.open",
        fake_open,
    )

    assert open_documentation_url("https://example.test/docs", qt_gui=BrokenQtGui) is True
    assert opened == ["https://example.test/docs"]
    assert FakeQDesktopServices.opened == []
