"""Deadline job templates and farm submit API for Shader Health validation."""
from __future__ import annotations

import shlex
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from shader_health.integrations.deadline.client import DeadlineClient
from shader_health.integrations.deadline.config import DeadlineConfig
from shader_health.integrations.deadline.eligibility import (
    FarmEligibilityResult,
    FarmSceneState,
    FarmValidationResult,
    evaluate_farm_submit_eligibility,
)
from shader_health.integrations.deadline.preflight import (
    DeadlinePreflightResult,
    Runner,
    build_validator_command,
    run_deadline_preflight,
)

DeadlineValidationPlugin = Literal["command_script", "maya_batch"]
COMMAND_SCRIPT_PLUGIN = "CommandScript"
MAYA_BATCH_PLUGIN = "MayaBatch"
DEFAULT_FRAMES = "0"


class DeadlineSubmitError(RuntimeError):
    """Raised when farm validation submit is blocked or fails."""


@dataclass(frozen=True)
class ShaderHealthValidationJobResult:
    """Result returned after submitting a farm validation utility job."""

    job_id: str
    report_path: Path
    plugin: DeadlineValidationPlugin
    preflight_result: DeadlinePreflightResult | None = None
    eligibility: FarmEligibilityResult | None = None
    command_script_line: str | None = None


def build_command_script_line(command: Sequence[str]) -> str:
    """Format a validator command for a Deadline CommandScript aux file."""

    if not command:
        raise ValueError("command must not be empty")
    if _needs_shell_quoting():
        return subprocess.list2cmdline(list(command))
    return " ".join(shlex.quote(part) for part in command)


def write_command_script_file(path: Path, command: Sequence[str]) -> str:
    """Write a CommandScript aux file and return the rendered command line."""

    line = build_command_script_line(command)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(line + "\n", encoding="utf-8")
    return line


def build_command_script_job(
    *,
    config: DeadlineConfig,
    scene_path: Path,
    report_path: Path,
    command_script_path: Path,
    job_name: str | None = None,
    extra_args: Sequence[str] = (),
    extra_job_info: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], tuple[str, ...]]:
    """Build JobInfo/PluginInfo/AuxFiles for a CommandScript validation job.

    Per Thinkbox Deadline REST docs, CommandScript jobs execute the command
    stored in an auxiliary text file referenced by ``AuxFiles``. Paths must be
    valid on the Web Service host.
    """

    command = build_validator_command(
        mayapy=config.mayapy,
        scene_path=scene_path,
        report_path=report_path,
        profile_path=config.resolved_profile_path(),
        extra_args=extra_args,
    )
    _ = command  # command line is written to command_script_path by the caller
    job_info = _base_job_info(
        plugin=COMMAND_SCRIPT_PLUGIN,
        scene_path=scene_path,
        job_name=job_name,
        config=config,
        extra_job_info=extra_job_info,
    )
    plugin_info = {
        "StartupDirectory": _startup_directory(scene_path, config.repo_root),
    }
    aux_files = (str(command_script_path),)
    return job_info, plugin_info, aux_files


def build_maya_batch_script_job(
    *,
    config: DeadlineConfig,
    scene_path: Path,
    script_path: Path,
    job_name: str | None = None,
    maya_version: str | None = None,
    extra_job_info: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], tuple[str, ...]]:
    """Build JobInfo/PluginInfo for a MayaBatch script utility job.

    This uses Deadline's MayaBatch plugin to open ``scene_path`` and execute a
    Python/MEL ``script_path`` on the worker. Script and scene paths must be
    visible to farm workers and the Web Service host.
    """

    job_info = _base_job_info(
        plugin=MAYA_BATCH_PLUGIN,
        scene_path=scene_path,
        job_name=job_name,
        config=config,
        extra_job_info=extra_job_info,
    )
    plugin_info: dict[str, Any] = {
        "SceneFile": str(scene_path),
        "ScriptFile": str(script_path),
        "ScriptJob": True,
    }
    if maya_version:
        plugin_info["Version"] = maya_version
    return job_info, plugin_info, ()


