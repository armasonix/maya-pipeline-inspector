from __future__ import annotations

from pathlib import Path

from shader_health.studio_config import StudioEnvironmentSettings
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


def _sample_environment() -> StudioEnvironmentSettings:
    return StudioEnvironmentSettings(
        texture_root="\\\\farm\\textures",
        asset_root="\\\\farm\\assets",
        cache_root="\\\\farm\\cache",
        render_root="\\\\farm\\render",
        variable_aliases={"SHOW_ROOT": "\\\\farm\\show"},
    )


def test_studio_variable_aliases_maps_builtin_roots_and_custom_aliases():
    aliases = paths.studio_variable_aliases(_sample_environment())

    assert aliases["STUDIO_TEXTURE_ROOT"] == "\\\\farm\\textures"
    assert aliases["STUDIO_ASSET_ROOT"] == "\\\\farm\\assets"
    assert aliases["STUDIO_CACHE_ROOT"] == "\\\\farm\\cache"
    assert aliases["STUDIO_RENDER_ROOT"] == "\\\\farm\\render"
    assert aliases["SHOW_ROOT"] == "\\\\farm\\show"


def test_resolve_studio_path_expands_builtin_root_tokens():
    environment = _sample_environment()

    resolved = paths.resolve_studio_path(
        "${STUDIO_TEXTURE_ROOT}/hero/albedo.tx",
        environment,
    )

    assert resolved == "\\\\farm\\textures/hero/albedo.tx"


def test_resolve_studio_path_expands_custom_aliases_and_leaves_unknown_tokens():
    environment = _sample_environment()

    resolved = paths.resolve_studio_path(
        "${SHOW_ROOT}/assets/${UNKNOWN}/file.tx",
        environment,
    )

    assert resolved == "\\\\farm\\show/assets/${UNKNOWN}/file.tx"


def test_resolve_studio_path_allows_variable_aliases_to_override_builtin_names():
    environment = StudioEnvironmentSettings(
        texture_root="\\\\farm\\textures",
        variable_aliases={"STUDIO_TEXTURE_ROOT": "\\\\override\\textures"},
    )

    resolved = paths.resolve_studio_path(
        "${STUDIO_TEXTURE_ROOT}/albedo.tx",
        environment,
    )

    assert resolved == "\\\\override\\textures/albedo.tx"


def test_resolve_studio_path_supports_nested_substitution():
    environment = StudioEnvironmentSettings(
        variable_aliases={
            "BASE": "${STUDIO_TEXTURE_ROOT}",
        },
        texture_root="\\\\farm\\textures",
    )

    resolved = paths.resolve_studio_path("${BASE}/nested.tx", environment, max_passes=4)

    assert resolved == "\\\\farm\\textures/nested.tx"


def test_resolve_studio_path_returns_empty_string_for_blank_input():
    assert paths.resolve_studio_path("", _sample_environment()) == ""
