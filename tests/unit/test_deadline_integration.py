from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from shader_health.integrations.deadline import (
    DeadlineClient,
    DeadlineClientError,
    DeadlineConfig,
    HttpRequest,
    run_deadline_preflight,
)
from shader_health.integrations.deadline.client import DeadlineResponse
from shader_health.integrations.deadline.preflight import (
    PREFLIGHT_ERROR,
    SUBMISSION_ALLOWED,
    SUBMISSION_BLOCKED,
    VALIDATOR_CONFIG_ERROR,
    VALIDATOR_DEADLINE_BLOCK,
    VALIDATOR_OK,
    build_validator_command,
)


def test_deadline_config_resolves_packaged_profile_path():
    config = DeadlineConfig(profile_id="deadline_critical")
    path = config.resolved_profile_path()
    assert path.name == "deadline_critical.json"
    assert path.is_file()


def test_deadline_config_from_env(tmp_path: Path):
    profile_path = tmp_path / "custom_deadline.json"
    profile_path.write_text("{}", encoding="utf-8")
    config = DeadlineConfig.from_env(
        {
            "SHADER_HEALTH_DEADLINE_API_URL": "http://farm.local:8082",
            "SHADER_HEALTH_DEADLINE_TIMEOUT": "12.5",
            "SHADER_HEALTH_DEADLINE_PROFILE_PATH": str(profile_path),
            "SHADER_HEALTH_DEADLINE_QUEUE": "shader_q",
        }
    )
    assert config.api_url == "http://farm.local:8082"
    assert config.timeout_seconds == 12.5
    assert config.resolved_profile_path() == profile_path
    assert config.queue == "shader_q"


def test_deadline_config_from_json(tmp_path: Path):
    config_path = tmp_path / "deadline.json"
    config_path.write_text(
        json.dumps(
            {
                "api_url": "http://deadline:8082",
                "profile_id": "deadline_critical",
                "queue": "lookdev",
            }
        ),
        encoding="utf-8",
    )
    config = DeadlineConfig.from_json(config_path)
    assert config.api_url == "http://deadline:8082"
    assert config.queue == "lookdev"
    assert config.resolved_profile_path().name == "deadline_critical.json"


def test_build_validator_command_runs_validator_in_critical_mode(tmp_path: Path):
    command = build_validator_command(
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
        return subprocess.CompletedProcess(command, VALIDATOR_DEADLINE_BLOCK)

    result = run_deadline_preflight(
        scene_path=tmp_path / "scene.ma",
        report_path=tmp_path / "report.json",
        profile_path=tmp_path / "deadline_critical.json",
        runner=runner,
    )

    assert result.allowed is False
    assert result.exit_code == SUBMISSION_BLOCKED
    assert result.validator_exit_code == VALIDATOR_DEADLINE_BLOCK
    assert calls[0][0] == "mayapy"


def test_deadline_preflight_allows_clean_validation(tmp_path: Path):
    def runner(command: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, VALIDATOR_OK)

    result = run_deadline_preflight(
        scene_path=tmp_path / "scene.ma",
        report_path=tmp_path / "report.json",
        profile_path=tmp_path / "deadline_critical.json",
        runner=runner,
    )

    assert result.allowed is True
    assert result.exit_code == SUBMISSION_ALLOWED


def test_deadline_preflight_maps_validator_errors_to_preflight_error(tmp_path: Path):
    def runner(command: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, VALIDATOR_CONFIG_ERROR)

    result = run_deadline_preflight(
        scene_path=tmp_path / "scene.ma",
        report_path=tmp_path / "report.json",
        profile_path=tmp_path / "deadline_critical.json",
        runner=runner,
    )

    assert result.allowed is False
    assert result.exit_code == PREFLIGHT_ERROR


def test_deadline_client_ping_uses_jobs_endpoint():
    requests: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> DeadlineResponse:
        requests.append(request)
        assert timeout == 15.0
        return DeadlineResponse(status_code=200, body="[]", json_data=[])

    client = DeadlineClient(
        DeadlineConfig(api_url="http://localhost:8082", timeout_seconds=15.0),
        transport=transport,
    )
    assert client.ping() is True
    assert len(requests) == 1
    assert requests[0].method == "GET"
    assert requests[0].url == "http://localhost:8082/api/jobs?IdOnly=true"


def test_deadline_client_get_job():
    def transport(request: HttpRequest, timeout: float) -> DeadlineResponse:
        assert request.url == "http://farm:8082/api/jobs?JobID=job-42"
        return DeadlineResponse(
            status_code=200,
            body='{"_id":"job-42","JobStatus":"Completed"}',
            json_data={"_id": "job-42", "JobStatus": "Completed"},
        )

    client = DeadlineClient(DeadlineConfig(api_url="http://farm:8082"), transport=transport)
    payload = client.get_job("job-42")
    assert payload["_id"] == "job-42"
    assert payload["JobStatus"] == "Completed"


def test_deadline_client_submit_job_returns_plain_text_id():
    requests: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> DeadlineResponse:
        requests.append(request)
        return DeadlineResponse(status_code=200, body="job-9001")

    client = DeadlineClient(DeadlineConfig(api_url="http://farm:8082"), transport=transport)
    job_id = client.submit_job(
        job_info={"Name": "Shader Health", "Plugin": "CommandScript", "Frames": "0"},
        plugin_info={"StartupDirectory": "/"},
    )
    assert job_id == "job-9001"
    assert requests[0].method == "POST"
    assert requests[0].url == "http://farm:8082/api/jobs"
    payload = json.loads(requests[0].body.decode("utf-8"))
    assert payload["JobInfo"]["Plugin"] == "CommandScript"
    assert payload["AuxFiles"] == []
    assert payload["IdOnly"] is True


def test_deadline_client_submit_job_raises_on_http_error():
    def transport(request: HttpRequest, timeout: float) -> DeadlineResponse:
        return DeadlineResponse(status_code=400, body="Missing JobInfo")

    client = DeadlineClient(DeadlineConfig(), transport=transport)
    with pytest.raises(DeadlineClientError, match="submit job failed"):
        client.submit_job(job_info={}, plugin_info={})
