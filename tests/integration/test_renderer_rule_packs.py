"""Integration tests for packaged renderer rule packs."""

from __future__ import annotations

from pathlib import Path

from tests.integration.fixtures import arnold_scene_snapshot, broken_scene_snapshot

from shader_health.maya.validation_pipeline import run_validation


def test_vray_renderer_pack_flags_missing_plugin_node(tmp_path: Path):
    snapshot = broken_scene_snapshot(tmp_path)
    run = run_validation(snapshot, profile_id="supervisor_full", scan_scope="scene")

    failed = next(
        item
        for item in run.results
        if item.rule_id == "vray.scene.plugin_missing.error" and item.status == "failed"
    )
    assert failed.current_value is False


def test_vray_renderer_pack_flags_displacement_review_material(tmp_path: Path):
    snapshot = broken_scene_snapshot(tmp_path)
    run = run_validation(snapshot, profile_id="supervisor_full", scan_scope="scene")

    failed = [
        item
        for item in run.results
        if item.rule_id == "vray.material.displacement_review.warning" and item.status == "failed"
    ]
    assert failed
    assert failed[0].material == "demo_displacement_MTL"


def test_publish_strict_profile_blocks_on_vray_plugin_rule(tmp_path: Path):
    snapshot = broken_scene_snapshot(tmp_path)
    run = run_validation(snapshot, profile_id="publish_strict", scan_scope="scene")

    failed = next(
        item
        for item in run.results
        if item.rule_id == "vray.scene.plugin_missing.error" and item.status == "failed"
    )
    assert failed.block_publish is True


def test_vray_renderer_pack_flags_untextured_material(tmp_path: Path):
    snapshot = broken_scene_snapshot(tmp_path)
    run = run_validation(snapshot, profile_id="supervisor_full", scan_scope="scene")

    info_results = [
        item
        for item in run.results
        if item.rule_id == "vray.material.untextured.info" and item.status == "failed"
    ]
    assert info_results
    assert info_results[0].material == "demo_untextured_MTL"


def test_vray_renderer_pack_flags_displacement_linked_material(tmp_path: Path):
    snapshot = broken_scene_snapshot(tmp_path)
    displacement_material = next(
        material for material in snapshot.materials if material.name == "demo_displacement_MTL"
    )
    assert displacement_material.displacement_nodes

    run = run_validation(snapshot, profile_id="supervisor_full", scan_scope="scene")
    info_results = [
        item
        for item in run.results
        if item.rule_id == "vray.material.displacement_linked.info" and item.status == "failed"
    ]
    assert info_results
    assert info_results[0].material == "demo_displacement_MTL"


def test_arnold_renderer_pack_flags_untextured_material(tmp_path: Path):
    snapshot = arnold_scene_snapshot(tmp_path)
    run = run_validation(snapshot, profile_id="supervisor_full", scan_scope="scene")

    info_results = [
        item
        for item in run.results
        if item.rule_id == "arnold.material.untextured.info" and item.status == "failed"
    ]
    assert info_results
    assert info_results[0].material == "aiStandardSurface1"


def test_renderer_rules_are_loaded_for_matching_renderer(tmp_path: Path):
    snapshot = broken_scene_snapshot(tmp_path)
    run = run_validation(snapshot, profile_id="artist_relaxed", scan_scope="scene")

    rule_ids = {rule.id for rule in run.rules}
    assert "vray.material.untextured.info" in rule_ids
    assert "vray.material.displacement_linked.info" in rule_ids
    assert "vray.scene.plugin_missing.error" in rule_ids
    assert "vray.material.displacement_review.warning" in rule_ids
    assert "vray.material.texture_budget.warning" in rule_ids
    assert "vray.material.trace_depth.warning" in rule_ids
