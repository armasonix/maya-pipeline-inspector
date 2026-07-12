"""Deadline submit preflight example for Pipeline Inspector."""
from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from pipeline_inspector.integrations.deadline import (
    PREFLIGHT_ERROR,
    SUBMISSION_ALLOWED,
    SUBMISSION_BLOCKED,
    VALIDATOR_CONFIG_ERROR,
    VALIDATOR_DEADLINE_BLOCK,
    VALIDATOR_OK,
    VALIDATOR_PUBLISH_BLOCK,
    VALIDATOR_RUNTIME_ERROR,
    DeadlinePreflightResult,
    blocked_message,
    build_validator_command,
    run_deadline_preflight,
)

__all__ = [
    "VALIDATOR_OK",
    "VALIDATOR_PUBLISH_BLOCK",
    "VALIDATOR_DEADLINE_BLOCK",
    "VALIDATOR_RUNTIME_ERROR",
    "VALIDATOR_CONFIG_ERROR",
    "SUBMISSION_ALLOWED",
    "SUBMISSION_BLOCKED",
    "PREFLIGHT_ERROR",
    "DeadlinePreflightResult",
    "build_validator_command",
    "run_deadline_preflight",
    "main",
]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Pipeline Inspector before Deadline submission.")
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
        print(blocked_message(result), file=sys.stderr)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
