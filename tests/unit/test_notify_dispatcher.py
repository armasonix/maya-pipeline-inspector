from __future__ import annotations

from types import SimpleNamespace

from pipeline_inspector.core.manifest_gate import ManifestGatePolicy  # noqa: F401
from pipeline_inspector.core.scoring import HealthScore
from pipeline_inspector.integrations.notify.dispatcher import (
    NOTIFICATION_CONNECTOR_IDS,
    ConnectorNotificationOutcome,
    ValidationNotificationDispatchResult,
    dispatch_validation_notifications,
    report_validation_notification_outcomes,
)
from pipeline_inspector.studio_config import (
    ConnectorSettings,
    DiscordConnectorSettings,
    SlackConnectorSettings,
    StudioConfig,
    TelegramConnectorSettings,
)


def _run_result(**overrides: object) -> SimpleNamespace:
    defaults = {
        "snapshot": SimpleNamespace(scene_path="/tmp/hero.ma"),
        "scan_scope": "scene",
        "profile_id": "publish_strict",
        "asset_class_id": "",
        "health_score": HealthScore(
            score=40,
            raw_score=40,
            critical=1,
            block_publish=True,
        ),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_notification_connector_ids_include_all_connectors():
    assert NOTIFICATION_CONNECTOR_IDS == ("telegram", "discord", "slack")


def test_dispatch_validation_notifications_fans_out_to_all_connectors(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(
        "pipeline_inspector.integrations.notify.dispatcher.maybe_send_telegram_validation_notification",
        lambda *_args, **_kwargs: (
            calls.append("telegram"),
            __import__(
                "pipeline_inspector.integrations.telegram.notify",
                fromlist=["TelegramNotificationResult"],
            ).TelegramNotificationResult(sent=True),
        )[1],
    )
    monkeypatch.setattr(
        "pipeline_inspector.integrations.notify.dispatcher.maybe_send_discord_validation_notification",
        lambda *_args, **_kwargs: (
            calls.append("discord"),
            __import__(
                "pipeline_inspector.integrations.discord.notify",
                fromlist=["DiscordNotificationResult"],
            ).DiscordNotificationResult(sent=False, skipped_reason="disabled"),
        )[1],
    )
    monkeypatch.setattr(
        "pipeline_inspector.integrations.notify.dispatcher.maybe_send_slack_validation_notification",
        lambda *_args, **_kwargs: (
            calls.append("slack"),
            __import__(
                "pipeline_inspector.integrations.slack.notify",
                fromlist=["SlackNotificationResult"],
            ).SlackNotificationResult(sent=True, routes_sent=1),
        )[1],
    )

    result = dispatch_validation_notifications(StudioConfig(), _run_result())

    assert calls == ["telegram", "discord", "slack"]
    assert len(result.outcomes) == 3
    assert result.outcomes[0].connector_id == "telegram"
    assert result.outcomes[0].sent is True
    assert result.outcomes[1].connector_id == "discord"
    assert result.outcomes[1].skipped_reason == "disabled"
    assert result.outcomes[2].connector_id == "slack"
    assert result.outcomes[2].sent is True


def test_report_validation_notification_outcomes_prints_sent_and_failed_messages():
    messages: list[str] = []
    dispatch_result = ValidationNotificationDispatchResult(
        outcomes=(
            ConnectorNotificationOutcome("telegram", sent=True),
            ConnectorNotificationOutcome(
                "discord",
                sent=False,
                error_message="HTTP 500",
            ),
            ConnectorNotificationOutcome(
                "slack",
                sent=False,
                skipped_reason="disabled",
            ),
        )
    )

    report_validation_notification_outcomes(
        dispatch_result,
        print_fn=messages.append,
    )

    assert messages == [
        "Telegram notification sent.",
        "Discord notification failed: HTTP 500",
        "Slack notification skipped: disabled",
    ]


def test_dispatch_validation_notifications_passes_studio_config_to_connectors(monkeypatch):
    captured_configs: list[StudioConfig | None] = []

    def _capture_config(studio_config: StudioConfig | None, *_args, **_kwargs):
        captured_configs.append(studio_config)
        from pipeline_inspector.integrations.telegram.notify import TelegramNotificationResult

        return TelegramNotificationResult(sent=False, skipped_reason="disabled")

    monkeypatch.setattr(
        "pipeline_inspector.integrations.notify.dispatcher.maybe_send_telegram_validation_notification",
        _capture_config,
    )
    monkeypatch.setattr(
        "pipeline_inspector.integrations.notify.dispatcher.maybe_send_discord_validation_notification",
        _capture_config,
    )
    monkeypatch.setattr(
        "pipeline_inspector.integrations.notify.dispatcher.maybe_send_slack_validation_notification",
        _capture_config,
    )

    studio_config = StudioConfig(
        connectors=ConnectorSettings(
            telegram=TelegramConnectorSettings(enabled=True),
            discord=DiscordConnectorSettings(enabled=True),
            slack=SlackConnectorSettings(enabled=True),
        )
    )
    dispatch_validation_notifications(studio_config, _run_result())

    assert captured_configs == [studio_config, studio_config, studio_config]
