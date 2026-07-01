from __future__ import annotations

from shader_health.core.fix_plan import build_fix_plan
from shader_health.core.models import GraphSnapshot, MaterialSnapshot, NodeSnapshot
from shader_health.core.rule_schema import (
    RuleCheck,
    RuleDefinition,
    RuleFix,
    RuleMatch,
    RulePolicy,
    RuleResult,
)


def test_fix_planner_builds_action_for_failed_result_with_rule_fix():
    rule = _rule_with_fix()
    result = _failed_result()
    snapshot = _snapshot(
        NodeSnapshot(
            id="node:file1",
            name="file1",
            full_name="asset:file1",
            type_name="file",
            attrs={"colorSpace": "ACEScg"},
        )
    )

    plan = build_fix_plan([result], [rule], snapshot)

    assert plan.total == 1
    assert plan.safe_count == 1
    assert plan.blocked_count == 0
    action = plan.actions[0]
    assert action.rule_id == "common.texture.colorspace.data_raw"
    assert action.fix_type == "set_attr"
    assert action.risk == "low"
    assert action.target_node == "asset:file1"
    assert action.target_attr == "colorSpace"
    assert action.before_value == "ACEScg"
    assert action.after_value == "Raw"
    assert action.referenced is False
    assert action.locked is False
    assert action.blocked is False


def test_fix_planner_skips_non_failed_results_and_rules_without_fix():
    snapshot = _snapshot(NodeSnapshot(id="node:file1", name="file1", type_name="file"))
    passed = _failed_result(status="passed")
    no_fix_rule = _rule_with_fix(fix=None)

    plan = build_fix_plan([passed, _failed_result()], [no_fix_rule], snapshot)

    assert plan.total == 0
    assert plan.to_dict() == {
        "total": 0,
        "safe_count": 0,
        "blocked_count": 0,
        "actions": [],
    }


def test_fix_planner_includes_referenced_and_locked_status():
    rule = _rule_with_fix()
    result = _failed_result()
    snapshot = _snapshot(
        NodeSnapshot(
            id="node:file1",
            name="file1",
            type_name="file",
            referenced=True,
            reference_path="D:/show/assets/char/hero.ma",
            locked=True,
        )
    )

    plan = build_fix_plan([result], [rule], snapshot)

    action = plan.actions[0]
    assert action.referenced is True
    assert action.locked is True
    assert action.reference_path == "D:/show/assets/char/hero.ma"
    assert action.requires_reference_edit is True
    assert action.blocked is True
    assert action.block_reasons == ["target_referenced", "target_locked"]
    assert plan.blocked_count == 1


def test_fix_planner_marks_high_risk_actions_as_supervisor_required_and_blocked():
    rule = _rule_with_fix(
        fix=RuleFix(
            type="cleanup_orphan",
            risk="high",
            params={"value": "delete_unused_network"},
        )
    )
    result = _failed_result()
    snapshot = _snapshot(NodeSnapshot(id="node:file1", name="file1", type_name="file"))

    plan = build_fix_plan([result], [rule], snapshot)

    action = plan.actions[0]
    assert action.risk == "high"
    assert action.requires_supervisor is True
    assert action.undo_supported is False
    assert action.blocked is True
    assert action.block_reasons == ["high_risk_requires_explicit_confirmation"]


def test_fix_planner_resolves_material_target_to_underlying_node():
    rule = _rule_with_fix()
    result = _failed_result(
        target_kind="material",
        target_id="node:mat1",
        node="mat1",
    )
    snapshot = GraphSnapshot(
        nodes=(
            NodeSnapshot(
                id="node:mat1",
                name="mat1",
                full_name="asset:mat1",
                type_name="VRayMtl",
                referenced=True,
            ),
        ),
        materials=(
            MaterialSnapshot(
                node_id="node:mat1",
                name="mat1",
                type_name="VRayMtl",
            ),
        ),
    )

    plan = build_fix_plan([result], [rule], snapshot)

    action = plan.actions[0]
    assert action.target_node == "asset:mat1"
    assert action.referenced is True
    assert action.block_reasons == ["target_referenced"]


def _rule_with_fix(fix: RuleFix | None = None) -> RuleDefinition:
    if fix is None:
        fix = RuleFix(
            type="set_attr",
            risk="low",
            params={"attribute": "colorSpace", "value": "Raw"},
        )
    return RuleDefinition(
        id="common.texture.colorspace.data_raw",
        name="Data textures must use Raw color space",
        enabled=True,
        renderer=["common"],
        scope="texture_node",
        severity="critical",
        owner="shader_td",
        message="Data texture uses a color-managed color space.",
        why="Data textures must not be color transformed.",
        match=RuleMatch(criteria={"node_type": ["file"]}),
        check=RuleCheck(type="attribute_equals", params={"attribute": "colorSpace"}),
        policy=RulePolicy(auto_fix_allowed=True),
        fix=fix,
    )


def _failed_result(
    *,
    status: str = "failed",
    target_kind: str = "node",
    target_id: str = "node:file1",
    node: str = "file1",
) -> RuleResult:
    return RuleResult(
        rule_id="common.texture.colorspace.data_raw",
        severity="critical",
        status=status,
        title="Data textures must use Raw color space",
        message="Data texture uses a color-managed color space.",
        why="Data textures must not be color transformed.",
        owner="shader_td",
        target_kind=target_kind,
        target_id=target_id,
        node=node,
        plug="colorSpace",
        current_value="ACEScg",
        expected_value="Raw",
        auto_fix_available=True,
        fix_id="set_attr",
    )


def _snapshot(node: NodeSnapshot) -> GraphSnapshot:
    return GraphSnapshot(nodes=(node,))
