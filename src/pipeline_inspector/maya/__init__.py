"""Maya integration layer.

Modules under this package must keep Maya imports lazy so the pure Python core
and public CI can run without Autodesk Maya installed.
"""
from __future__ import annotations

from typing import Any

__all__ = [
    "AppliedFixRecord",
    "ApplyFixReport",
    "MayaUnavailableError",
    "ScanOptions",
    "apply_fix_actions",
    "scan_scene",
    "scan_selection",
]

def __getattr__(name: str) -> Any:
    """Load Maya-layer exports lazily.

    Importing pipeline_inspector.maya must stay lightweight because Maya UI commands
    are imported from this package before scanner, applier, or core compatibility
    layers are needed.
    """

    if name in {"MayaUnavailableError", "ScanOptions", "scan_scene", "scan_selection"}:
        from pipeline_inspector.maya import scanner

        return getattr(scanner, name)
    if name in {"AppliedFixRecord", "ApplyFixReport", "apply_fix_actions"}:
        from pipeline_inspector.maya import fix_applier

        return getattr(fix_applier, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
