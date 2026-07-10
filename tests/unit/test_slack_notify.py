from __future__ import annotations

import json
from types import SimpleNamespace

from shader_health.core.manifest_gate import ManifestGatePolicy  # noqa: F401
from shader_health.core.scoring import HealthScore
from shader_health.integrations.slack.blocks import ValidationBlocksContext
from shader_health.integrations.slack.client import HttpRequest, SlackClient, SlackResponse
from shader_health.integrations.slack.notify import (
    matched_notify_events,
    maybe_send_slack_validation_notification,
    send_slack_validation_notification,
    should_send_slack_notification,
    validation_notification_context_from_run,
)
from shader_health.studio_config import (
    ConnectorSettings,
    SlackConnectorSettings,
    StudioConfig,
    StudioEnvironmentSettings,
)


def _context(**overrides: object) -> ValidationBlocksContext:
    defaults = {
        "scene_name": "hero.ma",
        "scene_path": r"C:\shots\hero.ma",
        "scan_scope": "scene",
        "profile_id": "publish_strict",
        "asset_class_id": "",
        "health_score": 42,
        "critical_count": 2,
        "error_count": 1,
        "warning_count": 3,
        "info_count": 0,
        "block_publish": True,
        "block_deadline": False,
    }
    defaults.update(overrides)
    return ValidationBlocksContext(**defaults)


def _slack_settings(**overrides: object) -> SlackConnectorSettings:
    defaults = {
        "enabled": True,
        "publish_webhook_url": "https://hooks.slack.com/services/publish",
        "deadline_webhook_url": "https://hooks.slack.com/services/deadline",
        "notify_on": ("block_publish", "block_deadline"),
    }
    defaults.update(overrides)
    return SlackConnectorSettings(**defaults)


def _studio_config(slack: SlackConnectorSettings, *, render_root: str = "") -> StudioConfig:
    return StudioConfig(
        connectors=ConnectorSettings(slack=slack),
        studio_environment=StudioEnvironmentSettings(render_root=render_root),
    )


def test_validation_notification_context_from_run_reads_snapshot_and_health():
    result = SimpleNamespace(
        snapshot=SimpleNamespace(scene_path=r"C:\shots\hero.ma"),
        scan_scope="scene",
        profile_id="publish_strict",
        asset_class_id="character",
        health_score=HealthScore(
            score=42,
            raw_score=42,
            critical=2,
            error=1,
            warning=3,
            info=0,
            block_publish=True,
            block_deadline=False,
        ),
    )

    context = validation_notification_context_from_run(result)

    assert context.scene_name == "hero.ma"
    assert context.scene_path == r"C:\shots\hero.ma"
    assert context.profile_id == "publish_strict"
    assert context.asset_class_id == "character"
    assert context.health_score == 42
    assert context.block_publish is True
    assert context.block_deadline is False


def test_should_send_slack_notification_requires_enabled_connector_and_routed_webhook():
    settings = _slack_settings()

    assert should_send_slack_notification(
        settings,
        block_publish=True,
        block_deadline=False,
    )
    assert not should_send_slack_notification(
        _slack_settings(enabled=False),
        block_publish=True,
        block_deadline=False,
    )
    assert not should_send_slack_notification(
        settings,
        block_publish=False,
        block_deadline=False,
    )
    assert not should_send_slack_notification(
        _slack_settings(publish_webhook_url="", deadline_webhook_url=""),
        block_publish=True,
        block_deadline=False,
    )


def test_send_slack_validation_notification_skips_when_connector_disabled():
    result = send_slack_validation_notification(
        _studio_config(_slack_settings(enabled=False)),
        _context(),
    )

    assert result.sent is False
    assert result.skipped_reason == "disabled"


def test_send_slack_validation_notification_posts_blocks_to_routed_publish_webhook():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> SlackResponse:
        captured.append(request)
        _ = timeout
        return SlackResponse(status_code=200, body="ok", json_data=None)

    def client_factory() -> SlackClient:
        return SlackClient(transport=transport)

    result = send_slack_validation_notification(
        _studio_config(_slack_settings()),
        _context(),
        client_factory=client_factory,
    )

    assert result.sent is True
    assert result.routes_sent == 1
    assert len(captured) == 1
    assert captured[0].url == "https://hooks.slack.com/services/publish"
    payload = json.loads(captured[0].body.decode("utf-8"))
    assert payload["blocks"][0]["text"]["text"] == "Shader Health: Publish block"


def test_send_slack_validation_notification_routes_deadline_block_to_deadline_webhook():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> SlackResponse:
        captured.append(request)
        _ = timeout
        return SlackResponse(status_code=200, body="ok", json_data=None)

    result = send_slack_validation_notification(
        _studio_config(_slack_settings()),
        _context(block_publish=False, block_deadline=True),
        client_factory=lambda: SlackClient(transport=transport),
    )

    assert result.sent is True
    assert captured[0].url == "https://hooks.slack.com/services/deadline"


def test_send_slack_validation_notification_includes_report_link_when_enabled():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> SlackResponse:
        captured.append(request)
        _ = timeout
        return SlackResponse(status_code=200, body="ok", json_data=None)

    result = send_slack_validation_notification(
        _studio_config(
            _slack_settings(include_report_link=True),
            render_root=r"\\farm\render",
        ),
        _context(scene_path=r"\\farm\assets\hero\hero.ma"),
        client_factory=lambda: SlackClient(transport=transport),
    )

    assert result.sent is True
    payload = json.loads(captured[0].body.decode("utf-8"))
    report_blocks = [
        block
        for block in payload["blocks"]
        if "Report:" in block.get("text", {}).get("text", "")
    ]
    assert report_blocks


def test_maybe_send_slack_validation_notification_accepts_validation_run_result():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> SlackResponse:
        captured.append(request)
        _ = timeout
        return SlackResponse(status_code=200, body="ok", json_data=None)

    run_result = SimpleNamespace(
        snapshot=SimpleNamespace(scene_path="/tmp/hero.ma"),
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

    result = maybe_send_slack_validation_notification(
        _studio_config(_slack_settings()),
        run_result,
        client_factory=lambda: SlackClient(transport=transport),
    )

    assert result.sent is True
    assert len(captured) == 1


def test_matched_notify_events_returns_publish_and_deadline_flags():
    settings = _slack_settings(notify_on=("block_publish", "block_deadline"))

    assert matched_notify_events(
        settings,
        block_publish=True,
        block_deadline=True,
    ) == ("block_publish", "block_deadline")
