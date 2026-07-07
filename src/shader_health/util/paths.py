"""Cross-shell path helpers for CLI commands and verification scripts."""
from __future__ import annotations

import sys
from pathlib import Path


def normalize_cli_path(path: str | Path) -> Path:
    """Convert Git Bash MSYS paths (/d/foo) to Windows paths on win32."""

    resolved = Path(path)
    raw = resolved.as_posix()
    if sys.platform != "win32":
        return resolved
    if len(raw) >= 2 and raw[1] == ":":
        return resolved
    if len(raw) >= 3 and raw[0] == "/" and raw[2] == "/":
        drive = raw[1].upper()
        rest = raw[3:].replace("/", "\\")
        normalized = Path(f"{drive}:\\{rest}")
        return normalized
    return resolved


def resolve_cli_path(path: str | Path) -> str:
    """Return a filesystem path string safe for ``open()`` in Windows Python."""

    return str(normalize_cli_path(path))
