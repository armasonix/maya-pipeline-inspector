from __future__ import annotations

import json
from types import SimpleNamespace

from shader_health.core.manifest_gate import ManifestGatePolicy  # noqa: F401
from shader_health.core.scoring import HealthScore
from shader_health.integrations.shotgrid import ShotGridClient, ShotGridConfig, ShotGridResponse
from shader_health.integrations.shotgrid.client import HttpRequest
from shader_health.integrations.shotgrid.publish import (
    maybe_publish_validation_summary,
    publish_validation_summary,
    resolve_entity,
)
from shader_health.integrations.trackers.publish import ValidationPublishPayload
from shader_health.studio_config import (
    ConnectorSettings,
    ShotGridConnectorSettings,
    StudioConfig,
    resolve_shotgrid_config,
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


def _shotgrid_settings(**overrides: object) -> ShotGridConnectorSettings:
    defaults = {
        "enabled": True,
        "site_url": "https://studio.shotgrid.autodesk.com",
        "script_name": "shader_health",
        "api_key": "secret",
        "project": "Demo Project",
        "entity_type": "Shot",
    }
    defaults.update(overrides)
    return ShotGridConnectorSettings(**defaults)


def _studio_config(shotgrid: ShotGridConnectorSettings) -> StudioConfig:
    return StudioConfig(connectors=ConnectorSettings(shotgrid=shotgrid))


def test_resolve_shotgrid_config_requires_complete_settings():
    assert resolve_shotgrid_config(_studio_config(_shotgrid_settings())) is not None
    assert resolve_shotgrid_config(_studio_config(_shotgrid_settings(enabled=False))) is None
    assert resolve_shotgrid_config(_studio_config(_shotgrid_settings(api_key=""))) is None


def test_resolve_entity_prefers_payload_metadata():
    captured: list[str] = []

    def transport(request: HttpRequest, timeout: float) -> ShotGridResponse:
        _ = timeout
        captured.append(request.url)
        if request.url.endswith("/auth/access_token"):
            return ShotGridResponse(
                status_code=200,
                body='{"data": {"access_token": "token-1"}}',
                json_data={"data": {"access_token": "token-1"}},
            )
        return ShotGridResponse(status_code=200, body="{}", json_data={})

    client = ShotGridClient(
        ShotGridConfig(
            site_url="https://studio.shotgrid.autodesk.com",
            script_name="shader_health",
            api_key="secret",
            project="Demo Project",
        ),
        transport=transport,
    )

    resolved = resolve_entity(
        client,
        client.config,
        _payload(metadata={"shot_id": "88"}),
    )

    assert resolved == ("Shot", 88)
    assert all("/entity/shots" not in url for url in captured)


def test_publish_validation_summary_creates_note_from_scene_lookup():
    requests: list[tuple[str, dict[str, object] | None]] = []

    def transport(request: HttpRequest, timeout: float) -> ShotGridResponse:
        _ = timeout
        payload = None
        if request.body and request.headers.get("Content-Type") == "application/json":
            payload = json.loads(request.body.decode("utf-8"))
        requests.append((request.url, payload))
        if request.url.endswith("/auth/access_token"):
            return ShotGridResponse(
                status_code=200,
                body='{"data": {"access_token": "token-1"}}',
                json_data={"data": {"access_token": "token-1"}},
            )
        if "/entity/projects" in request.url:
            return ShotGridResponse(
                status_code=200,
                body='{"data": [{"id": 12, "type": "Project"}]}',
                json_data={"data": [{"id": 12, "type": "Project"}]},
            )
        if "/entity/shots" in request.url:
            return ShotGridResponse(
                status_code=200,
                body='{"data": [{"id": 34, "type": "Shot", "code": "hero.ma"}]}',
                json_data={"data": [{"id": 34, "type": "Shot", "code": "hero.ma"}]},
            )
        return ShotGridResponse(
            status_code=201,
            body='{"data": {"type": "Note", "id": 99}}',
            json_data={"data": {"type": "Note", "id": 99}},
        )

    result = publish_validation_summary(
        _studio_config(_shotgrid_settings()),
        _payload(),
        client_factory=lambda config: ShotGridClient(config, transport=transport),
    )

    assert result.published is True
    assert result.external_url == "99"
    assert result.metadata["note_id"] == "99"
    assert any("/entity/shots" in url for url, _payload in requests)
    note_request = next(payload for url, payload in requests if payload and "note_links" in payload)
    assert note_request["note_links"] == [{"type": "Shot", "id": 34}]
    assert "Health Validation Result" in str(note_request["content"])


def test_publish_validation_summary_skips_when_entity_not_found():
    def transport(request: HttpRequest, timeout: float) -> ShotGridResponse:
        _ = timeout
        if request.url.endswith("/auth/access_token"):
            return ShotGridResponse(
                status_code=200,
                body='{"data": {"access_token": "token-1"}}',
                json_data={"data": {"access_token": "token-1"}},
            )
        return ShotGridResponse(status_code=200, body='{"data": []}', json_data={"data": []})

    result = publish_validation_summary(
        _studio_config(_shotgrid_settings()),
        _payload(),
        client_factory=lambda config: ShotGridClient(config, transport=transport),
    )

    assert result.published is False
    assert result.skipped_reason == "entity_not_found"


def test_maybe_publish_validation_summary_accepts_validation_run_result():
    def transport(request: HttpRequest, timeout: float) -> ShotGridResponse:
        _ = timeout
        if request.url.endswith("/auth/access_token"):
            return ShotGridResponse(
                status_code=200,
                body='{"data": {"access_token": "token-1"}}',
                json_data={"data": {"access_token": "token-1"}},
            )
        if "/entity/projects" in request.url:
            return ShotGridResponse(
                status_code=200,
                body='{"data": [{"id": 12, "type": "Project"}]}',
                json_data={"data": [{"id": 12, "type": "Project"}]},
            )
        if "/entity/shots" in request.url:
            return ShotGridResponse(
                status_code=200,
                body='{"data": [{"id": 34, "type": "Shot"}]}',
                json_data={"data": [{"id": 34, "type": "Shot"}]},
            )
        return ShotGridResponse(
            status_code=201,
            body='{"data": {"type": "Note", "id": 1}}',
            json_data={"data": {"type": "Note", "id": 1}},
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
        _studio_config(_shotgrid_settings()),
        run_result,
        client_factory=lambda config: ShotGridClient(config, transport=transport),
    )

    assert result.published is True
