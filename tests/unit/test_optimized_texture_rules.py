from __future__ import annotations

import os
import time
from pathlib import Path

from shader_health.core import (
    FileDependencySnapshot,
    GraphSnapshot,
    NodeSnapshot,
    RuleDefinition,
    ValidationEngine,
    apply_profile_overrides,
    load_profile,
    load_rule_file,
)
from shader_health.maya.snapshot_enrichment import prepare_snapshot_for_validation

ROOT = Path(__file__).resolve().parents[2]
RULE_PATH = ROOT / "src" / "shader_health" / "rules" / "common" / "optimized_textures.json"
DEADLINE_PROFILE = ROOT / "src" / "shader_health" / "rules" / "profiles" / "deadline_critical.json"


def load_optimized_rule(rule_id: str) -> RuleDefinition:
    rules = {rule.id: rule for rule in load_rule_file(RULE_PATH)}
    return rules[rule_id]


def snapshot_for_optimized_texture(
    *,
    optimized_exists: bool | None = True,
    optimized_is_stale: bool | None = False,
    optimized_kind: str = "tx",
    is_udim: bool = False,
    optimized_missing_udim_tiles: list[int] | None = None,
) -> GraphSnapshot:
    return GraphSnapshot(
        scene_path="demo.ma",
        renderer="arnold",
        file_dependencies=[
            FileDependencySnapshot(
                node_id="node:file_albedo",
                attr="fileTextureName",
                raw_path="$ASSET_ROOT/tex/albedo_v003.exr",
                resolved_path="D:/show/assets/tex/albedo_v003.exr",
                exists=True,
                extension=".exr",
                is_udim=is_udim,
                mtime_utc="2026-06-30T11:00:00Z",
                optimized_kind=optimized_kind,
                optimized_path="D:/show/assets/tex/albedo_v003.tx",
                optimized_exists=optimized_exists,
                optimized_mtime_utc="2026-06-30T11:05:00Z",
                optimized_is_stale=optimized_is_stale,
                optimized_missing_udim_tiles=list(optimized_missing_udim_tiles or []),
            )
        ],
    )


def test_file_dependency_snapshot_round_trips_optimized_texture_metadata():
    snapshot = snapshot_for_optimized_texture(
        optimized_exists=True,
        optimized_is_stale=False,
    )

    data = snapshot.to_dict()
    restored = GraphSnapshot.from_dict(data)

    dependency = data["file_dependencies"][0]
    assert restored == snapshot
    assert dependency["optimized_kind"] == "tx"
    assert dependency["optimized_path"] == "D:/show/assets/tex/albedo_v003.tx"
    assert dependency["optimized_exists"] is True
    assert dependency["optimized_mtime_utc"] == "2026-06-30T11:05:00Z"
    assert dependency["optimized_is_stale"] is False


def test_optimized_exists_rule_pack_has_production_defaults():
    rule = load_optimized_rule("common.texture.optimized.exists")

    assert rule.scope == "file_dependency"
    assert rule.severity == "warning"
    assert rule.match.criteria == {
        "dependency_kind": "texture",
        "exists": True,
        "optimized_kind": ["tx", "udim_tx"],
    }
    assert rule.check.type == "attribute_equals"
    assert rule.check.params["attribute"] == "optimized_exists"
    assert rule.check.params["expected"] is True
    assert rule.policy.block_publish is False
    assert rule.policy.block_deadline is False
    assert rule.policy.auto_fix_allowed is False


def test_optimized_exists_rule_fails_when_derivative_is_missing():
    rule = load_optimized_rule("common.texture.optimized.exists")
    snapshot = snapshot_for_optimized_texture(optimized_exists=False)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.target_kind == "file_dependency"
    assert result.target_id == "node:file_albedo"
    assert result.plug == "optimized_exists"
    assert result.current_value is False
    assert result.expected_value is True
    assert result.block_publish is False
    assert result.block_deadline is False


def test_optimized_exists_rule_passes_when_derivative_exists():
    rule = load_optimized_rule("common.texture.optimized.exists")
    snapshot = snapshot_for_optimized_texture(optimized_exists=True)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.current_value is True
    assert result.expected_value is True


