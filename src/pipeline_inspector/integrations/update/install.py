"""Safe staging install for Pipeline Inspector updates."""
from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

from pipeline_inspector.studio_config import STUDIO_CONFIG_FILENAME, discover_studio_config_path
from pipeline_inspector.user_config import (
    USER_CONFIG_DIRNAME,
    USER_CONFIG_FILENAME,
    discover_user_config_path,
)

INSTALL_DIRS = ("maya_module", "src")
UPDATE_BACKUP_DIRNAME = "backups"
PRESERVED_CONFIG_FILENAMES = frozenset({STUDIO_CONFIG_FILENAME, USER_CONFIG_FILENAME})


class UpdateInstallError(RuntimeError):
    """Raised when a staged update cannot be installed safely."""


@dataclass(frozen=True)
class PreservedConfigSnapshot:
    """In-memory backup of one preserved JSON config file."""

    path: Path
    payload: bytes


@dataclass(frozen=True)
class UpdateInstallResult:
    """Outcome from installing a staged update package."""

    success: bool
    message: str
    install_root: str = ""
    backup_path: str = ""
    rolled_back: bool = False
    error_message: str = ""


def install_staged_update(
    staging_path: Path,
    *,
    tag_name: str = "",
    install_root: Path | None = None,
    backup_root: Path | None = None,
) -> UpdateInstallResult:
    """Install a staged release package with config preservation and rollback."""

    resolved_install_root = install_root or resolve_default_install_root()
    resolved_backup_root = backup_root or default_update_backup_root(tag_name)
    config_snapshots = collect_preserved_config_snapshots()
    backup_path = resolved_backup_root / _sanitize_tag_name(tag_name or staging_path.stem)

    try:
        payload_root = extract_staged_package(staging_path)
        create_install_backup(resolved_install_root, backup_path)
        apply_install_payload(payload_root, resolved_install_root)
        restore_preserved_config_snapshots(config_snapshots)
    except (OSError, UpdateInstallError, zipfile.BadZipFile) as exc:
        rolled_back = False
        rollback_message = str(exc)
        if backup_path.is_dir():
            try:
                rollback_install(resolved_install_root, backup_path)
                restore_preserved_config_snapshots(config_snapshots)
                rolled_back = True
            except OSError as rollback_exc:
                rollback_message = (
                    f"{exc} Rollback also failed: {rollback_exc}"
                )
        return UpdateInstallResult(
            success=False,
            message=(
                "Install failed and previous plugin files were restored: "
                f"{rollback_message}"
                if rolled_back
                else f"Install failed: {rollback_message}"
            ),
            install_root=str(resolved_install_root),
            backup_path=str(backup_path),
            rolled_back=rolled_back,
            error_message=rollback_message,
        )

    return UpdateInstallResult(
        success=True,
        message=(
            "Update installed to "
            f"{resolved_install_root}. "
            f"{STUDIO_CONFIG_FILENAME} and {USER_CONFIG_FILENAME} preserved."
        ),
        install_root=str(resolved_install_root),
        backup_path=str(backup_path),
    )


def resolve_default_install_root(start: Path | None = None) -> Path:
    """Resolve the plugin install root containing ``maya_module/`` and ``src/``."""

    if start is None:
        import pipeline_inspector

        start = Path(pipeline_inspector.__file__).resolve().parent

    candidates = (
        start.parent.parent,
        start.parent,
        start,
    )
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if (resolved / "maya_module").is_dir() and (resolved / "src").is_dir():
            return resolved
    raise UpdateInstallError("Could not resolve plugin install root for update install.")


def default_update_backup_root(tag_name: str = "") -> Path:
    """Return the default backup directory for update rollback snapshots."""

    _ = tag_name
    return Path.home() / USER_CONFIG_DIRNAME / "updates" / UPDATE_BACKUP_DIRNAME


def collect_preserved_config_snapshots() -> tuple[PreservedConfigSnapshot, ...]:
    """Capture studio and user config files that must survive an update install."""

    snapshots: list[PreservedConfigSnapshot] = []
    for path in _preserved_config_paths():
        if not path.is_file():
            continue
        snapshots.append(
            PreservedConfigSnapshot(path=path, payload=path.read_bytes())
        )
    return tuple(snapshots)


