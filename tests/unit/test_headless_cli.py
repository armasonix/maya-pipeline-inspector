from __future__ import annotations

import json
from pathlib import Path

from shader_health import cli
from shader_health.core import GraphSnapshot, NodeSnapshot


def test_validate_snapshot_writes_report_and_returns_publish_block(tmp_path: Path):
    snapshot_path = _write_snapshot(tmp_path, "ACEScg")
    report_path = tmp_path / "report.json"

    code = cli.main(
        [
            "validate",
            str(snapshot_path),
            "--report",
            str(report_path),
            "--rule-root",
            str(_rule_root(tmp_path, block_publish=True)),
        ]
    )

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert code == cli.EXIT_PUBLISH_BLOCK
    assert payload["block_publish"] is True
    assert payload["results"][0]["status"] == "failed"


def test_validate_snapshot_returns_deadline_block(tmp_path: Path):
    snapshot_path = _write_snapshot(tmp_path, "ACEScg")
    report_path = tmp_path / "report.json"

    code = cli.main(
        [
            "validate",
            str(snapshot_path),
            "--report",
            str(report_path),
            "--rule-root",
            str(_rule_root(tmp_path, block_deadline=True)),
        ]
    )

    assert code == cli.EXIT_DEADLINE_BLOCK


def test_validate_snapshot_returns_ok_when_no_blocking_results(tmp_path: Path):
    snapshot_path = _write_snapshot(tmp_path, "Raw")
    report_path = tmp_path / "report.json"

    code = cli.main(
        [
            "validate",
            str(snapshot_path),
            "--report",
            str(report_path),
            "--rule-root",
            str(_rule_root(tmp_path, block_publish=True)),
        ]
    )

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert code == cli.EXIT_OK
    assert payload["status"] == "passed"


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

    code = cli.main(
        [
            "validate",
            str(scene_path),
            "--input-kind",
            "scene",
            "--report",
            str(report_path),
            "--rule-root",
            str(_rule_root(tmp_path, block_publish=True)),
        ]
    )

    assert code == cli.EXIT_OK
    assert report_path.exists()


def _write_snapshot(tmp_path: Path, color_space: str) -> Path:
    path = tmp_path / f"snapshot_{color_space}.json"
    path.write_text(_snapshot(color_space).to_json(), encoding="utf-8")
    return path


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


def _rule_root(
    tmp_path: Path,
    *,
    block_publish: bool = False,
    block_deadline: bool = False,
) -> Path:
    rule_root = tmp_path / f"rules_{block_publish}_{block_deadline}"
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
    (common / "colorspace.json").write_text(json.dumps(rule), encoding="utf-8")
    return rule_root
