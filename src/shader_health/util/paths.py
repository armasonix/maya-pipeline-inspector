"""Cross-shell path helpers for CLI commands and verification scripts."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from shader_health.studio_config import StudioEnvironmentSettings

_STUDIO_VARIABLE_PATTERN = re.compile(r"\$\{([^}]+)\}")
_BUILTIN_STUDIO_VARIABLES = (
    "STUDIO_TEXTURE_ROOT",
    "STUDIO_ASSET_ROOT",
    "STUDIO_CACHE_ROOT",
    "STUDIO_RENDER_ROOT",
)


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


def studio_variable_aliases(environment: StudioEnvironmentSettings) -> dict[str, str]:
    """Build the substitution map for studio environment path tokens."""

    aliases = {
        "STUDIO_TEXTURE_ROOT": environment.texture_root.strip(),
        "STUDIO_ASSET_ROOT": environment.asset_root.strip(),
        "STUDIO_CACHE_ROOT": environment.cache_root.strip(),
        "STUDIO_RENDER_ROOT": environment.render_root.strip(),
    }
    for name, value in environment.variable_aliases.items():
        normalized_name = str(name).strip()
        if normalized_name:
            aliases[normalized_name] = str(value or "")
    return aliases


def resolve_studio_path(
    path: str,
    environment: StudioEnvironmentSettings,
    *,
    max_passes: int = 4,
) -> str:
    """Expand ``${VAR}`` tokens using studio environment roots and aliases."""

    if not path:
        return ""
    aliases = studio_variable_aliases(environment)
    resolved = str(path)
    passes = max(1, max_passes)
    for _ in range(passes):
        changed = False

        def _replace(match: re.Match[str]) -> str:
            nonlocal changed
            key = match.group(1).strip()
            if key not in aliases:
                return match.group(0)
            changed = True
            return aliases[key]

        resolved = _STUDIO_VARIABLE_PATTERN.sub(_replace, resolved)
        if not changed:
            break
    return resolved


def builtin_studio_variable_names() -> tuple[str, ...]:
    """Return the built-in studio environment variable names."""

    return _BUILTIN_STUDIO_VARIABLES
