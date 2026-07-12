"""Rebrand pipeline_inspector -> pipeline_inspector across the repository."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    "_recovery",
    "_recovery_client",
}

TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".json",
    ".html",
    ".toml",
    ".ini",
    ".yml",
    ".yaml",
    ".mel",
    ".mod",
    ".txt",
    ".cpp",
    ".cmake",
    ".ps1",
    ".ma",
    ".gitignore",
}

# Longest-first replacements
REPLACEMENTS: list[tuple[str, str]] = [
    ("pipelineInspector", "pipelineInspector"),
    ("PipelineInspector", "PipelineInspector"),
    ("pipeline_inspector_bootstrap", "pipeline_inspector_bootstrap"),
    ("pipeline_inspector", "pipeline_inspector"),
    ("Pipeline Inspector Farm Check", "Pipeline Inspector Farm Check"),
    ("Open Pipeline Inspector", "Open Pipeline Inspector"),
    ("Close Pipeline Inspector", "Open Pipeline Inspector"),  # fixed below
    ("Maya Pipeline Inspector", "Maya Pipeline Inspector"),
    ("Pipeline Inspector", "Pipeline Inspector"),
    ("Pipeline Inspector", "Pipeline Inspector"),
    ("PipelineInspector", "PipelineInspector"),
    ("maya-pipeline-inspector", "maya-pipeline-inspector"),
    ("PIPELINE_INSPECTOR", "PIPELINE_INSPECTOR"),
    ("pipeline_inspector", "pipeline_inspector"),
]

FILE_RENAMES: list[tuple[Path, Path]] = [
    (ROOT / "src" / "pipeline_inspector", ROOT / "src" / "pipeline_inspector"),
    (
        ROOT / "maya_module" / "pipeline_inspector.mod",
        ROOT / "maya_module" / "pipeline_inspector.mod",
    ),
    (
        ROOT / "maya_module" / "scripts" / "pipeline_inspector_bootstrap.py",
        ROOT / "maya_module" / "scripts" / "pipeline_inspector_bootstrap.py",
    ),
    (
        ROOT / "maya_module" / "plug-ins" / "pipeline_inspector.py",
        ROOT / "maya_module" / "plug-ins" / "pipeline_inspector.py",
    ),
    (
        ROOT / "maya_module" / "shelves" / "shelf_PipelineInspector.mel",
        ROOT / "maya_module" / "shelves" / "shelf_PipelineInspector.mel",
    ),
    (
        ROOT / "native" / "src" / "pipeline_inspector_plugin.cpp",
        ROOT / "native" / "src" / "pipeline_inspector_plugin.cpp",
    ),
]


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def replace_in_file(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    original = text
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    # Fix mistaken close label from ordered replacement
    text = text.replace(
        "Close Pipeline Inspector",
        "Close Pipeline Inspector",
    )
    text = text.replace(
        'CLOSE_MENU_ITEM_LABEL = "Close Pipeline Inspector"',
        'CLOSE_MENU_ITEM_LABEL = "Close Pipeline Inspector"',
    )
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def walk_and_replace() -> int:
    changed = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or should_skip(path):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {
            "CMakeLists.txt",
            "LICENSE",
            "CONTRIBUTING",
        }:
            continue
        if replace_in_file(path):
            changed += 1
    return changed


def rename_paths() -> None:
    for src, dst in FILE_RENAMES:
        if not src.exists():
            if dst.exists():
                continue
            raise FileNotFoundError(src)
        if dst.exists():
            raise FileExistsError(dst)
        shutil.move(str(src), str(dst))


def main() -> int:
    # Fix close menu replacement before running (insert explicit pair)
    global REPLACEMENTS
    REPLACEMENTS = [
        ("pipelineInspector", "pipelineInspector"),
        ("PipelineInspector", "PipelineInspector"),
        ("pipeline_inspector_bootstrap", "pipeline_inspector_bootstrap"),
        ("pipeline_inspector", "pipeline_inspector"),
        ("Pipeline Inspector Farm Check", "Pipeline Inspector Farm Check"),
        ("Close Pipeline Inspector", "Close Pipeline Inspector"),
        ("Open Pipeline Inspector", "Open Pipeline Inspector"),
        ("Maya Pipeline Inspector", "Maya Pipeline Inspector"),
        ("Pipeline Inspector", "Pipeline Inspector"),
        ("Pipeline Inspector", "Pipeline Inspector"),
        ("PipelineInspector", "PipelineInspector"),
        ("maya-pipeline-inspector", "maya-pipeline-inspector"),
        ("PIPELINE_INSPECTOR", "PIPELINE_INSPECTOR"),
        ("pipeline_inspector", "pipeline_inspector"),
    ]
    rename_paths()
    changed = walk_and_replace()
    print(f"Updated {changed} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
