from __future__ import annotations

from pathlib import Path

from shader_health.core import GraphSnapshot, NodeSnapshot
from shader_health.maya.validation_pipeline import (
    list_packaged_profile_ids,
    packaged_profile_path,
    run_validation,
)


def test_list_packaged_profile_ids_includes_mvp_profiles():
    profile_ids = list_packaged_profile_ids()

    assert "artist_relaxed" in profile_ids
    assert "publish_strict" in profile_ids
    assert "deadline_critical" in profile_ids
    assert "supervisor_full" in profile_ids
    assert "ci_headless" in profile_ids


def test_packaged_profile_path_resolves_known_profile():
    path = packaged_profile_path("artist_relaxed")

    assert path.is_file()
    assert path.name == "artist_relaxed.json"


def test_run_validation_enriches_results_and_loads_renderer_rules(tmp_path: Path):
    snapshot = GraphSnapshot(
        scene_path=str(tmp_path / "demo.ma"),
        renderer="vray",
        nodes=[
            NodeSnapshot(
                id="node:file1",
                name="file1",
                type_name="file",
                attrs={"colorSpace": "sRGB", "semantic_slot": "roughness"},
            ),
            NodeSnapshot(
                id="node:mtl1",
                name="mtl1",
                type_name="VRayMtl",
            ),
        ],
    )

    run = run_validation(snapshot, profile_id="artist_relaxed")

    assert run.profile_id == "artist_relaxed"
    assert run.snapshot is not None
    assert any(rule.renderer == ("vray",) or "vray" in rule.renderer for rule in run.rules)
    assert run.health_score.score <= 100
    assert "validated with profile artist_relaxed" in run.message.casefold()


def test_run_validation_enriches_failed_result_materials(tmp_path: Path):
    from tests.unit.test_snapshot_enrichment import _broken_scene_like_snapshot

    snapshot = _broken_scene_like_snapshot(tmp_path)
    run = run_validation(snapshot, profile_id="artist_relaxed")
    failed = [item for item in run.results if item.status == "failed"]

    assert failed
    assert any(item.material for item in failed)
    colorspace = next(
        item for item in failed if item.rule_id == "common.texture.colorspace.data_raw"
    )
    assert colorspace.material == "demo_wrong_colorspace_MTL"
