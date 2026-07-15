from __future__ import annotations

from pathlib import Path

from pipeline_inspector.integrations.shotgrid import ShotGridClient, ShotGridConfig, ShotGridResponse
from pipeline_inspector.integrations.shotgrid.attachments import attach_html_report_to_note
from pipeline_inspector.integrations.shotgrid.client import HttpRequest


def test_attach_html_report_to_note_uploads_multipart_payload(tmp_path: Path):
    report_path = tmp_path / "pipeline_inspector_report.html"
    report_path.write_text("<html>report</html>", encoding="utf-8")
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> ShotGridResponse:
        _ = timeout
        captured.append(request)
        if request.url.endswith("/auth/access_token"):
            return ShotGridResponse(
                status_code=200,
                body='{"data": {"access_token": "token-1"}}',
                json_data={"data": {"access_token": "token-1"}},
            )
        return ShotGridResponse(
            status_code=201,
            body='{"data": {"type": "Attachment", "id": 501}}',
            json_data={"data": {"type": "Attachment", "id": 501}},
        )

    client = ShotGridClient(
        ShotGridConfig(
            site_url="https://studio.shotgrid.autodesk.com",
            script_name="pipeline_inspector",
            api_key="secret",
            project="Demo Project",
        ),
        transport=transport,
    )

    attachment_id, error = attach_html_report_to_note(
        client,
        note_id=99,
        file_path=str(report_path),
        filename="pipeline_inspector_report.html",
    )

    assert error == ""
    assert attachment_id == "501"
    upload_request = next(request for request in captured if "/upload/Attachment/99" in request.url)
    assert upload_request.method == "POST"
    assert b"multipart/form-data" in upload_request.headers["Content-Type"].encode()
    assert b"pipeline_inspector_report.html" in (upload_request.body or b"")


def test_attach_html_report_to_note_reports_missing_file():
    client = ShotGridClient(
        ShotGridConfig(
            site_url="https://studio.shotgrid.autodesk.com",
            script_name="pipeline_inspector",
            api_key="secret",
            project="Demo Project",
        ),
        transport=lambda _request, _timeout: ShotGridResponse(status_code=200, body="{}", json_data={}),
    )

    attachment_id, error = attach_html_report_to_note(
        client,
        note_id=1,
        file_path="/missing/report.html",
        filename="pipeline_inspector_report.html",
    )

    assert attachment_id == ""
    assert error == "missing_note_or_report_file"
