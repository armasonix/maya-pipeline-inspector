"""Derive safe rename suggestions from studio naming regex templates."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from pipeline_inspector.core.naming_conventions import compile_naming_pattern

_KNOWN_STUDIO_PREFIXES: tuple[str, ...] = (
    "geo_",
    "grp_",
    "mat_",
    "ctrl_",
    "tex_",
    "SG_",
    "lgt_",
)
_REGEX_LITERAL_STOP = frozenset(r".+*?[](){}|^$\\")
_UDIM_TILE_IN_STEM_RE = re.compile(r"^(.*)\.(1\d{3}|2\d{3})$")
_UDIM_MARKER_RE = re.compile(r"(<UDIM>|<udim>)", re.IGNORECASE)


def propose_naming_fix(current_name: str, pattern: str) -> Optional[str]:
    """Return a short name that satisfies the naming regex, or None if unknown."""

    short_name = _short_dag_name(current_name)
    if not short_name or not str(pattern or "").strip():
        return None

    try:
        compiled = compile_naming_pattern(pattern)
    except re.error:
        return None

    if compiled.fullmatch(short_name):
        return None

    prefix = _extract_required_prefix(pattern)
    candidates: list[str] = []

    if prefix and short_name.startswith(prefix):
        candidates.append(prefix + _sanitize_body(short_name[len(prefix) :], pattern))

    if prefix:
        body = _strip_known_prefix(short_name)
        sanitized_body = _sanitize_body(body, pattern)
        if sanitized_body:
            candidates.append(prefix + sanitized_body)

    candidates.append(_sanitize_body(short_name, pattern))

    seen: set[str] = set()
    for candidate in candidates:
        normalized = _normalize_candidate(candidate)
        if not normalized or normalized in seen or normalized == short_name:
            continue
        seen.add(normalized)
        if compiled.fullmatch(normalized):
            return normalized
    return None


def texture_filename_stem(path: str) -> str:
    """Return the basename stem used when validating texture file naming."""

    normalized_name = Path(
        str(path or "")
        .replace("\\", "/")
        .replace("<UDIM>", "1001")
        .replace("<udim>", "1001")
    ).name
    stem = Path(normalized_name).stem
    tile_match = _UDIM_TILE_IN_STEM_RE.match(stem)
    if tile_match:
        return tile_match.group(1)
    return stem


def propose_texture_file_path_fix(file_path: str, pattern: str) -> Optional[str]:
    """Return a renamed texture path that satisfies the studio naming regex."""

    normalized = str(file_path or "").replace("\\", "/").strip()
    if not normalized:
        return None

    path = Path(normalized)
    current_stem = texture_filename_stem(normalized)
    proposed_stem = propose_naming_fix(current_stem, pattern)
    if not proposed_stem or proposed_stem == current_stem:
        return None

    filename = path.name
    if _UDIM_MARKER_RE.search(filename):
        marker_match = _UDIM_MARKER_RE.search(filename)
        assert marker_match is not None
        prefix = filename[: marker_match.start()]
        if not prefix.startswith(current_stem):
            return None
        new_filename = proposed_stem + filename[len(current_stem) :]
        return str(path.with_name(new_filename)).replace("\\", "/")

    tile_match = _UDIM_TILE_IN_STEM_RE.match(path.stem)
    if tile_match:
        base, tile = tile_match.groups()
        if base != current_stem:
            return None
        new_filename = f"{proposed_stem}.{tile}{path.suffix}"
        return str(path.with_name(new_filename)).replace("\\", "/")

    new_filename = f"{proposed_stem}{path.suffix}"
    if new_filename == filename:
        return None
    return str(path.with_name(new_filename)).replace("\\", "/")


def texture_tile_filename_from_paths(
    tile_filename: str,
    *,
    raw_before: str,
    raw_after: str,
) -> Optional[str]:
    """Map one UDIM tile filename to its renamed counterpart."""

    before_stem = texture_filename_stem(raw_before)
    after_stem = texture_filename_stem(raw_after)
    if not before_stem or not after_stem or before_stem == after_stem:
        return None

    tile_path = Path(tile_filename)
    tile_match = _UDIM_TILE_IN_STEM_RE.match(tile_path.stem)
    if tile_match is None:
        return None
    base, tile = tile_match.groups()
    if base != before_stem:
        return None
    return f"{after_stem}.{tile}{tile_path.suffix}"


def _short_dag_name(name: str) -> str:
    normalized = str(name or "").strip()
    if not normalized:
        return ""
    return normalized.split("|")[-1].split(":")[-1]


def _extract_required_prefix(pattern: str) -> str:
    if not pattern.startswith("^"):
        return ""
    prefix_chars: list[str] = []
    for char in pattern[1:]:
        if char in _REGEX_LITERAL_STOP:
            break
        prefix_chars.append(char)
    return "".join(prefix_chars)


def _strip_known_prefix(name: str) -> str:
    lowered = name.casefold()
    for prefix in _KNOWN_STUDIO_PREFIXES:
        if lowered.startswith(prefix.casefold()):
            return name[len(prefix) :]
    return name


def _sanitize_body(body: str, pattern: str) -> str:
    del pattern
    sanitized: list[str] = []
    for char in body:
        if char.isalnum() or char == "_":
            sanitized.append(char)
        else:
            sanitized.append("_")
    return _normalize_candidate("".join(sanitized))


def _normalize_candidate(name: str) -> str:
    collapsed = re.sub(r"_+", "_", name).strip("_")
    return collapsed
