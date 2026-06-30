from __future__ import annotations

import subprocess
import sys
from pathlib import Path

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
