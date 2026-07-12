from __future__ import annotations

from pathlib import Path

import pytest

from pipeline_inspector.core import (
    FileDependencySnapshot,
    GraphSnapshot,
    RuleDefinition,
    ValidationEngine,
    load_rule_file,
)

ROOT = Path(__file__).resolve().parents[2]
RULE_PATH = ROOT / "src" / "pipeline_inspector" / "rules" / "common" / "texture_freshness.json"
FIXTURES_ROOT = ROOT / "tests" / "fixtures" / "snapshots"

TEXTURE_FRESHNESS_FIXTURE_CASES = (
    ("texture_freshness_outdated", "failed"),
    ("texture_freshness_latest", "passed"),
)


def load_texture_freshness_rule() -> RuleDefinition:
    rules = load_rule_file(RULE_PATH)
    assert len(rules) == 1
    return rules[0]


def snapshot_for_texture_version(
    *,
    version: str | None,
    latest_version: str | None,
) -> GraphSnapshot:
    return GraphSnapshot(
        scene_path="demo.ma",
        renderer="vray",
        file_dependencies=[
            FileDependencySnapshot(
                node_id="node:file_albedo",
                attr="fileTextureName",
                raw_path="$ASSET_ROOT/tex/albedo_v001.<UDIM>.exr",
                resolved_path="D:/show/assets/tex/albedo_v001.<UDIM>.exr",
                exists=True,
                is_udim=True,
                udim_tiles=[1001, 1002],
                version=version,
                latest_version=latest_version,
                extension=".exr",
            )
        ],
    )


def test_texture_freshness_rule_pack_has_production_defaults():
    rule = load_texture_freshness_rule()

    assert rule.id == "common.texture.version.latest"
    assert rule.scope == "file_dependency"
    assert rule.severity == "warning"
    assert rule.match.criteria == {"dependency_kind": "texture"}
    assert rule.check.type == "texture_version_latest"
    assert rule.policy.block_publish is False
    assert rule.policy.block_deadline is False
    assert rule.policy.auto_fix_allowed is True
    assert rule.fix is not None
    assert rule.fix.type == "relink_path"
    assert rule.fix.risk == "medium"


def test_texture_freshness_rule_fails_for_outdated_version():
    rule = load_texture_freshness_rule()
    snapshot = snapshot_for_texture_version(version="001", latest_version="003")

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.severity == "warning"
    assert result.target_kind == "file_dependency"
    assert result.target_id == "node:file_albedo"
    assert result.node == "node:file_albedo"
    assert result.plug == "version"
    assert result.current_value == "001"
    assert result.expected_value == "003"
    assert result.evidence["latest_version"] == "003"
    assert result.block_publish is False
    assert result.block_deadline is False
    assert result.auto_fix_available is True
    assert result.fix_id == "relink_path"


def test_texture_freshness_rule_passes_for_latest_version():
    rule = load_texture_freshness_rule()
    snapshot = snapshot_for_texture_version(version="003", latest_version="003")

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.current_value == "003"
    assert result.expected_value == "003"
    assert result.block_publish is False
    assert result.block_deadline is False


def test_texture_freshness_rule_skips_when_version_metadata_is_missing():
    rule = load_texture_freshness_rule()
    snapshot = snapshot_for_texture_version(version=None, latest_version=None)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "skipped"
    assert result.evidence["reason"] == "texture_version_latest_requires_version_metadata"


def test_texture_freshness_rule_skips_when_only_version_token_is_missing():
    rule = load_texture_freshness_rule()
    snapshot = GraphSnapshot(
        scene_path="demo.ma",
        renderer="vray",
        file_dependencies=[
            FileDependencySnapshot(
                node_id="node:file_albedo",
                attr="fileTextureName",
                raw_path="$ASSET_ROOT/tex/albedo.<UDIM>.exr",
                resolved_path="D:/show/assets/tex/albedo.<UDIM>.exr",
                exists=True,
                is_udim=True,
                udim_tiles=[1001, 1002],
                version=None,
                latest_version=None,
                extension=".exr",
            )
        ],
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "skipped"
    assert result.evidence["reason"] == "texture_version_latest_requires_version_metadata"


@pytest.mark.parametrize(("fixture_stem", "expected_status"), TEXTURE_FRESHNESS_FIXTURE_CASES)
def test_texture_freshness_fixture_cases(fixture_stem: str, expected_status: str):
    rule = load_texture_freshness_rule()
    fixture_path = FIXTURES_ROOT / f"{fixture_stem}.json"
    snapshot = GraphSnapshot.from_json(fixture_path.read_text(encoding="utf-8"))

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == expected_status
    assert result.rule_id == "common.texture.version.latest"
