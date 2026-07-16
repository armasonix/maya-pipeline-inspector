"""Capture a JPEG screenshot of the Maya main window for bug reports."""
from __future__ import annotations

from typing import Any


def capture_maya_main_window_jpeg(*, qt_widgets: Any | None = None) -> bytes | None:
    """Return a JPEG screenshot of the Maya main window, or None when unavailable."""

    try:
        import maya.OpenMayaUI as omui
    except ImportError:
        return None

    if qt_widgets is None:
        from pipeline_inspector.ui.qt import load_qt_widgets

        qt_widgets = load_qt_widgets()

    main_window_ptr = omui.MQtUtil.mainWindow()
    if main_window_ptr is None:
        return None

    try:
        import shiboken2  # type: ignore[import-not-found]
    except ImportError:
        return None

    widget_cls = getattr(qt_widgets, "QWidget", None)
    if widget_cls is None:
        return None

    main_window = shiboken2.wrapInstance(int(main_window_ptr), widget_cls)
    grab = getattr(main_window, "grab", None)
    if grab is None:
        return None

    pixmap = grab()
    if pixmap is None:
        return None

    buffer_cls = getattr(qt_widgets, "QBuffer", None)
    io_device = getattr(qt_widgets, "QIODevice", None)
    if buffer_cls is None or io_device is None:
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

    save = getattr(pixmap, "save", None)
    if save is None or not save(buffer, "JPG", 85):
        return None

    data_fn = getattr(buffer, "data", None)
    if data_fn is None:
        return None
    raw = data_fn()
    if raw is None:
        return None
    return bytes(raw)
