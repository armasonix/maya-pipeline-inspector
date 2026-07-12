"""Open documentation URLs from the Maya panel header."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from shader_health.ui.qt import load_qt_gui

DEFAULT_DOCUMENTATION_URL = "https://github.com/armasonix/maya-shader-health-inspector/wiki"

def normalize_documentation_url(url: str) -> str:
    """Return a non-empty documentation URL, falling back to the packaged default."""

    text = str(url or "").strip()
    return text or DEFAULT_DOCUMENTATION_URL

def is_valid_http_url(url: str) -> bool:
    """Return whether ``url`` is an absolute HTTP or HTTPS URL."""

    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

def open_documentation_url(url: str, *, qt_gui: Any | None = None) -> bool:
    """Open ``url`` in the system browser via ``QDesktopServices``."""

    target = normalize_documentation_url(url)
    if not is_valid_http_url(target):
        return False

    gui = qt_gui or load_qt_gui()
    qurl_cls = getattr(gui, "QUrl", None)
    desktop_services = getattr(gui, "QDesktopServices", None)
    open_url = getattr(desktop_services, "openUrl", None) if desktop_services else None
    if qurl_cls is None or open_url is None:
        return False
    return bool(open_url(qurl_cls(target)))
