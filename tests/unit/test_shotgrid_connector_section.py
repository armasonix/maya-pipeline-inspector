from __future__ import annotations

from tests.unit.test_telegram_connector_section import (
    FakeLineEdit,
    FakeQtWidgets,
    _find,
)

from pipeline_inspector.core.manifest_gate import ManifestGatePolicy  # noqa: F401
from pipeline_inspector.studio_config import (
    ConnectorSettings,
    ShotGridConnectorSettings,
    StudioConfig,
)
from pipeline_inspector.ui.shotgrid_connector_section import (
    SETTINGS_SHOTGRID_API_KEY_INPUT_OBJECT_NAME,
    SETTINGS_SHOTGRID_DETAILS_OBJECT_NAME,
    SETTINGS_SHOTGRID_ENABLED_TOGGLE_OBJECT_NAME,
    SETTINGS_SHOTGRID_ENTITY_TYPE_INPUT_OBJECT_NAME,
    SETTINGS_SHOTGRID_PROJECT_INPUT_OBJECT_NAME,
    SETTINGS_SHOTGRID_SCRIPT_NAME_INPUT_OBJECT_NAME,
    SETTINGS_SHOTGRID_SECTION_OBJECT_NAME,
    SETTINGS_SHOTGRID_SITE_URL_INPUT_OBJECT_NAME,
    build_shotgrid_connector_section,
    read_shotgrid_connector_from_view,
    update_shotgrid_connector_view,
)


def test_build_shotgrid_connector_section_exposes_toggle_and_collapsed_details():
    section = build_shotgrid_connector_section(
        FakeQtWidgets,
        StudioConfig(
            connectors=ConnectorSettings(
                shotgrid=ShotGridConnectorSettings(enabled=False),
            )
        ),
    )

    assert section.object_name == SETTINGS_SHOTGRID_SECTION_OBJECT_NAME
    toggle = _find(section, SETTINGS_SHOTGRID_ENABLED_TOGGLE_OBJECT_NAME)
    details = _find(section, SETTINGS_SHOTGRID_DETAILS_OBJECT_NAME)
    assert toggle.checked is False
    assert details.visible is False


def test_build_shotgrid_connector_section_masks_api_key_and_shows_fields():
    section = build_shotgrid_connector_section(
        FakeQtWidgets,
        StudioConfig(
            connectors=ConnectorSettings(
                shotgrid=ShotGridConnectorSettings(
                    enabled=True,
                    site_url="https://studio.shotgrid.autodesk.com",
                    script_name="pipeline_inspector",
                    api_key="secret",
                    project="Demo Project",
                    entity_type="Shot",
                )
            )
        ),
    )

    details = _find(section, SETTINGS_SHOTGRID_DETAILS_OBJECT_NAME)
    site_url = _find(section, SETTINGS_SHOTGRID_SITE_URL_INPUT_OBJECT_NAME)
    api_key = _find(section, SETTINGS_SHOTGRID_API_KEY_INPUT_OBJECT_NAME)
    project = _find(section, SETTINGS_SHOTGRID_PROJECT_INPUT_OBJECT_NAME)
    entity_type = _find(section, SETTINGS_SHOTGRID_ENTITY_TYPE_INPUT_OBJECT_NAME)

    assert details.visible is True
    assert site_url.value == "https://studio.shotgrid.autodesk.com"
    assert api_key.value == "secret"
    assert api_key.echo_mode == FakeLineEdit.Password
    assert project.value == "Demo Project"
    assert entity_type.value == "Shot"


def test_read_shotgrid_connector_from_view_round_trips_settings():
    section = build_shotgrid_connector_section(
        FakeQtWidgets,
        StudioConfig(
            connectors=ConnectorSettings(
                shotgrid=ShotGridConnectorSettings(enabled=True),
            )
        ),
    )
    site_url = _find(section, SETTINGS_SHOTGRID_SITE_URL_INPUT_OBJECT_NAME)
    script_name = _find(section, SETTINGS_SHOTGRID_SCRIPT_NAME_INPUT_OBJECT_NAME)
    api_key = _find(section, SETTINGS_SHOTGRID_API_KEY_INPUT_OBJECT_NAME)
    project = _find(section, SETTINGS_SHOTGRID_PROJECT_INPUT_OBJECT_NAME)
    entity_type = _find(section, SETTINGS_SHOTGRID_ENTITY_TYPE_INPUT_OBJECT_NAME)
    site_url.setText("https://studio.shotgrid.autodesk.com")
    script_name.setText("pipeline_inspector")
    api_key.setText("secret")
    project.setText("Demo Project")
    entity_type.setText("Asset")

    settings = read_shotgrid_connector_from_view(section, FakeQtWidgets)

    assert settings.enabled is True
    assert settings.site_url == "https://studio.shotgrid.autodesk.com"
    assert settings.script_name == "pipeline_inspector"
    assert settings.api_key == "secret"
    assert settings.project == "Demo Project"
    assert settings.entity_type == "Asset"


def test_update_shotgrid_connector_view_refreshes_controls():
    section = build_shotgrid_connector_section(
        FakeQtWidgets,
        StudioConfig(
            connectors=ConnectorSettings(
                shotgrid=ShotGridConnectorSettings(enabled=False),
            )
        ),
    )

    update_shotgrid_connector_view(
        section,
        FakeQtWidgets,
        ShotGridConnectorSettings(
            enabled=True,
            site_url="https://studio.shotgrid.autodesk.com",
            script_name="pipeline_inspector",
            api_key="rotated",
            project="Hero Project",
            entity_type="Asset",
        ),
    )

    details = _find(section, SETTINGS_SHOTGRID_DETAILS_OBJECT_NAME)
    api_key = _find(section, SETTINGS_SHOTGRID_API_KEY_INPUT_OBJECT_NAME)
    project = _find(section, SETTINGS_SHOTGRID_PROJECT_INPUT_OBJECT_NAME)
    entity_type = _find(section, SETTINGS_SHOTGRID_ENTITY_TYPE_INPUT_OBJECT_NAME)

    assert details.visible is True
    assert api_key.value == "rotated"
    assert project.value == "Hero Project"
    assert entity_type.value == "Asset"
