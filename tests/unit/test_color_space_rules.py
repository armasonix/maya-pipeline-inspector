from pathlib import Path

from pipeline_inspector.core import (
    GraphSnapshot,
    NodeSnapshot,
    RuleDefinition,
    ValidationEngine,
    load_rule_file,
)

ROOT = Path(__file__).resolve().parents[2]
RULE_PATH = ROOT / "src" / "pipeline_inspector" / "rules" / "common" / "color_space.json"


def load_color_space_rule(rule_id: str) -> RuleDefinition:
    rules = {rule.id: rule for rule in load_rule_file(RULE_PATH)}
    return rules[rule_id]


def snapshot_for_texture(
    *,
    semantic_slot: str,
    color_space: str,
    type_name: str = "file",
) -> GraphSnapshot:
    return GraphSnapshot(
        scene_path="demo.ma",
        renderer="vray",
        nodes=[
            NodeSnapshot(
                id="node:file_texture",
                name="file_texture",
                type_name=type_name,
                attrs={
                    "semantic_slot": semantic_slot,
                    "colorSpace": color_space,
                },
                classification=["texture", "file"],
            )
        ],
    )


def evaluate(rule_id: str, *, semantic_slot: str, color_space: str):
    return ValidationEngine().validate(
        snapshot_for_texture(semantic_slot=semantic_slot, color_space=color_space),
        [load_color_space_rule(rule_id)],
    )[0]


def test_data_color_space_rule_pack_has_safe_autofix_defaults():
    rule = load_color_space_rule("common.texture.colorspace.data_raw")

    assert rule.scope == "texture_node"
    assert rule.severity == "critical"
    assert "opacity" in rule.match.criteria["semantic_slot"]
    assert rule.check.type == "attribute_equals"
    assert rule.check.params["attribute"] == "colorSpace"
    assert rule.check.params["expected"] == "Raw"
    assert rule.policy.block_publish is True
    assert rule.policy.block_deadline is True
    assert rule.policy.auto_fix_allowed is True
    assert rule.fix is not None
    assert rule.fix.type == "set_attr"
    assert rule.fix.risk == "low"
    assert rule.fix.params["value"] == "Raw"


def test_data_color_space_rule_fails_and_offers_low_risk_autofix():
    result = evaluate(
        "common.texture.colorspace.data_raw",
        semantic_slot="roughness",
        color_space="ACEScg",
    )

    assert result.status == "failed"
    assert result.current_value == "ACEScg"
    assert result.expected_value == "Raw"
    assert result.plug == "colorSpace"
    assert result.block_publish is True
    assert result.block_deadline is True
    assert result.auto_fix_available is True
    assert result.fix_id == "set_attr"


def test_data_color_space_rule_passes_for_raw_data_map():
    result = evaluate(
        "common.texture.colorspace.data_raw",
        semantic_slot="normal",
        color_space="Raw",
    )

    assert result.status == "passed"
    assert result.block_publish is False
    assert result.block_deadline is False


def test_data_color_space_rule_applies_to_opacity_semantic():
    result = evaluate(
        "common.texture.colorspace.data_raw",
        semantic_slot="opacity",
        color_space="sRGB",
    )

    assert result.status == "failed"
    assert result.current_value == "sRGB"
    assert result.expected_value == "Raw"


def test_data_color_space_rule_skips_color_semantics():
    result = evaluate(
        "common.texture.colorspace.data_raw",
        semantic_slot="base_color",
        color_space="sRGB",
    )

    assert result.status == "skipped"
    assert result.evidence["reason"] == "no_matching_targets"


def test_color_managed_rule_pack_has_production_defaults():
    rule = load_color_space_rule("common.texture.colorspace.color_managed")

    assert rule.scope == "texture_node"
    assert rule.severity == "error"
    assert rule.match.criteria["semantic_slot"] == [
        "base_color",
        "specular_color",
        "emission",
    ]
    assert rule.check.type == "attribute_in"
    assert rule.check.params["attribute"] == "colorSpace"
    assert rule.check.params["expected"] == ["sRGB", "ACEScg"]
    assert rule.policy.block_publish is True
    assert rule.policy.block_deadline is False
    assert rule.policy.auto_fix_allowed is True
    assert rule.fix is not None
    assert rule.fix.type == "set_attr"
    assert rule.fix.params["value"] == "sRGB"


def test_color_managed_rule_fails_for_raw_base_color():
    result = evaluate(
        "common.texture.colorspace.color_managed",
        semantic_slot="base_color",
        color_space="Raw",
    )

    assert result.status == "failed"
    assert result.severity == "error"
    assert result.current_value == "Raw"
    assert result.expected_value == ["sRGB", "ACEScg"]
    assert result.block_publish is True
    assert result.block_deadline is False
    assert result.auto_fix_available is True
    assert result.fix_id == "set_attr"


def test_color_managed_rule_passes_for_srgb_base_color():
    result = evaluate(
        "common.texture.colorspace.color_managed",
        semantic_slot="base_color",
        color_space="sRGB",
    )

    assert result.status == "passed"
    assert result.block_publish is False
    assert result.block_deadline is False


def test_color_managed_rule_skips_data_semantics():
    result = evaluate(
        "common.texture.colorspace.color_managed",
        semantic_slot="roughness",
        color_space="Raw",
    )

    assert result.status == "skipped"
    assert result.evidence["reason"] == "no_matching_targets"
