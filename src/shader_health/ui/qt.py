"""Qt binding discovery for Maya UI modules."""
from __future__ import annotations

import importlib
from typing import Any

QT_WIDGETS_CANDIDATES = (
    "PySide6.QtWidgets",
    "PySide2.QtWidgets",
)

QT_CORE_CANDIDATES = (
    "PySide6.QtCore",
    "PySide2.QtCore",
)

QT_GUI_CANDIDATES = (
    "PySide6.QtGui",
    "PySide2.QtGui",
)

def load_qt_widgets() -> Any:
    """Return Maya's available QtWidgets module.

    The project does not depend on Qt in public CI. Qt is imported lazily so pure
    Python tests can import UI launcher modules outside Maya.
    """

    errors: list[str] = []
    for module_name in QT_WIDGETS_CANDIDATES:
        try:
            return importlib.import_module(module_name)
        except ImportError as exc:
            errors.append(f"{module_name}: {exc}")
    joined_errors = "; ".join(errors)
    raise RuntimeError(f"No supported Qt binding found for Maya UI: {joined_errors}")

def load_qt_core() -> Any:
    """Return Maya's available QtCore module."""

    errors: list[str] = []
    for module_name in QT_CORE_CANDIDATES:
        try:
            return importlib.import_module(module_name)
        except ImportError as exc:
            errors.append(f"{module_name}: {exc}")
    joined_errors = "; ".join(errors)
    raise RuntimeError(f"No supported QtCore binding found for Maya UI: {joined_errors}")

def load_qt_gui() -> Any:
    """Return Maya's available QtGui module."""

    errors: list[str] = []
    for module_name in QT_GUI_CANDIDATES:
        try:
            return importlib.import_module(module_name)
        except ImportError as exc:
            errors.append(f"{module_name}: {exc}")
    joined_errors = "; ".join(errors)
    raise RuntimeError(f"No supported QtGui binding found for Maya UI: {joined_errors}")
