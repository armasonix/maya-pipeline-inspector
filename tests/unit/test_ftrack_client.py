from __future__ import annotations

import json

from pipeline_inspector.integrations.ftrack import FtrackClient, FtrackConfig, FtrackResponse
from pipeline_inspector.integrations.ftrack.client import HttpRequest
from pipeline_inspector.integrations.ftrack.queries import list_projects_expression


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


def test_ftrack_client_query_rows_surfaces_batch_exception():
    def transport(_request: HttpRequest, _timeout: float) -> FtrackResponse:
        return FtrackResponse(
            status_code=200,
            body=(
                '[{"action": "query", "exception": '
                '{"message": "Invalid user credentials.", "class_name": "NotAuthenticatedError"}}]'
            ),
            json_data=[
                {
                    "action": "query",
                    "exception": {
                        "message": "Invalid user credentials.",
                        "class_name": "NotAuthenticatedError",
                    },
                }
            ],
        )

    client = FtrackClient(
        FtrackConfig(
            api_url="https://studio.ftrackapp.com",
            api_user="Pavel Kuzmenko",
            api_key="secret",
            project="Demo Project",
        ),
        transport=transport,
    )

    rows, status_code, exception_message = client.query_rows(list_projects_expression())
    assert status_code == 200
    assert rows == []
    assert "Invalid user credentials" in exception_message


def test_ftrack_client_query_rows_accepts_single_entity_dict():
    def transport(_request: HttpRequest, _timeout: float) -> FtrackResponse:
        return FtrackResponse(
            status_code=200,
            body='[{"action": "query", "data": {"id": "project-1", "name": "Demo Project"}}]',
            json_data=[
                {"action": "query", "data": {"id": "project-1", "name": "Demo Project"}}
            ],
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

    rows, status_code, exception_message = client.query_rows(
        'select id, name, full_name from Project where name is "Demo Project"'
    )
    assert status_code == 200
    assert exception_message == ""
    assert rows == [{"id": "project-1", "name": "Demo Project"}]


def test_ftrack_client_create_task_note_posts_note_payload():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> FtrackResponse:
        captured.append(request)
        _ = timeout
        payload = json.loads(request.body.decode("utf-8"))
        if payload[0]["action"] == "query":
            expression = str(payload[0]["expression"])
            if "from User where username" in expression:
                return FtrackResponse(
                    status_code=200,
                    body='[{"action": "query", "data": [{"id": "user-1"}]}]',
                    json_data=[{"action": "query", "data": [{"id": "user-1"}]}],
                )
            return FtrackResponse(
                status_code=200,
                body='[{"action": "query", "data": [{"id": "user-1"}]}]',
                json_data=[{"action": "query", "data": [{"id": "user-1"}]}],
            )
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

    note_result = client.create_task_note(task_id="task-42", content="Pipeline Inspector summary")

    assert note_result.entity == {"id": "note-1"}
    assert note_result.exception_message == ""
    create_payload = json.loads(captured[-1].body.decode("utf-8"))
    op = create_payload[0]
    assert op["entity_type"] == "Note"
    assert op["entity_data"]["__entity_type__"] == "Note"
    assert op["entity_data"]["content"] == "Pipeline Inspector summary"
    assert op["entity_data"]["parent_id"] == "task-42"
    assert op["entity_data"]["parent_type"] == "Task"
    assert op["entity_data"]["author"] == {"__entity_type__": "User", "id": "user-1"}
    generated_id = op["entity_data"]["id"]
    assert generated_id
    assert op["entity_key"] == [generated_id]


def test_ftrack_client_create_task_note_surfaces_top_level_exception_content():
    def transport(request: HttpRequest, timeout: float) -> FtrackResponse:
        _ = timeout
        payload = json.loads(request.body.decode("utf-8"))
        if payload[0]["action"] == "query":
            expression = str(payload[0]["expression"])
            if "from Appointment" in expression:
                return FtrackResponse(
                    status_code=200,
                    body='[{"action": "query", "data": []}]',
                    json_data=[{"action": "query", "data": []}],
                )
            return FtrackResponse(
                status_code=200,
                body='[{"action": "query", "data": [{"id": "user-1"}]}]',
                json_data=[{"action": "query", "data": [{"id": "user-1"}]}],
            )
        return FtrackResponse(
            status_code=200,
            body=(
                '{"exception":"IntegrityError","content":"Invalid parent_type None for Note",'
                '"error_code":null}'
            ),
            json_data={
                "exception": "IntegrityError",
                "content": "Invalid parent_type None for Note",
                "error_code": None,
            },
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

    note_result = client.create_task_note(task_id="task-42", content="Pipeline Inspector summary")

    assert note_result.entity is None
    assert "Invalid parent_type None for Note" in note_result.exception_message


def test_ftrack_client_update_task_status_posts_status_update():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> FtrackResponse:
        captured.append(request)
        _ = timeout
        payload = json.loads(request.body.decode("utf-8"))
        if payload[0]["action"] == "query":
            return FtrackResponse(
                status_code=200,
                body=(
                    '[{"action": "query", "data": '
                    '[{"id": "status-1", "name": "Pending Review"}]}]'
                ),
                json_data=[
                    {"action": "query", "data": [{"id": "status-1", "name": "Pending Review"}]}
                ],
            )
        return FtrackResponse(
            status_code=200,
            body='[{"action": "update", "data": {"id": "task-42"}}]',
            json_data=[{"action": "update", "data": {"id": "task-42"}}],
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

    result = client.update_task_status(task_id="task-42", status_name="Pending Review")

    assert result.exception_message == ""
    update_payload = json.loads(captured[-1].body.decode("utf-8"))
    assert update_payload[0]["action"] == "update"
    assert update_payload[0]["entity_type"] == "Task"
    assert update_payload[0]["entity_key"] == ["task-42"]
    assert update_payload[0]["entity_data"]["status_id"] == "status-1"
