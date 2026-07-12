from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from pipeline_inspector import cli
from pipeline_inspector.core import (
    FileDependencySnapshot,
    GraphSnapshot,
    MaterialSnapshot,
    NodeSnapshot,
)
from pipeline_inspector.studio_config import (
    LEGACY_STUDIO_CONFIG_ENV_VAR,
    STUDIO_CONFIG_ENV_VAR,
    PipelineSettings,
    StudioConfig,
    save_studio_config,
)


def test_validate_snapshot_writes_report_and_returns_publish_block(tmp_path: Path):
    snapshot_path = _write_snapshot(tmp_path, "ACEScg")
    report_path = tmp_path / "report.json"
    rule_root = _rule_root(tmp_path, block_publish=True)

    code = cli.main(
        [
            "validate",
            str(snapshot_path),
            "--report",
            str(report_path),
            "--rule-root",
            str(rule_root),
            "--profile",
            str(_minimal_profile(tmp_path)),
        ]
    )

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert code == cli.EXIT_PUBLISH_BLOCK
    assert payload["block_publish"] is True
    assert payload["results"][0]["status"] == "failed"


def test_validate_snapshot_returns_deadline_block(tmp_path: Path):
    snapshot_path = _write_snapshot(tmp_path, "ACEScg")
    report_path = tmp_path / "report.json"
    rule_root = _rule_root(tmp_path, block_deadline=True)

    code = cli.main(
        [
            "validate",
            str(snapshot_path),
            "--report",
            str(report_path),
            "--rule-root",
            str(rule_root),
            "--profile",
            str(_minimal_profile(tmp_path)),
        ]
    )

    assert code == cli.EXIT_DEADLINE_BLOCK


def test_validate_snapshot_returns_ok_when_no_blocking_results(tmp_path: Path):
    snapshot_path = _write_snapshot(tmp_path, "Raw")
    report_path = tmp_path / "report.json"
    rule_root = _rule_root(tmp_path, block_publish=True)

    code = cli.main(
        [
            "validate",
            str(snapshot_path),
            "--report",
            str(report_path),
            "--rule-root",
            str(rule_root),
            "--profile",
            str(_minimal_profile(tmp_path)),
        ]
    )

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert code == cli.EXIT_OK
    assert payload["status"] == "passed"


def test_validate_snapshot_writes_fix_plan_when_flag_and_fixes_exist(tmp_path: Path):
    snapshot_path = _write_snapshot(tmp_path, "ACEScg")
    report_path = tmp_path / "report.json"
    fix_plan_path = tmp_path / "fix_plan.json"
    rule_root = _rule_root(tmp_path, block_publish=True, include_fix=True)

    code = cli.main(
        [
            "validate",
            str(snapshot_path),
            "--report",
            str(report_path),
            "--export-fix-plan",
            str(fix_plan_path),
            "--rule-root",
            str(rule_root),
            "--profile",
            str(_minimal_profile(tmp_path)),
        ]
    )

    payload = json.loads(fix_plan_path.read_text(encoding="utf-8"))
    assert code == cli.EXIT_PUBLISH_BLOCK
    assert payload["fix_plan_schema_version"] == "1.0"
    assert payload["total"] == 1
    assert payload["actions"][0]["fix_type"] == "set_attr"
    assert payload["actions"][0]["before_value"] == "ACEScg"
    assert payload["actions"][0]["after_value"] == "Raw"


def test_validate_snapshot_skips_fix_plan_export_without_fixes(tmp_path: Path):
    snapshot_path = _write_snapshot(tmp_path, "Raw")
    report_path = tmp_path / "report.json"
    fix_plan_path = tmp_path / "fix_plan.json"
    rule_root = _rule_root(tmp_path, block_publish=True, include_fix=True)

    code = cli.main(
        [
            "validate",
            str(snapshot_path),
            "--report",
            str(report_path),
            "--export-fix-plan",
            str(fix_plan_path),
            "--rule-root",
            str(rule_root),
            "--profile",
            str(_minimal_profile(tmp_path)),
        ]
    )

    assert code == cli.EXIT_OK
    assert not fix_plan_path.exists()


