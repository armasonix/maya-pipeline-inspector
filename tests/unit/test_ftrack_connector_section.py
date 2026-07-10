from __future__ import annotations

from tests.unit.test_telegram_connector_section import (
    FakeLineEdit,
    FakeQtWidgets,
    _find,
)

from shader_health.core.manifest_gate import ManifestGatePolicy  # noqa: F401
from shader_health.studio_config import (
    ConnectorSettings,
    FtrackConnectorSettings,
    StudioConfig,
)
from shader_health.ui.ftrack_connector_section import (
    SETTINGS_FTRACK_API_KEY_INPUT_OBJECT_NAME,
    SETTINGS_FTRACK_API_URL_INPUT_OBJECT_NAME,
    SETTINGS_FTRACK_DETAILS_OBJECT_NAME,
    SETTINGS_FTRACK_ENABLED_TOGGLE_OBJECT_NAME,
    SETTINGS_FTRACK_PROJECT_INPUT_OBJECT_NAME,
    SETTINGS_FTRACK_SECTION_OBJECT_NAME,
    build_ftrack_connector_section,
    read_ftrack_connector_from_view,
    update_ftrack_connector_view,
)


def test_build_ftrack_connector_section_exposes_toggle_and_collapsed_details():
    section = build_ftrack_connector_section(
        FakeQtWidgets,
        StudioConfig(
            connectors=ConnectorSettings(
                ftrack=FtrackConnectorSettings(enabled=False),
            )
        ),
    )

    assert section.object_name == SETTINGS_FTRACK_SECTION_OBJECT_NAME
    toggle = _find(section, SETTINGS_FTRACK_ENABLED_TOGGLE_OBJECT_NAME)
    details = _find(section, SETTINGS_FTRACK_DETAILS_OBJECT_NAME)
    assert toggle.checked is False
    assert details.visible is False


def test_build_ftrack_connector_section_masks_api_key_and_shows_fields():
    section = build_ftrack_connector_section(
        FakeQtWidgets,
        StudioConfig(
            connectors=ConnectorSettings(
                ftrack=FtrackConnectorSettings(
                    enabled=True,
                    api_url="https://studio.ftrackapp.com",
                    api_user="pipeline.bot",
                    api_key="secret",
                    project="Demo Project",
                )
            )
        ),
    )

    details = _find(section, SETTINGS_FTRACK_DETAILS_OBJECT_NAME)
    api_url = _find(section, SETTINGS_FTRACK_API_URL_INPUT_OBJECT_NAME)
    api_key = _find(section, SETTINGS_FTRACK_API_KEY_INPUT_OBJECT_NAME)
    project = _find(section, SETTINGS_FTRACK_PROJECT_INPUT_OBJECT_NAME)

    assert details.visible is True
    assert api_url.value == "https://studio.ftrackapp.com"
    assert api_key.value == "secret"
    assert api_key.echo_mode == FakeLineEdit.Password
    assert project.value == "Demo Project"


def test_read_ftrack_connector_from_view_round_trips_settings():
    section = build_ftrack_connector_section(
        FakeQtWidgets,
        StudioConfig(
            connectors=ConnectorSettings(
                ftrack=FtrackConnectorSettings(enabled=True),
            )
        ),
    )
    api_url = _find(section, SETTINGS_FTRACK_API_URL_INPUT_OBJECT_NAME)
    api_key = _find(section, SETTINGS_FTRACK_API_KEY_INPUT_OBJECT_NAME)
    project = _find(section, SETTINGS_FTRACK_PROJECT_INPUT_OBJECT_NAME)
    api_url.setText("https://studio.ftrackapp.com")
    api_key.setText("secret")
    project.setText("Demo Project")

    settings = read_ftrack_connector_from_view(section, FakeQtWidgets)

    assert settings.enabled is True
    assert settings.api_url == "https://studio.ftrackapp.com"
    assert settings.api_key == "secret"
    assert settings.project == "Demo Project"


def test_update_ftrack_connector_view_refreshes_controls():
    section = build_ftrack_connector_section(
        FakeQtWidgets,
        StudioConfig(
            connectors=ConnectorSettings(
                ftrack=FtrackConnectorSettings(enabled=False),
            )
        ),
    )

    update_ftrack_connector_view(
        section,
        FakeQtWidgets,
        FtrackConnectorSettings(
            enabled=True,
            api_url="https://studio.ftrackapp.com",
            api_user="pipeline.bot",
            api_key="rotated",
            project="Hero Project",
        ),
    )

    details = _find(section, SETTINGS_FTRACK_DETAILS_OBJECT_NAME)
    api_key = _find(section, SETTINGS_FTRACK_API_KEY_INPUT_OBJECT_NAME)
    project = _find(section, SETTINGS_FTRACK_PROJECT_INPUT_OBJECT_NAME)

    assert details.visible is True
    assert api_key.value == "rotated"
    assert project.value == "Hero Project"
