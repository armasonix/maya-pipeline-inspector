"""Fixture-driven integration tests for studio path token substitution."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from pipeline_inspector import cli
from pipeline_inspector.core import FileDependencySnapshot, GraphSnapshot, NodeSnapshot
from pipeline_inspector.maya.validation_pipeline import ValidationRunResult, run_validation
from pipeline_inspector.studio_config import (
    LEGACY_STUDIO_CONFIG_ENV_VAR,
    STUDIO_CONFIG_ENV_VAR,
    PipelineSettings,
    StudioConfig,
    StudioEnvironmentSettings,
    save_studio_config,
)

FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "snapshots"
FIXTURE_STEM = "studio_path_substitution"


def load_snapshot_fixture(
    stem: str = FIXTURE_STEM,
    *,
    tmp_path: Path | None = None,
) -> GraphSnapshot:
    fixture_path = FIXTURES_ROOT / f"{stem}.json"
    snapshot = GraphSnapshot.from_json(fixture_path.read_text(encoding="utf-8"))
    if tmp_path is None:
        return snapshot
    return replace(snapshot, scene_path=str(tmp_path / "studio_path_substitution.ma"))


def load_substitution_expectations(stem: str = FIXTURE_STEM) -> dict[str, Any]:
    expectations_path = FIXTURES_ROOT / f"{stem}.expectations.json"
    return json.loads(expectations_path.read_text(encoding="utf-8"))


def _materialize_fixture_workspace(
    tmp_path: Path,
    expectations: dict[str, Any],
) -> StudioEnvironmentSettings:
    roots_config = expectations["studio_roots"]
    roots: dict[str, str] = {}
    for field_name in ("texture_root", "asset_root", "cache_root", "render_root"):
        relative_root = str(roots_config.get(field_name, "") or "").strip()
        if not relative_root:
            roots[field_name] = ""
            continue
        root_path = tmp_path / relative_root
        root_path.mkdir(parents=True, exist_ok=True)
        roots[field_name] = str(root_path).replace("\\", "/")

    for entry in expectations.get("materialize", []):
        relative = str(entry["relative"])
        file_path = tmp_path / relative
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b"fixture")

    aliases_raw = roots_config.get("variable_aliases", {})
    aliases = (
        {str(key): str(value) for key, value in aliases_raw.items()}
        if isinstance(aliases_raw, dict)
        else {}
    )
    return StudioEnvironmentSettings(
        texture_root=roots["texture_root"],
        asset_root=roots["asset_root"],
        cache_root=roots["cache_root"],
        render_root=roots["render_root"],
        variable_aliases=aliases,
    )


def _dependency_by_node(run: ValidationRunResult, node_id: str) -> Any:
    for dependency in run.snapshot.file_dependencies:
        if dependency.node_id == node_id:
            return dependency
    raise AssertionError(f"Dependency not found for {node_id!r}")


def _assert_passed_rule_ids(run: ValidationRunResult, rule_ids: list[str]) -> None:
    for rule_id in rule_ids:
        failed = [
            item
            for item in run.results
            if item.rule_id == rule_id and item.status == "failed"
        ]
        assert not failed, f"Expected {rule_id!r} to pass, got failures: {failed}"


def _assert_failed_rule_ids(run: ValidationRunResult, rule_ids: list[str]) -> None:
    for rule_id in rule_ids:
        failed = [
            item
            for item in run.results
            if item.rule_id == rule_id and item.status == "failed"
        ]
        assert failed, f"Expected {rule_id!r} to fail"


@pytest.fixture(name="studio_path_expectations")
def studio_path_expectations_fixture() -> dict[str, Any]:
    return load_substitution_expectations()


def test_studio_path_substitution_fixture_round_trips() -> None:
    snapshot = load_snapshot_fixture()
    restored = GraphSnapshot.from_dict(snapshot.to_dict())
    assert restored == snapshot


def test_studio_path_substitution_resolves_builtin_root_tokens(
    tmp_path: Path,
    studio_path_expectations: dict[str, Any],
) -> None:
    snapshot = load_snapshot_fixture(tmp_path=tmp_path)
    environment = _materialize_fixture_workspace(tmp_path, studio_path_expectations)
    scenario = studio_path_expectations["scenarios"]["with_studio_environment"]
    profile_payload = scenario["profiles"]["publish_strict"]

    run = run_validation(
        snapshot,
        profile_id="publish_strict",
        scan_scope="scene",
        studio_config=StudioConfig(
            pipeline=PipelineSettings(require_tx_derivatives=False),
            studio_environment=environment,
        ),
    )

    _assert_passed_rule_ids(run, ["common.texture.missing"])
    for node_id in (
        "node:tex_root",
        "node:asset_root",
        "node:cache_root",
        "node:render_root",
    ):
        project_root_failures = [
            item
            for item in run.results
            if item.rule_id == "common.texture.path.project_root"
            and item.status == "failed"
            and item.node == node_id
        ]
        assert not project_root_failures, project_root_failures
    for node_id, suffix in profile_payload["resolved_suffixes"].items():
        dependency = _dependency_by_node(run, node_id)
        assert dependency.exists is True
        assert dependency.resolved_path.replace("\\", "/").endswith(suffix)

    alias_dependency = _dependency_by_node(run, "node:alias_root")
    assert "${SHOW_TEXTURE_ROOT}" in alias_dependency.raw_path


def test_studio_path_substitution_without_studio_environment_fails_missing_texture(
    tmp_path: Path,
    studio_path_expectations: dict[str, Any],
) -> None:
    snapshot = load_snapshot_fixture(tmp_path=tmp_path)
    scenario = studio_path_expectations["scenarios"]["without_studio_environment"]
    profile_payload = scenario["profiles"]["publish_strict"]

    run = run_validation(snapshot, profile_id="publish_strict", scan_scope="scene")

    _assert_failed_rule_ids(run, profile_payload["failed_rule_ids"])


def test_studio_path_substitution_cli_respects_studio_config_flag(
    tmp_path: Path,
    studio_path_expectations: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_studio_config_discovery(monkeypatch, tmp_path)
    environment = _materialize_fixture_workspace(tmp_path, studio_path_expectations)
    snapshot = load_snapshot_fixture(tmp_path=tmp_path)
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(snapshot.to_json(), encoding="utf-8")
    report_path = tmp_path / "report.json"
    studio_path = tmp_path / "studio" / "pipeline_inspector_studio.json"
    save_studio_config(
        studio_path,
        StudioConfig(
            pipeline=PipelineSettings(require_tx_derivatives=False),
            studio_environment=environment,
        ),
    )

    exit_code = cli.main(
        [
            "validate",
            str(snapshot_path),
            "--input-kind",
            "snapshot",
            "--profile-id",
            "publish_strict",
            "--studio-config",
            str(studio_path),
            "--report",
            str(report_path),
        ]
    )

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    missing_results = [
        item
        for item in payload["results"]
        if item["rule_id"] == "common.texture.missing" and item["status"] == "failed"
    ]
    assert not missing_results
    assert exit_code in {
        cli.EXIT_OK,
        cli.EXIT_PUBLISH_BLOCK,
        cli.EXIT_DEADLINE_BLOCK,
    }


def test_studio_path_substitution_custom_alias_resolves_nested_texture_root(
    tmp_path: Path,
) -> None:
    texture_root = tmp_path / "textures"
    texture_root.mkdir()
    texture_file = texture_root / "nested" / "alias.exr"
    texture_file.parent.mkdir(parents=True)
    texture_file.write_bytes(b"fixture")
    environment = StudioEnvironmentSettings(
        texture_root=str(texture_root).replace("\\", "/"),
        variable_aliases={"SHOW_TEXTURE_ROOT": "${STUDIO_TEXTURE_ROOT}"},
    )
    snapshot = GraphSnapshot(
        scene_path=str(tmp_path / "alias_demo.ma"),
        renderer="arnold",
        nodes=[
            NodeSnapshot(
                id="node:alias_only",
                name="alias_only",
                type_name="file",
                attrs={"fileTextureName": "${SHOW_TEXTURE_ROOT}/nested/alias.exr"},
            )
        ],
        file_dependencies=[
            FileDependencySnapshot(
                node_id="node:alias_only",
                attr="fileTextureName",
                raw_path="${SHOW_TEXTURE_ROOT}/nested/alias.exr",
            )
        ],
    )

    run = run_validation(
        snapshot,
        profile_id="publish_strict",
        scan_scope="scene",
        studio_config=StudioConfig(
            pipeline=PipelineSettings(require_tx_derivatives=False),
            studio_environment=environment,
        ),
    )

    dependency = _dependency_by_node(run, "node:alias_only")
    assert dependency.exists is True
    assert dependency.resolved_path.replace("\\", "/").endswith("/nested/alias.exr")
    _assert_passed_rule_ids(run, ["common.texture.missing"])


def _isolate_studio_config_discovery(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv(STUDIO_CONFIG_ENV_VAR, raising=False)
    monkeypatch.delenv(LEGACY_STUDIO_CONFIG_ENV_VAR, raising=False)
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
