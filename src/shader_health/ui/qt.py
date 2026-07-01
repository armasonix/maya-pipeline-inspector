"""Qt binding discovery for Maya UI modules."""
from __future__ import annotations

import importlib
from typing import Any

QT_WIDGETS_CANDIDATES = (
    "PySide6.QtWidgets",
    "PySide2.QtWidgets",
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
