"""Build a GitHub Release zip for Pipeline Inspector auto-update."""
from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "dist"
PACKAGE_DIRS = ("maya_module", "src")
REQUIRED_NATIVE_MAYA_YEARS = (2024, 2025)
NATIVE_PLUGIN_BASENAME = "pipeline_inspector.mll"
SKIP_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
    ".git",
}
SKIP_FILE_SUFFIXES = {".pyc", ".pyo", ".pyd"}


def read_project_version() -> str:
    version_path = REPO_ROOT / "src" / "pipeline_inspector" / "version.py"
    text = version_path.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
    if not match:
        raise RuntimeError(f"Could not read __version__ from {version_path}")
    return match.group(1)


def release_zip_name(version: str) -> str:
    return f"maya-pipeline-inspector-{version}.zip"


def native_plugin_paths(repo_root: Path = REPO_ROOT) -> tuple[Path, ...]:
    plug_ins = repo_root / "maya_module" / "plug-ins"
    paths: list[Path] = []
    for year in REQUIRED_NATIVE_MAYA_YEARS:
        paths.append(plug_ins / str(year) / NATIVE_PLUGIN_BASENAME)
    paths.append(plug_ins / NATIVE_PLUGIN_BASENAME)
    return tuple(paths)


def validate_native_plugins_present(repo_root: Path = REPO_ROOT) -> None:
    """Ensure release builds include native Maya plug-ins artists need."""

    plug_ins = repo_root / "maya_module" / "plug-ins"
    missing_years = [
        str(year)
        for year in REQUIRED_NATIVE_MAYA_YEARS
        if not (plug_ins / str(year) / NATIVE_PLUGIN_BASENAME).is_file()
    ]
    if missing_years:
        raise RuntimeError(
            "Release package is missing native plug-ins for Maya "
            + ", ".join(missing_years)
            + ". Run tools/build_release_assets.ps1 or build_native_plugin.ps1 first."
        )
    manager_copy = plug_ins / NATIVE_PLUGIN_BASENAME
    if not manager_copy.is_file():
        raise RuntimeError(
            "Release package is missing Plug-in Manager copy: "
            f"{manager_copy.relative_to(repo_root)}"
        )


def list_native_plugins_in_zip(archive: zipfile.ZipFile) -> list[str]:
    return sorted(
        name
        for name in archive.namelist()
        if name.endswith(NATIVE_PLUGIN_BASENAME)
    )


def should_skip_path(path: Path) -> bool:
    for part in path.parts:
        if part in SKIP_DIR_NAMES:
            return True
    return path.suffix.lower() in SKIP_FILE_SUFFIXES


def iter_package_files(root: Path, relative_root: Path) -> list[Path]:
    if not root.is_dir():
        raise FileNotFoundError(f"Missing release payload directory: {root}")

    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or should_skip_path(path.relative_to(relative_root)):
            continue
        files.append(path)
    return files


def build_release_package(
    *,
    version: str,
    output_dir: Path,
    repo_root: Path = REPO_ROOT,
    require_native: bool = False,
) -> Path:
    missing = [name for name in PACKAGE_DIRS if not (repo_root / name).is_dir()]
    if missing:
        raise FileNotFoundError(
            "Release package requires directories: "
            + ", ".join(missing)
        )
    if require_native:
        validate_native_plugins_present(repo_root)

    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / release_zip_name(version)
    if destination.exists():
        destination.unlink()

    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for package_name in PACKAGE_DIRS:
            package_root = repo_root / package_name
            for file_path in iter_package_files(package_root, repo_root):
                archive.write(
                    file_path,
                    arcname=str(file_path.relative_to(repo_root)).replace("\\", "/"),
                )
        if require_native:
            bundled = list_native_plugins_in_zip(archive)
            if not bundled:
                raise RuntimeError(
                    f"Release zip did not bundle any {NATIVE_PLUGIN_BASENAME} files."
                )

    return destination


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version",
        help="Release version (defaults to src/pipeline_inspector/version.py)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--require-native",
        action="store_true",
        help=(
            "Fail unless maya_module/plug-ins contains pipeline_inspector.mll "
            "for Maya 2024 and 2025 plus the Plug-in Manager copy."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    version = (args.version or read_project_version()).strip()
    if not version:
        raise SystemExit("Release version is empty.")

    destination = build_release_package(
        version=version,
        output_dir=args.output_dir.resolve(),
        require_native=bool(args.require_native),
    )
    print(f"Built release package: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
