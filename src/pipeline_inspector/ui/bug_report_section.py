"""Bug Report relay settings for the Settings Bug Report tab."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional

from pipeline_inspector.integrations.bug_report.config import (
    BUG_REPORT_MAX_REPORTS_PER_DAY,
    DEFAULT_PUBLIC_BUG_REPORT_RELAY_URL,
)
from pipeline_inspector.studio_config import BugReportSettings, StudioConfig
from pipeline_inspector.ui.settings_widgets import (
    apply_password_echo_mode,
    apply_toggle_style,
    build_settings_toggle,
    find_child,
    line_edit_text,
    set_line_edit_text,
    toggle_label,
    wire_line_edit_finished,
)

SETTINGS_BUG_REPORT_SECTION_OBJECT_NAME = "pipelineInspectorSettingsBugReportSection"
SETTINGS_BUG_REPORT_ENABLED_TOGGLE_OBJECT_NAME = (
    "pipelineInspectorSettingsBugReportEnabledToggle"
)
SETTINGS_BUG_REPORT_DETAILS_OBJECT_NAME = "pipelineInspectorSettingsBugReportDetails"
SETTINGS_BUG_REPORT_RELAY_URL_INPUT_OBJECT_NAME = (
    "pipelineInspectorSettingsBugReportRelayUrlInput"
)
SETTINGS_BUG_REPORT_API_KEY_INPUT_OBJECT_NAME = (
    "pipelineInspectorSettingsBugReportApiKeyInput"
)
SETTINGS_BUG_REPORT_PRIVACY_NOTICE_OBJECT_NAME = (
    "pipelineInspectorSettingsBugReportPrivacyNotice"
)

_BUG_REPORT_LABEL_WIDTH = 132
_BUG_REPORT_FIELD_WIDTH = 292

BUG_REPORT_PRIVACY_NOTICE = (
    "Artists report bugs in Pipeline Inspector itself — not general scene shading issues. "
    "Reports route through your studio HTTPS relay to plugin maintainers on GitHub. "
    "Submissions include validation summary, plugin version, and scene basename only. "
    f"Optional screenshots can be attached in the report form. "
    f"Daily limit: {BUG_REPORT_MAX_REPORTS_PER_DAY} reports per machine/user "
    "(enforced in plugin and relay). "
    "Full scene paths and environment dumps are not sent."
)

def build_bug_report_section(
    qt_widgets: Any,
    config: StudioConfig,
    *,
    on_enabled_changed: Optional[Callable[[bool], None]] = None,
    on_settings_changed: Optional[Callable[[], None]] = None,
) -> Any:
    """Build the Bug Report relay settings section."""

    section = qt_widgets.QWidget()
    section.setObjectName(SETTINGS_BUG_REPORT_SECTION_OBJECT_NAME)
    section_layout = qt_widgets.QVBoxLayout(section)
    section_layout.setContentsMargins(0, 0, 0, 0)
    section_layout.setSpacing(6)

    intro = qt_widgets.QLabel(
        "Enable artist reports when Pipeline Inspector itself misbehaves. "
        "By default submissions use the public maintainer relay; studios may override "
        "relay URL and API key in pipeline_inspector_studio.json."
    )
    intro.setWordWrap(True)
    section_layout.addWidget(intro)

    enabled_row = qt_widgets.QHBoxLayout()
    set_enabled_margins = getattr(enabled_row, "setContentsMargins", None)
    if set_enabled_margins is not None:
        set_enabled_margins(0, 0, 0, 0)
    set_enabled_spacing = getattr(enabled_row, "setSpacing", None)
    if set_enabled_spacing is not None:
        set_enabled_spacing(4)
    enabled_row.addWidget(qt_widgets.QLabel("Bug Report"))
    enabled_row.addWidget(
        build_settings_toggle(
            qt_widgets,
            object_name=SETTINGS_BUG_REPORT_ENABLED_TOGGLE_OBJECT_NAME,
            enabled=config.bug_report.enabled,
            on_changed=lambda enabled: _on_bug_report_enabled_changed(
                qt_widgets,
                section,
                enabled,
                on_enabled_changed,
                on_settings_changed,
            ),
        )
    )
    enabled_row.addStretch(1)
    section_layout.addLayout(enabled_row)

    details = qt_widgets.QWidget()
    details.setObjectName(SETTINGS_BUG_REPORT_DETAILS_OBJECT_NAME)
    details_layout = qt_widgets.QVBoxLayout(details)
    set_details_margins = getattr(details_layout, "setContentsMargins", None)
    if set_details_margins is not None:
        set_details_margins(0, 2, 0, 0)
    set_details_spacing = getattr(details_layout, "setSpacing", None)
    if set_details_spacing is not None:
        set_details_spacing(4)

    bug_report = config.bug_report
    details_layout.addWidget(
        _build_bug_report_field_row(
            qt_widgets,
            label="Relay URL",
            object_name=SETTINGS_BUG_REPORT_RELAY_URL_INPUT_OBJECT_NAME,
            value=bug_report.relay_url,
            placeholder=DEFAULT_PUBLIC_BUG_REPORT_RELAY_URL,
            on_changed=on_settings_changed,
        )
    )
    details_layout.addWidget(
        _build_bug_report_field_row(
            qt_widgets,
            label="API key",
            object_name=SETTINGS_BUG_REPORT_API_KEY_INPUT_OBJECT_NAME,
            value=bug_report.api_key,
            placeholder="optional for public relay",
            secret=True,
            on_changed=on_settings_changed,
        )
    )

    privacy_notice = qt_widgets.QLabel(BUG_REPORT_PRIVACY_NOTICE)
    privacy_notice.setObjectName(SETTINGS_BUG_REPORT_PRIVACY_NOTICE_OBJECT_NAME)
    privacy_notice.setWordWrap(True)
    details_layout.addWidget(privacy_notice)

    section_layout.addWidget(details)
    _set_bug_report_details_visible(details, config.bug_report.enabled)
    return section

def read_bug_report_from_view(
    view: Any,
    qt_widgets: Any,
    *,
    base: StudioConfig,
) -> StudioConfig:
    """Read bug report relay settings from the settings UI."""

    return base.with_updates(
        bug_report=BugReportSettings(
            enabled=_toggle_checked(
                view,
                qt_widgets,
                SETTINGS_BUG_REPORT_ENABLED_TOGGLE_OBJECT_NAME,
                base.bug_report.enabled,
            ),
            relay_url=line_edit_text(
                view,
                qt_widgets,
                SETTINGS_BUG_REPORT_RELAY_URL_INPUT_OBJECT_NAME,
            ),
            api_key=line_edit_text(
                view,
                qt_widgets,
                SETTINGS_BUG_REPORT_API_KEY_INPUT_OBJECT_NAME,
            ),
        )
    )

def update_bug_report_view(
    view: Any,
    qt_widgets: Any,
    bug_report: BugReportSettings,
) -> None:
    """Refresh bug report controls from studio config."""

    toggle = find_child(
        view,
        qt_widgets.QWidget,
        SETTINGS_BUG_REPORT_ENABLED_TOGGLE_OBJECT_NAME,
    )
    if toggle is not None:
        set_checked = getattr(toggle, "setChecked", None)
        if set_checked is not None:
            set_checked(bug_report.enabled)
        toggle.setText(toggle_label(bug_report.enabled))
        apply_toggle_style(toggle, bug_report.enabled)

    details = find_child(view, qt_widgets.QWidget, SETTINGS_BUG_REPORT_DETAILS_OBJECT_NAME)
    if details is not None:
        _set_bug_report_details_visible(details, bug_report.enabled)

    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_BUG_REPORT_RELAY_URL_INPUT_OBJECT_NAME,
        bug_report.relay_url,
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_BUG_REPORT_API_KEY_INPUT_OBJECT_NAME,
        bug_report.api_key,
    )

def _on_bug_report_enabled_changed(
    qt_widgets: Any,
    section: Any,
    enabled: bool,
    on_enabled_changed: Optional[Callable[[bool], None]],
    on_settings_changed: Optional[Callable[[], None]],
) -> None:
    details = find_child(section, qt_widgets.QWidget, SETTINGS_BUG_REPORT_DETAILS_OBJECT_NAME)
    if details is not None:
        _set_bug_report_details_visible(details, enabled)
    if on_enabled_changed is not None:
        on_enabled_changed(enabled)
    if on_settings_changed is not None:
        on_settings_changed()

def _build_bug_report_field_row(
    qt_widgets: Any,
    *,
    label: str,
    object_name: str,
    value: str,
    placeholder: str,
    secret: bool = False,
    on_changed: Optional[Callable[[], None]],
) -> Any:
    row = qt_widgets.QWidget()
    row_layout = qt_widgets.QHBoxLayout(row)
    set_row_margins = getattr(row_layout, "setContentsMargins", None)
    if set_row_margins is not None:
        set_row_margins(0, 0, 0, 0)
    set_row_spacing = getattr(row_layout, "setSpacing", None)
    if set_row_spacing is not None:
        set_row_spacing(4)

    caption = qt_widgets.QLabel(label)
    set_caption_width = getattr(caption, "setFixedWidth", None)
    if set_caption_width is not None:
        set_caption_width(_BUG_REPORT_LABEL_WIDTH)
    row_layout.addWidget(caption)

    field = qt_widgets.QLineEdit(value)
    field.setObjectName(object_name)
    set_placeholder = getattr(field, "setPlaceholderText", None)
    if set_placeholder is not None and placeholder:
        set_placeholder(placeholder)
    set_fixed_width = getattr(field, "setFixedWidth", None)
    if set_fixed_width is not None:
        set_fixed_width(_BUG_REPORT_FIELD_WIDTH)
    if secret:
        apply_password_echo_mode(qt_widgets, field)
    wire_line_edit_finished(field, on_changed)
    row_layout.addWidget(field)
    row_layout.addStretch(1)
    return row

def _set_bug_report_details_visible(details: Any, visible: bool) -> None:
    set_visible = getattr(details, "setVisible", None)
    if set_visible is not None:
        set_visible(visible)

def _toggle_checked(
    view: Any,
    qt_widgets: Any,
    object_name: str,
    default: bool,
) -> bool:
    toggle = find_child(view, qt_widgets.QWidget, object_name)
    if toggle is None:
        return default
    is_checked = getattr(toggle, "isChecked", None)
    if is_checked is None:
        return default
    return bool(is_checked())