def restore_preserved_config_snapshots(
    snapshots: tuple[PreservedConfigSnapshot, ...],
) -> None:
    """Restore preserved config files after install or rollback."""

    for snapshot in snapshots:
        snapshot.path.parent.mkdir(parents=True, exist_ok=True)
        snapshot.path.write_bytes(snapshot.payload)


def extract_staged_package(staging_path: Path) -> Path:
    """Extract a staged zip package and return the install payload root."""

    if staging_path.suffix.lower() != ".zip":
        raise UpdateInstallError(
            f"Staged update package must be a .zip file: {staging_path}"
        )
    if not staging_path.is_file():
        raise UpdateInstallError(f"Staged update package not found: {staging_path}")

    extract_dir = staging_path.parent / f"{staging_path.stem}_extracted"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(staging_path) as archive:
        archive.extractall(extract_dir)
    return resolve_extracted_package_root(extract_dir)


def resolve_extracted_package_root(extracted_dir: Path) -> Path:
    """Find the directory inside an extracted archive that contains install payload."""

    if not extracted_dir.is_dir():
        raise UpdateInstallError(f"Extracted update directory not found: {extracted_dir}")

    if _looks_like_install_payload(extracted_dir):
        return extracted_dir

    children = [path for path in extracted_dir.iterdir() if path.is_dir()]
    if len(children) == 1 and _looks_like_install_payload(children[0]):
        return children[0]

    for candidate in children:
        if _looks_like_install_payload(candidate):
            return candidate

    raise UpdateInstallError(
        "Staged update package does not contain maya_module/ and src/ payload."
    )


def create_install_backup(install_root: Path, backup_path: Path) -> None:
    """Copy install payload directories to a rollback backup location."""

    if backup_path.exists():
        shutil.rmtree(backup_path)
    backup_path.mkdir(parents=True, exist_ok=True)
    for directory_name in INSTALL_DIRS:
        source = install_root / directory_name
        if not source.is_dir():
            raise UpdateInstallError(
                f"Install root is missing required directory: {source}"
            )
        shutil.copytree(
            source,
            backup_path / directory_name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )


def apply_install_payload(payload_root: Path, install_root: Path) -> None:
    """Merge staged payload directories into the live install root."""

    for directory_name in INSTALL_DIRS:
        source = payload_root / directory_name
        if not source.is_dir():
            raise UpdateInstallError(
                f"Staged update package is missing required directory: {source}"
            )
        destination = install_root / directory_name
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            source,
            destination,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )


def rollback_install(install_root: Path, backup_path: Path) -> None:
    """Restore install payload directories from a rollback backup."""

    for directory_name in INSTALL_DIRS:
        source = backup_path / directory_name
        destination = install_root / directory_name
        if destination.exists():
            shutil.rmtree(destination)
        if source.is_dir():
            shutil.copytree(
                source,
                destination,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )


def _preserved_config_paths() -> tuple[Path, ...]:
    paths: list[Path] = []
    discovered_studio = discover_studio_config_path()
    if discovered_studio is not None:
        paths.append(discovered_studio)
    discovered_user = discover_user_config_path()
    if discovered_user is not None:
        paths.append(discovered_user)

    pipeline_inspector_dir = Path.home() / USER_CONFIG_DIRNAME
    legacy_dir = Path.home() / ".shader_health"
    defaults = (
        pipeline_inspector_dir / STUDIO_CONFIG_FILENAME,
        pipeline_inspector_dir / USER_CONFIG_FILENAME,
        legacy_dir / STUDIO_CONFIG_FILENAME,
        legacy_dir / "shader_health_studio.json",
        legacy_dir / USER_CONFIG_FILENAME,
    )
    for path in defaults:
        if path not in paths:
            paths.append(path)
    return tuple(paths)


def _looks_like_install_payload(path: Path) -> bool:
    return (path / "maya_module").is_dir() and (path / "src").is_dir()


def _sanitize_tag_name(tag_name: str) -> str:
    cleaned = "".join(
        char if char.isalnum() or char in {".", "-", "_"} else "_"
        for char in tag_name.strip()
    )
    return cleaned or "release"
