from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from shader_health.integrations.deadline import (
    DeadlineClient,
    DeadlineConfig,
    DeadlineSubmitError,
    FarmSceneState,
    FarmValidationResult,
    build_command_script_job,
    build_maya_batch_script_job,
    submit_shader_health_validation_job,
    write_command_script_file,
)
from shader_health.integrations.deadline.client import DeadlineResponse, HttpRequest
from shader_health.integrations.deadline.preflight import VALIDATOR_OK


def test_write_command_script_file_uses_windows_quoting_on_win32(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("sys.platform", "win32")
    command = ("mayapy", str(tmp_path / "scene file.ma"), "--report", "out.json")
    line = write_command_script_file(tmp_path / "command.txt", command)
    assert '"' in line or " " not in line.split()[1]
    assert (tmp_path / "command.txt").read_text(encoding="utf-8").strip() == line


def test_build_command_script_job_payload(tmp_path: Path):
    config = DeadlineConfig(
        mayapy="mayapy",
        queue="shader_health",
        user_name="pipeline",
    )
    command_script = tmp_path / "shader_health_command.txt"
    job_info, plugin_info, aux_files = build_command_script_job(
        config=config,
        scene_path=tmp_path / "scene.ma",
        report_path=tmp_path / "report.json",
        command_script_path=command_script,
        extra_args=("--renderer", "vray"),
    )
    assert job_info["Plugin"] == "CommandScript"
    assert job_info["Frames"] == "0"
    assert job_info["Pool"] == "shader_health"
    assert job_info["UserName"] == "pipeline"
    assert plugin_info["StartupDirectory"] == str(tmp_path)
    assert aux_files == (str(command_script),)


def test_build_maya_batch_script_job_payload(tmp_path: Path):
    config = DeadlineConfig(group="lookdev")
    job_info, plugin_info, aux_files = build_maya_batch_script_job(
        config=config,
        scene_path=tmp_path / "scene.ma",
        script_path=tmp_path / "shader_health_deadline_validate.py",
        maya_version="2024",
    )
    assert job_info["Plugin"] == "MayaBatch"
    assert job_info["Group"] == "lookdev"
    assert plugin_info["SceneFile"] == str(tmp_path / "scene.ma")
    assert plugin_info["ScriptFile"] == str(tmp_path / "shader_health_deadline_validate.py")
    assert plugin_info["ScriptJob"] is True
    assert plugin_info["Version"] == "2024"
    assert aux_files == ()


def test_submit_shader_health_validation_job_submits_command_script(tmp_path: Path):
    requests: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> DeadlineResponse:
        requests.append(request)
        return DeadlineResponse(status_code=200, body="job-551")

    client = DeadlineClient(DeadlineConfig(mayapy="mayapy"), transport=transport)
    command_script = tmp_path / "shader_health_command.txt"
    result = submit_shader_health_validation_job(
        client=client,
        scene_path=tmp_path / "scene.ma",
        report_path=tmp_path / "report.json",
        command_script_path=command_script,
    )

    assert result.job_id == "job-551"
    assert result.plugin == "command_script"
    assert result.report_path == tmp_path / "report.json"
    assert command_script.is_file()
    assert result.command_script_line is not None
    assert "shader_health" in result.command_script_line

    payload = json.loads(requests[0].body.decode("utf-8"))
    assert payload["JobInfo"]["Plugin"] == "CommandScript"
    assert payload["AuxFiles"] == [str(command_script)]


def test_submit_shader_health_validation_job_can_run_local_preflight(tmp_path: Path):
    calls: list[tuple[str, ...]] = []

    def runner(command: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(tuple(command))
        return subprocess.CompletedProcess(command, VALIDATOR_OK)

    def transport(request: HttpRequest, timeout: float) -> DeadlineResponse:
        return DeadlineResponse(status_code=200, body="job-552")

    client = DeadlineClient(DeadlineConfig(), transport=transport)
    result = submit_shader_health_validation_job(
        client=client,
        scene_path=tmp_path / "scene.ma",
        report_path=tmp_path / "report.json",
        command_script_path=tmp_path / "command.txt",
        run_local_preflight=True,
        runner=runner,
    )
    assert result.preflight_result is not None
    assert result.preflight_result.allowed is True
    assert calls


def test_submit_shader_health_validation_job_blocks_on_eligibility(tmp_path: Path):
    client = DeadlineClient(DeadlineConfig())

    with pytest.raises(DeadlineSubmitError, match="eligibility gate"):
        submit_shader_health_validation_job(
            client=client,
            scene_path=tmp_path / "scene.ma",
            report_path=tmp_path / "report.json",
            command_script_path=tmp_path / "command.txt",
            scene_state=FarmSceneState(scene_saved=False),
            validation_result=FarmValidationResult.from_validator_exit_code(0),
        )


def test_submit_shader_health_validation_job_requires_script_path_for_maya_batch(
    tmp_path: Path,
):
    client = DeadlineClient(DeadlineConfig())

    with pytest.raises(DeadlineSubmitError, match="script_path is required"):
        submit_shader_health_validation_job(
            client=client,
            scene_path=tmp_path / "scene.ma",
            report_path=tmp_path / "report.json",
            plugin="maya_batch",
        )
