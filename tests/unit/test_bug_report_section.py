from __future__ import annotations

from tests.unit.test_telegram_connector_section import (
    FakeLineEdit,
    FakeQtWidgets,
    _find,
)

from pipeline_inspector.core.manifest_gate import ManifestGatePolicy  # noqa: F401
from pipeline_inspector.integrations.bug_report.config import BUG_REPORT_MAX_REPORTS_PER_DAY
from pipeline_inspector.studio_config import BugReportSettings, StudioConfig
from pipeline_inspector.ui.bug_report_section import (
    BUG_REPORT_PRIVACY_NOTICE,
    SETTINGS_BUG_REPORT_API_KEY_INPUT_OBJECT_NAME,
    SETTINGS_BUG_REPORT_DETAILS_OBJECT_NAME,
    SETTINGS_BUG_REPORT_ENABLED_TOGGLE_OBJECT_NAME,
    SETTINGS_BUG_REPORT_PRIVACY_NOTICE_OBJECT_NAME,
    SETTINGS_BUG_REPORT_RELAY_URL_INPUT_OBJECT_NAME,
    SETTINGS_BUG_REPORT_SECTION_OBJECT_NAME,
    build_bug_report_section,
    read_bug_report_from_view,
    update_bug_report_view,
)


def test_build_bug_report_section_exposes_toggle_and_collapsed_details():
    section = build_bug_report_section(
        FakeQtWidgets,
        StudioConfig(bug_report=BugReportSettings(enabled=False)),
    )

    assert section.object_name == SETTINGS_BUG_REPORT_SECTION_OBJECT_NAME
    toggle = _find(section, SETTINGS_BUG_REPORT_ENABLED_TOGGLE_OBJECT_NAME)
    details = _find(section, SETTINGS_BUG_REPORT_DETAILS_OBJECT_NAME)
    assert toggle.checked is False
    assert details.visible is False


def test_build_bug_report_section_shows_relay_fields_and_privacy_notice():
    section = build_bug_report_section(
        FakeQtWidgets,
        StudioConfig(
            bug_report=BugReportSettings(
                enabled=True,
                relay_url="https://pipeline.studio.internal/shader-health/bug-report",
                api_key="studio-secret",
            )
        ),
    )

    details = _find(section, SETTINGS_BUG_REPORT_DETAILS_OBJECT_NAME)
    relay_url = _find(section, SETTINGS_BUG_REPORT_RELAY_URL_INPUT_OBJECT_NAME)
    api_key = _find(section, SETTINGS_BUG_REPORT_API_KEY_INPUT_OBJECT_NAME)
    privacy_notice = _find(section, SETTINGS_BUG_REPORT_PRIVACY_NOTICE_OBJECT_NAME)

    assert details.visible is True
    assert relay_url.value.endswith("/bug-report")
    assert api_key.value == "studio-secret"
    assert api_key.echo_mode == FakeLineEdit.Password
    assert str(BUG_REPORT_MAX_REPORTS_PER_DAY) in privacy_notice.text
    assert BUG_REPORT_PRIVACY_NOTICE in privacy_notice.text


def test_read_bug_report_from_view_round_trips_settings():
    section = build_bug_report_section(
        FakeQtWidgets,
        StudioConfig(bug_report=BugReportSettings(enabled=True)),
    )
    toggle = _find(section, SETTINGS_BUG_REPORT_ENABLED_TOGGLE_OBJECT_NAME)
    relay_url = _find(section, SETTINGS_BUG_REPORT_RELAY_URL_INPUT_OBJECT_NAME)
    api_key = _find(section, SETTINGS_BUG_REPORT_API_KEY_INPUT_OBJECT_NAME)

    toggle.setChecked(True)
    relay_url.setText("https://relay.studio/bug-report")
    api_key.setText("relay-key")

    loaded = read_bug_report_from_view(section, FakeQtWidgets, base=StudioConfig())

    assert loaded.bug_report == BugReportSettings(
        enabled=True,
        relay_url="https://relay.studio/bug-report",
        api_key="relay-key",
    )


def test_update_bug_report_view_refreshes_fields():
    section = build_bug_report_section(
        FakeQtWidgets,
        StudioConfig(bug_report=BugReportSettings(enabled=False)),
    )

    update_bug_report_view(
        section,
        FakeQtWidgets,
        BugReportSettings(
            enabled=True,
            relay_url="https://relay.studio/bug-report",
            api_key="updated-key",
        ),
    )

    toggle = _find(section, SETTINGS_BUG_REPORT_ENABLED_TOGGLE_OBJECT_NAME)
    details = _find(section, SETTINGS_BUG_REPORT_DETAILS_OBJECT_NAME)
    relay_url = _find(section, SETTINGS_BUG_REPORT_RELAY_URL_INPUT_OBJECT_NAME)
    api_key = _find(section, SETTINGS_BUG_REPORT_API_KEY_INPUT_OBJECT_NAME)

    assert toggle.checked is True
    assert details.visible is True
    assert relay_url.value == "https://relay.studio/bug-report"
    assert api_key.value == "updated-key"
