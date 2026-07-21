"""Open documentation URLs from the Maya panel header."""
from __future__ import annotations

import webbrowser
from typing import Any
from urllib.parse import urlparse

from pipeline_inspector.ui.qt import load_qt_gui

DEFAULT_DOCUMENTATION_URL = "https://github.com/armasonix/maya-pipeline-inspector/wiki/Home"


def normalize_documentation_url(url: str) -> str:
    """Return a non-empty documentation URL, falling back to the packaged default."""

    text = str(url or "").strip()
    return text or DEFAULT_DOCUMENTATION_URL


def is_valid_http_url(url: str) -> bool:
    """Return whether ``url`` is an absolute HTTP or HTTPS URL."""

    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def resolve_documentation_url(
    *,
    user_docs_url: str = "",
    studio_documentation_url: str = "",
) -> str:
    """Pick the first valid HTTP(S) docs URL: user override, studio policy, default."""

    for candidate in (user_docs_url, studio_documentation_url):
        text = str(candidate or "").strip()
        if text and is_valid_http_url(text):
            return text
    return DEFAULT_DOCUMENTATION_URL


def _open_with_qt_desktop_services(target: str, qt_gui: Any | None) -> bool:
    try:
        gui = qt_gui or load_qt_gui()
    except RuntimeError:
        return False

    qurl_cls = getattr(gui, "QUrl", None)
    desktop_services = getattr(gui, "QDesktopServices", None)
    open_url = getattr(desktop_services, "openUrl", None) if desktop_services else None
    if qurl_cls is None or open_url is None:
        return False
    return bool(open_url(qurl_cls(target)))


def _open_with_webbrowser(target: str) -> bool:
    try:
        return bool(webbrowser.open(target, new=2))
    except OSError:
        return False


def open_documentation_url(url: str, *, qt_gui: Any | None = None) -> bool:
    """Open ``url`` in the system browser."""

    target = normalize_documentation_url(url)
    if not is_valid_http_url(target):
        return False

    if _open_with_qt_desktop_services(target, qt_gui):
        return True
    return _open_with_webbrowser(target)
