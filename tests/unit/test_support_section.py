from __future__ import annotations

from pipeline_inspector.studio_config import (
    ReadinessCheckRequirements,
    ReadinessSettings,
    ReadinessSupportContacts,
    SoftwareVersionRequirement,
    StudioConfig,
)
from pipeline_inspector.ui.support_section import (
    SETTINGS_READINESS_CHECKS_ROW_OBJECT_NAME,
    SETTINGS_READINESS_ENV_VARS_INPUT_OBJECT_NAME,
    SETTINGS_READINESS_PLUGINS_INPUT_OBJECT_NAME,
    SETTINGS_SUPPORT_CHAT_ID_INPUT_OBJECT_NAME,
    SETTINGS_SYSADMIN_CHAT_ID_INPUT_OBJECT_NAME,
    build_support_and_roles_section,
    parse_software_version_lines,
    read_readiness_from_view,
    update_support_and_roles_view,
)
from tests.unit.test_studio_policy_section import FakeQtWidgets, _find


def test_build_support_and_roles_section_exposes_contact_and_requirement_fields():
    section = build_support_and_roles_section(
        FakeQtWidgets,
        StudioConfig(
            readiness=ReadinessSettings(
                checks=ReadinessCheckRequirements(maya_plugins=("mtoa",)),
                support=ReadinessSupportContacts(
                    sysadmin_telegram_chat_id="-10011",
                    support_telegram_chat_id="-10022",
                ),
            )
        ),
    )

    assert _find(section, SETTINGS_SYSADMIN_CHAT_ID_INPUT_OBJECT_NAME).value == "-10011"
    assert _find(section, SETTINGS_SUPPORT_CHAT_ID_INPUT_OBJECT_NAME).value == "-10022"
    assert "mtoa" in _find(section, SETTINGS_READINESS_PLUGINS_INPUT_OBJECT_NAME).toPlainText()
    readiness_row = _find(section, SETTINGS_READINESS_CHECKS_ROW_OBJECT_NAME)
    assert len(readiness_row.layout.widgets) == 5


def test_read_readiness_from_view_round_trips_settings():
    base = StudioConfig()
    section = build_support_and_roles_section(FakeQtWidgets, base)
    _find(section, SETTINGS_SYSADMIN_CHAT_ID_INPUT_OBJECT_NAME).setText("-10055")
    _find(section, SETTINGS_SUPPORT_CHAT_ID_INPUT_OBJECT_NAME).setText("-10066")
    plugins = _find(section, SETTINGS_READINESS_PLUGINS_INPUT_OBJECT_NAME)
    plugins.setPlainText("vrayformaya\nmtoa")

    loaded = read_readiness_from_view(section, FakeQtWidgets, base=base.readiness)

    assert loaded.support.sysadmin_telegram_chat_id == "-10055"
    assert loaded.support.support_telegram_chat_id == "-10066"
    assert loaded.checks.maya_plugins == ("vrayformaya", "mtoa")


def test_parse_software_version_lines_reads_product_version_pairs():
    versions = parse_software_version_lines("maya=2024\nmaya=2025\nmtoa=5.4.0\ninvalid-line")

    assert versions == (
        SoftwareVersionRequirement("maya", "2024"),
        SoftwareVersionRequirement("maya", "2025"),
        SoftwareVersionRequirement("mtoa", "5.4.0"),
    )


def test_update_support_and_roles_view_refreshes_fields():
    section = build_support_and_roles_section(FakeQtWidgets, StudioConfig())
    update_support_and_roles_view(
        section,
        FakeQtWidgets,
        ReadinessSettings(
            checks=ReadinessCheckRequirements(env_vars=("PIPELINE_ROOT",)),
            support=ReadinessSupportContacts(support_telegram_chat_id="-10088"),
        ),
    )

    assert _find(section, SETTINGS_SUPPORT_CHAT_ID_INPUT_OBJECT_NAME).value == "-10088"
    assert "PIPELINE_ROOT" in _find(section, SETTINGS_READINESS_ENV_VARS_INPUT_OBJECT_NAME).toPlainText()