def test_validate_respects_studio_config_flag_disabling_tx_rules(tmp_path: Path, monkeypatch):
    _isolate_studio_config_discovery(monkeypatch, tmp_path)
    snapshot_path = _write_optimized_texture_snapshot(tmp_path)
    report_path = tmp_path / "report.json"
    studio_path = tmp_path / "studio" / "pipeline_inspector_studio.json"

    blocked_code = cli.main(
        [
            "validate",
            str(snapshot_path),
            "--report",
            str(report_path),
            "--profile-id",
            "deadline_critical",
        ]
    )
    save_studio_config(
        studio_path,
        StudioConfig(pipeline=PipelineSettings(require_tx_derivatives=False)),
    )
    cli.main(
        [
            "validate",
            str(snapshot_path),
            "--report",
            str(tmp_path / "report_allowed.json"),
            "--profile-id",
            "deadline_critical",
            "--studio-config",
            str(studio_path),
        ]
    )

    assert blocked_code == cli.EXIT_DEADLINE_BLOCK
    blocked_result = _rule_result(report_path, "common.texture.optimized.exists")
    assert blocked_result["status"] == "failed"
    assert blocked_result["block_deadline"] is True

    allowed_result = _rule_result(
        tmp_path / "report_allowed.json",
        "common.texture.optimized.exists",
    )
    assert allowed_result["status"] in {"skipped", "passed"}
    assert allowed_result["block_deadline"] is False


def test_validate_respects_studio_config_env_var(tmp_path: Path, monkeypatch):
    _isolate_studio_config_discovery(monkeypatch, tmp_path)
    snapshot_path = _write_optimized_texture_snapshot(tmp_path)
    report_path = tmp_path / "report.json"
    studio_path = tmp_path / "studio" / "pipeline_inspector_studio.json"
    save_studio_config(
        studio_path,
        StudioConfig(pipeline=PipelineSettings(require_tx_derivatives=False)),
    )
    monkeypatch.setenv("PIPELINE_INSPECTOR_STUDIO_CONFIG", str(studio_path))

    cli.main(
        [
            "validate",
            str(snapshot_path),
            "--report",
            str(report_path),
            "--profile-id",
            "deadline_critical",
        ]
    )

    result = _rule_result(report_path, "common.texture.optimized.exists")
    assert result["status"] in {"skipped", "passed"}
    assert result["block_deadline"] is False


def test_validate_missing_studio_config_path_returns_config_error(tmp_path: Path, monkeypatch):
    _isolate_studio_config_discovery(monkeypatch, tmp_path)
    snapshot_path = _write_optimized_texture_snapshot(tmp_path)
    report_path = tmp_path / "report.json"

    code = cli.main(
        [
            "validate",
            str(snapshot_path),
            "--report",
            str(report_path),
            "--profile-id",
            "deadline_critical",
            "--studio-config",
            str(tmp_path / "missing_studio.json"),
        ]
    )

    assert code == cli.EXIT_CONFIG_ERROR


def test_manifest_accepts_studio_config_flag(tmp_path: Path, monkeypatch):
    _isolate_studio_config_discovery(monkeypatch, tmp_path)
    snapshot_path = _write_optimized_texture_snapshot(tmp_path)
    studio_path = tmp_path / "studio" / "pipeline_inspector_studio.json"
    save_studio_config(
        studio_path,
        StudioConfig(pipeline=PipelineSettings(require_tx_derivatives=False)),
    )
    manifest_path = tmp_path / "manifest.json"

    code = cli.main(
        [
            "manifest",
            str(snapshot_path),
            "--profile-id",
            "deadline_critical",
            "--studio-config",
            str(studio_path),
            "--out",
            str(manifest_path),
        ]
    )

    assert code == cli.EXIT_OK
    assert manifest_path.exists()


