"""Fixture-driven integration tests for renderer production policy packs.

See tests/fixtures/snapshots/README.md for how to add new renderer policy cases.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import pytest

from pipeline_inspector.core import GraphSnapshot, RuleResult
from pipeline_inspector.maya.validation_pipeline import ValidationRunResult, run_validation

FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "snapshots"

POLICY_FIXTURE_CASES = (
    "vray_policy_scene",
    "arnold_policy_scene",
)


@dataclass(frozen=True)
class PolicyExpectation:
    rule_id: str
    severity: str
    block_publish: bool = False
    block_deadline: bool = False
    material: Optional[str] = None


def load_snapshot_fixture(stem: str) -> GraphSnapshot:
    fixture_path = FIXTURES_ROOT / f"{stem}.json"
    return GraphSnapshot.from_json(fixture_path.read_text(encoding="utf-8"))


def load_policy_expectations(stem: str) -> dict[str, list[PolicyExpectation]]:
    expectations_path = FIXTURES_ROOT / f"{stem}.expectations.json"
    payload = json.loads(expectations_path.read_text(encoding="utf-8"))
    profiles = payload.get("profiles", {})
    if not isinstance(profiles, dict):
        raise ValueError(f"{expectations_path}: 'profiles' must be an object")

    parsed: dict[str, list[PolicyExpectation]] = {}
    for profile_id, profile_payload in profiles.items():
        failed = profile_payload.get("failed", [])
        if not isinstance(failed, list):
            raise ValueError(f"{expectations_path}: profiles.{profile_id}.failed must be a list")
        parsed[str(profile_id)] = [_parse_expectation(item) for item in failed]
    return parsed


def _parse_expectation(raw: Any) -> PolicyExpectation:
    if not isinstance(raw, dict):
        raise TypeError("policy expectation entries must be objects")
    return PolicyExpectation(
        rule_id=str(raw["rule_id"]),
        severity=str(raw["severity"]),
        block_publish=bool(raw.get("block_publish", False)),
        block_deadline=bool(raw.get("block_deadline", False)),
        material=raw.get("material"),
    )


def _find_result(run: ValidationRunResult, expectation: PolicyExpectation) -> RuleResult:
    matches = [
        item
        for item in run.results
        if item.rule_id == expectation.rule_id and item.status == "failed"
    ]
    if expectation.material is not None:
        matches = [item for item in matches if item.material == expectation.material]
    if len(matches) != 1:
        material_hint = f" material={expectation.material!r}" if expectation.material else ""
        raise AssertionError(
            f"Expected exactly one failed result for {expectation.rule_id!r}{material_hint}, "
            f"found {len(matches)}"
        )
    return matches[0]


def assert_policy_expectations(
    run: ValidationRunResult,
    expectations: list[PolicyExpectation],
) -> None:
    for expectation in expectations:
        result = _find_result(run, expectation)
        assert result.severity == expectation.severity
        assert result.block_publish is expectation.block_publish
        assert result.block_deadline is expectation.block_deadline


@pytest.mark.parametrize("fixture_stem", POLICY_FIXTURE_CASES)
def test_renderer_policy_fixture_matches_expectations_for_all_profiles(fixture_stem: str):
    snapshot = load_snapshot_fixture(fixture_stem)
    expectations_by_profile = load_policy_expectations(fixture_stem)

    for profile_id, expectations in expectations_by_profile.items():
        run = run_validation(snapshot, profile_id=profile_id, scan_scope="scene")
        assert_policy_expectations(run, expectations)


@pytest.mark.parametrize("fixture_stem", POLICY_FIXTURE_CASES)
def test_renderer_policy_fixture_snapshot_round_trips(fixture_stem: str):
    snapshot = load_snapshot_fixture(fixture_stem)
    restored = GraphSnapshot.from_dict(snapshot.to_dict())
    assert restored == snapshot
