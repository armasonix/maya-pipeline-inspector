"""Deadline submit preflight helpers for Pipeline Inspector."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

VALIDATOR_OK = 0
VALIDATOR_PUBLISH_BLOCK = 1
VALIDATOR_DEADLINE_BLOCK = 2
VALIDATOR_RUNTIME_ERROR = 3
VALIDATOR_CONFIG_ERROR = 4

SUBMISSION_ALLOWED = 0
SUBMISSION_BLOCKED = 2
PREFLIGHT_ERROR = 3

Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class DeadlinePreflightResult:
    """Result returned by the Deadline submit preflight helper."""

    allowed: bool
    exit_code: int
    validator_exit_code: int
    command: tuple[str, ...]
    report_path: Path
    stdout: str = ""
    stderr: str = ""


def build_validator_command(
    *,
    mayapy: str,
    scene_path: Path,
    report_path: Path,
    profile_path: Path,
    studio_config_path: Path | None = None,
    extra_args: Sequence[str] = (),
) -> tuple[str, ...]:
    """Build the critical-mode headless validator command."""

    command: tuple[str, ...] = (
        mayapy,
        "-m",
        "pipeline_inspector",
        "validate",
        str(scene_path),
        "--input-kind",
        "scene",
        "--report",
        str(report_path),
        "--profile",
        str(profile_path),
    )
    if studio_config_path is not None:
        command = command + ("--studio-config", str(studio_config_path))
    command = command + tuple(extra_args)
    return command


def run_deadline_preflight(
    *,
    scene_path: Path,
    report_path: Path,
    profile_path: Path,
    mayapy: str = "mayapy",
    repo_root: Path | None = None,
    studio_config_path: Path | None = None,
    extra_args: Sequence[str] = (),
    runner: Runner = subprocess.run,
) -> DeadlinePreflightResult:
    """Run Pipeline Inspector validation and map result to a Deadline submit decision."""

    command = build_validator_command(
        mayapy=mayapy,
        scene_path=scene_path,
        report_path=report_path,
        profile_path=profile_path,
        studio_config_path=studio_config_path,
        extra_args=extra_args,
    )
    completed = runner(
        command,
        cwd=str(repo_root) if repo_root else None,
        capture_output=True,
        text=True,
    )
    validator_exit_code = int(completed.returncode)
    if validator_exit_code == VALIDATOR_OK:
        return _result(
            True, SUBMISSION_ALLOWED, validator_exit_code, command, report_path, completed
        )
    if validator_exit_code == VALIDATOR_DEADLINE_BLOCK:
        return _result(
            False, SUBMISSION_BLOCKED, validator_exit_code, command, report_path, completed
        )
    return _result(False, PREFLIGHT_ERROR, validator_exit_code, command, report_path, completed)


def blocked_message(result: DeadlinePreflightResult) -> str:
    """Return a stderr-friendly message for blocked preflight runs."""

    return (
        "Deadline submission blocked by Pipeline Inspector preflight. "
        f"validator_exit_code={result.validator_exit_code}; "
        f"report={result.report_path}"
    )


def _result(
    allowed: bool,
    exit_code: int,
    validator_exit_code: int,
    command: tuple[str, ...],
    report_path: Path,
    completed: subprocess.CompletedProcess[str],
) -> DeadlinePreflightResult:
    return DeadlinePreflightResult(
        allowed=allowed,
        exit_code=exit_code,
        validator_exit_code=validator_exit_code,
        command=command,
        report_path=report_path,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