def test_optimized_exists_rule_skips_when_metadata_is_absent():
    rule = load_optimized_rule("common.texture.optimized.exists")
    snapshot = snapshot_for_optimized_texture(optimized_exists=None, optimized_kind="")

    dependency = snapshot.file_dependencies[0]
    snapshot = GraphSnapshot(
        scene_path="demo.ma",
        renderer="arnold",
        file_dependencies=[
            FileDependencySnapshot(
                node_id=dependency.node_id,
                attr=dependency.attr,
                raw_path=dependency.raw_path,
                resolved_path=dependency.resolved_path,
                exists=True,
                extension=".exr",
            )
        ],
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "skipped"
    assert result.evidence["reason"] == "no_matching_targets"


def test_optimized_fresh_rule_pack_has_production_defaults():
    rule = load_optimized_rule("common.texture.optimized.fresh")

    assert rule.scope == "file_dependency"
    assert rule.severity == "warning"
    assert rule.match.criteria == {
        "dependency_kind": "texture",
        "exists": True,
        "optimized_kind": ["tx", "udim_tx"],
        "optimized_is_stale": [True, False],
    }
    assert rule.check.type == "attribute_equals"
    assert rule.check.params["attribute"] == "optimized_is_stale"
    assert rule.check.params["expected"] is False
    assert rule.policy.block_publish is False
    assert rule.policy.block_deadline is False
    assert rule.policy.auto_fix_allowed is False


def test_optimized_fresh_rule_fails_when_derivative_is_stale():
    rule = load_optimized_rule("common.texture.optimized.fresh")
    snapshot = snapshot_for_optimized_texture(optimized_is_stale=True)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.target_kind == "file_dependency"
    assert result.target_id == "node:file_albedo"
    assert result.plug == "optimized_is_stale"
    assert result.current_value is True
    assert result.expected_value is False


def test_optimized_fresh_rule_passes_when_derivative_is_fresh():
    rule = load_optimized_rule("common.texture.optimized.fresh")
    snapshot = snapshot_for_optimized_texture(optimized_is_stale=False)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.current_value is False
    assert result.expected_value is False


def test_optimized_fresh_rule_skips_when_metadata_is_absent():
    rule = load_optimized_rule("common.texture.optimized.fresh")
    snapshot = snapshot_for_optimized_texture(optimized_is_stale=None)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "skipped"
    assert result.evidence["reason"] == "no_matching_targets"


def test_optimized_udim_tx_missing_rule_fails_when_tiles_are_missing():
    rule = load_optimized_rule("common.texture.optimized.udim_tx.missing")
    snapshot = snapshot_for_optimized_texture(
        optimized_kind="udim_tx",
        is_udim=True,
        optimized_exists=False,
        optimized_missing_udim_tiles=[1002],
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.plug == "optimized_missing_udim_tiles"
    assert result.current_value == 1
    assert result.expected_value == 0


def test_deadline_critical_profile_enables_optimized_texture_farm_blocks():
    rules = load_rule_file(RULE_PATH)
    profile = load_profile(DEADLINE_PROFILE)
    resolved = {rule.id: rule for rule in apply_profile_overrides(rules, profile)}

    exists = resolved["common.texture.optimized.exists"]
    fresh = resolved["common.texture.optimized.fresh"]
    udim = resolved["common.texture.optimized.udim_tx.missing"]

    assert exists.enabled is True
    assert exists.severity == "error"
    assert exists.policy.block_deadline is True
    assert fresh.enabled is True
    assert fresh.policy.block_deadline is True
    assert udim.enabled is True
    assert udim.policy.block_deadline is True


def test_enrichment_detects_missing_tx_for_flat_exr(tmp_path: Path):
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

    enriched = prepare_snapshot_for_validation(snapshot)
    dependency = enriched.file_dependencies[0]

    assert dependency.optimized_kind == "tx"
    assert dependency.optimized_exists is False
    assert dependency.optimized_path.endswith("albedo_v003.tx")


def test_enrichment_marks_stale_tx_when_source_is_newer(tmp_path: Path):
    source = tmp_path / "albedo_v003.exr"
    tx_path = tmp_path / "albedo_v003.tx"
    source.write_bytes(b"source")
    tx_path.write_bytes(b"tx")
    stale_time = time.time() - 60
    os.utime(tx_path, (stale_time, stale_time))
    time.sleep(0.02)
    source.write_bytes(b"source-newer")
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

    enriched = prepare_snapshot_for_validation(snapshot)
    dependency = enriched.file_dependencies[0]

    assert dependency.optimized_exists is True
    assert dependency.optimized_is_stale is True


def test_enrichment_detects_missing_udim_tx_tiles(tmp_path: Path):
    tile_1001 = tmp_path / "albedo_v001.1001.exr"
    tile_1002 = tmp_path / "albedo_v001.1002.exr"
    tile_1001.write_bytes(b"tile")
    tile_1002.write_bytes(b"tile")
    (tmp_path / "albedo_v001.1001.tx").write_bytes(b"tx")
    pattern = str(tmp_path / "albedo_v001.<UDIM>.exr").replace("\\", "/")

    snapshot = GraphSnapshot(
        scene_path=str(tmp_path / "demo.ma"),
        renderer="arnold",
        nodes=[
            NodeSnapshot(
                id="node:file_albedo",
                name="file_albedo",
                type_name="file",
                attrs={
                    "fileTextureName": pattern,
                    "uvTilingMode": 3,
                },
            )
        ],
        file_dependencies=[
            FileDependencySnapshot(
                node_id="node:file_albedo",
                attr="fileTextureName",
                raw_path=pattern,
                resolved_path=pattern,
                exists=True,
                is_udim=True,
                udim_tiles=[1001, 1002],
                extension=".exr",
            )
        ],
    )

    enriched = prepare_snapshot_for_validation(snapshot)
    dependency = enriched.file_dependencies[0]

    assert dependency.is_udim is True
    assert dependency.optimized_kind == "udim_tx"
    assert dependency.optimized_udim_tiles == [1001]
    assert dependency.optimized_missing_udim_tiles == [1002]
    assert dependency.optimized_exists is False
