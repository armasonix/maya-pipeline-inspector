from __future__ import annotations

from shader_health.integrations.bug_report import (
    BugReportPayload,
    BugReportRelayClient,
    BugReportRelayConfig,
    HttpRequest,
    RelayResponse,
    maybe_submit_bug_report,
    parse_issue_url,
)
from shader_health.integrations.bug_report.relay_client import is_jpeg_bytes
from shader_health.studio_config import BugReportSettings, StudioConfig


def _config() -> BugReportRelayConfig:
    return BugReportRelayConfig(
        relay_url="https://pipeline.studio.internal/shader-health/bug-report",
        api_key="studio-secret",
        allow_screenshot=True,
    )


def _payload() -> BugReportPayload:
    return BugReportPayload(
        title="Shader Health bug",
        description="Issue details from the Maya panel.",
        plugin_version="0.5.0",
        scene_basename="hero.ma",
        validation_summary="Health 40/100",
    )


def test_parse_issue_url_reads_issue_url_from_relay_json():
    response = RelayResponse(
        status_code=201,
        body='{"issue_url":"https://github.com/org/repo/issues/42"}',
        json_data={"issue_url": "https://github.com/org/repo/issues/42"},
    )

    assert parse_issue_url(response) == "https://github.com/org/repo/issues/42"


def test_bug_report_relay_client_submits_multipart_payload_with_jpeg_and_returns_issue_url():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> RelayResponse:
        captured.append(request)
        _ = timeout
        return RelayResponse(
            status_code=201,
            body='{"issue_url":"https://github.com/org/repo/issues/99"}',
            json_data={"issue_url": "https://github.com/org/repo/issues/99"},
        )

    client = BugReportRelayClient(_config(), transport=transport)
    screenshot = b"\xff\xd8\xff\xe0" + b"jpeg-body"

    result = client.submit(_payload(), screenshot_jpeg=screenshot)

    assert result.submitted is True
    assert result.issue_url == "https://github.com/org/repo/issues/99"
    assert result.status_code == 201
    assert len(captured) == 1
    request = captured[0]
    assert request.method == "POST"
    assert request.url.endswith("/bug-report")
    assert request.headers["Authorization"] == "Bearer studio-secret"
    assert request.headers["Content-Type"].startswith("multipart/form-data; boundary=")
    body = request.body.decode("utf-8", errors="replace")
    assert 'name="payload"' in body
    assert "Shader Health bug" in body
    assert 'filename="screenshot.jpg"' in body
    assert b"jpeg-body" in request.body


def test_bug_report_relay_client_omits_invalid_screenshot_and_still_submits():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> RelayResponse:
        captured.append(request)
        _ = timeout
        return RelayResponse(
            status_code=201,
            body='{"issue_url":"https://github.com/org/repo/issues/55"}',
            json_data={"issue_url": "https://github.com/org/repo/issues/55"},
        )

    client = BugReportRelayClient(_config(), transport=transport)

    result = client.submit(_payload(), screenshot_jpeg=b"not-a-jpeg")

    assert result.submitted is True
    assert 'filename="screenshot.jpg"' not in captured[0].body.decode("utf-8", errors="replace")


def test_bug_report_relay_client_skips_screenshot_when_not_allowed():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> RelayResponse:
        captured.append(request)
        _ = timeout
        return RelayResponse(
            status_code=201,
            body='{"issue_url":"https://github.com/org/repo/issues/12"}',
            json_data={"issue_url": "https://github.com/org/repo/issues/12"},
        )

    client = BugReportRelayClient(
        _config().with_overrides(allow_screenshot=False),
        transport=transport,
    )

    result = client.submit(_payload(), screenshot_jpeg=b"\xff\xd8\xff\xe0jpeg")

    assert result.submitted is True
    assert 'filename="screenshot.jpg"' not in captured[0].body.decode("utf-8", errors="replace")


def test_maybe_submit_bug_report_returns_disabled_when_connector_off():
    result = maybe_submit_bug_report(
        StudioConfig(bug_report=BugReportSettings(enabled=False)),
        _payload(),
    )

    assert result.submitted is False
    assert result.skipped_reason == "disabled"


def test_maybe_submit_bug_report_returns_incomplete_config_when_relay_missing():
    result = maybe_submit_bug_report(
        StudioConfig(
            bug_report=BugReportSettings(
                enabled=True,
                relay_url="",
                api_key="secret",
            )
        ),
        _payload(),
    )

    assert result.submitted is False
    assert result.skipped_reason == "incomplete_config"


def test_is_jpeg_bytes_detects_jpeg_magic_prefix():
    assert is_jpeg_bytes(b"\xff\xd8\xff\xe0") is True
    assert is_jpeg_bytes(b"PNG") is False
