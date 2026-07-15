from __future__ import annotations

import json
from types import SimpleNamespace

from pipeline_inspector.core.manifest_gate import ManifestGatePolicy  # noqa: F401
from pipeline_inspector.core.scoring import HealthScore
from pipeline_inspector.integrations.telegram import (
    TelegramClient,
    TelegramConfig,
    TelegramResponse,
)
from pipeline_inspector.integrations.telegram.client import HttpRequest
from pipeline_inspector.integrations.telegram.notify import (
    format_validation_summary_message,
    matched_notify_events,
    maybe_send_telegram_validation_notification,
    send_telegram_validation_notification,
    should_send_telegram_notification,
    validation_notification_context_from_run,
)
from pipeline_inspector.studio_config import (
    ConnectorSettings,
    StudioConfig,
    TelegramConnectorSettings,
)


def _context(**overrides: object):
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
    from pipeline_inspector.integrations.telegram.notify import ValidationNotificationContext

    return ValidationNotificationContext(**defaults)


def _telegram_settings(**overrides: object) -> TelegramConnectorSettings:
    defaults = {
        "enabled": True,
        "bot_token": "123:abc",
        "chat_id": "-10042",
        "notify_on": ("block_publish",),
    }
    defaults.update(overrides)
    return TelegramConnectorSettings(**defaults)


def _studio_config(telegram: TelegramConnectorSettings) -> StudioConfig:
    return StudioConfig(connectors=ConnectorSettings(telegram=telegram))


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


def test_should_send_telegram_notification_requires_enabled_connector_and_matching_event():
    settings = _telegram_settings()

    assert should_send_telegram_notification(
        settings,
        block_publish=True,
        block_deadline=False,
    )
    assert not should_send_telegram_notification(
        _telegram_settings(enabled=False),
        block_publish=True,
        block_deadline=False,
    )
    assert not should_send_telegram_notification(
        settings,
        block_publish=False,
        block_deadline=False,
    )
    assert not should_send_telegram_notification(
        _telegram_settings(notify_on=("block_deadline",)),
        block_publish=True,
        block_deadline=False,
    )


def test_matched_notify_events_returns_on_pass_when_no_blocks_or_critical():
    settings = _telegram_settings(notify_on=("on_pass", "block_publish"))

    assert matched_notify_events(
        settings,
        block_publish=False,
        block_deadline=False,
        critical_count=0,
        health_score=90,
    ) == ("on_pass",)


def test_matched_notify_events_returns_score_below_when_threshold_configured():
    settings = _telegram_settings(notify_on=("score_below",), notify_score_below=70)

    assert matched_notify_events(
        settings,
        block_publish=False,
        block_deadline=False,
        critical_count=0,
        health_score=55,
    ) == ("score_below",)


def test_send_telegram_validation_notification_posts_to_notify_targets(monkeypatch):
    captured_chat_ids: list[str] = []

    class _Client:
        def __init__(self, config: TelegramConfig) -> None:
            captured_chat_ids.append(config.chat_id)

        def send_message(self, _message: str) -> TelegramResponse:
            return TelegramResponse(
                status_code=200,
                body='{"ok": true}',
                json_data={"ok": True},
            )

    settings = _telegram_settings(
        notify_on=("block_publish",),
        notify_targets=(
            __import__(
                "pipeline_inspector.studio_config",
                fromlist=["NotifyTarget"],
            ).NotifyTarget(
                chat_id="-10099",
                events=("on_critical",),
            ),
        ),
    )
    result = send_telegram_validation_notification(
        _studio_config(settings),
        _context(block_publish=False, block_deadline=False, critical_count=3),
        client_factory=lambda _config: _Client(_config),
    )

    assert result.sent is True
    assert captured_chat_ids == ["-10099"]


def test_matched_notify_events_returns_only_configured_active_blocks():
    settings = _telegram_settings(notify_on=("block_publish", "block_deadline"))

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


def test_format_validation_summary_message_includes_profile_overlay_and_counts():
    message = format_validation_summary_message(
        _context(asset_class_id="character"),
        matched_events=("block_publish",),
    )

    assert "Health Validation · Publish block" in message
    assert "📁 Scene: hero.ma" in message
    assert "🎬 Profile: publish_strict+character" in message
    assert "🎯 Scope: Scene" in message
    assert "Health score: 42/100" in message
    assert "🚨 2 critical" in message
    assert "❌ 1 error" in message


def test_send_telegram_validation_notification_skips_when_connector_disabled():
    result = send_telegram_validation_notification(
        _studio_config(_telegram_settings(enabled=False)),
        _context(),
    )

    assert result.sent is False
    assert result.skipped_reason == "disabled"


def test_send_telegram_validation_notification_skips_without_matching_block_events():
    result = send_telegram_validation_notification(
        _studio_config(_telegram_settings()),
        _context(block_publish=False, block_deadline=False),
    )

    assert result.sent is False
    assert result.skipped_reason == "no_matching_events"


def test_send_telegram_validation_notification_posts_summary_on_publish_block():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> TelegramResponse:
        captured.append(request)
        _ = timeout
        return TelegramResponse(
            status_code=200,
            body='{"ok": true, "result": {"message_id": 7}}',
            json_data={"ok": True, "result": {"message_id": 7}},
        )

    def client_factory(config: TelegramConfig) -> TelegramClient:
        return TelegramClient(config, transport=transport)

    result = send_telegram_validation_notification(
        _studio_config(_telegram_settings()),
        _context(),
        client_factory=client_factory,
    )

    assert result.sent is True
    assert len(captured) == 1
    assert captured[0].method == "POST"
    assert captured[0].body is not None
    payload = json.loads(captured[0].body.decode("utf-8"))
    assert "Health Validation · Publish block" in payload["text"]
    assert "hero.ma" in payload["text"]


def test_maybe_send_telegram_validation_notification_accepts_validation_run_result():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> TelegramResponse:
        captured.append(request)
        _ = timeout
        return TelegramResponse(
            status_code=200,
            body='{"ok": true}',
            json_data={"ok": True},
        )

    def client_factory(config: TelegramConfig) -> TelegramClient:
        return TelegramClient(config, transport=transport)

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

    result = maybe_send_telegram_validation_notification(
        _studio_config(_telegram_settings()),
        run_result,
        client_factory=client_factory,
    )

    assert result.sent is True
    assert len(captured) == 1
