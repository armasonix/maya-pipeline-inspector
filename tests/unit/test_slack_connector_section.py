from __future__ import annotations

from tests.unit.test_telegram_connector_section import (
    FakeLineEdit,
    FakeQtWidgets,
    _find,
)

from shader_health.core.manifest_gate import ManifestGatePolicy  # noqa: F401
from shader_health.studio_config import (
    ConnectorSettings,
    SlackConnectorSettings,
    StudioConfig,
)
from shader_health.ui.slack_connector_section import (
    SETTINGS_SLACK_DEADLINE_WEBHOOK_INPUT_OBJECT_NAME,
    SETTINGS_SLACK_DETAILS_OBJECT_NAME,
    SETTINGS_SLACK_ENABLED_TOGGLE_OBJECT_NAME,
    SETTINGS_SLACK_INCLUDE_REPORT_LINK_CHECKBOX_OBJECT_NAME,
    SETTINGS_SLACK_NOTIFY_BLOCK_DEADLINE_CHECKBOX_OBJECT_NAME,
    SETTINGS_SLACK_NOTIFY_BLOCK_PUBLISH_CHECKBOX_OBJECT_NAME,
    SETTINGS_SLACK_PUBLISH_WEBHOOK_INPUT_OBJECT_NAME,
    SETTINGS_SLACK_SECTION_OBJECT_NAME,
    build_slack_connector_section,
    read_slack_connector_from_view,
    update_slack_connector_view,
)


def test_build_slack_connector_section_exposes_toggle_and_collapsed_details():
    section = build_slack_connector_section(
        FakeQtWidgets,
        StudioConfig(
            connectors=ConnectorSettings(
                slack=SlackConnectorSettings(enabled=False),
            )
        ),
    )

    assert section.object_name == SETTINGS_SLACK_SECTION_OBJECT_NAME
    toggle = _find(section, SETTINGS_SLACK_ENABLED_TOGGLE_OBJECT_NAME)
    details = _find(section, SETTINGS_SLACK_DETAILS_OBJECT_NAME)
    assert toggle.checked is False
    assert details.visible is False


def test_build_slack_connector_section_masks_webhooks_and_shows_routing_fields():
    section = build_slack_connector_section(
        FakeQtWidgets,
        StudioConfig(
            connectors=ConnectorSettings(
                slack=SlackConnectorSettings(
                    enabled=True,
                    publish_webhook_url="https://hooks.slack.com/publish",
                    deadline_webhook_url="https://hooks.slack.com/deadline",
                    notify_on=("block_publish",),
                    include_report_link=True,
                )
            )
        ),
    )

    details = _find(section, SETTINGS_SLACK_DETAILS_OBJECT_NAME)
    publish = _find(section, SETTINGS_SLACK_PUBLISH_WEBHOOK_INPUT_OBJECT_NAME)
    deadline = _find(section, SETTINGS_SLACK_DEADLINE_WEBHOOK_INPUT_OBJECT_NAME)
    publish_notify = _find(section, SETTINGS_SLACK_NOTIFY_BLOCK_PUBLISH_CHECKBOX_OBJECT_NAME)
    report_link = _find(section, SETTINGS_SLACK_INCLUDE_REPORT_LINK_CHECKBOX_OBJECT_NAME)

    assert details.visible is True
    assert publish.value == "https://hooks.slack.com/publish"
    assert publish.echo_mode == FakeLineEdit.Password
    assert deadline.value == "https://hooks.slack.com/deadline"
    assert publish_notify.checked is True
    assert report_link.checked is True


def test_read_slack_connector_from_view_round_trips_settings():
    section = build_slack_connector_section(
        FakeQtWidgets,
        StudioConfig(
            connectors=ConnectorSettings(
                slack=SlackConnectorSettings(enabled=True),
            )
        ),
    )
    toggle = _find(section, SETTINGS_SLACK_ENABLED_TOGGLE_OBJECT_NAME)
    publish = _find(section, SETTINGS_SLACK_PUBLISH_WEBHOOK_INPUT_OBJECT_NAME)
    deadline = _find(section, SETTINGS_SLACK_DEADLINE_WEBHOOK_INPUT_OBJECT_NAME)
    publish_notify = _find(section, SETTINGS_SLACK_NOTIFY_BLOCK_PUBLISH_CHECKBOX_OBJECT_NAME)
    deadline_notify = _find(section, SETTINGS_SLACK_NOTIFY_BLOCK_DEADLINE_CHECKBOX_OBJECT_NAME)
    report_link = _find(section, SETTINGS_SLACK_INCLUDE_REPORT_LINK_CHECKBOX_OBJECT_NAME)

    toggle.setChecked(True)
    publish.setText("https://hooks.slack.com/publish")
    deadline.setText("https://hooks.slack.com/deadline")
    publish_notify.setChecked(True)
    deadline_notify.setChecked(True)
    report_link.setChecked(False)

    loaded = read_slack_connector_from_view(section, FakeQtWidgets)

    assert loaded == SlackConnectorSettings(
        enabled=True,
        publish_webhook_url="https://hooks.slack.com/publish",
        deadline_webhook_url="https://hooks.slack.com/deadline",
        notify_on=("block_publish", "block_deadline"),
        include_report_link=False,
    )


def test_update_slack_connector_view_refreshes_fields():
    section = build_slack_connector_section(
        FakeQtWidgets,
        StudioConfig(
            connectors=ConnectorSettings(
                slack=SlackConnectorSettings(enabled=False),
            )
        ),
    )

    update_slack_connector_view(
        section,
        FakeQtWidgets,
        SlackConnectorSettings(
            enabled=True,
            publish_webhook_url="https://hooks.slack.com/new-publish",
            deadline_webhook_url="https://hooks.slack.com/new-deadline",
            notify_on=("block_deadline",),
            include_report_link=True,
        ),
    )

    details = _find(section, SETTINGS_SLACK_DETAILS_OBJECT_NAME)
    publish = _find(section, SETTINGS_SLACK_PUBLISH_WEBHOOK_INPUT_OBJECT_NAME)
    deadline = _find(section, SETTINGS_SLACK_DEADLINE_WEBHOOK_INPUT_OBJECT_NAME)
    publish_notify = _find(section, SETTINGS_SLACK_NOTIFY_BLOCK_PUBLISH_CHECKBOX_OBJECT_NAME)
    deadline_notify = _find(section, SETTINGS_SLACK_NOTIFY_BLOCK_DEADLINE_CHECKBOX_OBJECT_NAME)
    report_link = _find(section, SETTINGS_SLACK_INCLUDE_REPORT_LINK_CHECKBOX_OBJECT_NAME)

    assert details.visible is True
    assert publish.value == "https://hooks.slack.com/new-publish"
    assert deadline.value == "https://hooks.slack.com/new-deadline"
    assert publish_notify.checked is False
    assert deadline_notify.checked is True
    assert report_link.checked is True
