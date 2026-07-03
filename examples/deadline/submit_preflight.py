"""Deadline submit preflight example for Shader Health Inspector."""
from __future__ import annotations

import argparse
import subprocess
import sys
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
    """Result returned by the Deadline submit preflight example."""

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
    extra_args: Sequence[str] = (),
) -> tuple[str, ...]:
    """Build the critical-mode headless validator command."""

    return (
        mayapy,
        "-m",
        "shader_health",
        "validate",
        str(scene_path),
        "--input-kind",
        "scene",
        "--report",
        str(report_path),
        "--profile",
        str(profile_path),
        *tuple(extra_args),
    )


def run_deadline_preflight(
    *,
    scene_path: Path,
    report_path: Path,
    profile_path: Path,
    mayapy: str = "mayapy",
    repo_root: Path | None = None,
    extra_args: Sequence[str] = (),
    runner: Runner = subprocess.run,
) -> DeadlinePreflightResult:
    """Run Shader Health validation and map result to a Deadline submit decision."""

    command = build_validator_command(
        mayapy=mayapy,
        scene_path=scene_path,
        report_path=report_path,
        profile_path=profile_path,
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Shader Health before Deadline submission.")
    parser.add_argument("scene_path", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--mayapy", default="mayapy")
    parser.add_argument("--repo-root", type=Path)
    args, extra_args = parser.parse_known_args(argv)

    result = run_deadline_preflight(
        scene_path=args.scene_path,
        report_path=args.report,
        profile_path=args.profile,
        mayapy=args.mayapy,
        repo_root=args.repo_root,
        extra_args=extra_args,
    )
    if not result.allowed:
        print(_blocked_message(result), file=sys.stderr)
    return result.exit_code


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


def _blocked_message(result: DeadlinePreflightResult) -> str:
    return (
        "Deadline submission blocked by Shader Health preflight. "
        f"validator_exit_code={result.validator_exit_code}; "
        f"report={result.report_path}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
