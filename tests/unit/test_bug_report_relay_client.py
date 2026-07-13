from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pipeline_inspector.integrations.bug_report import (
    DEFAULT_PUBLIC_BUG_REPORT_RELAY_URL,
    BugReportPayload,
    BugReportRelayClient,
    BugReportRelayConfig,
    HttpRequest,
    RelayResponse,
    maybe_submit_bug_report,
    parse_issue_url,
)
from pipeline_inspector.integrations.bug_report.relay_client import is_jpeg_bytes
from pipeline_inspector.integrations.bug_report.throttle import record_bug_report_submission
from pipeline_inspector.studio_config import BugReportSettings, StudioConfig


def _config() -> BugReportRelayConfig:
    return BugReportRelayConfig(
        relay_url="https://pipeline.studio.internal/shader-health/bug-report",
        api_key="studio-secret",
        allow_screenshot=True,
    )


def _payload() -> BugReportPayload:
    return BugReportPayload(
        title="Pipeline Inspector bug",
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
    assert request.headers["User-Agent"] == "maya-pipeline-inspector"
    assert request.headers["Content-Type"].startswith("multipart/form-data; boundary=")
    body = request.body.decode("utf-8", errors="replace")
    assert 'name="payload"' in body
    assert "Pipeline Inspector bug" in body
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


def test_bug_report_relay_client_submits_without_api_key_for_public_relay():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> RelayResponse:
        captured.append(request)
        _ = timeout
        return RelayResponse(
            status_code=201,
            body='{"issue_url":"https://github.com/org/repo/issues/11"}',
            json_data={"issue_url": "https://github.com/org/repo/issues/11"},
        )

    client = BugReportRelayClient(
        BugReportRelayConfig(
            relay_url=DEFAULT_PUBLIC_BUG_REPORT_RELAY_URL,
            api_key="",
        ),
        transport=transport,
    )

    result = client.submit(_payload())

    assert result.submitted is True
    assert "Authorization" not in captured[0].headers


def test_maybe_submit_bug_report_uses_public_relay_without_api_key(tmp_path: Path):
    state_path = tmp_path / "bug_report_throttle.json"

    def transport(request: HttpRequest, timeout: float) -> RelayResponse:
        _ = (request, timeout)
        return RelayResponse(
            status_code=201,
            body='{"issue_url":"https://github.com/org/repo/issues/88"}',
            json_data={"issue_url": "https://github.com/org/repo/issues/88"},
        )

    result = maybe_submit_bug_report(
        StudioConfig(
            bug_report=BugReportSettings(
                enabled=True,
                relay_url="",
                api_key="",
            )
        ),
        _payload(),
        transport=transport,
        throttle_state_path=state_path,
    )

    assert result.submitted is True
    assert result.issue_url.endswith("/issues/88")


def test_maybe_submit_bug_report_returns_disabled_when_connector_off():
    result = maybe_submit_bug_report(
        StudioConfig(bug_report=BugReportSettings(enabled=False)),
        _payload(),
    )

    assert result.submitted is False
    assert result.skipped_reason == "disabled"


def test_maybe_submit_bug_report_keeps_private_studio_relay_with_api_key(tmp_path: Path):
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> RelayResponse:
        captured.append(request)
        _ = timeout
        return RelayResponse(
            status_code=201,
            body='{"issue_url":"https://github.com/org/repo/issues/33"}',
            json_data={"issue_url": "https://github.com/org/repo/issues/33"},
        )

    result = maybe_submit_bug_report(
        StudioConfig(
            bug_report=BugReportSettings(
                enabled=True,
                relay_url="https://pipeline.studio.internal/shader-health/bug-report",
                api_key="studio-secret",
            )
        ),
        _payload(),
        transport=transport,
        throttle_state_path=tmp_path / "bug_report_throttle.json",
    )

    assert result.submitted is True
    assert captured[0].headers["Authorization"] == "Bearer studio-secret"


def test_maybe_submit_bug_report_blocks_when_local_daily_limit_reached(tmp_path: Path):
    state_path = tmp_path / "bug_report_throttle.json"
    now = datetime.now(timezone.utc)
    payload = BugReportPayload(
        title="Pipeline Inspector bug",
        description="Issue details from the Maya panel.",
        plugin_version="0.5.0",
        scene_basename="hero.ma",
        machine_id="workstation-01",
        os_user="artist",
    )

    record_bug_report_submission(
        machine_id="workstation-01",
        os_user="artist",
        now_utc=now,
        state_path=state_path,
    )
    record_bug_report_submission(
        machine_id="workstation-01",
        os_user="artist",
        now_utc=now,
        state_path=state_path,
    )

    result = maybe_submit_bug_report(
        StudioConfig(
            bug_report=BugReportSettings(
                enabled=True,
                relay_url="https://pipeline.studio.internal/shader-health/bug-report",
                api_key="studio-secret",
                max_reports_per_day=2,
            )
        ),
        payload,
        throttle_state_path=state_path,
    )

    assert result.submitted is False
    assert result.skipped_reason == "rate_limited"
    assert "2/2" in result.error_message


def test_maybe_submit_bug_report_records_successful_submission(tmp_path: Path):
    state_path = tmp_path / "bug_report_throttle.json"

    def transport(request: HttpRequest, timeout: float) -> RelayResponse:
        _ = (request, timeout)
        return RelayResponse(
            status_code=201,
            body='{"issue_url":"https://github.com/org/repo/issues/77"}',
            json_data={"issue_url": "https://github.com/org/repo/issues/77"},
        )

    payload = BugReportPayload(
        title="Pipeline Inspector bug",
        description="Issue details from the Maya panel.",
        plugin_version="0.5.0",
        scene_basename="hero.ma",
        machine_id="workstation-01",
        os_user="artist",
    )

    result = maybe_submit_bug_report(
        StudioConfig(
            bug_report=BugReportSettings(
                enabled=True,
                relay_url="https://pipeline.studio.internal/shader-health/bug-report",
                api_key="studio-secret",
                max_reports_per_day=2,
            )
        ),
        payload,
        transport=transport,
        throttle_state_path=state_path,
    )

    assert result.submitted is True
    blocked = maybe_submit_bug_report(
        StudioConfig(
            bug_report=BugReportSettings(
                enabled=True,
                relay_url="https://pipeline.studio.internal/shader-health/bug-report",
                api_key="studio-secret",
                max_reports_per_day=1,
            )
        ),
        payload,
        transport=transport,
        throttle_state_path=state_path,
    )

    assert blocked.submitted is False
    assert blocked.skipped_reason == "rate_limited"


def test_bug_report_relay_client_maps_relay_429_to_rate_limited():
    def transport(request: HttpRequest, timeout: float) -> RelayResponse:
        _ = (request, timeout)
        return RelayResponse(
            status_code=429,
            body='{"error":"rate_limited"}',
            json_data={"error": "rate_limited"},
        )

    client = BugReportRelayClient(_config(), transport=transport)

    result = client.submit(_payload())

    assert result.submitted is False
    assert result.skipped_reason == "rate_limited"
    assert result.status_code == 429


def test_is_jpeg_bytes_detects_jpeg_magic_prefix():
    assert is_jpeg_bytes(b"\xff\xd8\xff\xe0") is True
    assert is_jpeg_bytes(b"PNG") is False
