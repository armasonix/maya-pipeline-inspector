from __future__ import annotations

from tests.unit.test_telegram_connector_section import (
    FakeLineEdit,
    FakeQtWidgets,
    _find,
)

from pipeline_inspector.core.manifest_gate import ManifestGatePolicy  # noqa: F401
from pipeline_inspector.studio_config import (
    ConnectorSettings,
    DiscordConnectorSettings,
    StudioConfig,
)
from pipeline_inspector.ui.discord_connector_section import (
    SETTINGS_DISCORD_DETAILS_OBJECT_NAME,
    SETTINGS_DISCORD_ENABLED_TOGGLE_OBJECT_NAME,
    SETTINGS_DISCORD_NOTIFY_BLOCK_DEADLINE_CHECKBOX_OBJECT_NAME,
    SETTINGS_DISCORD_NOTIFY_BLOCK_PUBLISH_CHECKBOX_OBJECT_NAME,
    SETTINGS_DISCORD_SECTION_OBJECT_NAME,
    SETTINGS_DISCORD_WEBHOOK_URL_INPUT_OBJECT_NAME,
    build_discord_connector_section,
    read_discord_connector_from_view,
    update_discord_connector_view,
)


def test_build_discord_connector_section_exposes_toggle_and_collapsed_details():
    section = build_discord_connector_section(
        FakeQtWidgets,
        StudioConfig(
            connectors=ConnectorSettings(
                discord=DiscordConnectorSettings(enabled=False),
            )
        ),
    )

    assert section.object_name == SETTINGS_DISCORD_SECTION_OBJECT_NAME
    toggle = _find(section, SETTINGS_DISCORD_ENABLED_TOGGLE_OBJECT_NAME)
    details = _find(section, SETTINGS_DISCORD_DETAILS_OBJECT_NAME)
    assert toggle.checked is False
    assert details.visible is False


def test_build_discord_connector_section_masks_webhook_url_and_shows_notify_checkboxes():
    section = build_discord_connector_section(
        FakeQtWidgets,
        StudioConfig(
            connectors=ConnectorSettings(
                discord=DiscordConnectorSettings(
                    enabled=True,
                    webhook_url="https://discord.com/api/webhooks/1/secret",
                    notify_on=("block_publish",),
                )
            )
        ),
    )

    details = _find(section, SETTINGS_DISCORD_DETAILS_OBJECT_NAME)
    webhook = _find(section, SETTINGS_DISCORD_WEBHOOK_URL_INPUT_OBJECT_NAME)
    publish = _find(section, SETTINGS_DISCORD_NOTIFY_BLOCK_PUBLISH_CHECKBOX_OBJECT_NAME)
    deadline = _find(section, SETTINGS_DISCORD_NOTIFY_BLOCK_DEADLINE_CHECKBOX_OBJECT_NAME)

    assert details.visible is True
    assert webhook.value == "https://discord.com/api/webhooks/1/secret"
    assert webhook.echo_mode == FakeLineEdit.Password
    assert publish.checked is True
    assert deadline.checked is False


def test_read_discord_connector_from_view_round_trips_settings():
    section = build_discord_connector_section(
        FakeQtWidgets,
        StudioConfig(
            connectors=ConnectorSettings(
                discord=DiscordConnectorSettings(enabled=True),
            )
        ),
    )
    toggle = _find(section, SETTINGS_DISCORD_ENABLED_TOGGLE_OBJECT_NAME)
    webhook = _find(section, SETTINGS_DISCORD_WEBHOOK_URL_INPUT_OBJECT_NAME)
    publish = _find(section, SETTINGS_DISCORD_NOTIFY_BLOCK_PUBLISH_CHECKBOX_OBJECT_NAME)
    deadline = _find(section, SETTINGS_DISCORD_NOTIFY_BLOCK_DEADLINE_CHECKBOX_OBJECT_NAME)

    toggle.setChecked(True)
    webhook.setText("https://discord.com/api/webhooks/9/abc")
    publish.setChecked(True)
    deadline.setChecked(True)

    loaded = read_discord_connector_from_view(section, FakeQtWidgets)

    assert loaded == DiscordConnectorSettings(
        enabled=True,
        webhook_url="https://discord.com/api/webhooks/9/abc",
        notify_on=("block_publish", "block_deadline"),
    )


def test_update_discord_connector_view_refreshes_fields():
    section = build_discord_connector_section(
        FakeQtWidgets,
        StudioConfig(
            connectors=ConnectorSettings(
                discord=DiscordConnectorSettings(enabled=False),
            )
        ),
    )

    update_discord_connector_view(
        section,
        FakeQtWidgets,
        DiscordConnectorSettings(
            enabled=True,
            webhook_url="https://discord.com/api/webhooks/42/new",
            notify_on=("block_deadline",),
        ),
    )

    details = _find(section, SETTINGS_DISCORD_DETAILS_OBJECT_NAME)
    webhook = _find(section, SETTINGS_DISCORD_WEBHOOK_URL_INPUT_OBJECT_NAME)
    publish = _find(section, SETTINGS_DISCORD_NOTIFY_BLOCK_PUBLISH_CHECKBOX_OBJECT_NAME)
    deadline = _find(section, SETTINGS_DISCORD_NOTIFY_BLOCK_DEADLINE_CHECKBOX_OBJECT_NAME)

    assert details.visible is True
    assert webhook.value == "https://discord.com/api/webhooks/42/new"
    assert publish.checked is False
    assert deadline.checked is True
