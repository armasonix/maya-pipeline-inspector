"""Organized scene-adjacent output paths for Pipeline Inspector exports."""

from __future__ import annotations

from pathlib import Path

REPORTS_DIR_NAME = "reports"
EXPORT_CATEGORIES: dict[str, str] = {
    "report": "validation",
    "manifest": "manifests",
    "manifest_diff": "manifests",
    "fix_plan": "fix_plans",
    "farm": "farm",
}


def scene_stem_and_parent(scene_path: str | Path | None) -> tuple[Path, str]:
    """Return the scene parent directory and stem, with safe fallbacks."""
    scene = Path(str(scene_path or ""))
    if scene.name:
        return (scene.parent, scene.stem or "untitled_scene")
    return (Path.cwd(), "untitled_scene")


def default_scene_export_path(
    scene_path: str | Path | None, *, suffix: str, extension: str
) -> Path:
    """Return the organized default export path beside a Maya scene."""
    parent, stem = scene_stem_and_parent(scene_path)
    category = EXPORT_CATEGORIES.get(suffix, "misc")
    resolved = (
        parent / REPORTS_DIR_NAME / category / f"{stem}_pipeline_inspector_{suffix}.{extension}"
    )
    return resolved


def legacy_scene_export_path(scene_path: str | Path | None, *, suffix: str, extension: str) -> Path:
    """Return the legacy flat export path directly beside the scene file."""
    parent, stem = scene_stem_and_parent(scene_path)
    return parent / f"{stem}_pipeline_inspector_{suffix}.{extension}"


def resolve_existing_scene_export_path(
    scene_path: str | Path | None, *, suffix: str, extension: str
) -> Path | None:
    """Return an existing export path, preferring the organized layout."""
    organized = default_scene_export_path(scene_path, suffix=suffix, extension=extension)
    if organized.is_file():
        return organized
    legacy = legacy_scene_export_path(scene_path, suffix=suffix, extension=extension)
    if legacy.is_file():
        return legacy
    return None


def default_farm_html_report_path(scene_path: str | Path | None) -> Path:
    """Return the organized default Deadline farm HTML report path."""
    parent, stem = scene_stem_and_parent(scene_path)
    return parent / REPORTS_DIR_NAME / "farm" / f"{stem}_deadline_farm_report.html"


def default_farm_validation_json_path(scene_path: str | Path | None) -> Path:
    """Return the organized default farm validation JSON report path."""
    parent, stem = scene_stem_and_parent(scene_path)
    return parent / REPORTS_DIR_NAME / "farm" / f"{stem}_pipeline_inspector_farm.json"


def resolve_existing_farm_html_report_path(scene_path: str | Path | None) -> Path | None:
    """Return an existing farm HTML report path if present."""
    organized = default_farm_html_report_path(scene_path)
    if organized.is_file():
        return organized
    parent, stem = scene_stem_and_parent(scene_path)
    legacy = parent / f"{stem}_deadline_farm_report.html"
    if legacy.is_file():
        return legacy
    return None
