from __future__ import annotations

import json
from types import SimpleNamespace

from shader_health.core.manifest_gate import ManifestGatePolicy  # noqa: F401
from shader_health.core.scoring import HealthScore
from shader_health.integrations.ftrack import FtrackClient, FtrackConfig, FtrackResponse
from shader_health.integrations.ftrack.client import HttpRequest
from shader_health.integrations.ftrack.publish import (
    maybe_publish_validation_summary,
    publish_validation_summary,
    resolve_task_id,
)
from shader_health.integrations.trackers.publish import ValidationPublishPayload
from shader_health.studio_config import (
    ConnectorSettings,
    FtrackConnectorSettings,
    StudioConfig,
    resolve_ftrack_config,
)


def _payload(**overrides: object) -> ValidationPublishPayload:
    defaults = {
        "scene_name": "hero.ma",
        "scene_path": r"C:\shots\hero.ma",
        "scan_scope": "scene",
        "profile_id": "publish_strict",
        "asset_class_id": "",
        "health_score": 42,
        "critical_count": 1,
        "error_count": 0,
        "warning_count": 0,
        "info_count": 0,
        "block_publish": True,
        "block_deadline": False,
        "validated_at_utc": "2026-07-10T12:00:00Z",
    }
    defaults.update(overrides)
    return ValidationPublishPayload(**defaults)


def _ftrack_settings(**overrides: object) -> FtrackConnectorSettings:
    defaults = {
        "enabled": True,
        "api_url": "https://studio.ftrackapp.com",
        "api_user": "pipeline.bot",
        "api_key": "secret",
        "project": "Demo Project",
    }
    defaults.update(overrides)
    return FtrackConnectorSettings(**defaults)


def _studio_config(ftrack: FtrackConnectorSettings) -> StudioConfig:
    return StudioConfig(connectors=ConnectorSettings(ftrack=ftrack))


def test_resolve_ftrack_config_requires_complete_settings():
    assert resolve_ftrack_config(_studio_config(_ftrack_settings())) is not None
    assert resolve_ftrack_config(_studio_config(_ftrack_settings(enabled=False))) is None
    assert resolve_ftrack_config(_studio_config(_ftrack_settings(api_key=""))) is None


def test_resolve_task_id_prefers_payload_metadata():
    captured: list[str] = []

    def transport(request: HttpRequest, timeout: float) -> FtrackResponse:
        _ = timeout
        captured.append(request.body.decode("utf-8"))
        return FtrackResponse(status_code=200, body="[]", json_data=[])

    client = FtrackClient(
        FtrackConfig(
            api_url="https://studio.ftrackapp.com",
            api_user="pipeline.bot",
            api_key="secret",
            project="Demo Project",
        ),
        transport=transport,
    )

    task_id = resolve_task_id(
        client,
        client.config,
        _payload(metadata={"task_id": "task-99"}),
    )

    assert task_id == "task-99"
    assert captured == []


def test_publish_validation_summary_creates_task_note_from_scene_lookup():
    requests: list[dict[str, object]] = []

    def transport(request: HttpRequest, timeout: float) -> FtrackResponse:
        _ = timeout
        payload = json.loads(request.body.decode("utf-8"))
        requests.append(payload[0])
        if payload[0]["action"] == "query":
            return FtrackResponse(
                status_code=200,
                body='[{"action": "query", "data": [{"id": "task-42"}]}]',
                json_data=[{"action": "query", "data": [{"id": "task-42"}]}],
            )
        return FtrackResponse(
            status_code=200,
            body='[{"action": "create", "data": {"id": "note-7"}}]',
            json_data=[{"action": "create", "data": {"id": "note-7"}}],
        )

    def client_factory(config: FtrackConfig) -> FtrackClient:
        return FtrackClient(config, transport=transport)

    result = publish_validation_summary(
        _studio_config(_ftrack_settings()),
        _payload(),
        client_factory=client_factory,
    )

    assert result.published is True
    assert result.external_url == "note-7"
    assert result.metadata["note_id"] == "note-7"
    assert requests[0]["action"] == "query"
    assert requests[1]["action"] == "create"
    assert "Shader Health validation summary" in str(requests[1]["data"])


def test_publish_validation_summary_skips_when_task_not_found():
    def transport(_request: HttpRequest, _timeout: float) -> FtrackResponse:
        return FtrackResponse(
            status_code=200,
            body='[{"action": "query", "data": []}]',
            json_data=[{"action": "query", "data": []}],
        )

    result = publish_validation_summary(
        _studio_config(_ftrack_settings()),
        _payload(),
        client_factory=lambda config: FtrackClient(config, transport=transport),
    )

    assert result.published is False
    assert result.skipped_reason == "task_not_found"


def test_maybe_publish_validation_summary_accepts_validation_run_result():
    def transport(request: HttpRequest, timeout: float) -> FtrackResponse:
        _ = timeout
        payload = json.loads(request.body.decode("utf-8"))
        if payload[0]["action"] == "query":
            return FtrackResponse(
                status_code=200,
                body='[{"action": "query", "data": [{"id": "task-42"}]}]',
                json_data=[{"action": "query", "data": [{"id": "task-42"}]}],
            )
        return FtrackResponse(
            status_code=200,
            body='[{"action": "create", "data": {"id": "note-1"}}]',
            json_data=[{"action": "create", "data": {"id": "note-1"}}],
        )

    run_result = SimpleNamespace(
        snapshot=SimpleNamespace(
            scene_path="/tmp/hero.ma",
            scanned_at_utc="2026-07-10T12:00:00Z",
        ),
        scan_scope="scene",
        profile_id="publish_strict",
        asset_class_id="",
        health_score=HealthScore(
            score=40,
            raw_score=40,
            critical=1,
            block_publish=True,
        ),
    )

    result = maybe_publish_validation_summary(
        _studio_config(_ftrack_settings()),
        run_result,
        client_factory=lambda config: FtrackClient(config, transport=transport),
    )

    assert result.published is True
