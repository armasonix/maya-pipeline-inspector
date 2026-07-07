from __future__ import annotations

from pathlib import Path

from shader_health.core import (
    FileDependencySnapshot,
    GraphSnapshot,
    NodeSnapshot,
    RuleDefinition,
    ValidationEngine,
    load_rule_file,
)

ROOT = Path(__file__).resolve().parents[2]
DISPLACEMENT_RULE_PATH = (
    ROOT / "src" / "shader_health" / "rules" / "common" / "displacement_common.json"
)
COLOR_SPACE_RULE_PATH = (
    ROOT / "src" / "shader_health" / "rules" / "common" / "color_space.json"
)


def load_rule(path: Path, rule_id: str) -> RuleDefinition:
    rules = {rule.id: rule for rule in load_rule_file(path)}
    return rules[rule_id]


def snapshot_for_displacement_dependency(
    *,
    semantic_slot: str,
    exists: bool,
) -> GraphSnapshot:
    return GraphSnapshot(
        scene_path="demo.ma",
        renderer="vray",
        nodes=[
            NodeSnapshot(
                id="node:file_displacement",
                name="file_displacement",
                type_name="file",
                attrs={
                    "semantic_slot": semantic_slot,
                    "colorSpace": "Raw",
                },
                classification=["texture", "file"],
            )
        ],
        file_dependencies=[
            FileDependencySnapshot(
                node_id="node:file_displacement",
                attr="fileTextureName",
                raw_path="$ASSET_ROOT/tex/displacement_v001.<UDIM>.exr",
                resolved_path="D:/show/assets/tex/displacement_v001.<UDIM>.exr",
                exists=exists,
                is_udim=True,
                udim_tiles=[1001, 1002],
                extension=".exr",
            )
        ],
    )


def snapshot_for_displacement_amount(amount: object) -> GraphSnapshot:
    return GraphSnapshot(
        scene_path="demo.ma",
        renderer="vray",
        nodes=[
            NodeSnapshot(
                id="node:disp",
                name="disp",
                type_name="displacementShader",
                attrs={"amount": amount},
                classification=["displacement"],
            )
        ],
    )


def snapshot_for_displacement_color_space(color_space: str) -> GraphSnapshot:
    return GraphSnapshot(
        scene_path="demo.ma",
        renderer="vray",
        nodes=[
            NodeSnapshot(
                id="node:file_displacement",
                name="file_displacement",
                type_name="file",
                attrs={
                    "semantic_slot": "displacement",
                    "colorSpace": color_space,
                },
                classification=["texture", "file"],
            )
        ],
    )


def test_displacement_missing_texture_rule_pack_has_production_defaults():
    rule = load_rule(DISPLACEMENT_RULE_PATH, "common.displacement.texture.missing")

    assert rule.scope == "file_dependency"
    assert rule.severity == "critical"
    assert rule.match.criteria == {
        "dependency_kind": "texture",
        "semantic_slot": "displacement",
    }
    assert rule.check.type == "path_exists"
    assert rule.policy.block_publish is True
    assert rule.policy.block_deadline is True
    assert rule.policy.auto_fix_allowed is False


