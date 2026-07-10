from __future__ import annotations

import json

from shader_health.integrations.ftrack import FtrackClient, FtrackConfig, FtrackResponse
from shader_health.integrations.ftrack.client import HttpRequest


def test_ftrack_config_normalizes_endpoint_url():
    config = FtrackConfig(
        api_url="https://studio.ftrackapp.com",
        api_user="pipeline.bot",
        api_key="secret",
        project="Demo Project",
    )

    assert config.endpoint_url == "https://studio.ftrackapp.com/api"


def test_ftrack_client_ping_returns_true_for_authenticated_query():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> FtrackResponse:
        captured.append(request)
        _ = timeout
        return FtrackResponse(
            status_code=200,
            body='[{"action": "query", "data": [{"id": "user-1"}]}]',
            json_data=[{"action": "query", "data": [{"id": "user-1"}]}],
        )

    client = FtrackClient(
        FtrackConfig(
            api_url="https://studio.ftrackapp.com",
            api_user="pipeline.bot",
            api_key="secret",
            project="Demo Project",
        ),
        transport=transport,
    )

    assert client.ping() is True
    assert captured[0].url == "https://studio.ftrackapp.com/api"
    assert captured[0].headers["ftrack-user"] == "pipeline.bot"
    assert captured[0].headers["ftrack-api-key"] == "secret"
    payload = json.loads(captured[0].body.decode("utf-8"))
    assert payload[0]["action"] == "query"


def test_ftrack_client_create_task_note_posts_note_payload():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> FtrackResponse:
        captured.append(request)
        _ = timeout
        return FtrackResponse(
            status_code=200,
            body='[{"action": "create", "data": {"id": "note-1"}}]',
            json_data=[{"action": "create", "data": {"id": "note-1"}}],
        )

    client = FtrackClient(
        FtrackConfig(
            api_url="https://studio.ftrackapp.com/api",
            api_user="pipeline.bot",
            api_key="secret",
            project="Demo Project",
        ),
        transport=transport,
    )

    note = client.create_task_note(task_id="task-42", content="Shader Health summary")

    assert note == {"id": "note-1"}
    payload = json.loads(captured[0].body.decode("utf-8"))
    assert payload[0]["entityType"] == "Note"
    assert payload[0]["data"]["content"] == "Shader Health summary"
    assert payload[0]["data"]["parent_id"] == "task-42"
    assert payload[0]["data"]["parent_type"] == "task"
