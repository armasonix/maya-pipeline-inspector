import pytest

from shader_health.core import (
    FileDependencySnapshot,
    GraphSnapshot,
    NodeSnapshot,
    RuleDefinition,
    RuleFix,
    RulePolicy,
    RuleSchemaError,
    ValidationEngine,
    summarize_results,
)


def make_rule_data(
    rule_id: str = "common.texture.colorspace.data_raw",
    *,
    enabled: bool = True,
    severity: str = "critical",
    scope: str = "texture_node",
    auto_fix: bool = True,
    check_type: str = "attribute_equals",
):
    data = {
        "schema_version": "1.0",
        "id": rule_id,
        "name": "Data textures must use Raw color space",
        "enabled": enabled,
        "renderer": ["common", "vray", "arnold"],
        "scope": scope,
        "severity": severity,
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
            "type": check_type,
            "attribute": "colorSpace",
            "expected": "Raw",
        },
        "policy": {
            "block_publish": True,
            "block_deadline": True,
            "waiver_allowed": True,
            "auto_fix_allowed": auto_fix,
        },
    }
    if auto_fix:
        data["fix"] = {
            "type": "set_attr",
            "attribute": "colorSpace",
            "value": "Raw",
            "risk": "low",
        }
    return data


def make_snapshot(color_space: str = "Raw", *, texture_exists: bool = True) -> GraphSnapshot:
    return GraphSnapshot(
        scene_path="demo.ma",
        renderer="vray",
        nodes=[
            NodeSnapshot(
                id="node:file_roughness",
                name="file_roughness",
                type_name="file",
                attrs={
                    "colorSpace": color_space,
                    "semantic_slot": "roughness",
                    "fileTextureName": "roughness.<UDIM>.exr",
                },
                classification=["texture", "file"],
            )
        ],
        file_dependencies=[
            FileDependencySnapshot(
                node_id="node:file_roughness",
                attr="fileTextureName",
                raw_path="$ASSET_ROOT/tex/missing_roughness.exr",
                resolved_path="D:/show/assets/tex/missing_roughness.exr",
                exists=texture_exists,
                extension=".exr",
            )
        ],
    )


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

    error_match = "fix is defined but policy.auto_fix_allowed is false"
    with pytest.raises(RuleSchemaError, match=error_match):
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


def test_validation_engine_returns_passed_result_for_matching_attribute():
    snapshot = make_snapshot(color_space="Raw")
    rule = RuleDefinition.from_dict(make_rule_data())

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.current_value == "Raw"
    assert result.expected_value == "Raw"
    assert result.block_publish is False
    assert result.block_deadline is False
    assert result.auto_fix_available is False
    assert result.to_dict()["status"] == "passed"


def test_validation_engine_returns_failed_result_with_block_policy_and_fix():
    snapshot = make_snapshot(color_space="ACEScg")
    rule = RuleDefinition.from_dict(make_rule_data())

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.current_value == "ACEScg"
    assert result.expected_value == "Raw"
    assert result.block_publish is True
    assert result.block_deadline is True
    assert result.auto_fix_available is True
    assert result.fix_id == "set_attr"
    assert result.node == "file_roughness"
    assert result.plug == "colorSpace"


def test_validation_engine_returns_skipped_for_disabled_rule():
    snapshot = make_snapshot()
    rule = RuleDefinition.from_dict(make_rule_data(enabled=False))

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "skipped"
    assert result.evidence["reason"] == "rule_disabled"


def test_validation_engine_returns_skipped_when_no_targets_match():
    snapshot = make_snapshot()
    data = make_rule_data()
    data["match"]["node_type"] = ["aiImage"]
    rule = RuleDefinition.from_dict(data)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "skipped"
    assert result.evidence["reason"] == "no_matching_targets"


def test_validation_engine_reports_failed_missing_path():
    snapshot = make_snapshot(texture_exists=False)
    data = make_rule_data(
        rule_id="common.texture.missing",
        scope="file_dependency",
        auto_fix=False,
        check_type="path_exists",
    )
    data["match"] = {"dependency_kind": "texture"}
    rule = RuleDefinition.from_dict(data)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.target_kind == "file_dependency"
    assert result.current_value == "D:/show/assets/tex/missing_roughness.exr"
    assert result.expected_value == "existing file"
    assert result.block_deadline is True


def test_validation_engine_returns_skipped_for_unsupported_check_type():
    snapshot = make_snapshot()
    data = make_rule_data(check_type="not_implemented")
    rule = RuleDefinition.from_dict(data)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "skipped"
    assert result.evidence["reason"] == "unsupported_check_type:not_implemented"

def test_summary_counts_severity_and_status_independently():
    engine = ValidationEngine()
    snapshot = make_snapshot(color_space="ACEScg")
    failed_rule = RuleDefinition.from_dict(make_rule_data())
    skipped_rule = RuleDefinition.from_dict(make_rule_data(enabled=False))

    results = engine.validate(snapshot, [failed_rule, skipped_rule])
    summary = summarize_results(results)

    assert summary.total == 2
    assert summary.failed == 1
    assert summary.skipped == 1
    assert summary.critical == 2
    assert summary.block_publish is True
    assert summary.block_deadline is True
    assert summary.auto_fixable == 1
    assert summary.to_dict()["critical"] == 2


def test_critical_severity_does_not_implicitly_block_without_policy_flags():
    data = make_rule_data()
    data["policy"]["block_publish"] = False
    data["policy"]["block_deadline"] = False
    rule = RuleDefinition.from_dict(data)
    snapshot = make_snapshot(color_space="ACEScg")

    result = ValidationEngine().validate(snapshot, [rule])[0]
    summary = summarize_results([result])

    assert result.status == "failed"
    assert result.severity == "critical"
    assert result.block_publish is False
    assert result.block_deadline is False
    assert summary.critical == 1
    assert summary.block_publish is False
    assert summary.block_deadline is False


def test_warning_can_block_deadline_when_policy_explicitly_says_so():
    data = make_rule_data(severity="warning", auto_fix=False)
    data["policy"]["block_publish"] = False
    data["policy"]["block_deadline"] = True
    rule = RuleDefinition.from_dict(data)
    snapshot = make_snapshot(color_space="ACEScg")

    result = ValidationEngine().validate(snapshot, [rule])[0]
    summary = summarize_results([result])

    assert result.status == "failed"
    assert result.severity == "warning"
    assert result.block_publish is False
    assert result.block_deadline is True
    assert summary.warning == 1
    assert summary.block_publish is False
    assert summary.block_deadline is True


def test_passed_result_never_blocks_even_when_rule_policy_blocks():
    rule = RuleDefinition.from_dict(make_rule_data())
    snapshot = make_snapshot(color_space="Raw")

    result = ValidationEngine().validate(snapshot, [rule])[0]
    summary = summarize_results([result])

    assert result.status == "passed"
    assert result.severity == "critical"
    assert result.block_publish is False
    assert result.block_deadline is False
    assert summary.critical == 1
    assert summary.block_publish is False
    assert summary.block_deadline is False

