from __future__ import annotations

from pathlib import Path

from pipeline_inspector.core import (
    GraphSnapshot,
    MaterialSnapshot,
    NodeSnapshot,
    RuleDefinition,
    ValidationEngine,
    load_rule_file,
)
from pipeline_inspector.core.rule_loader import apply_profile_overrides, load_profile
from pipeline_inspector.maya.snapshot_enrichment import prepare_snapshot_for_validation

ROOT = Path(__file__).resolve().parents[2]
ARNOLD_RULES = ROOT / "src" / "pipeline_inspector" / "rules" / "arnold" / "renderer_health.json"
PUBLISH_STRICT = ROOT / "src" / "pipeline_inspector" / "rules" / "profiles" / "publish_strict.json"


def _policy_rules() -> dict[str, RuleDefinition]:
    rules = load_rule_file(ARNOLD_RULES)
    return {rule.id: rule for rule in rules}


def test_arnold_policy_rules_validate_with_rule_loader():
    rules = load_rule_file(ARNOLD_RULES)
    rule_ids = {rule.id for rule in rules}

    assert {
        "arnold.scene.plugin_missing.error",
        "arnold.material.displacement_review.warning",
        "arnold.material.texture_budget.warning",
        "arnold.material.transmission_depth.warning",
        "arnold.scene.stand_in_review.warning",
    } <= rule_ids


def test_arnold_plugin_missing_rule_fails_without_options_node():
    snapshot = prepare_snapshot_for_validation(
        GraphSnapshot(
            scene_path="D:/show/asset/shading/hero.ma",
            renderer="arnold",
            nodes=[
                NodeSnapshot(
                    id="node:hero_mtl",
                    name="hero_mtl",
                    type_name="aiStandardSurface",
                )
            ],
            materials=[
                MaterialSnapshot(
                    node_id="node:hero_mtl",
                    name="hero_mtl",
                    type_name="aiStandardSurface",
                    texture_nodes=["node:file_roughness"],
                )
            ],
        )
    )
    rule = _policy_rules()["arnold.scene.plugin_missing.error"]

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.current_value is False
    assert result.expected_value is True


def test_arnold_plugin_missing_rule_passes_when_options_node_exists():
    snapshot = prepare_snapshot_for_validation(
        GraphSnapshot(
            scene_path="D:/show/asset/shading/hero.ma",
            renderer="arnold",
            nodes=[
                NodeSnapshot(
                    id="node:defaultArnoldRenderOptions",
                    name="defaultArnoldRenderOptions",
                    type_name="aiOptions",
                ),
                NodeSnapshot(
                    id="node:hero_mtl",
                    name="hero_mtl",
                    type_name="aiStandardSurface",
                ),
            ],
            materials=[
                MaterialSnapshot(
                    node_id="node:hero_mtl",
                    name="hero_mtl",
                    type_name="aiStandardSurface",
                    texture_nodes=["node:file_roughness"],
                )
            ],
        )
    )
    rule = _policy_rules()["arnold.scene.plugin_missing.error"]

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"


def test_arnold_displacement_review_rule_uses_enrichment_metadata():
    snapshot = prepare_snapshot_for_validation(
        GraphSnapshot(
            scene_path="D:/show/asset/shading/hero.ma",
            renderer="arnold",
            nodes=[
                NodeSnapshot(
                    id="node:hero_mtl",
                    name="hero_mtl",
                    type_name="aiStandardSurface",
                )
            ],
            materials=[
                MaterialSnapshot(
                    node_id="node:hero_mtl",
                    name="hero_mtl",
                    type_name="aiStandardSurface",
                    displacement_nodes=["node:disp_shader"],
                )
            ],
        )
    )
    rule = _policy_rules()["arnold.material.displacement_review.warning"]

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.plug == "arnold_metadata.displacement_linked"
    assert result.current_value is True


def test_arnold_texture_budget_rule_uses_enrichment_texture_count():
    texture_nodes = [f"node:file_{index}" for index in range(25)]
    snapshot = prepare_snapshot_for_validation(
        GraphSnapshot(
            scene_path="D:/show/asset/shading/hero.ma",
            renderer="arnold",
            nodes=[
                NodeSnapshot(
                    id="node:hero_mtl",
                    name="hero_mtl",
                    type_name="aiStandardSurface",
                )
            ],
            materials=[
                MaterialSnapshot(
                    node_id="node:hero_mtl",
                    name="hero_mtl",
                    type_name="aiStandardSurface",
                    texture_nodes=texture_nodes,
                )
            ],
        )
    )
    rule = _policy_rules()["arnold.material.texture_budget.warning"]

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.current_value == 25
    assert result.expected_value == 24


def test_arnold_transmission_depth_rule_uses_enrichment_limit_attrs():
    snapshot = prepare_snapshot_for_validation(
        GraphSnapshot(
            scene_path="D:/show/asset/shading/hero.ma",
            renderer="arnold",
            nodes=[
                NodeSnapshot(
                    id="node:hero_mtl",
                    name="hero_mtl",
                    type_name="aiStandardSurface",
                    attrs={"transmissionDepth": 16},
                )
            ],
            materials=[
                MaterialSnapshot(
                    node_id="node:hero_mtl",
                    name="hero_mtl",
                    type_name="aiStandardSurface",
                    texture_nodes=["node:file_roughness"],
                )
            ],
        )
    )
    rule = _policy_rules()["arnold.material.transmission_depth.warning"]

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.current_value == 16
    assert result.expected_value == 8


def test_arnold_stand_in_review_rule_uses_scene_enrichment_metadata():
    snapshot = prepare_snapshot_for_validation(
        GraphSnapshot(
            scene_path="D:/show/asset/shading/hero.ma",
            renderer="arnold",
            nodes=[
                NodeSnapshot(
                    id="node:hero_mtl",
                    name="hero_mtl",
                    type_name="aiStandardSurface",
                ),
                NodeSnapshot(
                    id="node:hero_proxyStandIn",
                    name="hero_proxyStandIn",
                    type_name="aiStandIn",
                ),
            ],
            materials=[
                MaterialSnapshot(
                    node_id="node:hero_mtl",
                    name="hero_mtl",
                    type_name="aiStandardSurface",
                    texture_nodes=["node:file_roughness"],
                )
            ],
        )
    )
    rule = _policy_rules()["arnold.scene.stand_in_review.warning"]

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.plug == "arnold_scene_metadata.has_stand_ins"
    assert result.current_value is True


def test_publish_strict_profile_blocks_on_arnold_plugin_rule():
    rules = apply_profile_overrides(load_rule_file(ARNOLD_RULES), load_profile(PUBLISH_STRICT))
    rule = next(item for item in rules if item.id == "arnold.scene.plugin_missing.error")

    assert rule.policy.block_publish is True
