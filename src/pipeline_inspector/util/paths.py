"""Cross-shell path helpers for CLI commands and verification scripts."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Optional

from pipeline_inspector.studio_config import StudioEnvironmentSettings

_STUDIO_VARIABLE_PATTERN = re.compile("\\$\\{([^}]+)\\}")
_UDIM_TILE_IN_NAME_RE = re.compile("(?<!\\d)(1\\d{3}|2\\d{3})(?!\\d)")
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
    if len(raw) >= 3 and raw[0] == "/" and (raw[2] == "/"):
        drive = raw[1].upper()
        rest = raw[3:].replace("/", "\\")
        normalized = Path(f"{drive}:\\{rest}")
        return normalized
    return resolved


def resolve_cli_path(path: str | Path) -> str:
    """Return a filesystem path string safe for ``open()`` in Windows Python."""
    return str(normalize_cli_path(path))


def sanitize_studio_path_value(value: str) -> str:
    """Strip trailing punctuation accidentally copied from UI text fields."""
    text = str(value or "").strip()
    while text and text[-1] in ",;":
        text = text[:-1].rstrip()
    return text


def studio_variable_aliases(environment: StudioEnvironmentSettings) -> dict[str, str]:
    """Build the substitution map for studio environment path tokens."""
    aliases = {
        "STUDIO_TEXTURE_ROOT": sanitize_studio_path_value(environment.texture_root),
        "STUDIO_ASSET_ROOT": sanitize_studio_path_value(environment.asset_root),
        "STUDIO_CACHE_ROOT": sanitize_studio_path_value(environment.cache_root),
        "STUDIO_RENDER_ROOT": sanitize_studio_path_value(environment.render_root),
    }
    for name, value in environment.variable_aliases.items():
        normalized_name = str(name).strip()
        if normalized_name:
            aliases[normalized_name] = sanitize_studio_path_value(str(value or ""))
    return aliases


def resolve_studio_path(
    path: str, environment: StudioEnvironmentSettings, *, max_passes: int = 4
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
    return resolved.replace("textures,/", "textures/").replace("textures,\\", "textures\\")


def studio_environment_is_configured(environment: StudioEnvironmentSettings) -> bool:
    """Return whether any studio path roots or aliases are configured."""
    for field_name, _token in _STUDIO_ROOT_TOKEN_PAIRS:
        if str(getattr(environment, field_name, "") or "").strip():
            return True
    return bool(environment.variable_aliases)


def normalize_path_to_studio_tokens(
    path: str, environment: StudioEnvironmentSettings
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
    replace_to: str, environment: StudioEnvironmentSettings | None
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


def is_local_drive_path(path: str) -> bool:
    """Return whether ``path`` looks like a Windows drive-letter absolute path."""
    normalized = str(path or "").replace("\\", "/").strip()
    return len(normalized) >= 3 and normalized[1] == ":" and (normalized[2] == "/")


def normalize_udim_tile_token_in_path(path: str) -> str:
    """Replace a concrete UDIM tile suffix in a filename with ``<UDIM>``."""
    raw = str(path or "").strip().replace("\\", "/")
    if not raw or "<UDIM>" in raw or "<udim>" in raw:
        return raw
    if "/" in raw:
        directory, name = raw.rsplit("/", 1)
    else:
        directory, name = ("", raw)
    matches = list(_UDIM_TILE_IN_NAME_RE.finditer(name))
    if not matches:
        return raw
    match = matches[-1]
    new_name = name[: match.start()] + "<UDIM>" + name[match.end() :]
    return f"{directory}/{new_name}" if directory else new_name


def resolve_authored_absolute_path(
    planned_path: str,
    *,
    studio_environment: StudioEnvironmentSettings | None = None,
    fallback_absolute: str = "",
) -> str:
    """Expand studio tokens to an absolute path suitable for USD relpath authoring."""
    raw = str(planned_path or "").strip()
    if not raw:
        return ""
    expanded = raw
    if studio_environment is not None:
        expanded = resolve_studio_path(raw, studio_environment) or raw
    if "${" not in expanded:
        return expanded.replace("\\", "/")
    fallback = str(fallback_absolute or "").strip().replace("\\", "/")
    if fallback and "${" not in fallback:
        filename = Path(raw.replace("\\", "/").rstrip("/").split("/")[-1]).name
        if filename:
            return str((Path(fallback).parent / filename).resolve()).replace("\\", "/")
    return ""


def author_usd_asset_path(
    path: str,
    *,
    anchor_dir: Path,
    studio_environment: StudioEnvironmentSettings | None = None,
    fallback_absolute: str = "",
) -> str:
    """Return a USD layer path that resolves locally and avoids farm-local drives."""
    raw = str(path or "").strip()
    if not raw:
        return raw
    raw_norm = raw.replace("\\", "/")
    if (
        not is_local_drive_path(raw_norm)
        and "${" not in raw_norm
        and (not raw_norm.startswith("$"))
        and (not raw_norm.startswith("//"))
    ):
        return raw_norm.lstrip("/")
    if raw_norm.startswith("$") and "${" not in raw_norm and (not is_local_drive_path(raw_norm)):
        return raw_norm
    absolute = resolve_authored_absolute_path(
        raw, studio_environment=studio_environment, fallback_absolute=fallback_absolute
    )
    if not absolute or "${" in absolute:
        absolute = (
            resolve_authored_absolute_path(
                fallback_absolute,
                studio_environment=studio_environment,
                fallback_absolute=fallback_absolute,
            )
            or ""
        )
    if not absolute or "${" in absolute:
        if "${" in raw_norm:
            return raw_norm
        absolute = raw_norm
    candidate = Path(str(absolute).replace("\\", "/"))
    if not candidate.is_absolute():
        candidate = (anchor_dir / candidate).resolve()
    try:
        relative = os.path.relpath(candidate, anchor_dir.resolve())
    except ValueError:
        relative = candidate.name
    else:
        relative = relative.replace("\\", "/")
    if relative and (not is_local_drive_path(relative)) and ("${" not in relative):
        return relative
    return candidate.name


def author_maya_texture_path(
    path: str,
    *,
    scene_path: str = "",
    studio_environment: StudioEnvironmentSettings | None = None,
    fallback_absolute: str = "",
) -> str:
    """Return a Maya texture path that renderers can resolve immediately."""
    raw = str(path or "").strip()
    if not raw:
        return raw
    absolute = resolve_authored_absolute_path(
        raw, studio_environment=studio_environment, fallback_absolute=fallback_absolute
    )
    if not absolute or "$" in absolute:
        fallback = str(fallback_absolute or "").strip().replace("\\", "/")
        if fallback and "$" not in fallback:
            filename = Path(raw.replace("\\", "/").rstrip("/").split("/")[-1]).name
            if filename:
                absolute = str((Path(fallback).parent / filename).resolve()).replace("\\", "/")
    if not absolute:
        return raw.replace("\\", "/")
    absolute_path = Path(absolute.replace("\\", "/"))
    scene_parent = Path(scene_path).parent if scene_path else None
    if scene_parent is not None and scene_parent.is_dir() and absolute_path.is_absolute():
        try:
            relative = os.path.relpath(absolute_path, scene_parent.resolve()).replace("\\", "/")
            if (
                relative
                and (not relative.startswith("../"))
                and (not is_local_drive_path(relative))
                and ("$" not in relative)
            ):
                return relative
        except ValueError:
            pass
    return str(absolute_path).replace("\\", "/")


def replace_path_prefix(path: str, old_prefix: str, new_prefix: str) -> Optional[str]:
    """Replace a path prefix, preserving the remainder of the path."""
    path_norm = path.replace("\\", "/")
    old_norm = old_prefix.replace("\\", "/").rstrip("/")
    new_norm = new_prefix.replace("\\", "/").rstrip("/")
    if not path_norm or not old_norm or (not new_norm):
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


def sync_studio_environment_to_os(environment: StudioEnvironmentSettings | None) -> None:
    """Publish configured studio roots to process env vars for DCC path resolution."""
    if environment is None:
        return
    import os

    for env_name, value in studio_variable_aliases(environment).items():
        normalized = sanitize_studio_path_value(value)
        if normalized:
            os.environ[env_name] = normalized.replace("\\", "/")
    for name, value in environment.variable_aliases.items():
        env_name = str(name).strip()
        env_value = sanitize_studio_path_value(str(value or ""))
        if env_name and env_value:
            os.environ[env_name] = env_value.replace("\\", "/")


def author_maya_texture_path_for_fix(
    planned_path: str,
    *,
    scene_path: str = "",
    studio_environment: StudioEnvironmentSettings | None = None,
    fallback_absolute: str = "",
) -> str:
    """Return a Maya texture path that satisfies path-policy fixes and resolves locally."""
    raw = str(planned_path or "").strip()
    if not raw:
        return raw
    if "${" in raw or raw.startswith("$"):
        return raw.replace("\\", "/")
    if studio_environment is not None:
        tokenized = normalize_path_to_studio_tokens(raw, studio_environment)
        if tokenized is not None:
            return tokenized.replace("\\", "/")
    return author_maya_texture_path(
        raw,
        scene_path=scene_path,
        studio_environment=studio_environment,
        fallback_absolute=fallback_absolute,
    )


def path_under_studio_roots(path: str, environment: StudioEnvironmentSettings) -> bool:
    """Return whether ``path`` resolves under a configured studio root."""
    candidates: list[str] = []
    for candidate in (path, resolve_studio_path(path, environment) or ""):
        normalized = str(candidate or "").replace("\\", "/").strip().lower().rstrip("/")
        if normalized:
            candidates.append(normalized)
    for root, _token in studio_normalize_prefixes(environment):
        root_norm = str(root or "").replace("\\", "/").strip().lower().rstrip("/")
        if not root_norm:
            continue
        for candidate in candidates:
            if candidate == root_norm or candidate.startswith(f"{root_norm}/"):
                return True
    return False


def is_render_safe_studio_texture_path(
    raw_path: str, resolved_path: str, environment: StudioEnvironmentSettings
) -> bool:
    """Return whether a Maya texture path is an absolute/relative path under studio roots."""
    raw = str(raw_path or "").strip()
    if not raw or "\\" in raw or "${" in raw or raw.startswith("$"):
        return False
    raw_norm = raw.replace("\\", "/")
    resolved_norm = str(resolved_path or raw).replace("\\", "/").strip()
    if raw_norm.startswith("//") or resolved_norm.startswith("//"):
        return False
    if not path_under_studio_roots(resolved_norm, environment):
        return False
    if raw_norm.startswith("../") or raw_norm.startswith("./"):
        return True
    if "/../" in f"/{raw_norm.lstrip('/')}/":
        return False
    if is_local_drive_path(raw_norm):
        return path_under_studio_roots(raw_norm, environment)
    return bool(raw_norm) and path_under_studio_roots(raw_norm, environment)


def is_farm_token_texture_path(
    raw_path: str, allowed_prefixes: list[str] | tuple[str, ...]
) -> bool:
    """Return whether ``raw_path`` is a forward-slash studio token path for farm handoff."""
    raw = str(raw_path or "").strip()
    if not raw or "\\" in raw or "$" not in raw:
        return False
    raw_norm = raw.replace("\\", "/")
    normalized_prefixes = [
        str(prefix).replace("\\", "/").strip().rstrip("/").lower()
        for prefix in allowed_prefixes
        if str(prefix).strip()
    ]
    path_norm = raw_norm.strip().rstrip("/").lower()
    return any(
        path_norm == prefix or path_norm.startswith(f"{prefix}/") for prefix in normalized_prefixes
    )


def texture_path_policy_compliant(
    raw_path: str,
    resolved_path: str,
    allowed_prefixes: list[str] | tuple[str, ...],
    environment: StudioEnvironmentSettings | None,
) -> bool:
    """Return whether a texture path satisfies project-root policy for the active context."""
    configured = environment is not None and studio_environment_is_configured(environment)
    render_safe = bool(
        environment is not None
        and is_render_safe_studio_texture_path(raw_path, resolved_path, environment)
    )
    farm_token = is_farm_token_texture_path(raw_path, allowed_prefixes)
    raw_norm = str(raw_path or "").replace("\\", "/")
    if configured:
        if is_local_drive_path(raw_norm):
            compliant = False
        elif farm_token:
            compliant = True
        else:
            compliant = render_safe
    elif farm_token or render_safe:
        compliant = True
    else:
        compliant = False
    return compliant
