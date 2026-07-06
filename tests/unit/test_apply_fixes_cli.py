from __future__ import annotations

import json
from pathlib import Path

from shader_health import cli
from shader_health.core.fix_plan import FixAction, FixPlan, fix_plan_from_export
from shader_health.maya.fix_applier import AppliedFixRecord, ApplyFixReport


def test_fix_plan_from_export_loads_actions():
    payload = {
        "fix_plan_schema_version": "1.0",
        "actions": [
            {
                "fix_id": "common.texture.colorspace.data_raw:node:file1:set_attr",
                "rule_id": "common.texture.colorspace.data_raw",
                "title": "Data textures must use Raw color space: set_attr",
                "fix_type": "set_attr",
                "risk": "low",
                "target_kind": "node",
                "target_id": "node:file1",
                "target_node": "file1",
                "target_attr": "colorSpace",
                "before_value": "ACEScg",
                "after_value": "Raw",
                "explanation": "Data textures must not be color transformed.",
                "referenced": False,
                "locked": False,
                "reference_path": None,
                "requires_reference_edit": False,
                "requires_supervisor": False,
                "undo_supported": True,
                "blocked": False,
                "block_reasons": [],
                "params": {"attribute": "colorSpace", "value": "Raw"},
            }
        ],
    }

    plan = fix_plan_from_export(payload)

    assert plan.total == 1
    assert plan.actions[0].fix_type == "set_attr"
    assert plan.actions[0].after_value == "Raw"


def test_fix_action_from_dict_round_trip():
    action = FixAction(
        fix_id="rule:node:set_attr",
        rule_id="rule",
        title="title",
        fix_type="set_attr",
        risk="low",
        target_kind="node",
        target_id="node:file1",
        target_node="file1",
        target_attr="colorSpace",
        before_value="ACEScg",
        after_value="Raw",
        explanation="why",
        blocked=True,
        block_reasons=["target_locked"],
        params={"attribute": "colorSpace", "value": "Raw"},
    )

    restored = FixAction.from_dict(action.to_dict())

    assert restored == action


def test_apply_fixes_cli_applies_non_blocked_actions_from_fix_plan(
    tmp_path: Path,
    monkeypatch,
):
    scene_path = tmp_path / "scene.ma"
    scene_path.write_text("// scene", encoding="utf-8")
    fix_plan_path = tmp_path / "fix_plan.json"
    report_path = tmp_path / "apply_report.json"
    fix_plan_path.write_text(
        json.dumps(
            {
                "actions": [
                    FixAction(
                        fix_id="rule:node:set_attr",
                        rule_id="rule",
                        title="title",
                        fix_type="set_attr",
                        risk="low",
                        target_kind="node",
                        target_id="node:file1",
                        target_node="file1",
                        target_attr="colorSpace",
                        before_value="ACEScg",
                        after_value="Raw",
                        explanation="why",
                    ).to_dict()
                ]
            }
        ),
        encoding="utf-8",
    )

    fake_report = ApplyFixReport(
        records=(
            AppliedFixRecord(
                fix_id="rule:node:set_attr",
                rule_id="rule",
                fix_type="set_attr",
                target_node="file1",
                target_attr="colorSpace",
                applied=True,
            ),
        )
    )
    monkeypatch.setattr(cli, "_apply_fixes_in_scene", lambda *_args, **_kwargs: fake_report)

    exit_code = cli.main(
        [
            "apply-fixes",
            str(scene_path),
            "--fix-plan",
            str(fix_plan_path),
            "--report",
            str(report_path),
        ]
    )

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert exit_code == cli.EXIT_OK
    assert payload["applied_count"] == 1


def test_apply_fixes_cli_plans_fixes_inline_when_fix_plan_omitted(
    tmp_path: Path,
    monkeypatch,
):
    scene_path = tmp_path / "scene.ma"
    scene_path.write_text("// scene", encoding="utf-8")
    inline_plan = FixPlan(
        actions=(
            FixAction(
                fix_id="rule:node:set_attr",
                rule_id="rule",
                title="title",
                fix_type="set_attr",
                risk="low",
                target_kind="node",
                target_id="node:file1",
                target_node="file1",
                target_attr="colorSpace",
                before_value="ACEScg",
                after_value="Raw",
                explanation="why",
            ),
        )
    )
    monkeypatch.setattr(cli, "_load_fix_plan_for_scene", lambda *_args, **_kwargs: inline_plan)
    monkeypatch.setattr(
        cli,
        "_apply_fixes_in_scene",
        lambda *_args, **_kwargs: ApplyFixReport(records=()),
    )

    exit_code = cli.main(["apply-fixes", str(scene_path)])

    assert exit_code == cli.EXIT_OK


def test_apply_fixes_cli_returns_config_error_for_invalid_fix_plan(tmp_path: Path, capsys):
    scene_path = tmp_path / "scene.ma"
    scene_path.write_text("// scene", encoding="utf-8")
    fix_plan_path = tmp_path / "fix_plan.json"
    fix_plan_path.write_text(json.dumps({"actions": "not-a-list"}), encoding="utf-8")

    exit_code = cli.main(["apply-fixes", str(scene_path), "--fix-plan", str(fix_plan_path)])

    captured = capsys.readouterr()
    assert exit_code == cli.EXIT_CONFIG_ERROR
    assert "Configuration error:" in captured.err
