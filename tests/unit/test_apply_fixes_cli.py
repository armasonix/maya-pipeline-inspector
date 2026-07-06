from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shader_health import cli
from shader_health.core.fix_audit import load_fix_audit_sidecar
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


def test_apply_fixes_cli_dry_run_writes_planned_actions_without_applying(
    tmp_path: Path,
    monkeypatch,
):
    scene_path = tmp_path / "scene.ma"
    scene_path.write_text("// scene", encoding="utf-8")
    report_path = tmp_path / "dry_run.json"
    plan = FixPlan(
        actions=(
            FixAction(
                fix_id="safe:node:set_attr",
                rule_id="rule",
                title="safe",
                fix_type="set_attr",
                risk="low",
                target_kind="node",
                target_id="node:file1",
                target_node="file1",
            ),
            FixAction(
                fix_id="blocked:node:set_attr",
                rule_id="rule",
                title="blocked",
                fix_type="set_attr",
                risk="high",
                target_kind="node",
                target_id="node:file2",
                target_node="file2",
                blocked=True,
                block_reasons=["high_risk_requires_explicit_confirmation"],
            ),
        )
    )
    monkeypatch.setattr(cli, "_load_fix_plan_for_scene", lambda *_args, **_kwargs: plan)

    def fail_if_apply(*_args, **_kwargs):
        raise AssertionError("apply-fixes dry-run must not mutate the scene")

    monkeypatch.setattr(cli, "_apply_fixes_in_scene", fail_if_apply)

    exit_code = cli.main(
        [
            "apply-fixes",
            str(scene_path),
            "--dry-run",
            "--report",
            str(report_path),
        ]
    )

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert exit_code == cli.EXIT_OK
    assert payload["dry_run"] is True
    assert payload["total"] == 1
    assert payload["blocked_count"] == 0
    assert payload["records"][0]["fix_id"] == "safe:node:set_attr"


def test_apply_fixes_cli_fix_ids_select_explicit_actions(tmp_path: Path, monkeypatch):
    scene_path = tmp_path / "scene.ma"
    scene_path.write_text("// scene", encoding="utf-8")
    plan = FixPlan(
        actions=(
            FixAction(
                fix_id="keep:node:set_attr",
                rule_id="rule",
                title="keep",
                fix_type="set_attr",
                risk="low",
                target_kind="node",
                target_id="node:file1",
                target_node="file1",
            ),
            FixAction(
                fix_id="skip:node:set_attr",
                rule_id="rule",
                title="skip",
                fix_type="set_attr",
                risk="low",
                target_kind="node",
                target_id="node:file2",
                target_node="file2",
            ),
        )
    )
    captured: dict[str, tuple[Any, ...]] = {}

    def capture_apply(_scene_path, actions, **kwargs):
        captured["actions"] = tuple(actions)
        return ApplyFixReport(records=())

    monkeypatch.setattr(cli, "_load_fix_plan_for_scene", lambda *_args, **_kwargs: plan)
    monkeypatch.setattr(cli, "_apply_fixes_in_scene", capture_apply)

    exit_code = cli.main(
        [
            "apply-fixes",
            str(scene_path),
            "--fix-ids",
            "keep:node:set_attr",
        ]
    )

    assert exit_code == cli.EXIT_OK
    assert len(captured["actions"]) == 1
    assert captured["actions"][0].fix_id == "keep:node:set_attr"


def test_apply_fixes_cli_forwards_policy_flags_to_applier(tmp_path: Path, monkeypatch):
    scene_path = tmp_path / "scene.ma"
    scene_path.write_text("// scene", encoding="utf-8")
    plan = FixPlan(
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
            ),
        )
    )
    captured: dict[str, bool] = {}

    def capture_apply(_scene_path, actions, **kwargs):
        captured["allow_referenced"] = kwargs["allow_referenced"]
        captured["allow_high_risk"] = kwargs["allow_high_risk"]
        return ApplyFixReport(records=())

    monkeypatch.setattr(cli, "_load_fix_plan_for_scene", lambda *_args, **_kwargs: plan)
    monkeypatch.setattr(cli, "_apply_fixes_in_scene", capture_apply)

    exit_code = cli.main(
        [
            "apply-fixes",
            str(scene_path),
            "--allow-referenced",
            "--allow-high-risk",
        ]
    )

    assert exit_code == cli.EXIT_OK
    assert captured["allow_referenced"] is True
    assert captured["allow_high_risk"] is True


