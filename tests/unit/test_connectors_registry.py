from __future__ import annotations

from tests.unit.test_settings_panel import FakeQtWidgets

from shader_health.connectors_registry import (
    CONNECTORS,
    get_connector,
    iter_connectors,
    read_connectors_from_settings_view,
    resolve_connector,
)
from shader_health.studio_config import (
    ConnectorSettings,
    DeadlineConnectorSettings,
    DiscordConnectorSettings,
    StudioConfig,
    TelegramConnectorSettings,
    resolve_discord_config,
    resolve_telegram_config,
)
from shader_health.ui import settings_panel


def test_iter_connectors_includes_deadline_telegram_and_discord():
    connectors = iter_connectors()

    assert len(connectors) == 3
    assert connectors[0].id == "deadline"
    assert connectors[0].display_name == "Thinkbox Deadline"
    assert connectors[0].settings_dataclass is DeadlineConnectorSettings
    assert connectors[1].id == "telegram"
    assert connectors[1].settings_dataclass is TelegramConnectorSettings
    assert "bot_token" in connectors[1].secret_field_names
    assert connectors[2].id == "discord"
    assert connectors[2].settings_dataclass is DiscordConnectorSettings
    assert "webhook_url" in connectors[2].secret_field_names


def test_get_connector_returns_none_for_unknown_id():
    assert get_connector("unknown") is None
    assert get_connector("telegram") is CONNECTORS[1]
    assert get_connector("discord") is CONNECTORS[2]
    assert get_connector("deadline") is CONNECTORS[0]


def test_read_connectors_preserves_extra_connectors_from_base():
    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        config=StudioConfig(
            connectors=ConnectorSettings(
                deadline=DeadlineConnectorSettings(enabled=True),
                extra={"slack": {"enabled": True, "webhook_url": "https://hooks.slack.com/example"}},
            )
        ),
    )
    base = ConnectorSettings(
        deadline=DeadlineConnectorSettings(enabled=False),
        extra={"slack": {"enabled": True, "webhook_url": "https://hooks.slack.com/example"}},
    )

    connectors = read_connectors_from_settings_view(view, FakeQtWidgets, base=base)

    assert connectors.deadline.enabled is True
    assert connectors.extra["slack"]["webhook_url"] == "https://hooks.slack.com/example"


def test_resolve_connector_delegates_to_telegram_resolver():
    config = StudioConfig(
        connectors=ConnectorSettings(
            telegram=TelegramConnectorSettings(
                enabled=True,
                bot_token="123:abc",
                chat_id="-10042",
            )
        )
    )

    resolved = resolve_connector(config, "telegram")

    assert resolved is not None
    assert resolved.bot_token == "123:abc"
    assert resolved.chat_id == "-10042"
    assert resolve_telegram_config(
        StudioConfig(
            connectors=ConnectorSettings(
                telegram=TelegramConnectorSettings(enabled=False, bot_token="123:abc", chat_id="1"),
            )
        )
    ) is None


def test_resolve_connector_delegates_to_deadline_resolver():
    config = StudioConfig(
        connectors=ConnectorSettings(
            deadline=DeadlineConnectorSettings(
                enabled=True,
                web_service_host="farm.local",
                web_service_port=8081,
            )
        )
    )

    resolved = resolve_connector(config, "deadline")

    assert resolved is not None
    assert resolved.api_url == "http://farm.local:8081"
    assert resolve_connector(config, "unknown") is None


def test_resolve_connector_delegates_to_discord_resolver():
    config = StudioConfig(
        connectors=ConnectorSettings(
            discord=DiscordConnectorSettings(
                enabled=True,
                webhook_url="https://discord.com/api/webhooks/1/secret",
            )
        )
    )

    resolved = resolve_connector(config, "discord")

    assert resolved is not None
    assert resolved.webhook_url == "https://discord.com/api/webhooks/1/secret"
    assert resolve_discord_config(
        StudioConfig(
            connectors=ConnectorSettings(
                discord=DiscordConnectorSettings(
                    enabled=False,
                    webhook_url="https://discord.com/api/webhooks/1/secret",
                ),
            )
        )
    ) is None
