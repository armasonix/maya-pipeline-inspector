from __future__ import annotations

from tests.unit.test_telegram_connector_section import (
    FakeLineEdit,
    FakeQtWidgets,
    _find,
)

from shader_health.core.manifest_gate import ManifestGatePolicy  # noqa: F401
from shader_health.studio_config import (
    CerebroConnectorSettings,
    ConnectorSettings,
    StudioConfig,
)
from shader_health.ui.cerebro_connector_section import (
    SETTINGS_CEREBRO_API_PASSWORD_INPUT_OBJECT_NAME,
    SETTINGS_CEREBRO_API_USER_INPUT_OBJECT_NAME,
    SETTINGS_CEREBRO_DETAILS_OBJECT_NAME,
    SETTINGS_CEREBRO_ENABLED_TOGGLE_OBJECT_NAME,
    SETTINGS_CEREBRO_PROJECT_INPUT_OBJECT_NAME,
    SETTINGS_CEREBRO_SECTION_OBJECT_NAME,
    SETTINGS_CEREBRO_SERVER_URL_INPUT_OBJECT_NAME,
    build_cerebro_connector_section,
    read_cerebro_connector_from_view,
    update_cerebro_connector_view,
)


def test_build_cerebro_connector_section_exposes_toggle_and_collapsed_details():
    section = build_cerebro_connector_section(
        FakeQtWidgets,
        StudioConfig(
            connectors=ConnectorSettings(
                cerebro=CerebroConnectorSettings(enabled=False),
            )
        ),
    )

    assert section.object_name == SETTINGS_CEREBRO_SECTION_OBJECT_NAME
    hint = next(
        child
        for child in section.children
        if getattr(child, "text", "").startswith("When enabled, Shader Health")
    )
    assert "Connection is tested when you save or edit Cerebro settings." in hint.text
    assert len(hint.text) < 320
    toggle = _find(section, SETTINGS_CEREBRO_ENABLED_TOGGLE_OBJECT_NAME)
    details = _find(section, SETTINGS_CEREBRO_DETAILS_OBJECT_NAME)
    assert toggle.checked is False
    assert details.visible is False


def test_build_cerebro_connector_section_masks_password_and_shows_fields():
    section = build_cerebro_connector_section(
        FakeQtWidgets,
        StudioConfig(
            connectors=ConnectorSettings(
                cerebro=CerebroConnectorSettings(
                    enabled=True,
                    server_url="cerebrohq.com:45432",
                    api_user="pipeline.bot",
                    api_password="secret",
                    project="Demo Project",
                )
            )
        ),
    )

    details = _find(section, SETTINGS_CEREBRO_DETAILS_OBJECT_NAME)
    server_url = _find(section, SETTINGS_CEREBRO_SERVER_URL_INPUT_OBJECT_NAME)
    password = _find(section, SETTINGS_CEREBRO_API_PASSWORD_INPUT_OBJECT_NAME)
    project = _find(section, SETTINGS_CEREBRO_PROJECT_INPUT_OBJECT_NAME)

    assert details.visible is True
    assert server_url.value == "cerebrohq.com:45432"
    assert password.value == "secret"
    assert password.echo_mode == FakeLineEdit.Password
    assert project.value == "Demo Project"


def test_read_cerebro_connector_from_view_round_trips_settings():
    section = build_cerebro_connector_section(
        FakeQtWidgets,
        StudioConfig(
            connectors=ConnectorSettings(
                cerebro=CerebroConnectorSettings(enabled=True),
            )
        ),
    )
    server_url = _find(section, SETTINGS_CEREBRO_SERVER_URL_INPUT_OBJECT_NAME)
    api_user = _find(section, SETTINGS_CEREBRO_API_USER_INPUT_OBJECT_NAME)
    password = _find(section, SETTINGS_CEREBRO_API_PASSWORD_INPUT_OBJECT_NAME)
    project = _find(section, SETTINGS_CEREBRO_PROJECT_INPUT_OBJECT_NAME)
    server_url.setText("cerebrohq.com:45432")
    api_user.setText("pipeline.bot")
    password.setText("secret")
    project.setText("Demo Project")

    settings = read_cerebro_connector_from_view(section, FakeQtWidgets)

    assert settings.enabled is True
    assert settings.server_url == "cerebrohq.com:45432"
    assert settings.api_user == "pipeline.bot"
    assert settings.api_password == "secret"
    assert settings.project == "Demo Project"


def test_update_cerebro_connector_view_refreshes_controls():
    section = build_cerebro_connector_section(
        FakeQtWidgets,
        StudioConfig(
            connectors=ConnectorSettings(
                cerebro=CerebroConnectorSettings(enabled=False),
            )
        ),
    )

    update_cerebro_connector_view(
        section,
        FakeQtWidgets,
        CerebroConnectorSettings(
            enabled=True,
            server_url="cerebrohq.com:45432",
            api_user="pipeline.bot",
            api_password="rotated",
            project="Hero Project",
        ),
    )

    details = _find(section, SETTINGS_CEREBRO_DETAILS_OBJECT_NAME)
    password = _find(section, SETTINGS_CEREBRO_API_PASSWORD_INPUT_OBJECT_NAME)
    project = _find(section, SETTINGS_CEREBRO_PROJECT_INPUT_OBJECT_NAME)

    assert details.visible is True
    assert password.value == "rotated"
    assert project.value == "Hero Project"
