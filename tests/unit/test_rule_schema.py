import pytest

from shader_health.core import RuleDefinition, RuleFix, RulePolicy, RuleSchemaError


def make_rule_data():
    return {
        "schema_version": "1.0",
        "id": "common.texture.colorspace.data_raw",
        "name": "Data textures must use Raw color space",
        "enabled": True,
        "renderer": ["common", "vray", "arnold"],
        "scope": "texture_node",
        "severity": "critical",
        "owner": "shader_td",
        "message": "Data texture uses a color-managed color space.",
        "why": (
            "Roughness, masks, normal, bump, and displacement maps store numeric data. "
            "Color transforms can change those numeric values."
        ),
        "match": {
            "semantic_slot": ["roughness", "normal", "displacement", "mask"],
            "node_type": ["file", "VRayBitmap", "aiImage"],
        },
        "check": {
            "type": "attribute_equals",
            "attribute": "colorSpace",
            "expected": "Raw",
        },
        "policy": {
            "block_publish": True,
            "block_deadline": True,
            "waiver_allowed": True,
            "auto_fix_allowed": True,
        },
        "fix": {
            "type": "set_attr",
            "attribute": "colorSpace",
            "value": "Raw",
            "risk": "low",
        },
    }


def test_rule_definition_round_trip():
    data = make_rule_data()

    rule = RuleDefinition.from_dict(data)
    restored = RuleDefinition.from_dict(rule.to_dict())

    assert restored == rule
    assert rule.id == "common.texture.colorspace.data_raw"
    assert rule.policy == RulePolicy(
        block_publish=True,
        block_deadline=True,
        waiver_allowed=True,
        auto_fix_allowed=True,
    )
    assert rule.fix == RuleFix(
        type="set_attr",
        risk="low",
        params={"attribute": "colorSpace", "value": "Raw"},
    )
    assert rule.check.to_dict()["expected"] == "Raw"


def test_rule_definition_rejects_missing_required_field():
    data = make_rule_data()
    data.pop("why")

    with pytest.raises(RuleSchemaError, match="missing required field.*why"):
        RuleDefinition.from_dict(data)


def test_rule_definition_rejects_invalid_severity():
    data = make_rule_data()
    data["severity"] = "blocker"

    with pytest.raises(RuleSchemaError, match="severity must be one of"):
        RuleDefinition.from_dict(data)


def test_rule_definition_rejects_invalid_scope():
    data = make_rule_data()
    data["scope"] = "texture_magic"

    with pytest.raises(RuleSchemaError, match="scope must be one of"):
        RuleDefinition.from_dict(data)


def test_rule_definition_requires_non_empty_renderer_list():
    data = make_rule_data()
    data["renderer"] = []

    with pytest.raises(RuleSchemaError, match="renderer must be a non-empty list"):
        RuleDefinition.from_dict(data)


def test_rule_definition_rejects_fix_when_policy_disallows_autofix():
    data = make_rule_data()
    data["policy"]["auto_fix_allowed"] = False

    with pytest.raises(RuleSchemaError, match="fix is defined but policy.auto_fix_allowed is false"):
        RuleDefinition.from_dict(data)


def test_rule_definition_rejects_invalid_fix_risk():
    data = make_rule_data()
    data["fix"]["risk"] = "instant"

    with pytest.raises(RuleSchemaError, match="fix.risk must be one of"):
        RuleDefinition.from_dict(data)


def test_rule_definition_rejects_non_boolean_policy_value():
    data = make_rule_data()
    data["policy"]["block_deadline"] = "yes"

    with pytest.raises(RuleSchemaError, match="policy.block_deadline must be a boolean"):
        RuleDefinition.from_dict(data)