def test_apply_fixes_cli_appends_fix_audit_sidecar_on_real_apply(tmp_path: Path, monkeypatch):
    scene_path = tmp_path / "hero.ma"
    scene_path.write_text("// scene", encoding="utf-8")
    plan = FixPlan(
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
            ),
        )
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
    monkeypatch.setattr(cli, "_load_fix_plan_for_scene", lambda *_args, **_kwargs: plan)
    monkeypatch.setattr(cli, "_apply_fixes_in_scene", lambda *_args, **_kwargs: fake_report)

    exit_code = cli.main(["apply-fixes", str(scene_path)])

    audit_path = scene_path.with_name("hero.shader_health_fix_audit.json")
    loaded = load_fix_audit_sidecar(audit_path)
    assert exit_code == cli.EXIT_OK
    assert len(loaded.sessions) == 1
    assert loaded.sessions[0].applied_count == 1


def test_apply_fixes_cli_dry_run_skips_fix_audit_sidecar(tmp_path: Path, monkeypatch):
    scene_path = tmp_path / "hero.ma"
    scene_path.write_text("// scene", encoding="utf-8")
    plan = FixPlan(
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
            ),
        )
    )
    monkeypatch.setattr(cli, "_load_fix_plan_for_scene", lambda *_args, **_kwargs: plan)

    exit_code = cli.main(["apply-fixes", str(scene_path), "--dry-run"])

    audit_path = scene_path.with_name("hero.shader_health_fix_audit.json")
    assert exit_code == cli.EXIT_OK
    assert not audit_path.exists()


def test_apply_fixes_cli_returns_publish_block_when_all_actions_blocked(
    tmp_path: Path,
    monkeypatch,
):
    scene_path = tmp_path / "scene.ma"
    scene_path.write_text("// scene", encoding="utf-8")
    plan = FixPlan(
        actions=(
            FixAction(
                fix_id="blocked:node:set_attr",
                rule_id="rule",
                title="blocked",
                fix_type="set_attr",
                risk="high",
                target_kind="node",
                target_id="node:file1",
                target_node="file1",
                blocked=True,
                block_reasons=["high_risk_requires_explicit_confirmation"],
            ),
        )
    )
    fake_report = ApplyFixReport(
        records=(
            AppliedFixRecord(
                fix_id="blocked:node:set_attr",
                rule_id="rule",
                fix_type="set_attr",
                target_node="file1",
                target_attr="colorSpace",
                blocked=True,
                block_reasons=["high_risk_requires_explicit_confirmation"],
            ),
        )
    )
    monkeypatch.setattr(cli, "_load_fix_plan_for_scene", lambda *_args, **_kwargs: plan)
    monkeypatch.setattr(cli, "_apply_fixes_in_scene", lambda *_args, **_kwargs: fake_report)

    exit_code = cli.main(["apply-fixes", str(scene_path)])

    assert exit_code == cli.EXIT_PUBLISH_BLOCK


def test_apply_fixes_cli_returns_runtime_error_when_apply_fails(tmp_path: Path, monkeypatch):
    scene_path = tmp_path / "scene.ma"
    scene_path.write_text("// scene", encoding="utf-8")
    plan = FixPlan(
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
            ),
        )
    )
    fake_report = ApplyFixReport(
        records=(
            AppliedFixRecord(
                fix_id="rule:node:set_attr",
                rule_id="rule",
                fix_type="set_attr",
                target_node="file1",
                target_attr="colorSpace",
                message="Maya API error",
            ),
        )
    )
    monkeypatch.setattr(cli, "_load_fix_plan_for_scene", lambda *_args, **_kwargs: plan)
    monkeypatch.setattr(cli, "_apply_fixes_in_scene", lambda *_args, **_kwargs: fake_report)

    exit_code = cli.main(["apply-fixes", str(scene_path)])

    assert exit_code == cli.EXIT_RUNTIME_ERROR
