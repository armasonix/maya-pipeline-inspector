"""Maya integration layer.

Modules under this package must keep Maya imports lazy so the pure Python core
and public CI can run without Autodesk Maya installed.
"""
from __future__ import annotations

from typing import Any

__all__ = [
    "MayaUnavailableError",
    "ScanOptions",
    "scan_scene",
    "scan_selection",
]


def __getattr__(name: str) -> Any:
    """Load scanner exports lazily.

    Importing shader_health.maya must stay lightweight because Maya UI commands
    are imported from this package before the scanner/core compatibility layer is
    needed.
    """

    if name in __all__:
        from shader_health.maya import scanner

        return getattr(scanner, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
