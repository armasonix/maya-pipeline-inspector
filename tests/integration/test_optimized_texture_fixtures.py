"""Fixture-driven integration tests for optimized texture policy packs."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from shader_health.core import FileDependencySnapshot, GraphSnapshot, NodeSnapshot, RuleResult
from shader_health.maya.validation_pipeline import ValidationRunResult, run_validation

FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "snapshots"


@dataclass(frozen=True)
class PolicyExpectation:
    rule_id: str
    severity: str
    block_publish: bool = False
    block_deadline: bool = False
    material: Optional[str] = None


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
                material=item.get("material"),
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
    if expectation.material is not None:
        matches = [item for item in matches if item.material == expectation.material]
    if len(matches) != 1:
        raise AssertionError(
            f"Expected exactly one failed result for {expectation.rule_id!r}, found {len(matches)}"
        )
    return matches[0]


def test_optimized_texture_fixture_matches_expectations(tmp_path: Path):
    source = tmp_path / "albedo_v003.exr"
    source.write_bytes(b"source")
    resolved = str(source).replace("\\", "/")
    snapshot = GraphSnapshot(
        scene_path=str(tmp_path / "demo.ma"),
        renderer="arnold",
        nodes=[
            NodeSnapshot(
                id="node:file_albedo",
                name="file_albedo",
                type_name="file",
                attrs={"fileTextureName": resolved},
            )
        ],
        file_dependencies=[
            FileDependencySnapshot(
                node_id="node:file_albedo",
                attr="fileTextureName",
                raw_path=resolved,
                resolved_path=resolved,
                exists=True,
                extension=".exr",
            )
        ],
    )
    expectations_by_profile = load_policy_expectations("texture_optimized_missing")

    for profile_id, expectations in expectations_by_profile.items():
        run = run_validation(snapshot, profile_id=profile_id, scan_scope="scene")
        for expectation in expectations:
            result = _find_result(run, expectation)
            assert result.severity == expectation.severity
            assert result.block_publish is expectation.block_publish
            assert result.block_deadline is expectation.block_deadline
