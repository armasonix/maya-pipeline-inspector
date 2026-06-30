"""Maya integration layer.

Modules under this package must keep Maya imports lazy so the pure Python core
and public CI can run without Autodesk Maya installed.
"""

from shader_health.maya.scanner import (
    MayaUnavailableError,
    ScanOptions,
    scan_scene,
    scan_selection,
)

__all__ = [
    "MayaUnavailableError",
    "ScanOptions",
    "scan_scene",
    "scan_selection",
]
