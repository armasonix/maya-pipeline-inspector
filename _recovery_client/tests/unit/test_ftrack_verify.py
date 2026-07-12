from __future__ import annotations

from shader_health.integrations.ftrack import FtrackClient, FtrackResponse
from shader_health.integrations.ftrack.client import HttpRequest
from shader_health.integrations.ftrack.queries import list_projects_expression, ping_user_expression
from shader_health.integrations.ftrack.verify import verify_ftrack_connection
from shader_health.studio_config import ConnectorSettings, FtrackConnectorSettings, StudioConfig


def _studio(ftrack: FtrackConnectorSettings) -> StudioConfig:
    return StudioConfig(connectors=ConnectorSettings(ftrack=ftrack))


def test_verify_ftrack_connection_reports_auth_failure():
    def transport(_request: HttpRequest, _timeout: float) -> FtrackResponse:
        return FtrackResponse(
            status_code=200,
            body='[{"action": "query", "exception": {"message": "Invalid user credentials."}}]',
            json_data=[
                {"action": "query", "exception": {"message": "Invalid user credentials."}}
            ],
        )

    result = verify_ftrack_connection(
        _studio(
            FtrackConnectorSettings(
                enabled=True,
                api_url="https://studio.ftrackapp.com",
                api_user="Pavel Kuzmenko",
                api_key="secret",
                project="Demo",
            )
        ),
        client_factory=lambda config: FtrackClient(config, transport=transport),
    )

    assert result.ok is False
    assert "Authentication failed" in result.message
    assert "User name" in result.message


def test_verify_ftrack_connection_lists_projects_and_matches_configured_project():
    def transport(request: HttpRequest, timeout: float) -> FtrackResponse:
        _ = timeout
        payload = __import__("json").loads(request.body.decode("utf-8"))
        expression = str(payload[0]["expression"])
        if expression == ping_user_expression():
            return FtrackResponse(
                status_code=200,
                body='[{"action": "query", "data": [{"id": "user-1"}]}]',
                json_data=[{"action": "query", "data": [{"id": "user-1"}]}],
            )
        if expression == list_projects_expression():
            return FtrackResponse(
                status_code=200,
                body=(
                    '[{"action": "query", "data": '
                    '[{"id": "p1", "name": "mayaTestPipelineInspector", "full_name": "Demo"}]}]'
                ),
                json_data=[
                    {
                        "action": "query",
                        "data": [
                            {
                                "id": "p1",
                                "name": "mayaTestPipelineInspector",
                                "full_name": "Demo",
                            }
                        ],
                    }
                ],
            )
        return FtrackResponse(status_code=200, body="[]", json_data=[])

    result = verify_ftrack_connection(
        _studio(
            FtrackConnectorSettings(
                enabled=True,
                api_url="https://studio.ftrackapp.com",
                api_user="armasonix",
                api_key="secret",
                project="mayaTestPipelineInspector",
            )
        ),
        client_factory=lambda config: FtrackClient(config, transport=transport),
    )

    assert result.ok is True
    assert "mayaTestPipelineInspector" in result.message
