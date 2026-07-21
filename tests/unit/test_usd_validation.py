from __future__ import annotations

from pathlib import Path

import pytest

from pipeline_inspector.cli import (
    INPUT_AUTO,
    INPUT_SCENE,
    INPUT_SNAPSHOT,
    INPUT_USD,
    _resolve_input_kind,
)
from pipeline_inspector.core import GraphSnapshot
from pipeline_inspector.maya.snapshot_enrichment import prepare_snapshot_for_validation
from pipeline_inspector.maya.validation_pipeline import run_validation
from pipeline_inspector.usd.enrichment import is_usd_snapshot

FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "snapshots"
USD_FIXTURE = FIXTURES_ROOT / "usd_asset_broken.json"


def load_usd_fixture() -> GraphSnapshot:
    return GraphSnapshot.from_json(USD_FIXTURE.read_text(encoding="utf-8"))


def test_is_usd_snapshot_detects_renderer_and_metadata() -> None:
    snapshot = load_usd_fixture()
    assert is_usd_snapshot(snapshot) is True


def test_prepare_snapshot_for_validation_routes_usd_enrichment() -> None:
    snapshot = load_usd_fixture()
    enriched = prepare_snapshot_for_validation(snapshot)
    assert enriched.renderer == "usd"
    assert enriched.usd_stage_metadata is not None
    assert enriched.usd_stage_metadata.has_default_prim is False


def test_resolve_input_kind_auto_detects_usd_suffixes() -> None:
    assert _resolve_input_kind(Path("asset.usda"), INPUT_AUTO) == INPUT_USD
    assert _resolve_input_kind(Path("asset.usdc"), INPUT_AUTO) == INPUT_USD
    assert _resolve_input_kind(Path("snapshot.json"), INPUT_AUTO) == INPUT_SNAPSHOT


def test_usd_health_fixture_fails_expected_rules() -> None:
    run = run_validation(load_usd_fixture(), profile_id="publish_strict")
    failed_rule_ids = {item.rule_id for item in run.results if item.status == "failed"}
    assert "usd.stage.default_prim.required" in failed_rule_ids
    assert "usd.mesh.unbound_material.error" in failed_rule_ids
    assert "usd.reference.missing.error" in failed_rule_ids
    assert "usd.texture.missing" in failed_rule_ids
    assert "usd.texture.path.local_drive" in failed_rule_ids


def test_usd_default_prim_fix_plan_uses_suggested_prim() -> None:
    run = run_validation(load_usd_fixture(), profile_id="publish_strict")
    default_prim_actions = [
        action
        for action in run.fix_plan.actions
        if action.fix_type == "set_default_prim"
        and action.rule_id == "usd.stage.default_prim.required"
    ]
    assert len(default_prim_actions) == 1
    action = default_prim_actions[0]
    assert action.after_value == "/Hero"
    assert not action.blocked


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (Path("hero.usd"), INPUT_USD),
        (Path("hero.ma"), INPUT_SCENE),
    ],
)
def test_resolve_input_kind_auto(path: Path, expected: str) -> None:
    assert _resolve_input_kind(path, INPUT_AUTO) == expected
