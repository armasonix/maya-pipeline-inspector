"""Load and apply packaged Qt stylesheets for the Maya panel."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from shader_health.user_config import SUPPORTED_USER_THEMES

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


def apply_panel_theme(content: Any, theme: str) -> str:
    """Apply a theme stylesheet to the panel content root."""

    normalized = normalize_theme(theme)
    stylesheet = load_theme_stylesheet(normalized)
    set_style = getattr(content, "setStyleSheet", None)
    if set_style is not None:
        set_style(stylesheet)
    content._shader_health_theme = normalized
    return normalized
