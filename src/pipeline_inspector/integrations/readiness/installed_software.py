"""Detect installed DCC and plugin versions on the local workstation."""
from __future__ import annotations

import os
import platform
import re
from functools import lru_cache
from pathlib import Path

_MAYA_YEAR_PATTERN = re.compile(r"^maya(\d{4})$", re.IGNORECASE)
_MAYA_VERSION_PATTERN = re.compile(r"^\d{4}$")


def find_installed_maya_versions() -> frozenset[str]:
    """Return Maya release years detected as installed on this machine."""

    versions: set[str] = set()
    versions.update(_maya_versions_from_registry())
    versions.update(_maya_versions_from_filesystem())
    return frozenset(versions)


def find_installed_product_versions(product: str) -> frozenset[str]:
    """Return installed version tokens for a named product."""

    product_key = str(product or "").strip().casefold()
    if product_key == "maya":
        return find_installed_maya_versions()
    return frozenset()


def installed_version_matches(required: str, installed: str) -> bool:
    """Return whether one installed version token satisfies a requirement."""

    return _version_tokens_match(required, installed)


def is_installed_version_available(product: str, required_version: str) -> bool:
    """Return whether any detected install satisfies the required version token."""

    required_text = str(required_version or "").strip()
    if not required_text:
        return True
    installed_versions = find_installed_product_versions(product)
    if not installed_versions:
        return False
    return any(
        _version_tokens_match(required_text, installed_text)
        for installed_text in installed_versions
    )


def format_installed_versions(versions: frozenset[str]) -> str:
    if not versions:
        return "none"
    return ", ".join(sorted(versions))


def _version_tokens_match(required: str, installed: str) -> bool:
    required_text = str(required or "").strip()
    installed_text = str(installed or "").strip()
    if not required_text or not installed_text:
        return False
    if required_text.casefold() in installed_text.casefold():
        return True
    required_numbers = _version_numbers(required_text)
    installed_numbers = _version_numbers(installed_text)
    if required_numbers and installed_numbers:
        return installed_numbers[: len(required_numbers)] == required_numbers
    return installed_text.casefold() == required_text.casefold()


def _version_numbers(text: str) -> tuple[int, ...] | None:
    numbers = tuple(int(value) for value in re.findall(r"\d+", text))
    return numbers or None


@lru_cache(maxsize=1)
def _maya_versions_from_registry() -> frozenset[str]:
    if platform.system().casefold() != "windows":
        return frozenset()

    try:
        import winreg
    except ImportError:
        return frozenset()

    versions: set[str] = set()
    roots = (
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Autodesk\Maya"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Autodesk\Maya"),
    )
    for root, base_path in roots:
        versions.update(_enum_maya_registry_versions(winreg, root, base_path))
    return frozenset(versions)


def _enum_maya_registry_versions(winreg: object, root: object, base_path: str) -> set[str]:
    open_key = getattr(winreg, "OpenKey", None)
    enum_key = getattr(winreg, "EnumKey", None)
    close_key = getattr(winreg, "CloseKey", None)
    if open_key is None or enum_key is None:
        return set()

    versions: set[str] = set()
    try:
        base_key = open_key(root, base_path)
    except OSError:
        return set()

    index = 0
    while True:
        try:
            subkey_name = str(enum_key(base_key, index))
        except OSError:
            break
        index += 1
        if not _MAYA_VERSION_PATTERN.fullmatch(subkey_name):
            continue
        if _registry_maya_install_has_mayapy(winreg, root, base_path, subkey_name):
            versions.add(subkey_name)
    if close_key is not None:
        with _suppress_os_error():
            close_key(base_key)
    return versions


def _registry_maya_install_has_mayapy(
    winreg: object,
    root: object,
    base_path: str,
    version_year: str,
) -> bool:
    open_key = getattr(winreg, "OpenKey", None)
    query_value = getattr(winreg, "QueryValueEx", None)
    close_key = getattr(winreg, "CloseKey", None)
    if open_key is None:
        return True

    install_path = ""
    setup_path = f"{base_path}\\{version_year}\\Setup"
    try:
        setup_key = open_key(root, setup_path)
        if query_value is not None:
            install_path = str(query_value(setup_key, "InstallPath")[0] or "").strip()
        if close_key is not None:
            with _suppress_os_error():
                close_key(setup_key)
    except OSError:
        install_path = ""

    if install_path:
        mayapy = Path(install_path) / "bin" / "mayapy.exe"
        if mayapy.is_file():
            return True
    return _filesystem_maya_version_installed(version_year)


def _maya_versions_from_filesystem() -> frozenset[str]:
    versions: set[str] = set()
    for root in _autodesk_install_roots():
        if not root.is_dir():
            continue
        for entry in root.iterdir():
            match = _MAYA_YEAR_PATTERN.match(entry.name)
            if match is None:
                continue
            year = match.group(1)
            if _filesystem_maya_version_installed(year, install_root=entry):
                versions.add(year)
    return frozenset(versions)


def _filesystem_maya_version_installed(
    version_year: str,
    *,
    install_root: Path | None = None,
) -> bool:
    candidates: list[Path] = []
    if install_root is not None:
        candidates.append(install_root)
    else:
        for root in _autodesk_install_roots():
            candidates.append(root / f"Maya{version_year}")
            candidates.append(root / f"maya{version_year}")

    for candidate in candidates:
        if _maya_install_root_has_mayapy(candidate):
            return True
    return False


def _maya_install_root_has_mayapy(install_root: Path) -> bool:
    if platform.system().casefold() == "windows":
        return (install_root / "bin" / "mayapy.exe").is_file()
    return (install_root / "bin" / "mayapy").is_file()


def _autodesk_install_roots() -> tuple[Path, ...]:
    system = platform.system().casefold()
    if system == "windows":
        roots = [Path(r"C:\Program Files\Autodesk")]
        program_files = os.environ.get("ProgramFiles", "").strip()
        if program_files:
            roots.append(Path(program_files) / "Autodesk")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", "").strip()
        if program_files_x86:
            roots.append(Path(program_files_x86) / "Autodesk")
        return tuple(dict.fromkeys(roots))
    if system == "darwin":
        return (Path("/Applications/Autodesk"),)
    return (Path("/usr/autodesk"),)


class _suppress_os_error:
    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return exc_type is OSError
