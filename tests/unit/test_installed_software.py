from __future__ import annotations

from pathlib import Path

from pipeline_inspector.integrations.readiness.installed_software import (
    find_installed_maya_versions,
    is_installed_version_available,
)


def test_find_installed_maya_versions_reads_autodesk_directories(tmp_path: Path, monkeypatch):
    install_root = tmp_path / "Autodesk"
    maya_2024 = install_root / "Maya2024" / "bin"
    maya_2025 = install_root / "Maya2025" / "bin"
    maya_2024.mkdir(parents=True)
    maya_2025.mkdir(parents=True)
    (maya_2024 / "mayapy.exe").write_text("", encoding="utf-8")
    (maya_2025 / "mayapy.exe").write_text("", encoding="utf-8")

    monkeypatch.setattr(
        "pipeline_inspector.integrations.readiness.installed_software._autodesk_install_roots",
        lambda: (install_root,),
    )
    monkeypatch.setattr(
        "pipeline_inspector.integrations.readiness.installed_software._maya_versions_from_registry",
        lambda: frozenset(),
    )

    assert find_installed_maya_versions() == frozenset({"2024", "2025"})


def test_is_installed_version_available_matches_specific_maya_year(monkeypatch):
    monkeypatch.setattr(
        "pipeline_inspector.integrations.readiness.installed_software.find_installed_product_versions",
        lambda product: frozenset({"2024", "2025"}) if product == "maya" else frozenset(),
    )

    assert is_installed_version_available("maya", "2024") is True
    assert is_installed_version_available("maya", "2025") is True
    assert is_installed_version_available("maya", "2023") is False


def test_is_installed_version_available_requires_exact_match_for_partial_numbers(
    monkeypatch,
):
    monkeypatch.setattr(
        "pipeline_inspector.integrations.readiness.installed_software.find_installed_product_versions",
        lambda product: frozenset({"2025"}) if product == "maya" else frozenset(),
    )

    assert is_installed_version_available("maya", "2025") is True
    assert is_installed_version_available("maya", "2024") is False
