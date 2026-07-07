"""Submit a Shader Health validation utility job to Deadline."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from shader_health.integrations.deadline import (
    DeadlineClient,
    DeadlineConfig,
    DeadlineSubmitError,
    FarmSceneState,
    FarmValidationResult,
    submit_shader_health_validation_job,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Submit a Shader Health validation utility job to Deadline.",
    )
    parser.add_argument("scene_path", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--command-script",
        type=Path,
        required=True,
        help="Network-visible CommandScript aux file path for the Web Service host.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional Deadline JSON config. Defaults to SHADER_HEALTH_DEADLINE_* env vars.",
    )
    parser.add_argument(
        "--run-local-preflight",
        action="store_true",
        help="Run local mayapy preflight before submitting the farm job.",
    )
    parser.add_argument(
        "--check-eligibility",
        action="store_true",
        help="Apply the farm eligibility gate before REST submission.",
    )
    parser.add_argument(
        "--scene-saved",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Scene saved state used by the eligibility gate.",
    )
    parser.add_argument(
        "--renderer-plugin-loaded",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Renderer plug-in loaded state used by the eligibility gate.",
    )
    parser.add_argument(
        "--validator-exit-code",
        type=int,
        default=0,
        help="Last validator exit code used by the eligibility gate.",
    )
    args, extra_args = parser.parse_known_args(argv)

    config = (
        DeadlineConfig.from_json(args.config) if args.config else DeadlineConfig.from_env()
    )
    client = DeadlineClient(config)
    scene_state = None
    validation_result = None
    if args.check_eligibility:
        scene_state = FarmSceneState(
            scene_saved=args.scene_saved,
            renderer_plugin_loaded=args.renderer_plugin_loaded,
        )
        validation_result = FarmValidationResult.from_validator_exit_code(
            args.validator_exit_code
        )

    try:
        result = submit_shader_health_validation_job(
            client=client,
            scene_path=args.scene_path,
            report_path=args.report,
            config=config,
            command_script_path=args.command_script,
            scene_state=scene_state,
            validation_result=validation_result,
            run_local_preflight=args.run_local_preflight,
            extra_args=extra_args,
        )
    except DeadlineSubmitError as exc:
        print(str(exc), file=sys.stderr)
        return 3

    print(f"Submitted Deadline job {result.job_id}")
    print(f"Report path: {result.report_path}")
    if result.command_script_line:
        print(f"CommandScript: {result.command_script_line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
