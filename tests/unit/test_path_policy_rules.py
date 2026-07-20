from pathlib import Path

from pipeline_inspector.core import (
    FileDependencySnapshot,
    GraphSnapshot,
    RuleDefinition,
    ValidationEngine,
    load_rule_file,
)
from pipeline_inspector.studio_config import StudioEnvironmentSettings

ROOT = Path(__file__).resolve().parents[2]
RULE_PATH = ROOT / "src" / "pipeline_inspector" / "rules" / "common" / "texture_paths.json"


def load_texture_rule(rule_id: str) -> RuleDefinition:
    rules = {rule.id: rule for rule in load_rule_file(RULE_PATH)}
    return rules[rule_id]


def snapshot_for_path(raw_path: str, resolved_path: str = "") -> GraphSnapshot:
    return GraphSnapshot(
        scene_path="demo.ma",
        renderer="vray",
        file_dependencies=[
            FileDependencySnapshot(
                node_id="node:file_albedo",
                attr="fileTextureName",
                raw_path=raw_path,
                resolved_path=resolved_path or raw_path,
                exists=True,
                extension=".exr",
            )
        ],
    )


def evaluate(rule_id: str, raw_path: str, resolved_path: str = ""):
    return ValidationEngine().validate(
        snapshot_for_path(raw_path, resolved_path),
        [load_texture_rule(rule_id)],
    )[0]


def evaluate_with_studio(
    rule_id: str,
    raw_path: str,
    *,
    resolved_path: str = "",
    asset_root: str,
    texture_root: str = "",
):
    environment = StudioEnvironmentSettings(
        asset_root=asset_root,
        texture_root=texture_root or asset_root,
    )
    return ValidationEngine(studio_environment=environment).validate(
        snapshot_for_path(raw_path, resolved_path or raw_path),
        [load_texture_rule(rule_id)],
    )[0]


def test_local_drive_texture_path_rule_fails_for_windows_drive_path():
    result = evaluate(
        "common.texture.path.local_drive",
        "D:/show/assets/tex/albedo.exr",
    )

    assert result.status == "failed"
    assert result.block_publish is True
    assert result.block_deadline is True
    assert result.evidence["violations"] == ["local_drive"]


def test_local_drive_texture_path_rule_passes_for_project_variable_path():
    result = evaluate(
        "common.texture.path.local_drive",
        "$ASSET_ROOT/tex/albedo.exr",
        "D:/show/assets/tex/albedo.exr",
    )

    assert result.status == "passed"


def test_local_drive_texture_path_rule_passes_for_studio_token_path():
    asset_root = "D:/show/assets"
    result = evaluate_with_studio(
        "common.texture.path.local_drive",
        "${STUDIO_TEXTURE_ROOT}/albedo.exr",
        resolved_path=f"{asset_root}/textures/albedo.exr",
        asset_root=asset_root,
        texture_root=f"{asset_root}/textures",
    )

    assert result.status == "passed"


def test_local_drive_texture_path_rule_fails_for_studio_root_absolute_path():
    asset_root = "D:/show/assets"
    texture_path = f"{asset_root}/textures/albedo.exr"
    result = evaluate_with_studio(
        "common.texture.path.local_drive",
        texture_path,
        asset_root=asset_root,
        texture_root=f"{asset_root}/textures",
    )

    assert result.status == "failed"
    assert result.evidence["violations"] == ["local_drive"]


def test_local_drive_texture_path_rule_fails_for_usd_prim_studio_root_absolute_path():
    from pipeline_inspector.core import FileDependencySnapshot, GraphSnapshot, ValidationEngine
    from pipeline_inspector.core.rule_loader import load_rule_file

    asset_root = "D:/show/assets"
    texture_path = f"{asset_root}/textures/albedo.exr"
    environment = StudioEnvironmentSettings(
        asset_root=asset_root,
        texture_root=f"{asset_root}/textures",
    )
    usd_rules = {
        rule.id: rule
        for rule in load_rule_file(ROOT / "src" / "pipeline_inspector" / "rules" / "usd" / "usd_health.json")
    }
    snapshot = GraphSnapshot(
        scene_path="hero.usda",
        renderer="usd",
        file_dependencies=[
            FileDependencySnapshot(
                node_id="prim:/Hero/Looks/albedo",
                attr="file",
                raw_path=texture_path,
                resolved_path=texture_path,
                exists=True,
                extension=".exr",
            )
        ],
    )
    result = ValidationEngine(studio_environment=environment).validate(
        snapshot,
        [usd_rules["usd.texture.path.local_drive"]],
    )[0]

    assert result.status == "failed"
    assert result.evidence["violations"] == ["local_drive"]


def test_project_root_texture_path_rule_fails_for_studio_root_absolute_path():
    asset_root = "D:/show/assets"
    texture_path = f"{asset_root}/textures/albedo.exr"
    result = evaluate_with_studio(
        "common.texture.path.project_root",
        texture_path,
        asset_root=asset_root,
        texture_root=f"{asset_root}/textures",
    )

    assert result.status == "failed"
    assert result.evidence["violations"] == ["outside_project_root"]


def test_project_root_texture_path_rule_passes_for_studio_token_with_forward_slashes():
    asset_root = "D:/show/assets"
    result = evaluate_with_studio(
        "common.texture.path.project_root",
        "${STUDIO_ASSET_ROOT}/textures/albedo.exr",
        resolved_path=f"{asset_root}/textures/albedo.exr",
        asset_root=asset_root,
        texture_root=f"{asset_root}/textures",
    )

    assert result.status == "passed"


def test_project_root_texture_path_rule_fails_for_studio_token_with_backslashes():
    asset_root = "D:/show/assets"
    result = evaluate_with_studio(
        "common.texture.path.project_root",
        "${STUDIO_ASSET_ROOT}\\textures\\albedo.exr",
        resolved_path=f"{asset_root}/textures/albedo.exr",
        asset_root=asset_root,
        texture_root=f"{asset_root}/textures",
    )

    assert result.status == "failed"
    assert result.evidence["violations"] == ["outside_project_root"]


def test_user_location_texture_path_rule_fails_for_desktop_path():
    result = evaluate(
        "common.texture.path.user_location",
        "C:/Users/artist/Desktop/albedo.exr",
    )

    assert result.status == "failed"
    assert "user_home" in result.evidence["violations"]
    assert "desktop" in result.evidence["violations"]


def test_user_location_texture_path_rule_fails_for_temp_path():
    result = evaluate(
        "common.texture.path.user_location",
        "C:/Users/artist/AppData/Local/Temp/albedo.exr",
    )

    assert result.status == "failed"
    assert "temp" in result.evidence["violations"]


def test_project_root_texture_path_rule_passes_for_asset_root_variable():
    result = evaluate(
        "common.texture.path.project_root",
        "$ASSET_ROOT/tex/albedo.exr",
        "D:/show/assets/tex/albedo.exr",
    )

    assert result.status == "passed"


def test_project_root_texture_path_rule_fails_outside_approved_roots():
    result = evaluate(
        "common.texture.path.project_root",
        "//legacy_server/random/albedo.exr",
    )

    assert result.status == "failed"
    assert result.severity == "error"
    assert result.block_publish is True
    assert result.block_deadline is False
    assert result.evidence["violations"] == ["outside_project_root"]
