"""Fixture-driven integration tests for USD asset health rules."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from pipeline_inspector.core import GraphSnapshot, RuleResult
from pipeline_inspector.maya.validation_pipeline import ValidationRunResult, run_validation

FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "snapshots"
USD_FIXTURE_STEM = "usd_asset_broken"


@dataclass(frozen=True)
class PolicyExpectation:
    rule_id: str
    severity: str
    block_publish: bool = False
    block_deadline: bool = False


def load_snapshot_fixture(stem: str) -> GraphSnapshot:
    fixture_path = FIXTURES_ROOT / f"{stem}.json"
    return GraphSnapshot.from_json(fixture_path.read_text(encoding="utf-8"))


def load_policy_expectations(stem: str) -> dict[str, list[PolicyExpectation]]:
    expectations_path = FIXTURES_ROOT / f"{stem}.expectations.json"
    payload = json.loads(expectations_path.read_text(encoding="utf-8"))
    profiles = payload.get("profiles", {})
    parsed: dict[str, list[PolicyExpectation]] = {}
    for profile_id, profile_payload in profiles.items():
        failed = profile_payload.get("failed", [])
        parsed[str(profile_id)] = [
            PolicyExpectation(
                rule_id=str(item["rule_id"]),
                severity=str(item["severity"]),
                block_publish=bool(item.get("block_publish", False)),
                block_deadline=bool(item.get("block_deadline", False)),
            )
            for item in failed
        ]
    return parsed


def _find_result(run: ValidationRunResult, expectation: PolicyExpectation) -> RuleResult:
    matches = [
        item
        for item in run.results
        if item.rule_id == expectation.rule_id and item.status == "failed"
    ]
    if not matches:
        raise AssertionError(
            f"Expected at least one failed result for {expectation.rule_id!r}, found 0"
        )
    return matches[0]


@pytest.mark.parametrize("profile_id", ["publish_strict"])
def test_usd_asset_broken_fixture_matches_expectations(profile_id: str) -> None:
    expectations = load_policy_expectations(USD_FIXTURE_STEM)[profile_id]
    run = run_validation(load_snapshot_fixture(USD_FIXTURE_STEM), profile_id=profile_id)
    for expectation in expectations:
        result = _find_result(run, expectation)
        assert result.severity == expectation.severity
        assert result.block_publish is expectation.block_publish
        assert result.block_deadline is expectation.block_deadline
