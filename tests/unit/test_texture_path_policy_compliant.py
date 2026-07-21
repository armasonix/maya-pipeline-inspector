from __future__ import annotations

from pipeline_inspector.studio_config import StudioEnvironmentSettings
from pipeline_inspector.util.paths import texture_path_policy_compliant

_ALLOWED = (
    "$ASSET_ROOT",
    "${ASSET_ROOT}",
    "${STUDIO_ASSET_ROOT}",
    "${STUDIO_TEXTURE_ROOT}",
)


def test_texture_path_policy_compliant_rejects_render_safe_absolute_when_studio_configured() -> (
    None
):
    asset_root = "D:/show/assets"
    env = StudioEnvironmentSettings(
        asset_root=asset_root,
        texture_root=f"{asset_root}/textures",
    )
    raw = f"{asset_root}/textures/albedo.exr"

    assert texture_path_policy_compliant(raw, raw, _ALLOWED, env) is False


def test_texture_path_policy_compliant_accepts_render_safe_relative_when_studio_configured() -> (
    None
):
    asset_root = "D:/show/assets"
    env = StudioEnvironmentSettings(
        asset_root=asset_root,
        texture_root=f"{asset_root}/textures",
    )
    raw = "../assets/textures/albedo.exr"
    resolved = f"{asset_root}/textures/albedo.exr"

    assert texture_path_policy_compliant(raw, resolved, _ALLOWED, env) is True


def test_texture_path_policy_compliant_accepts_studio_token_when_studio_configured() -> None:
    asset_root = "D:/show/assets"
    env = StudioEnvironmentSettings(
        asset_root=asset_root,
        texture_root=f"{asset_root}/textures",
    )
    raw = "${STUDIO_ASSET_ROOT}/textures/albedo.exr"

    assert (
        texture_path_policy_compliant(
            raw,
            f"{asset_root}/textures/albedo.exr",
            _ALLOWED,
            env,
        )
        is True
    )


def test_texture_path_policy_compliant_accepts_farm_token_without_studio_config() -> None:
    raw = "$ASSET_ROOT/textures/albedo.exr"

    assert texture_path_policy_compliant(raw, raw, _ALLOWED, None) is True


def test_texture_path_policy_compliant_rejects_studio_token_with_backslashes() -> None:
    asset_root = "D:/show/assets"
    env = StudioEnvironmentSettings(
        asset_root=asset_root,
        texture_root=f"{asset_root}/textures",
    )

    assert (
        texture_path_policy_compliant(
            "${STUDIO_ASSET_ROOT}\\textures\\albedo.exr",
            f"{asset_root}/textures/albedo.exr",
            _ALLOWED,
            env,
        )
        is False
    )