def test_displacement_missing_texture_rule_fails_for_missing_texture():
    rule = load_rule(DISPLACEMENT_RULE_PATH, "common.displacement.texture.missing")
    snapshot = snapshot_for_displacement_dependency(
        semantic_slot="displacement",
        exists=False,
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.target_kind == "file_dependency"
    assert result.target_id == "node:file_displacement"
    assert result.plug == "fileTextureName"
    assert result.current_value == "D:/show/assets/tex/displacement_v001.<UDIM>.exr"
    assert result.expected_value == "existing file"
    assert result.block_publish is True
    assert result.block_deadline is True


def test_displacement_missing_texture_rule_skips_non_displacement_texture():
    rule = load_rule(DISPLACEMENT_RULE_PATH, "common.displacement.texture.missing")
    snapshot = snapshot_for_displacement_dependency(
        semantic_slot="roughness",
        exists=False,
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "skipped"
    assert result.evidence["reason"] == "no_matching_targets"


def test_existing_data_color_space_rule_detects_displacement_color_space_risk():
    rule = load_rule(COLOR_SPACE_RULE_PATH, "common.texture.colorspace.data_raw")
    snapshot = snapshot_for_displacement_color_space("sRGB")

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.current_value == "sRGB"
    assert result.expected_value == "Raw"
    assert result.block_publish is True
    assert result.block_deadline is True
    assert result.auto_fix_available is True


def test_displacement_amount_rule_pack_has_production_defaults():
    rule = load_rule(DISPLACEMENT_RULE_PATH, "common.displacement.amount.max")

    assert rule.scope == "node"
    assert rule.severity == "error"
    assert rule.match.criteria == {
        "node_type": ["displacementShader", "VRayDisplacement", "aiDisplacement"]
    }
    assert rule.check.type == "numeric_max"
    assert rule.check.params["attribute"] == "amount"
    assert rule.check.params["max"] == 1.0
    assert rule.policy.block_publish is True
    assert rule.policy.block_deadline is True


def test_displacement_amount_rule_fails_above_threshold():
    rule = load_rule(DISPLACEMENT_RULE_PATH, "common.displacement.amount.max")
    snapshot = snapshot_for_displacement_amount(2.5)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.target_kind == "node"
    assert result.target_id == "node:disp"
    assert result.node == "disp"
    assert result.plug == "amount"
    assert result.current_value == 2.5
    assert result.expected_value == 1.0
    assert result.evidence["max"] == 1.0
    assert result.block_publish is True
    assert result.block_deadline is True


def test_displacement_amount_rule_passes_at_threshold():
    rule = load_rule(DISPLACEMENT_RULE_PATH, "common.displacement.amount.max")
    snapshot = snapshot_for_displacement_amount(1.0)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.current_value == 1.0
    assert result.expected_value == 1.0
    assert result.block_publish is False
    assert result.block_deadline is False


def test_displacement_amount_rule_skips_missing_numeric_metadata():
    rule = load_rule(DISPLACEMENT_RULE_PATH, "common.displacement.amount.max")
    snapshot = snapshot_for_displacement_amount("not-a-number")

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "skipped"
    assert result.evidence["reason"] == "numeric_max_requires_numeric_values"


def test_displacement_risk_score_rule_fails_above_threshold():
    from shader_health.core import DisplacementRiskMetadata, MaterialSnapshot

    rule = load_rule(DISPLACEMENT_RULE_PATH, "common.displacement.risk_score.max")
    snapshot = GraphSnapshot(
        scene_path="demo.ma",
        renderer="vray",
        materials=[
            MaterialSnapshot(
                node_id="node:hero_material",
                name="hero_material",
                type_name="VRayMtl",
                renderer_family="vray",
                displacement_metadata=DisplacementRiskMetadata(
                    has_displacement=True,
                    risk_score=9.5,
                ),
            )
        ],
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.plug == "displacement_metadata.risk_score"
    assert result.current_value == 9.5
    assert result.expected_value == 8.0


def test_displacement_subdivision_rule_fails_when_subdivision_enabled():
    from shader_health.core import DisplacementRiskMetadata, MaterialSnapshot

    rule = load_rule(DISPLACEMENT_RULE_PATH, "common.displacement.subdivision.enabled")
    snapshot = GraphSnapshot(
        scene_path="demo.ma",
        renderer="vray",
        materials=[
            MaterialSnapshot(
                node_id="node:hero_material",
                name="hero_material",
                type_name="VRayMtl",
                renderer_family="vray",
                displacement_metadata=DisplacementRiskMetadata(
                    has_displacement=True,
                    subdivision_enabled=True,
                ),
            )
        ],
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.plug == "displacement_metadata.subdivision_enabled"
    assert result.current_value is True
    assert result.expected_value is False
