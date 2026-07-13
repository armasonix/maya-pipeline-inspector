"""Cross-shell path helpers for CLI commands and verification scripts."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional

from pipeline_inspector.studio_config import StudioEnvironmentSettings

_STUDIO_VARIABLE_PATTERN = re.compile(r"\$\{([^}]+)\}")
_BUILTIN_STUDIO_VARIABLES = (
    "STUDIO_TEXTURE_ROOT",
    "STUDIO_ASSET_ROOT",
    "STUDIO_CACHE_ROOT",
    "STUDIO_RENDER_ROOT",
)
_STUDIO_ROOT_TOKEN_PAIRS = (
    ("texture_root", "${STUDIO_TEXTURE_ROOT}"),
    ("asset_root", "${STUDIO_ASSET_ROOT}"),
    ("cache_root", "${STUDIO_CACHE_ROOT}"),
    ("render_root", "${STUDIO_RENDER_ROOT}"),
)
_LEGACY_TO_STUDIO_REPLACE_TO = {
    "${ASSET_ROOT}": "${STUDIO_ASSET_ROOT}",
    "$ASSET_ROOT": "${STUDIO_ASSET_ROOT}",
    "${TEXTURE_ROOT}": "${STUDIO_TEXTURE_ROOT}",
    "$TEXTURE_ROOT": "${STUDIO_TEXTURE_ROOT}",
}
_STUDIO_REPLACE_TO_ROOT_ATTR = {
    "${STUDIO_ASSET_ROOT}": "asset_root",
    "${STUDIO_TEXTURE_ROOT}": "texture_root",
}

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

def studio_environment_is_configured(environment: StudioEnvironmentSettings) -> bool:
    """Return whether any studio path roots or aliases are configured."""

    for field_name, _token in _STUDIO_ROOT_TOKEN_PAIRS:
        if str(getattr(environment, field_name, "") or "").strip():
            return True
    return bool(environment.variable_aliases)

def normalize_path_to_studio_tokens(
    path: str,
    environment: StudioEnvironmentSettings,
) -> Optional[str]:
    """Map absolute paths under configured studio roots to ``${STUDIO_*_ROOT}`` tokens."""

    for field_name, token in _STUDIO_ROOT_TOKEN_PAIRS:
        root = str(getattr(environment, field_name, "") or "").strip()
        if not root:
            continue
        normalized = replace_path_prefix(path, root, token)
        if normalized is not None:
            return normalized
    return None

def effective_studio_normalize_target(
    replace_to: str,
    environment: StudioEnvironmentSettings | None,
) -> str:
    """Prefer studio tokens for legacy ``${ASSET_ROOT}`` / ``${TEXTURE_ROOT}`` targets."""

    normalized = str(replace_to or "").strip()
    if not normalized or environment is None:
        return normalized
    studio_token = _LEGACY_TO_STUDIO_REPLACE_TO.get(normalized)
    if studio_token is None:
        return normalized
    root_attr = _STUDIO_REPLACE_TO_ROOT_ATTR.get(studio_token)
    if root_attr is None:
        return normalized
    if str(getattr(environment, root_attr, "") or "").strip():
        return studio_token
    return normalized

def studio_normalize_prefixes(
    environment: StudioEnvironmentSettings,
) -> tuple[tuple[str, str], ...]:
    """Return configured studio roots paired with their normalize tokens."""

    prefixes: list[tuple[str, str]] = []
    for field_name, token in _STUDIO_ROOT_TOKEN_PAIRS:
        root = str(getattr(environment, field_name, "") or "").strip()
        if root:
            prefixes.append((root, token))
    return tuple(prefixes)

def replace_path_prefix(path: str, old_prefix: str, new_prefix: str) -> Optional[str]:
    """Replace a path prefix, preserving the remainder of the path."""

    path_norm = path.replace("\\", "/")
    old_norm = old_prefix.replace("\\", "/").rstrip("/")
    new_norm = new_prefix.replace("\\", "/").rstrip("/")
    if not path_norm or not old_norm or not new_norm:
        return None

    if path_norm.lower() == old_norm.lower():
        return new_norm

    old_with_sep = f"{old_norm}/"
    if path_norm.lower().startswith(old_with_sep.lower()):
        suffix = path_norm[len(old_norm) :]
        return new_norm + suffix
    return None

def builtin_studio_variable_names() -> tuple[str, ...]:
    """Return the built-in studio environment variable names."""

    return _BUILTIN_STUDIO_VARIABLES
