"""Default readiness probe implementations for filesystem and environment checks."""
from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Protocol


class ReadinessProbes(Protocol):
    """Injectable probes used by the readiness engine."""

    def loaded_maya_plugins(self) -> frozenset[str]:
        """Return normalized Maya plugin names that are currently loaded."""

    def maya_version(self) -> str:
        """Return the active Maya version string when available."""

    def env_var_value(self, name: str) -> str | None:
        """Return an environment variable value or None when unset."""

    def path_exists(self, path: str) -> bool:
        """Return True when a filesystem or UNC path is reachable."""

    def drive_mapped(self, drive: str) -> bool:
        """Return True when a drive letter is mapped or present."""

    def software_version(self, product: str) -> str | None:
        """Return a detected version string for a named product."""


def normalize_drive_letter(drive: str) -> str:
    """Normalize a drive specifier to an upper-case letter."""

    text = str(drive or "").strip().rstrip(":\\/")
    if not text:
        return ""
    return text[0].upper()


def normalize_plugin_name(plugin_name: str) -> str:
    """Normalize Maya plugin identifiers for comparisons."""

    return str(plugin_name or "").strip().casefold()


class OsReadinessProbes:
    """Filesystem and environment probes that do not require Maya."""

    def loaded_maya_plugins(self) -> frozenset[str]:
        return frozenset()

    def maya_version(self) -> str:
        return ""

    def env_var_value(self, name: str) -> str | None:
        value = os.environ.get(str(name or "").strip())
        if value is None:
            return None
        text = value.strip()
        return text or None

    def path_exists(self, path: str) -> bool:
        text = str(path or "").strip()
        if not text:
            return False
        try:
            return Path(text).exists()
        except OSError:
            return False

    def drive_mapped(self, drive: str) -> bool:
        letter = normalize_drive_letter(drive)
        if not letter:
            return False
        if platform.system().casefold() != "windows":
            return self.path_exists(f"/mnt/{letter.lower()}")
        return self.path_exists(f"{letter}:\\")

    def software_version(self, product: str) -> str | None:
        return None
