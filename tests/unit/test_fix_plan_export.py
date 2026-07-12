from __future__ import annotations

import json
from pathlib import Path

from pipeline_inspector.core.fix_plan import FixAction, FixPlan, build_fix_plan
from pipeline_inspector.core.models import GraphSnapshot, NodeSnapshot
from pipeline_inspector.core.rule_schema import (
    RuleCheck,
    RuleDefinition,
    RuleFix,
    RuleMatch,
    RulePolicy,
    RuleResult,
)
from pipeline_inspector.reports import (
    FIX_PLAN_SCHEMA_VERSION,
    build_fix_plan_export,
    dumps_fix_plan_export,
    write_fix_plan_export,
)


def test_build_fix_plan_export_includes_adr_metadata():
    snapshot = _snapshot(
        NodeSnapshot(
            id="node:file1",
            name="file1",
            full_name="asset:file1",
            type_name="file",
            referenced=True,
            locked=True,
            reference_path="D:/show/assets/char/hero.ma",
        )
    )
    rule = _rule_with_fix()
    result = _failed_result()
    plan = build_fix_plan([result], [rule], snapshot)

    payload = build_fix_plan_export(
        plan,
        snapshot=snapshot,
        profile_id="artist_relaxed",
    )

    assert payload["fix_plan_schema_version"] == FIX_PLAN_SCHEMA_VERSION
    assert payload["scene_path"] == snapshot.scene_path
    assert payload["profile_id"] == "artist_relaxed"
    assert payload["scan_scope"] == "scene"
    assert payload["total"] == 1
    assert payload["blocked_count"] == 1
    assert payload["safe_count"] == 0
    action = payload["actions"][0]
    assert action["risk"] == "low"
    assert action["target_node"] == "asset:file1"
    assert action["before_value"] == "ACEScg"
    assert action["after_value"] == "Raw"
    assert action["referenced"] is True
    assert action["locked"] is True
    assert action["block_reasons"] == ["target_locked"]


def test_fix_plan_export_output_is_deterministic():
    snapshot = _snapshot(NodeSnapshot(id="node:file1", name="file1", type_name="file"))
    plan = FixPlan(
        actions=(
            FixAction(
                fix_id="z.fix",
                rule_id="rule.z",
                title="Z",
                fix_type="set_attr",
                risk="low",
                target_kind="node",
                target_id="node:file2",
                target_node="file2",
                target_attr="colorSpace",
            ),
            FixAction(
                fix_id="a.fix",
                rule_id="rule.a",
                title="A",
                fix_type="set_attr",
                risk="low",
                target_kind="node",
                target_id="node:file1",
                target_node="file1",
                target_attr="colorSpace",
            ),
        )
    )

    first = dumps_fix_plan_export(plan, snapshot=snapshot, profile_id="artist_relaxed")
    second = dumps_fix_plan_export(
        FixPlan(actions=tuple(reversed(plan.actions))),
        snapshot=snapshot,
        profile_id="artist_relaxed",
    )

    assert first == second
    assert first.endswith("\n")
    assert json.loads(first)["actions"][0]["fix_id"] == "a.fix"


def test_write_fix_plan_export_round_trips_through_json(tmp_path: Path):
    snapshot = _snapshot(NodeSnapshot(id="node:file1", name="file1", type_name="file"))
    plan = build_fix_plan([_failed_result()], [_rule_with_fix()], snapshot)
    output_path = tmp_path / "hero_pipeline_inspector_fix_plan.json"

    written_path = write_fix_plan_export(
        output_path,
        plan,
        snapshot=snapshot,
        profile_id="artist_relaxed",
    )

    payload = json.loads(written_path.read_text(encoding="utf-8"))
    assert payload == build_fix_plan_export(
        plan,
        snapshot=snapshot,
        profile_id="artist_relaxed",
    )


def _snapshot(node: NodeSnapshot) -> GraphSnapshot:
    return GraphSnapshot(
        scene_path="D:/show/asset/shading/hero.ma",
        maya_version="2025",
        renderer="vray",
        scan_scope="scene",
        scanned_at_utc="2026-07-01T12:00:00Z",
        nodes=[node],
    )


def _failed_result() -> RuleResult:
    return RuleResult(
        rule_id="common.texture.colorspace.data_raw",
        severity="critical",
        status="failed",
        title="Data texture color space",
        message="Data texture uses a color-managed color space.",
        why="Data textures must not be color transformed.",
        owner="shader_td",
        target_kind="node",
        target_id="node:file1",
        node="file1",
        plug="colorSpace",
        current_value="ACEScg",
        expected_value="Raw",
        block_publish=True,
        block_deadline=False,
        auto_fix_available=True,
        fix_id="set_attr",
    )


def _rule_with_fix() -> RuleDefinition:
    return RuleDefinition(
        id="common.texture.colorspace.data_raw",
        name="Data textures must use Raw color space",
        enabled=True,
        renderer=("common",),
        scope="texture_node",
        severity="critical",
        owner="shader_td",
        message="Data texture uses a color-managed color space.",
        why="Data textures must not be color transformed.",
        match=RuleMatch(criteria={"node_type": ["file"]}),
        check=RuleCheck(type="attribute_equals", params={"attribute": "colorSpace"}),
        policy=RulePolicy(auto_fix_allowed=True),
        fix=RuleFix(
            type="set_attr",
            risk="low",
            params={"attribute": "colorSpace", "value": "Raw"},
        ),
    )
