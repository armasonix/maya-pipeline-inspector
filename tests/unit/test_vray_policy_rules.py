from __future__ import annotations

from pathlib import Path

from shader_health.core import (
    GraphSnapshot,
    MaterialSnapshot,
    NodeSnapshot,
    RuleDefinition,
    ValidationEngine,
    load_rule_file,
)
from shader_health.core.rule_loader import apply_profile_overrides, load_profile
from shader_health.maya.snapshot_enrichment import prepare_snapshot_for_validation

ROOT = Path(__file__).resolve().parents[2]
VRAY_RULES = ROOT / "src" / "shader_health" / "rules" / "vray" / "renderer_health.json"
PUBLISH_STRICT = ROOT / "src" / "shader_health" / "rules" / "profiles" / "publish_strict.json"


def _policy_rules() -> dict[str, RuleDefinition]:
    rules = load_rule_file(VRAY_RULES)
    return {rule.id: rule for rule in rules}


def test_vray_policy_rules_validate_with_rule_loader():
    rules = load_rule_file(VRAY_RULES)
    rule_ids = {rule.id for rule in rules}

    assert {
        "vray.scene.plugin_missing.error",
        "vray.material.displacement_review.warning",
        "vray.material.texture_budget.warning",
        "vray.material.trace_depth.warning",
    } <= rule_ids


def test_vray_plugin_missing_rule_fails_without_settings_node():
    snapshot = prepare_snapshot_for_validation(
        GraphSnapshot(
            scene_path="D:/show/asset/shading/hero.ma",
            renderer="vray",
            nodes=[
                NodeSnapshot(
                    id="node:hero_mtl",
                    name="hero_mtl",
                    type_name="VRayMtl",
                )
            ],
            materials=[
                MaterialSnapshot(
                    node_id="node:hero_mtl",
                    name="hero_mtl",
                    type_name="VRayMtl",
                    texture_nodes=["node:file_roughness"],
                )
            ],
        )
    )
    rule = _policy_rules()["vray.scene.plugin_missing.error"]

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.current_value is False
    assert result.expected_value is True


def test_vray_plugin_missing_rule_passes_when_settings_node_exists():
    snapshot = prepare_snapshot_for_validation(
        GraphSnapshot(
            scene_path="D:/show/asset/shading/hero.ma",
            renderer="vray",
            nodes=[
                NodeSnapshot(
                    id="node:vraySettings",
                    name="vraySettings",
                    type_name="VRaySettingsNode",
                ),
                NodeSnapshot(
                    id="node:hero_mtl",
                    name="hero_mtl",
                    type_name="VRayMtl",
                ),
            ],
            materials=[
                MaterialSnapshot(
                    node_id="node:hero_mtl",
                    name="hero_mtl",
                    type_name="VRayMtl",
                    texture_nodes=["node:file_roughness"],
                )
            ],
        )
    )
    rule = _policy_rules()["vray.scene.plugin_missing.error"]

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"


def test_vray_displacement_review_rule_uses_enrichment_metadata():
    snapshot = prepare_snapshot_for_validation(
        GraphSnapshot(
            scene_path="D:/show/asset/shading/hero.ma",
            renderer="vray",
            nodes=[
                NodeSnapshot(
                    id="node:hero_mtl",
                    name="hero_mtl",
                    type_name="VRayMtl",
                )
            ],
            materials=[
                MaterialSnapshot(
                    node_id="node:hero_mtl",
                    name="hero_mtl",
                    type_name="VRayMtl",
                    displacement_nodes=["node:disp_shader"],
                )
            ],
        )
    )
    rule = _policy_rules()["vray.material.displacement_review.warning"]

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.plug == "vray_metadata.displacement_linked"
    assert result.current_value is True


def test_vray_texture_budget_rule_uses_enrichment_texture_count():
    texture_nodes = [f"node:file_{index}" for index in range(25)]
    snapshot = prepare_snapshot_for_validation(
        GraphSnapshot(
            scene_path="D:/show/asset/shading/hero.ma",
            renderer="vray",
            nodes=[
                NodeSnapshot(
                    id="node:hero_mtl",
                    name="hero_mtl",
                    type_name="VRayMtl",
                )
            ],
            materials=[
                MaterialSnapshot(
                    node_id="node:hero_mtl",
                    name="hero_mtl",
                    type_name="VRayMtl",
                    texture_nodes=texture_nodes,
                )
            ],
        )
    )
    rule = _policy_rules()["vray.material.texture_budget.warning"]

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.current_value == 25
    assert result.expected_value == 24


def test_vray_trace_depth_rule_uses_enrichment_limit_attrs():
    snapshot = prepare_snapshot_for_validation(
        GraphSnapshot(
            scene_path="D:/show/asset/shading/hero.ma",
            renderer="vray",
            nodes=[
                NodeSnapshot(
                    id="node:hero_mtl",
                    name="hero_mtl",
                    type_name="VRayMtl",
                    attrs={"rlmd": 16},
                )
            ],
            materials=[
                MaterialSnapshot(
                    node_id="node:hero_mtl",
                    name="hero_mtl",
                    type_name="VRayMtl",
                    texture_nodes=["node:file_roughness"],
                )
            ],
        )
    )
    rule = _policy_rules()["vray.material.trace_depth.warning"]

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.current_value == 16
    assert result.expected_value == 8


def test_publish_strict_profile_blocks_on_vray_plugin_rule():
    rules = apply_profile_overrides(load_rule_file(VRAY_RULES), load_profile(PUBLISH_STRICT))
    rule = next(item for item in rules if item.id == "vray.scene.plugin_missing.error")

    assert rule.policy.block_publish is True
