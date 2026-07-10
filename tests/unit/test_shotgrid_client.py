from __future__ import annotations

import json
import urllib.parse

from shader_health.integrations.shotgrid import ShotGridClient, ShotGridConfig, ShotGridResponse
from shader_health.integrations.shotgrid.client import HttpRequest


def test_shotgrid_config_normalizes_api_base_url():
    config = ShotGridConfig(
        site_url="https://studio.shotgrid.autodesk.com",
        script_name="shader_health",
        api_key="secret",
        project="Demo Project",
    )

    assert config.api_base_url == "https://studio.shotgrid.autodesk.com/api/v1"
    assert config.normalized_entity_type == "Shot"
    assert config.entity_collection == "shots"


def test_shotgrid_config_supports_asset_entity_type():
    config = ShotGridConfig(
        site_url="https://studio.shotgrid.autodesk.com/api/v1",
        script_name="shader_health",
        api_key="secret",
        project="Demo Project",
        entity_type="asset",
    )

    assert config.normalized_entity_type == "Asset"
    assert config.entity_collection == "assets"


def test_shotgrid_client_ping_requests_access_token_and_projects():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> ShotGridResponse:
        captured.append(request)
        _ = timeout
        if request.url.endswith("/auth/access_token"):
            return ShotGridResponse(
                status_code=200,
                body='{"data": {"access_token": "token-1"}}',
                json_data={"data": {"access_token": "token-1"}},
            )
        return ShotGridResponse(
            status_code=200,
            body='{"data": [{"id": 1, "type": "Project"}]}',
            json_data={"data": [{"id": 1, "type": "Project"}]},
        )

    client = ShotGridClient(
        ShotGridConfig(
            site_url="https://studio.shotgrid.autodesk.com",
            script_name="shader_health",
            api_key="secret",
            project="Demo Project",
        ),
        transport=transport,
    )

    assert client.ping() is True
    assert len(captured) == 2
    assert captured[0].url.endswith("/auth/access_token")
    assert captured[0].headers["Content-Type"] == "application/x-www-form-urlencoded"
    form = urllib.parse.parse_qs(captured[0].body.decode("utf-8"))
    assert form["grant_type"] == ["client_credentials"]
    assert captured[1].headers["Authorization"] == "Bearer token-1"
    assert "/entity/projects" in captured[1].url


def test_shotgrid_client_create_entity_note_posts_note_payload():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> ShotGridResponse:
        captured.append(request)
        _ = timeout
        if request.url.endswith("/auth/access_token"):
            return ShotGridResponse(
                status_code=200,
                body='{"data": {"access_token": "token-1"}}',
                json_data={"data": {"access_token": "token-1"}},
            )
        return ShotGridResponse(
            status_code=201,
            body='{"data": {"type": "Note", "id": 99}}',
            json_data={"data": {"type": "Note", "id": 99}},
        )

    client = ShotGridClient(
        ShotGridConfig(
            site_url="https://studio.shotgrid.autodesk.com",
            script_name="shader_health",
            api_key="secret",
            project="Demo Project",
        ),
        transport=transport,
    )

    note = client.create_entity_note(
        content="Shader Health summary",
        project_id=12,
        entity_type="Shot",
        entity_id=34,
    )

    assert note == {"type": "Note", "id": 99}
    payload = json.loads(captured[-1].body.decode("utf-8"))
    assert payload["content"] == "Shader Health summary"
    assert payload["project"] == {"type": "Project", "id": 12}
    assert payload["note_links"] == [{"type": "Shot", "id": 34}]
