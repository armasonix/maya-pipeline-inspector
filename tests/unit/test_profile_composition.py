from __future__ import annotations

import pytest

from shader_health.core.rule_loader import RuleLoadError
from shader_health.maya.validation_pipeline import (
    ASSET_CLASS_PROFILE_IDS,
    WORKFLOW_PROFILE_IDS,
    compose_profiles,
    list_asset_class_profile_options,
    list_workflow_profile_options,
    run_validation,
)
from shader_health.core import GraphSnapshot, MaterialSnapshot


def test_list_workflow_profile_options_excludes_asset_class_and_ci_headless():
    options = list_workflow_profile_options()
    ids = {option.profile_id for option in options}

    assert ids == set(WORKFLOW_PROFILE_IDS)
    assert "ci_headless" not in ids
    assert not ids.intersection(ASSET_CLASS_PROFILE_IDS)


def test_list_asset_class_profile_options_returns_resolution_profiles():
    options = list_asset_class_profile_options()
    ids = {option.profile_id for option in options}

    assert ids == set(ASSET_CLASS_PROFILE_IDS)


def test_compose_profiles_merges_asset_class_resolution_rules():
    composed = compose_profiles("publish_strict", "asset_class_hero")

    hero_override = composed.rule_overrides["common.texture.resolution.hero.max"]
    prop_override = composed.rule_overrides["common.texture.resolution.prop.max"]

    assert hero_override.enabled is True
    assert prop_override.enabled is False


def test_compose_profiles_without_asset_class_returns_workflow_profile():
    composed = compose_profiles("artist_relaxed", None)

    assert composed.id == "artist_relaxed"
    assert "common.texture.resolution.hero.max" not in composed.rule_overrides


def test_compose_profiles_rejects_asset_class_as_workflow():
    with pytest.raises(RuleLoadError, match="workflow profile"):
        compose_profiles("asset_class_hero", None)


def test_compose_profiles_accepts_pipeline_profile_standalone():
    composed = compose_profiles("ci_headless", None)

    assert composed.id == "ci_headless"
    assert composed.rule_overrides["common.shader_network.shading_engine.empty"].enabled is False


def test_compose_profiles_rejects_asset_class_overlay_on_pipeline_profile():
    with pytest.raises(RuleLoadError, match="pipeline profile"):
        compose_profiles("ci_headless", "asset_class_hero")


def test_run_validation_accepts_ci_headless_profile():
    snapshot = GraphSnapshot(
        scene_path="scene.ma",
        maya_version="2025",
        renderer="vray",
        scan_scope="scene",
        scanned_at_utc="2026-07-01T12:00:00Z",
        materials=[
            MaterialSnapshot(
                node_id="node:hero_mtl",
                name="hero_mtl",
                type_name="VRayMtl",
                renderer_family="vray",
            )
        ],
    )

    result = run_validation(snapshot, profile_id="ci_headless")

    assert result.profile_id == "ci_headless"
    assert "ci_headless" in result.message


def test_run_validation_accepts_asset_class_overlay():
    snapshot = GraphSnapshot(
        scene_path="scene.ma",
        maya_version="2025",
        renderer="vray",
        scan_scope="scene",
        scanned_at_utc="2026-07-01T12:00:00Z",
        materials=[
            MaterialSnapshot(
                node_id="node:hero_mtl",
                name="hero_mtl",
                type_name="VRayMtl",
                renderer_family="vray",
            )
        ],
    )

    result = run_validation(
        snapshot,
        profile_id="artist_relaxed",
        asset_class_id="asset_class_hero",
    )

    assert result.profile_id == "artist_relaxed"
    assert result.asset_class_id == "asset_class_hero"
    assert "asset_class_hero" in result.message
