from __future__ import annotations

from pathlib import Path

from pipeline_inspector.integrations.ftrack import FtrackClient, FtrackConfig, FtrackResponse
from pipeline_inspector.integrations.ftrack.client import HttpRequest
from pipeline_inspector.integrations.ftrack.components import attach_html_report_to_note


def test_attach_html_report_to_note_uploads_component_and_links_note_component(tmp_path: Path):
    report_path = tmp_path / "pipeline_inspector_report.html"
    report_path.write_text("<html>report</html>", encoding="utf-8")
    requests: list[dict[str, object]] = []

    def transport(request: HttpRequest, timeout: float) -> FtrackResponse:
        _ = timeout
        import json

        payload = json.loads(request.body.decode("utf-8"))
        action = payload[0]
        requests.append(action)
        if action.get("action") == "query":
            return FtrackResponse(
                status_code=200,
                body='[{"action": "query", "data": [{"id": "loc-server"}]}]',
                json_data=[{"action": "query", "data": [{"id": "loc-server"}]}],
            )
        if action.get("action") == "create" and action.get("entity_type") == "Component":
            return FtrackResponse(
                status_code=200,
                body='[{"action": "create", "data": {"id": "comp-1"}}]',
                json_data=[{"action": "create", "data": {"id": "comp-1"}}],
            )
        if action.get("action") == "get_upload_metadata":
            return FtrackResponse(
                status_code=200,
                body='[{"action": "get_upload_metadata", "url": "https://upload.test", "headers": {}}]',
                json_data=[
                    {
                        "action": "get_upload_metadata",
                        "url": "https://upload.test",
                        "headers": {},
                    }
                ],
            )
        return FtrackResponse(
            status_code=200,
            body='[{"action": "create", "data": {"id": "entity-1"}}]',
            json_data=[{"action": "create", "data": {"id": "entity-1"}}],
        )

    def binary_transport(url: str, body: bytes, headers: dict[str, str], timeout: float) -> int:
        _ = (url, body, headers, timeout)
        return 200

    client = FtrackClient(
        FtrackConfig(
            api_url="https://studio.ftrackapp.com",
            api_user="pipeline.bot",
            api_key="secret",
            project="Demo Project",
        ),
        transport=transport,
    )

    component_id, error = attach_html_report_to_note(
        client,
        note_id="note-42",
        file_path=str(report_path),
        filename="pipeline_inspector_report.html",
        binary_transport=binary_transport,
    )

    assert error == ""
    assert component_id
    assert any(action.get("action") == "get_upload_metadata" for action in requests)
    assert any(
        action.get("action") == "create" and action.get("entity_type") == "ComponentLocation"
        for action in requests
    )
    assert any(
        action.get("action") == "create" and action.get("entity_type") == "NoteComponent"
        for action in requests
    )


def test_attach_html_report_to_note_reports_missing_file():
    client = FtrackClient(
        FtrackConfig(
            api_url="https://studio.ftrackapp.com",
            api_user="pipeline.bot",
            api_key="secret",
            project="Demo Project",
        ),
        transport=lambda _request, _timeout: FtrackResponse(status_code=200, body="[]", json_data=[]),
    )

    component_id, error = attach_html_report_to_note(
        client,
        note_id="note-42",
        file_path="/missing/report.html",
        filename="pipeline_inspector_report.html",
    )

    assert component_id == ""
    assert error == "missing_note_or_report_file"