def submit_shader_health_validation_job(
    *,
    client: DeadlineClient,
    scene_path: Path,
    report_path: Path,
    config: DeadlineConfig | None = None,
    plugin: DeadlineValidationPlugin = "command_script",
    command_script_path: Path | None = None,
    script_path: Path | None = None,
    maya_version: str | None = None,
    scene_state: FarmSceneState | None = None,
    validation_result: FarmValidationResult | None = None,
    run_local_preflight: bool = False,
    extra_args: Sequence[str] = (),
    runner: Runner = subprocess.run,
    job_name: str | None = None,
    extra_job_info: Mapping[str, Any] | None = None,
    write_command_script: bool = True,
) -> ShaderHealthValidationJobResult:
    """Submit a Deadline utility job that runs Shader Health validation on a worker.

    Optional local preflight and eligibility checks run before REST submission.
    """

    effective_config = config or client.config
    eligibility = _evaluate_optional_eligibility(validation_result, scene_state)
    if eligibility is not None and not eligibility.allowed:
        raise DeadlineSubmitError(
            "Farm validation submit blocked by eligibility gate: "
            f"{','.join(eligibility.reasons or eligibility.warnings)}"
        )

    preflight_result = None
    if run_local_preflight:
        preflight_result = run_deadline_preflight(
            scene_path=scene_path,
            report_path=report_path,
            profile_path=effective_config.resolved_profile_path(),
            mayapy=effective_config.mayapy,
            repo_root=effective_config.repo_root,
            extra_args=extra_args,
            runner=runner,
        )
        if not preflight_result.allowed:
            raise DeadlineSubmitError(
                "Farm validation submit blocked by local preflight: "
                f"exit_code={preflight_result.exit_code}"
            )

    command_script_line = None
    if plugin == "command_script":
        if command_script_path is None:
            raise DeadlineSubmitError(
                "command_script_path is required for command_script farm validation jobs"
            )
        command = build_validator_command(
            mayapy=effective_config.mayapy,
            scene_path=scene_path,
            report_path=report_path,
            profile_path=effective_config.resolved_profile_path(),
            extra_args=extra_args,
        )
        if write_command_script:
            command_script_line = write_command_script_file(command_script_path, command)
        else:
            command_script_line = build_command_script_line(command)
        job_info, plugin_info, aux_files = build_command_script_job(
            config=effective_config,
            scene_path=scene_path,
            report_path=report_path,
            command_script_path=command_script_path,
            job_name=job_name,
            extra_args=extra_args,
            extra_job_info=extra_job_info,
        )
    else:
        if script_path is None:
            raise DeadlineSubmitError(
                "script_path is required for maya_batch farm validation jobs"
            )
        job_info, plugin_info, aux_files = build_maya_batch_script_job(
            config=effective_config,
            scene_path=scene_path,
            script_path=script_path,
            job_name=job_name,
            maya_version=maya_version,
            extra_job_info=extra_job_info,
        )

    job_id = client.submit_job(
        job_info=job_info,
        plugin_info=plugin_info,
        aux_files=aux_files,
    )
    return ShaderHealthValidationJobResult(
        job_id=job_id,
        report_path=report_path,
        plugin=plugin,
        preflight_result=preflight_result,
        eligibility=eligibility,
        command_script_line=command_script_line,
    )


def _evaluate_optional_eligibility(
    validation_result: FarmValidationResult | None,
    scene_state: FarmSceneState | None,
) -> FarmEligibilityResult | None:
    if validation_result is None or scene_state is None:
        return None
    return evaluate_farm_submit_eligibility(validation_result, scene_state)


def _base_job_info(
    *,
    plugin: str,
    scene_path: Path,
    job_name: str | None,
    config: DeadlineConfig,
    extra_job_info: Mapping[str, Any] | None,
) -> dict[str, Any]:
    job_info: dict[str, Any] = {
        "Name": job_name or f"Shader Health | {scene_path.name}",
        "Plugin": plugin,
        "Frames": DEFAULT_FRAMES,
        "ChunkSize": 1,
    }
    if config.pool:
        job_info["Pool"] = config.pool
    elif config.queue:
        job_info["Pool"] = config.queue
    if config.group:
        job_info["Group"] = config.group
    if config.user_name:
        job_info["UserName"] = config.user_name
    if extra_job_info:
        job_info.update(dict(extra_job_info))
    return job_info


def _startup_directory(scene_path: Path, repo_root: Path | None) -> str:
    if repo_root is not None:
        return str(repo_root)
    return str(scene_path.parent)


def _needs_shell_quoting() -> bool:
    import sys

    return sys.platform == "win32"
