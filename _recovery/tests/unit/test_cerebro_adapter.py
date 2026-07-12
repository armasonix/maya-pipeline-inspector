from __future__ import annotations

import sys
from pathlib import Path

from shader_health.integrations.cerebro.adapter import (
    bundled_psycopg2_sys_path,
    cerebro_core_sys_paths,
    cerebro_service_tools_sys_paths,
    probe_py_cerebro_import,
    psycopg2_install_hint,
)


def test_cerebro_core_sys_paths_excludes_bundled_psycopg2(tmp_path: Path):
    root = tmp_path / "service-tools"
    (root / "py-site-packages" / "win" / "psycopg2").mkdir(parents=True)
    (root / "py_cerebro").mkdir()

    paths = cerebro_core_sys_paths(str(root))

    assert str(root) in paths
    assert str(root / "py-site-packages") in paths
    assert str(root / "py-site-packages" / "win") not in paths


def test_cerebro_service_tools_sys_paths_matches_core_paths(tmp_path: Path):
    root = tmp_path / "service-tools"
    (root / "py-site-packages").mkdir(parents=True)
    (root / "py_cerebro").mkdir()

    assert cerebro_service_tools_sys_paths(str(root)) == cerebro_core_sys_paths(str(root))


def test_bundled_psycopg2_sys_path_points_at_platform_packages(tmp_path: Path):
    root = tmp_path / "service-tools"
    (root / "py-site-packages" / "win").mkdir(parents=True)

    bundled = bundled_psycopg2_sys_path(str(root))

    if sys.platform == "win32":
        assert bundled == str(root / "py-site-packages" / "win")
    else:
        assert bundled is not None


def test_probe_py_cerebro_import_reports_missing_service_tools_path():
    module, error = probe_py_cerebro_import(service_tools_path="")

    assert module is None
    assert error == "service_tools_path_empty"


def test_probe_py_cerebro_import_reports_missing_directory():
    module, error = probe_py_cerebro_import(
        service_tools_path=r"C:\missing\service-tools",
    )

    assert module is None
    assert "service_tools_path_not_found" in error


def test_psycopg2_install_hint_uses_sys_executable():
    hint = psycopg2_install_hint()

    assert "pip install psycopg2-binary" in hint
    assert sys.executable in hint
