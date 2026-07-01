import json
from pathlib import Path

from shader_health.core import (
    FileDependencySnapshot,
    GraphSnapshot,
    RuleDefinition,
    ValidationEngine,
    apply_profile_overrides,
    load_profile,
    load_rule_file,
)

ROOT = Path(__file__).resolve().parents[2]
RULE_PATH = ROOT / "src" / "shader_health" / "rules" / "common" / "texture_paths.json"


def make_file_dependency_snapshot(*, exists: bool) -> GraphSnapshot:
    return GraphSnapshot(
        scene_path="demo.ma",
        renderer="vray",
        file_dependencies=[
            FileDependencySnapshot(
                node_id="node:file_albedo",
                attr="fileTextureName",
                raw_path="$ASSET_ROOT/tex/missing_albedo.exr",
                resolved_path="D:/show/assets/tex/missing_albedo.exr",
                exists=exists,
                extension=".exr",
            )
        ],
    )


def load_missing_texture_rule() -> RuleDefinition:
    rules = {rule.id: rule for rule in load_rule_file(RULE_PATH)}
    return rules["common.texture.missing"]


def test_missing_texture_rule_pack_has_production_defaults():
    rule = load_missing_texture_rule()

    assert rule.id == "common.texture.missing"
    assert rule.scope == "file_dependency"
    assert rule.severity == "critical"
    assert rule.check.type == "path_exists"
    assert rule.match.criteria == {"dependency_kind": "texture"}
    assert rule.policy.block_publish is True
    assert rule.policy.block_deadline is False
    assert rule.policy.auto_fix_allowed is False


def test_missing_texture_rule_fails_for_missing_dependency():
    rule = load_missing_texture_rule()
    snapshot = make_file_dependency_snapshot(exists=False)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.severity == "critical"
    assert result.target_kind == "file_dependency"
    assert result.target_id == "node:file_albedo"
    assert result.node == "node:file_albedo"
    assert result.plug == "fileTextureName"
    assert result.current_value == "D:/show/assets/tex/missing_albedo.exr"
    assert result.expected_value == "existing file"
    assert result.block_publish is True
    assert result.block_deadline is False
    assert result.auto_fix_available is False


def test_missing_texture_rule_passes_for_existing_dependency():
    rule = load_missing_texture_rule()
    snapshot = make_file_dependency_snapshot(exists=True)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.block_publish is False
    assert result.block_deadline is False


def test_deadline_profile_can_make_missing_texture_farm_blocking(tmp_path):
    rule = load_missing_texture_rule()
    profile_path = tmp_path / "deadline_critical.json"
    profile_path.write_text(
        json.dumps(
            {
                "id": "deadline_critical",
                "display_name": "Deadline Critical",
                "rule_overrides": {
                    "common.texture.missing": {
                        "block_deadline": True,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    resolved_rule = apply_profile_overrides([rule], load_profile(profile_path))[0]
    snapshot = make_file_dependency_snapshot(exists=False)

    result = ValidationEngine().validate(snapshot, [resolved_rule])[0]

    assert result.status == "failed"
    assert result.block_publish is True
    assert result.block_deadline is True
