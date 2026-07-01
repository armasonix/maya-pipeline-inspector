from pathlib import Path

from shader_health.core import (
    FileDependencySnapshot,
    GraphSnapshot,
    RuleDefinition,
    ValidationEngine,
    load_rule_file,
)

ROOT = Path(__file__).resolve().parents[2]
RULE_PATH = ROOT / "src" / "shader_health" / "rules" / "common" / "udim_integrity.json"


def load_udim_rule(rule_id: str) -> RuleDefinition:
    rules = {rule.id: rule for rule in load_rule_file(RULE_PATH)}
    return rules[rule_id]


def snapshot_for_udim_dependency(
    *,
    is_udim: bool,
    udim_tiles: list[int],
    missing_udim_tiles: list[int],
) -> GraphSnapshot:
    return GraphSnapshot(
        scene_path="demo.ma",
        renderer="vray",
        file_dependencies=[
            FileDependencySnapshot(
                node_id="node:file_roughness",
                attr="fileTextureName",
                raw_path="$ASSET_ROOT/tex/roughness_v001.<UDIM>.exr",
                resolved_path="D:/show/assets/tex/roughness_v001.<UDIM>.exr",
                exists=True,
                is_udim=is_udim,
                udim_tiles=udim_tiles,
                missing_udim_tiles=missing_udim_tiles,
                extension=".exr",
            )
        ],
    )


def test_udim_missing_tiles_rule_pack_has_production_defaults():
    rule = load_udim_rule("common.texture.udim.missing_tiles")

    assert rule.scope == "file_dependency"
    assert rule.severity == "critical"
    assert rule.match.criteria == {"dependency_kind": "texture", "is_udim": True}
    assert rule.check.type == "attribute_equals"
    assert rule.check.params["attribute"] == "missing_udim_tiles"
    assert rule.check.params["expected"] == []
    assert rule.policy.block_publish is True
    assert rule.policy.block_deadline is True
    assert rule.policy.auto_fix_allowed is False


def test_udim_missing_tiles_rule_fails_when_tiles_are_missing():
    rule = load_udim_rule("common.texture.udim.missing_tiles")
    snapshot = snapshot_for_udim_dependency(
        is_udim=True,
        udim_tiles=[1001, 1003],
        missing_udim_tiles=[1002],
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.target_kind == "file_dependency"
    assert result.target_id == "node:file_roughness"
    assert result.plug == "missing_udim_tiles"
    assert result.current_value == [1002]
    assert result.expected_value == []
    assert result.block_publish is True
    assert result.block_deadline is True


def test_udim_missing_tiles_rule_passes_when_tile_set_is_complete():
    rule = load_udim_rule("common.texture.udim.missing_tiles")
    snapshot = snapshot_for_udim_dependency(
        is_udim=True,
        udim_tiles=[1001, 1002, 1003],
        missing_udim_tiles=[],
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.current_value == []
    assert result.block_publish is False
    assert result.block_deadline is False


def test_udim_missing_tiles_rule_skips_non_udim_dependencies():
    rule = load_udim_rule("common.texture.udim.missing_tiles")
    snapshot = snapshot_for_udim_dependency(
        is_udim=False,
        udim_tiles=[],
        missing_udim_tiles=[],
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "skipped"
    assert result.evidence["reason"] == "no_matching_targets"
