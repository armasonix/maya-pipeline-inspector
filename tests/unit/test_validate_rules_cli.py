from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from shader_health.core import (
    RuleLoadError,
    apply_profile_overrides,
    build_rule_search_paths,
    load_profile,
    load_rule_file,
    load_rule_stack,
    load_rules_from_path,
)

ROOT = Path(__file__).resolve().parents[2]
VALID_RULES = ROOT / "tests" / "fixtures" / "rules" / "valid"
INVALID_RULES = ROOT / "tests" / "fixtures" / "rules" / "invalid"
VALIDATOR = ROOT / "tools" / "validate_rules.py"


def run_validator(*args: Path) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(VALIDATOR), *(str(arg) for arg in args)]
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def make_rule(rule_id: str, severity: str = "error") -> dict:
    return {
        "schema_version": "1.0",
        "id": rule_id,
        "name": f"Rule {rule_id}",
        "enabled": True,
        "renderer": ["common"],
        "scope": "texture_node",
        "severity": severity,
        "owner": "shader_td",
        "message": "Test rule message.",
        "why": "Test rule explanation.",
        "match": {"node_type": ["file"]},
        "check": {
            "type": "attribute_equals",
            "attribute": "colorSpace",
            "expected": "Raw",
        },
        "policy": {
            "block_publish": True,
            "block_deadline": True,
            "waiver_allowed": True,
            "auto_fix_allowed": False,
        },
    }


def write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def write_rule_pack(path: Path, *rules: dict) -> Path:
    return write_json(path, {"rules": list(rules)})


def test_validate_rules_cli_accepts_valid_fixture():
    result = run_validator(VALID_RULES)

    assert result.returncode == 0
    assert "Validated 1 rule(s) from 1 file(s)." in result.stdout
    assert result.stderr == ""


def test_validate_rules_cli_rejects_invalid_fixture_with_actionable_error():
    result = run_validator(INVALID_RULES)

    assert result.returncode == 1
    assert "missing_why.json" in result.stderr
    assert "rule #1" in result.stderr
    assert "missing required field(s): why" in result.stderr


def test_validate_rules_cli_default_rule_pack_path_is_valid():
    result = run_validator()

    assert result.returncode == 0
    assert "Validated" in result.stdout
    assert "rule(s)" in result.stdout
    assert result.stderr == ""


def test_rule_search_paths_are_deterministic(tmp_path):
    rule_root = tmp_path / "rules"
    common = rule_root / "common"
    vray = rule_root / "vray"
    arnold = rule_root / "arnold"
    extra = tmp_path / "studio"
    for path in (common, vray, arnold, extra):
        path.mkdir(parents=True)

    paths = build_rule_search_paths(
        rule_root,
        renderer_ids=["vray", "common", "missing", "arnold", "vray"],
        extra_rule_paths=[extra],
    )

    assert paths == [common, vray, arnold, extra]


def test_rule_stack_loads_common_renderer_and_extra_rules(tmp_path):
    rule_root = tmp_path / "rules"
    extra = tmp_path / "studio"
    write_rule_pack(rule_root / "common" / "a.json", make_rule("common.test"))
    write_rule_pack(rule_root / "vray" / "b.json", make_rule("vray.test"))
    write_rule_pack(extra / "c.json", make_rule("studio.test"))

    rules = load_rule_stack(rule_root, renderer_ids=["vray"], extra_rule_paths=[extra])

    assert [rule.id for rule in rules] == ["common.test", "vray.test", "studio.test"]


def test_profile_override_changes_severity_and_block_policy(tmp_path):
    rule_path = write_rule_pack(tmp_path / "rules.json", make_rule("common.test"))
    rule = load_rule_file(rule_path)[0]
    profile_path = write_json(
        tmp_path / "profile.json",
        {
            "id": "deadline_critical",
            "rule_overrides": {
                "common.test": {
                    "enabled": False,
                    "severity": "warning",
                    "block_deadline": False,
                }
            },
        },
    )

    resolved = apply_profile_overrides([rule], load_profile(profile_path))

    assert len(resolved) == 1
    assert resolved[0].enabled is False
    assert resolved[0].severity == "warning"
    assert resolved[0].policy.block_publish is True
    assert resolved[0].policy.block_deadline is False


def test_profile_override_unknown_rule_fails(tmp_path):
    rule_path = write_rule_pack(tmp_path / "rules.json", make_rule("common.test"))
    rule = load_rule_file(rule_path)[0]
    profile_path = write_json(
        tmp_path / "profile.json",
        {
            "id": "publish_strict",
            "rule_overrides": {"missing.rule": {"severity": "critical"}},
        },
    )

    with pytest.raises(RuleLoadError, match="references unknown rule"):
        apply_profile_overrides([rule], load_profile(profile_path))


def test_load_rules_from_path_rejects_missing_path(tmp_path):
    with pytest.raises(RuleLoadError, match="Rule path does not exist"):
        load_rules_from_path(tmp_path / "missing")
