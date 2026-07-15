"""Load and apply packaged Qt stylesheets for the Maya panel."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pipeline_inspector.ui.main_window import PANEL_OBJECT_NAME
from pipeline_inspector.user_config import SUPPORTED_USER_THEMES

THEMES_DIR = Path(__file__).resolve().parent / "themes"
DEFAULT_THEME = "classic"


def normalize_theme(theme: str) -> str:
    """Return a supported theme id, falling back to classic."""

    normalized = str(theme or DEFAULT_THEME).strip().lower()
    if normalized in SUPPORTED_USER_THEMES:
        return normalized
    return DEFAULT_THEME


def theme_stylesheet_path(theme: str) -> Path:
    """Return the packaged QSS path for a theme id."""

    return THEMES_DIR / f"{normalize_theme(theme)}.qss"


@lru_cache(maxsize=len(SUPPORTED_USER_THEMES))
def load_theme_stylesheet(theme: str) -> str:
    """Load a theme stylesheet from disk."""

    path = theme_stylesheet_path(theme)
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _widget_object_name(widget: Any) -> str:
    object_name_fn = getattr(widget, "objectName", None)
    if object_name_fn is None:
        return ""
    return str(object_name_fn())


def _theme_root_widget(content: Any) -> Any:
    current = content
    while current is not None:
        if _widget_object_name(current) == PANEL_OBJECT_NAME:
            return current
        parent_fn = getattr(current, "parent", None)
        if parent_fn is None:
            break
        current = parent_fn()
    return content


def _apply_stylesheet(widget: Any, stylesheet: str) -> None:
    if not stylesheet:
        return
    set_style = getattr(widget, "setStyleSheet", None)
    if set_style is not None:
        set_style(stylesheet)
    set_auto_fill = getattr(widget, "setAutoFillBackground", None)
    if set_auto_fill is not None:
        set_auto_fill(True)
    attribute_fn = getattr(widget, "setAttribute", None)
    if attribute_fn is None:
        return
    try:
        from pipeline_inspector.ui.qt import load_qt_core

        qt_core = load_qt_core()
    except RuntimeError:
        return
    styled_background = getattr(qt_core, "WA_StyledBackground", None)
    if styled_background is not None:
        attribute_fn(styled_background, True)


def _apply_palette_theme(widget: Any, theme: str) -> None:
    """Apply a native Qt palette fallback when Maya ignores QSS."""

    try:
        from pipeline_inspector.ui.qt import load_qt_gui

        qt_gui = load_qt_gui()
    except RuntimeError:
        return

    QColor = getattr(qt_gui, "QColor", None)
    QPalette = getattr(qt_gui, "QPalette", None)
    palette_fn = getattr(widget, "palette", None)
    set_palette = getattr(widget, "setPalette", None)
    if QColor is None or QPalette is None or palette_fn is None or set_palette is None:
        return

    palette = palette_fn()
    if normalize_theme(theme) == "dark":
        window = QColor("#2b2b2b")
        base = QColor("#1f1f1f")
        button = QColor("#3a3a3a")
        text = QColor("#e6e6e6")
    else:
        window = QColor("#535353")
        base = QColor("#454545")
        button = QColor("#606060")
        text = QColor("#cccccc")

    palette.setColor(QPalette.Window, window)
    palette.setColor(QPalette.Base, base)
    palette.setColor(QPalette.Button, button)
    palette.setColor(QPalette.WindowText, text)
    palette.setColor(QPalette.ButtonText, text)
    palette.setColor(QPalette.Text, text)
    set_palette(palette)


def _widget_children(widget: Any) -> list[Any]:
    children_attr = getattr(widget, "children", None)
    if children_attr is None:
        return []
    if callable(children_attr):
        try:
            return list(children_attr() or [])
        except TypeError:
            return []
    if isinstance(children_attr, list):
        return children_attr
    return []


def _safe_widget_call(fn: Any) -> None:
    if not callable(fn):
        return
    try:
        fn()
    except (RuntimeError, TypeError):
        pass


def _repolish_widget_tree(root: Any) -> None:
    """Force Qt to re-apply stylesheets inside Maya dock widgets."""

    style_fn = getattr(root, "style", None)
    unpolish = polish = None
    if style_fn is not None:
        style = style_fn()
        unpolish = getattr(style, "unpolish", None)
        polish = getattr(style, "polish", None)

    stack = [root]
    seen: set[int] = set()
    while stack:
        widget = stack.pop()
        widget_id = id(widget)
        if widget_id in seen:
            continue
        seen.add(widget_id)
        if unpolish is not None and polish is not None:
            try:
                unpolish(widget)
                polish(widget)
            except Exception:
                pass
        update_fn = getattr(widget, "update", None)
        _safe_widget_call(update_fn)
        stack.extend(_widget_children(widget))


def apply_panel_theme(content: Any, theme: str, *, dock: Any | None = None) -> str:
    """Apply a theme stylesheet to the dock panel root and content."""

    normalized = normalize_theme(theme)
    stylesheet = load_theme_stylesheet(normalized)
    root = dock if dock is not None else _theme_root_widget(content)
    _apply_stylesheet(root, stylesheet)
    _apply_palette_theme(root, normalized)
    if root is not content:
        _apply_stylesheet(content, stylesheet)
        _apply_palette_theme(content, normalized)
    for widget in (root, content):
        _repolish_widget_tree(widget)
        _safe_widget_call(getattr(widget, "update", None))
        _safe_widget_call(getattr(widget, "repaint", None))
    content._pipeline_inspector_theme = normalized
    return normalized
