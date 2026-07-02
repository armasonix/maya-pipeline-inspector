from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

from examples.deadline import submit_preflight


def test_build_validator_command_runs_validator_in_critical_mode(tmp_path: Path):
    command = submit_preflight.build_validator_command(
        mayapy="mayapy",
        scene_path=tmp_path / "scene.ma",
        report_path=tmp_path / "report.json",
        profile_path=tmp_path / "deadline_critical.json",
        extra_args=("--renderer", "vray"),
    )

    assert command == (
        "mayapy",
        "-m",
        "shader_health",
        "validate",
        str(tmp_path / "scene.ma"),
        "--input-kind",
        "scene",
        "--report",
        str(tmp_path / "report.json"),
        "--profile",
        str(tmp_path / "deadline_critical.json"),
        "--renderer",
        "vray",
    )


def test_deadline_preflight_blocks_submission_on_farm_blocking_issue(tmp_path: Path):
    calls: list[tuple[str, ...]] = []

    def runner(command: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(tuple(command))
        return subprocess.CompletedProcess(command, submit_preflight.VALIDATOR_DEADLINE_BLOCK)

    result = submit_preflight.run_deadline_preflight(
        scene_path=tmp_path / "scene.ma",
        report_path=tmp_path / "report.json",
        profile_path=tmp_path / "deadline_critical.json",
        runner=runner,
    )

    assert result.allowed is False
    assert result.exit_code == submit_preflight.SUBMISSION_BLOCKED
    assert result.validator_exit_code == submit_preflight.VALIDATOR_DEADLINE_BLOCK
    assert calls[0][0] == "mayapy"


def test_deadline_preflight_allows_clean_validation(tmp_path: Path):
    def runner(command: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, submit_preflight.VALIDATOR_OK)

    result = submit_preflight.run_deadline_preflight(
        scene_path=tmp_path / "scene.ma",
        report_path=tmp_path / "report.json",
        profile_path=tmp_path / "deadline_critical.json",
        runner=runner,
    )

    assert result.allowed is True
    assert result.exit_code == submit_preflight.SUBMISSION_ALLOWED


def test_deadline_preflight_maps_validator_errors_to_preflight_error(tmp_path: Path):
    def runner(command: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, submit_preflight.VALIDATOR_CONFIG_ERROR)

    result = submit_preflight.run_deadline_preflight(
        scene_path=tmp_path / "scene.ma",
        report_path=tmp_path / "report.json",
        profile_path=tmp_path / "deadline_critical.json",
        runner=runner,
    )

    assert result.allowed is False
    assert result.exit_code == submit_preflight.PREFLIGHT_ERROR
