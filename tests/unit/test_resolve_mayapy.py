from __future__ import annotations

from pathlib import Path

import pytest
from tools.ci import resolve_mayapy as resolve_mayapy_module


def test_resolve_mayapy_writes_mayapy_path_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    fake_mayapy = tmp_path / "mayapy.exe"
    fake_mayapy.write_text("", encoding="utf-8")
    output_file = tmp_path / "github_output.txt"

    monkeypatch.setenv("MAYA_PY_INPUT", str(fake_mayapy))
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

    resolve_mayapy_module.main()

    assert output_file.read_text(encoding="utf-8").strip() == f"mayapy_path={fake_mayapy.resolve()}"
