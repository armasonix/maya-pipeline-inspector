from __future__ import annotations

import json
from types import SimpleNamespace

from shader_health.core.manifest_gate import ManifestGatePolicy  # noqa: F401
from shader_health.core.scoring import HealthScore
from shader_health.integrations.discord import DiscordClient, DiscordConfig, DiscordResponse
from shader_health.integrations.discord.client import HttpRequest
from shader_health.integrations.discord.embed import ValidationEmbedContext
from shader_health.integrations.discord.notify import (
    matched_notify_events,
    maybe_send_discord_validation_notification,
    send_discord_validation_notification,
    should_send_discord_notification,
    validation_notification_context_from_run,
)
from shader_health.studio_config import (
    ConnectorSettings,
    DiscordConnectorSettings,
    StudioConfig,
)


def _context(**overrides: object) -> ValidationEmbedContext:
    defaults = {
        "scene_name": "hero.ma",
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
    return ValidationEmbedContext(**defaults)


def _discord_settings(**overrides: object) -> DiscordConnectorSettings:
    defaults = {
        "enabled": True,
        "webhook_url": "https://discord.com/api/webhooks/1/secret",
        "notify_on": ("block_publish",),
    }
    defaults.update(overrides)
    return DiscordConnectorSettings(**defaults)


def _studio_config(discord: DiscordConnectorSettings) -> StudioConfig:
    return StudioConfig(connectors=ConnectorSettings(discord=discord))


def test_validation_notification_context_from_run_reads_snapshot_and_health():
    result = SimpleNamespace(
        snapshot=SimpleNamespace(scene_path=r"C:\shots\hero.ma"),
        scan_scope="selection",
        profile_id="lookdev",
        asset_class_id="character",
        health_score=HealthScore(
            score=61,
            raw_score=61,
            critical=1,
            error=2,
            warning=4,
            info=1,
            block_publish=True,
            block_deadline=True,
        ),
    )

    context = validation_notification_context_from_run(result)

    assert context.scene_name == "hero.ma"
    assert context.scan_scope == "selection"
    assert context.profile_id == "lookdev"
    assert context.asset_class_id == "character"
    assert context.health_score == 61
    assert context.critical_count == 1
    assert context.error_count == 2
    assert context.warning_count == 4
    assert context.info_count == 1
    assert context.block_publish is True
    assert context.block_deadline is True


def test_should_send_discord_notification_requires_enabled_connector_and_matching_event():
    settings = _discord_settings()

    assert should_send_discord_notification(
        settings,
        block_publish=True,
        block_deadline=False,
    )
    assert not should_send_discord_notification(
        _discord_settings(enabled=False),
        block_publish=True,
        block_deadline=False,
    )
    assert not should_send_discord_notification(
        settings,
        block_publish=False,
        block_deadline=False,
    )
    assert not should_send_discord_notification(
        _discord_settings(notify_on=("block_deadline",)),
        block_publish=True,
        block_deadline=False,
    )


def test_matched_notify_events_returns_only_configured_active_blocks():
    settings = _discord_settings(notify_on=("block_publish", "block_deadline"))

    assert matched_notify_events(
        settings,
        block_publish=True,
        block_deadline=True,
    ) == ("block_publish", "block_deadline")
    assert matched_notify_events(
        settings,
        block_publish=False,
        block_deadline=True,
    ) == ("block_deadline",)


def test_send_discord_validation_notification_skips_when_connector_disabled():
    result = send_discord_validation_notification(
        _studio_config(_discord_settings(enabled=False)),
        _context(),
    )

    assert result.sent is False
    assert result.skipped_reason == "disabled"


def test_send_discord_validation_notification_skips_without_matching_block_events():
    result = send_discord_validation_notification(
        _studio_config(_discord_settings()),
        _context(block_publish=False, block_deadline=False),
    )

    assert result.sent is False
    assert result.skipped_reason == "no_matching_events"


def test_send_discord_validation_notification_posts_embed_on_publish_block():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> DiscordResponse:
        captured.append(request)
        _ = timeout
        return DiscordResponse(status_code=204, body="", json_data=None)

    def client_factory(config: DiscordConfig) -> DiscordClient:
        return DiscordClient(config, transport=transport)

    result = send_discord_validation_notification(
        _studio_config(_discord_settings()),
        _context(),
        client_factory=client_factory,
    )

    assert result.sent is True
    assert len(captured) == 1
    assert captured[0].method == "POST"
    assert captured[0].body is not None
    payload = json.loads(captured[0].body.decode("utf-8"))
    assert payload["embeds"][0]["title"] == "🔍 Health Validation · Publish block"
    assert "hero.ma" in payload["embeds"][0]["description"]


def test_maybe_send_discord_validation_notification_accepts_validation_run_result():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> DiscordResponse:
        captured.append(request)
        _ = timeout
        return DiscordResponse(status_code=204, body="", json_data=None)

    def client_factory(config: DiscordConfig) -> DiscordClient:
        return DiscordClient(config, transport=transport)

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

    result = maybe_send_discord_validation_notification(
        _studio_config(_discord_settings()),
        run_result,
        client_factory=client_factory,
    )

    assert result.sent is True
    assert len(captured) == 1
