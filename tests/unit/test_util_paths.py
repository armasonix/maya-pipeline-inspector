from __future__ import annotations

from pathlib import Path

from shader_health.util import paths


def test_normalize_cli_path_converts_git_bash_drive_prefix_on_windows(monkeypatch):
    monkeypatch.setattr(paths.sys, "platform", "win32")

    normalized = paths.normalize_cli_path(
        "/d/Workspace/portfolio/maya-shader-health-inspector/_cli_test_out/report.json"
    )

    assert normalized == Path(
        "D:\\Workspace\\portfolio\\maya-shader-health-inspector\\_cli_test_out\\report.json"
    )


def test_normalize_cli_path_leaves_windows_paths_unchanged_on_windows(monkeypatch):
    monkeypatch.setattr(paths.sys, "platform", "win32")
    original = Path("D:/Workspace/repo/report.json")

    assert paths.normalize_cli_path(original) == original


def test_resolve_cli_path_returns_string_for_open(monkeypatch):
    monkeypatch.setattr(paths.sys, "platform", "win32")

    resolved = paths.resolve_cli_path(
        "/d/Workspace/portfolio/maya-shader-health-inspector/_cli_test_out/report.json"
    )

    assert resolved == (
        "D:\\Workspace\\portfolio\\maya-shader-health-inspector\\_cli_test_out\\report.json"
    )
