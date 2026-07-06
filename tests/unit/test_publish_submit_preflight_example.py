from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

from examples.publish import submit_preflight


def test_publish_preflight_example_imports():
    assert submit_preflight.DEFAULT_PROFILE_ID == "publish_strict"
    assert submit_preflight.PUBLISH_BLOCKED == submit_preflight.VALIDATOR_PUBLISH_BLOCK


def test_build_validator_command_runs_validator_for_publish_gate(tmp_path: Path):
    command = submit_preflight.build_validator_command(
        mayapy="mayapy",
        scene_path=tmp_path / "scene.ma",
        report_path=tmp_path / "report.json",
        profile_path=tmp_path / "publish_strict.json",
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
        str(tmp_path / "publish_strict.json"),
        "--renderer",
        "vray",
    )


def test_publish_preflight_blocks_publish_on_publish_blocking_issue(tmp_path: Path):
    calls: list[tuple[str, ...]] = []

    def runner(command: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(tuple(command))
        return subprocess.CompletedProcess(command, submit_preflight.VALIDATOR_PUBLISH_BLOCK)

    result = submit_preflight.run_publish_preflight(
        scene_path=tmp_path / "scene.ma",
        report_path=tmp_path / "report.json",
        profile_path=tmp_path / "publish_strict.json",
        runner=runner,
    )

    assert result.allowed is False
    assert result.exit_code == submit_preflight.PUBLISH_BLOCKED
    assert result.validator_exit_code == submit_preflight.VALIDATOR_PUBLISH_BLOCK
    assert calls[0][0] == "mayapy"


def test_publish_preflight_allows_clean_validation(tmp_path: Path):
    def runner(command: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, submit_preflight.VALIDATOR_OK)

    result = submit_preflight.run_publish_preflight(
        scene_path=tmp_path / "scene.ma",
        report_path=tmp_path / "report.json",
        profile_path=tmp_path / "publish_strict.json",
        runner=runner,
    )

    assert result.allowed is True
    assert result.exit_code == submit_preflight.PUBLISH_ALLOWED


def test_publish_preflight_maps_validator_errors_to_preflight_error(tmp_path: Path):
    def runner(command: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, submit_preflight.VALIDATOR_CONFIG_ERROR)

    result = submit_preflight.run_publish_preflight(
        scene_path=tmp_path / "scene.ma",
        report_path=tmp_path / "report.json",
        profile_path=tmp_path / "publish_strict.json",
        runner=runner,
    )

    assert result.allowed is False
    assert result.exit_code == submit_preflight.PREFLIGHT_ERROR
