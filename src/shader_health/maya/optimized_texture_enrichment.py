"""Optimized texture (.tx) path detection and freshness enrichment."""
from __future__ import annotations

import glob
import re
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from shader_health.core import FileDependencySnapshot

_OPTIMIZABLE_EXTENSIONS = frozenset(
    {
        ".exr",
        ".tiff",
        ".tif",
        ".png",
        ".jpg",
        ".jpeg",
        ".dds",
        ".bmp",
    }
)
_UDIM_TILE_RE = re.compile(r"(?<!\d)(1\d{3}|2\d{3})(?!\d)")


def enrich_optimized_texture_metadata(
    dependency: FileDependencySnapshot,
) -> FileDependencySnapshot:
    """Attach .tx / UDIM-tx derivative metadata for policy rules."""

    if not dependency.exists or not dependency.resolved_path:
        return dependency
    if dependency.extension and dependency.extension.lower() == ".tx":
        return dependency
    if not _is_optimizable_source(dependency):
        return dependency

    if dependency.is_udim:
        return _enrich_udim_tx_metadata(dependency)

    return _enrich_flat_tx_metadata(dependency)


def _is_optimizable_source(dependency: FileDependencySnapshot) -> bool:
    extension = (dependency.extension or Path(dependency.resolved_path or "").suffix).lower()
    return extension in _OPTIMIZABLE_EXTENSIONS


def _enrich_flat_tx_metadata(dependency: FileDependencySnapshot) -> FileDependencySnapshot:
    resolved = str(dependency.resolved_path).replace("\\", "/")
    candidates = _tx_candidates(resolved)
    optimized_path = _pick_existing_candidate(candidates) or candidates[0]
    optimized_exists = Path(optimized_path).is_file()
    optimized_mtime_utc = _file_mtime_utc(optimized_path) if optimized_exists else None
    source_mtime_utc = dependency.mtime_utc or _file_mtime_utc(resolved)
    optimized_is_stale = (
        _is_stale(source_mtime_utc, optimized_mtime_utc) if optimized_exists else None
    )

    return replace(
        dependency,
        optimized_kind="tx",
        optimized_path=optimized_path,
        optimized_exists=optimized_exists,
        optimized_mtime_utc=optimized_mtime_utc,
        optimized_is_stale=optimized_is_stale,
    )


def _enrich_udim_tx_metadata(dependency: FileDependencySnapshot) -> FileDependencySnapshot:
    resolved = str(dependency.resolved_path).replace("\\", "/")
    tx_pattern = _udim_swap_extension(resolved, ".tx")
    source_tiles = dependency.udim_tiles or _existing_udim_tiles(resolved)
    optimized_tiles: list[int] = []
    missing_tiles: list[int] = []
    stale = False

    for tile in source_tiles:
        tx_path = tx_pattern.replace("<UDIM>", f"{tile:04d}").replace("<udim>", f"{tile:04d}")
        if not Path(tx_path).is_file():
            missing_tiles.append(tile)
            continue
        optimized_tiles.append(tile)
        source_tile_path = (
            resolved.replace("<UDIM>", f"{tile:04d}").replace("<udim>", f"{tile:04d}")
        )
        source_mtime = _file_mtime_utc(source_tile_path)
        tx_mtime = _file_mtime_utc(tx_path)
        if _is_stale(source_mtime, tx_mtime):
            stale = True

    optimized_exists = bool(optimized_tiles) and not missing_tiles
    if missing_tiles:
        optimized_exists = False

    return replace(
        dependency,
        optimized_kind="udim_tx",
        optimized_path=tx_pattern,
        optimized_exists=optimized_exists,
        optimized_udim_tiles=optimized_tiles,
        optimized_missing_udim_tiles=missing_tiles,
        optimized_mtime_utc=None,
        optimized_is_stale=stale if optimized_tiles else None,
    )


def _tx_candidates(resolved_path: str) -> list[str]:
    path = Path(resolved_path.replace("\\", "/"))
    stem = path.stem
    parent = path.parent
    candidates = [
        str(parent / f"{stem}.tx"),
        str(parent / "tx" / f"{stem}.tx"),
    ]
    parts = path.parts
    if "textures" in parts:
        index = parts.index("textures")
        tx_dir = Path(*parts[: index + 1]) / "tx"
        candidates.append(str(tx_dir / f"{stem}.tx"))
    return candidates


def _pick_existing_candidate(candidates: list[str]) -> Optional[str]:
    for candidate in candidates:
        if "<UDIM>" in candidate or "<udim>" in candidate:
            if _udim_files(candidate):
                return candidate
            continue
        if Path(candidate).is_file():
            return candidate
    return None


def _udim_swap_extension(path: str, extension: str) -> str:
    normalized = path.replace("\\", "/")
    suffix = Path(normalized).suffix
    if not suffix:
        return normalized
    return normalized[: -len(suffix)] + extension


def _udim_glob_pattern(path: str) -> str:
    return path.replace("<UDIM>", "[0-9][0-9][0-9][0-9]").replace(
        "<udim>",
        "[0-9][0-9][0-9][0-9]",
    )


def _udim_files(path: str) -> list[Path]:
    return sorted(Path(item) for item in glob.glob(_udim_glob_pattern(path)))


def _existing_udim_tiles(path: str) -> list[int]:
    tiles: set[int] = set()
    for file_path in _udim_files(path):
        matches = _UDIM_TILE_RE.findall(file_path.name)
        if matches:
            tiles.add(int(matches[-1]))
    return sorted(tiles)


def _file_mtime_utc(path: str) -> Optional[str]:
    try:
        stat = Path(path).stat()
    except OSError:
        return None
    mtime = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
    return mtime.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _is_stale(source_mtime: Optional[str], optimized_mtime: Optional[str]) -> Optional[bool]:
    if source_mtime is None or optimized_mtime is None:
        return None
    source_ts = _parse_mtime(source_mtime)
    optimized_ts = _parse_mtime(optimized_mtime)
    if source_ts is None or optimized_ts is None:
        return None
    return source_ts > optimized_ts


def _parse_mtime(value: str) -> Optional[float]:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return None
