"""Load optional bug report screenshot attachments as JPEG bytes."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pipeline_inspector.integrations.bug_report.relay_client import is_jpeg_bytes

_SCREENSHOT_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def read_image_file_as_jpeg(path: str, *, qt_widgets: Any | None = None) -> bytes | None:
    """Return JPEG bytes for an image file, converting when needed."""

    normalized = str(path or "").strip()
    if not normalized:
        return None

    image_path = Path(normalized)
    if not image_path.is_file():
        return None
    if image_path.suffix.lower() not in _SCREENSHOT_SUFFIXES:
        return None

    raw = image_path.read_bytes()
    if is_jpeg_bytes(raw):
        return raw

    if qt_widgets is None:
        from pipeline_inspector.ui.qt import load_qt_widgets

        qt_widgets = load_qt_widgets()

    image_cls = getattr(qt_widgets, "QImage", None)
    buffer_cls = getattr(qt_widgets, "QBuffer", None)
    io_device = getattr(qt_widgets, "QIODevice", None)
    if image_cls is None or buffer_cls is None or io_device is None:
        return None

    image = image_cls(str(image_path))
    is_null = getattr(image, "isNull", None)
    if is_null is not None and is_null():
        return None

    write_only = getattr(getattr(io_device, "WriteOnly", None), "value", None)
    if write_only is None:
        write_only = getattr(io_device, "WriteOnly", None)
    if write_only is None:
        return None

    buffer = buffer_cls()
    open_buffer = getattr(buffer, "open", None)
    if open_buffer is None or not open_buffer(write_only):
        return None

    save = getattr(image, "save", None)
    if save is None or not save(buffer, "JPG", 85):
        return None

    data_fn = getattr(buffer, "data", None)
    if data_fn is None:
        return None
    converted = data_fn()
    if converted is None:
        return None
    return bytes(converted)