def test_gate_accepts_studio_config_flag(tmp_path: Path, monkeypatch):
    _isolate_studio_config_discovery(monkeypatch, tmp_path)
    snapshot_path = _write_optimized_texture_snapshot(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    studio_path = tmp_path / "studio" / "pipeline_inspector_studio.json"
    save_studio_config(
        studio_path,
        StudioConfig(pipeline=PipelineSettings(require_tx_derivatives=False)),
    )
    manifest_code = cli.main(
        [
            "manifest",
            str(snapshot_path),
            "--profile-id",
            "deadline_critical",
            "--studio-config",
            str(studio_path),
            "--out",
            str(manifest_path),
        ]
    )
    assert manifest_code == cli.EXIT_OK

    gate_path = tmp_path / "gate.json"
    gate_code = cli.main(
        [
            "gate",
            str(snapshot_path),
            str(manifest_path),
            "--profile-id",
            "deadline_critical",
            "--studio-config",
            str(studio_path),
            "--out",
            str(gate_path),
        ]
    )

    assert gate_code == cli.EXIT_OK
    assert gate_path.exists()


def test_validate_invalid_rule_root_returns_config_error(tmp_path: Path):
    snapshot_path = _write_snapshot(tmp_path, "Raw")

    code = cli.main(
        [
            "validate",
            str(snapshot_path),
            "--report",
            str(tmp_path / "report.json"),
            "--rule-root",
            str(tmp_path / "missing_rules"),
        ]
    )

    assert code == cli.EXIT_CONFIG_ERROR


def test_validate_scene_path_uses_scene_loader(monkeypatch, tmp_path: Path):
    scene_path = tmp_path / "scene.ma"
    scene_path.write_text("// scene", encoding="utf-8")
    report_path = tmp_path / "scene_report.json"
    monkeypatch.setattr(cli, "_snapshot_from_scene", lambda path: _snapshot("Raw"))
    rule_root = _rule_root(tmp_path, block_publish=True)

    code = cli.main(
        [
            "validate",
            str(scene_path),
            "--input-kind",
            "scene",
            "--report",
            str(report_path),
            "--rule-root",
            str(rule_root),
            "--profile",
            str(_minimal_profile(tmp_path)),
        ]
    )

    assert code == cli.EXIT_OK
    assert report_path.exists()


def test_gate_snapshot_blocks_fingerprint_drift(tmp_path: Path):
    snapshot_path = _write_material_snapshot(tmp_path, "sha256:new")
    baseline_path = tmp_path / "baseline_manifest.json"
    gate_path = tmp_path / "gate.json"
    baseline_path.write_text(
        json.dumps(
            {
                "manifest_schema_version": "1.1",
                "materials": [
                    {
                        "node_id": "node:hero_mtl",
                        "name": "hero_mtl",
                        "graph_fingerprint": "sha256:old",
                        "textures": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    profile_path = _strict_manifest_gate_profile(tmp_path)

    code = cli.main(
        [
            "gate",
            str(snapshot_path),
            str(baseline_path),
            "--profile",
            str(profile_path),
            "--out",
            str(gate_path),
        ]
    )

    payload = json.loads(gate_path.read_text(encoding="utf-8"))
    assert code == cli.EXIT_PUBLISH_BLOCK
    assert payload["manifest_regression_blocked"] is True
    assert any("fingerprint" in reason for reason in payload["reasons"])


def test_gate_passes_when_baseline_matches_manifest_export(tmp_path: Path):
    snapshot_path = _write_material_snapshot(tmp_path, "sha256:stable")
    manifest_path = tmp_path / "exported_manifest.json"
    gate_path = tmp_path / "gate_report.json"

    manifest_code = cli.main(
        [
            "manifest",
            str(snapshot_path),
            "--input-kind",
            "snapshot",
            "--profile-id",
            "artist_relaxed",
            "--out",
            str(manifest_path),
        ]
    )
    assert manifest_code == cli.EXIT_OK

    gate_code = cli.main(
        [
            "gate",
            str(snapshot_path),
            str(manifest_path),
            "--input-kind",
            "snapshot",
            "--profile-id",
            "publish_strict",
            "--out",
            str(gate_path),
        ]
    )
    assert gate_code == cli.EXIT_OK
    payload = json.loads(gate_path.read_text(encoding="utf-8"))
    assert payload["manifest_regression_blocked"] is False


def test_validate_snapshot_runs_manifest_gate_after_passing_validation(tmp_path: Path):
    snapshot_path = _write_material_snapshot(tmp_path, "sha256:new")
    report_path = tmp_path / "report.json"
    baseline_path = tmp_path / "baseline_manifest.json"
    rule_root = _rule_root(tmp_path, block_publish=True)
    baseline_path.write_text(
        json.dumps(
            {
                "manifest_schema_version": "1.1",
                "materials": [
                    {
                        "node_id": "node:hero_mtl",
                        "name": "hero_mtl",
                        "graph_fingerprint": "sha256:old",
                        "textures": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    code = cli.main(
        [
            "validate",
            str(snapshot_path),
            "--report",
            str(report_path),
            "--rule-root",
            str(rule_root),
            "--profile",
            str(_minimal_profile(tmp_path)),
            "--baseline-manifest",
            str(baseline_path),
        ]
    )

    assert code == cli.EXIT_PUBLISH_BLOCK
    assert report_path.exists()


def test_manifest_snapshot_writes_shader_manifest_with_health_score(tmp_path: Path):
    snapshot_path = _write_snapshot(tmp_path, "ACEScg")
    manifest_path = tmp_path / "manifest.json"

    code = cli.main(
        [
            "manifest",
            str(snapshot_path),
            "--out",
            str(manifest_path),
            "--profile",
            str(_minimal_profile(tmp_path)),
        ]
    )

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert code == cli.EXIT_OK
    assert payload["manifest_schema_version"] == "1.1"
    assert payload["health_score"] == 100


def test_manifest_snapshot_from_material_graph(tmp_path: Path):
    snapshot_path = _write_material_snapshot(tmp_path, "sha256:hero")
    manifest_path = tmp_path / "material_manifest.json"

    code = cli.main(
        [
            "manifest",
            str(snapshot_path),
            "--input-kind",
            "snapshot",
            "--out",
            str(manifest_path),
            "--profile",
            str(_minimal_profile(tmp_path)),
        ]
    )

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert code == cli.EXIT_OK
    assert payload["materials"][0]["graph_fingerprint"] == "sha256:hero"


def test_manifest_scene_path_uses_scene_loader(monkeypatch, tmp_path: Path):
    scene_path = tmp_path / "scene.ma"
    scene_path.write_text("// scene", encoding="utf-8")
    manifest_path = tmp_path / "scene_manifest.json"
    monkeypatch.setattr(
        cli,
        "_snapshot_from_scene",
        lambda path: _material_snapshot("sha256:scene"),
    )

    code = cli.main(
        [
            "manifest",
            str(scene_path),
            "--input-kind",
            "scene",
            "--out",
            str(manifest_path),
            "--profile",
            str(_minimal_profile(tmp_path)),
        ]
    )

    assert code == cli.EXIT_OK
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["materials"][0]["graph_fingerprint"] == "sha256:scene"


def test_validate_snapshot_accepts_asset_class_overlay(tmp_path: Path):
    snapshot_path = _write_snapshot(tmp_path, "Raw")
    report_path = tmp_path / "asset_class_report.json"

    code = cli.main(
        [
            "validate",
            str(snapshot_path),
            "--report",
            str(report_path),
            "--profile-id",
            "publish_strict",
            "--asset-class-id",
            "asset_class_hero",
        ]
    )

    assert code != cli.EXIT_CONFIG_ERROR
    assert report_path.exists()


def test_ensure_maya_standalone_initializes_once(monkeypatch):
    init_calls: list[str] = []

    class FakeStandalone:
        @staticmethod
        def initialize(*, name: str = "python") -> None:
            init_calls.append(name)

    monkeypatch.setitem(sys.modules, "maya.standalone", FakeStandalone())
    monkeypatch.setattr(cli, "_MAYA_STANDALONE_INITIALIZED", False)

    cli._ensure_maya_standalone()
    cli._ensure_maya_standalone()

    assert init_calls == ["python"]


def test_snapshot_from_scene_calls_maya_standalone_before_cmds_file(monkeypatch, tmp_path: Path):
    scene_path = tmp_path / "scene.ma"
    scene_path.write_text("//Maya ASCII", encoding="utf-8")
    init_calls: list[str] = []
    file_calls: list[str] = []

    class FakeStandalone:
        @staticmethod
        def initialize(*, name: str = "python") -> None:
            init_calls.append(name)

    class FakeCmds:
        @staticmethod
        def file(path: str, *, open: bool = True, force: bool = True) -> None:
            file_calls.append(path)

    scanner = importlib.import_module("pipeline_inspector.maya.scanner")
    monkeypatch.setitem(sys.modules, "maya.standalone", FakeStandalone())
    monkeypatch.setitem(sys.modules, "maya.cmds", FakeCmds())
    monkeypatch.setattr(cli, "_MAYA_STANDALONE_INITIALIZED", False)
    monkeypatch.setattr(scanner, "scan_scene", lambda: _snapshot("Raw"))

    snapshot = cli._snapshot_from_scene(scene_path)

    assert init_calls == ["python"]
    assert file_calls == [str(scene_path)]
    assert snapshot.nodes[0].attrs["colorSpace"] == "Raw"


def _write_snapshot(tmp_path: Path, color_space: str) -> Path:
    path = tmp_path / f"snapshot_{color_space}.json"
    path.write_text(_snapshot(color_space).to_json(), encoding="utf-8")
    return path


def _write_optimized_texture_snapshot(tmp_path: Path) -> Path:
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
    path = tmp_path / "optimized_texture_snapshot.json"
    path.write_text(snapshot.to_json(), encoding="utf-8")
    return path


def _isolate_studio_config_discovery(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv(STUDIO_CONFIG_ENV_VAR, raising=False)
    monkeypatch.delenv(LEGACY_STUDIO_CONFIG_ENV_VAR, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))


def _rule_result(report_path: Path, rule_id: str) -> dict:
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    return next(item for item in payload["results"] if item["rule_id"] == rule_id)


def _snapshot(color_space: str) -> GraphSnapshot:
    return GraphSnapshot(
        renderer="common",
        nodes=[
            NodeSnapshot(
                id="node:file1",
                name="file1",
                type_name="file",
                attrs={"colorSpace": color_space},
            )
        ],
    )


def _write_material_snapshot(tmp_path: Path, fingerprint: str) -> Path:
    path = tmp_path / f"material_snapshot_{fingerprint.replace(':', '_')}.json"
    path.write_text(_material_snapshot(fingerprint).to_json(), encoding="utf-8")
    return path


def _material_snapshot(fingerprint: str) -> GraphSnapshot:
    return GraphSnapshot(
        renderer="common",
        materials=[
            MaterialSnapshot(
                node_id="node:hero_mtl",
                name="hero_mtl",
                type_name="lambert",
                graph_fingerprint=fingerprint,
            )
        ],
    )


def _strict_manifest_gate_profile(tmp_path: Path) -> Path:
    path = tmp_path / "strict_gate_profile.json"
    path.write_text(
        json.dumps(
            {
                "id": "strict_gate",
                "display_name": "Strict Gate",
                "manifest_diff_policy": {
                    "max_new_changes": 0,
                    "max_fingerprint_changes": 0,
                    "block_on_new_textures": True,
                },
                "rule_overrides": {},
            }
        ),
        encoding="utf-8",
    )
    return path


def _rule_root(
    tmp_path: Path,
    *,
    block_publish: bool = False,
    block_deadline: bool = False,
    include_fix: bool = False,
) -> Path:
    rule_root = tmp_path / f"rules_{block_publish}_{block_deadline}_{include_fix}"
    common = rule_root / "common"
    common.mkdir(parents=True)
    rule = {
        "rules": [
            {
                "id": "common.texture.colorspace.data_raw",
                "name": "Data textures must use Raw color space",
                "enabled": True,
                "renderer": ["common"],
                "scope": "texture_node",
                "severity": "critical",
                "owner": "shader_td",
                "message": "Data texture uses a color-managed color space.",
                "why": "Data textures must not be color transformed.",
                "match": {"node_type": ["file"]},
                "check": {
                    "type": "attribute_equals",
                    "attribute": "colorSpace",
                    "expected": "Raw",
                },
                "policy": {
                    "block_publish": block_publish,
                    "block_deadline": block_deadline,
                    "waiver_allowed": True,
                    "auto_fix_allowed": False,
                },
            }
        ]
    }
    if include_fix:
        rule["rules"][0]["policy"]["auto_fix_allowed"] = True
        rule["rules"][0]["fix"] = {
            "type": "set_attr",
            "risk": "low",
            "params": {"attribute": "colorSpace", "value": "Raw"},
        }
    (common / "colorspace.json").write_text(json.dumps(rule), encoding="utf-8")
    return rule_root


def _minimal_profile(tmp_path: Path) -> Path:
    path = tmp_path / "minimal_profile.json"
    path.write_text(
        json.dumps(
            {
                "id": "minimal",
                "display_name": "Minimal",
                "rule_overrides": {},
            }
        ),
        encoding="utf-8",
    )
    return path
