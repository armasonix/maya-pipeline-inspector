"""Slack connector section for the Settings Connectors tab."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any, Optional

from shader_health.studio_config import (
    SLACK_NOTIFY_EVENTS,
    ConnectorSettings,
    SlackConnectorSettings,
    StudioConfig,
)
from shader_health.ui.settings_widgets import (
    apply_password_echo_mode,
    build_settings_toggle,
    checkbox_checked,
    find_child,
    line_edit_text,
    qt_align_left,
    set_checkbox_checked,
    set_fixed_horizontal_size_policy,
    set_line_edit_text,
    wire_checkbox_changed,
    wire_line_edit_finished,
)

SETTINGS_SLACK_SECTION_OBJECT_NAME = "shaderHealthInspectorSettingsSlackSection"
SETTINGS_SLACK_ENABLED_TOGGLE_OBJECT_NAME = "shaderHealthInspectorSettingsSlackEnabledToggle"
SETTINGS_SLACK_DETAILS_OBJECT_NAME = "shaderHealthInspectorSettingsSlackDetails"
SETTINGS_SLACK_PUBLISH_WEBHOOK_INPUT_OBJECT_NAME = (
    "shaderHealthInspectorSettingsSlackPublishWebhookInput"
)
SETTINGS_SLACK_DEADLINE_WEBHOOK_INPUT_OBJECT_NAME = (
    "shaderHealthInspectorSettingsSlackDeadlineWebhookInput"
)
SETTINGS_SLACK_NOTIFY_BLOCK_PUBLISH_CHECKBOX_OBJECT_NAME = (
    "shaderHealthInspectorSettingsSlackNotifyBlockPublishCheckbox"
)
SETTINGS_SLACK_NOTIFY_BLOCK_DEADLINE_CHECKBOX_OBJECT_NAME = (
    "shaderHealthInspectorSettingsSlackNotifyBlockDeadlineCheckbox"
)
SETTINGS_SLACK_INCLUDE_REPORT_LINK_CHECKBOX_OBJECT_NAME = (
    "shaderHealthInspectorSettingsSlackIncludeReportLinkCheckbox"
)

_SLACK_LABEL_WIDTH = 108
_SLACK_FIELD_WIDTH = 292
_SLACK_NOTIFY_CHECKBOX_OBJECT_NAMES = {
    event_id: object_name
    for event_id, object_name in (
        (
            SLACK_NOTIFY_EVENTS[0][0],
            SETTINGS_SLACK_NOTIFY_BLOCK_PUBLISH_CHECKBOX_OBJECT_NAME,
        ),
        (
            SLACK_NOTIFY_EVENTS[1][0],
            SETTINGS_SLACK_NOTIFY_BLOCK_DEADLINE_CHECKBOX_OBJECT_NAME,
        ),
    )
}


def build_slack_connector_section(
    qt_widgets: Any,
    config: StudioConfig,
    *,
    on_enabled_changed: Optional[Callable[[bool], None]] = None,
    on_settings_changed: Optional[Callable[[], None]] = None,
) -> Any:
    """Build the Slack connector section widget."""

    section = qt_widgets.QWidget()
    section.setObjectName(SETTINGS_SLACK_SECTION_OBJECT_NAME)
    section_layout = qt_widgets.QVBoxLayout(section)
    section_layout.setContentsMargins(0, 0, 0, 0)
    section_layout.setSpacing(6)

    title = qt_widgets.QLabel("Slack")
    set_style = getattr(title, "setStyleSheet", None)
    if set_style is not None:
        set_style("font-size: 11pt; font-weight: bold;")
    section_layout.addWidget(title)

    enabled_row = qt_widgets.QHBoxLayout()
    set_enabled_margins = getattr(enabled_row, "setContentsMargins", None)
    if set_enabled_margins is not None:
        set_enabled_margins(0, 0, 0, 0)
    set_enabled_spacing = getattr(enabled_row, "setSpacing", None)
    if set_enabled_spacing is not None:
        set_enabled_spacing(4)
    enabled_row.addWidget(qt_widgets.QLabel("Notifications"))
    enabled_row.addWidget(
        build_settings_toggle(
            qt_widgets,
            object_name=SETTINGS_SLACK_ENABLED_TOGGLE_OBJECT_NAME,
            enabled=config.connectors.slack.enabled,
            on_changed=lambda enabled: _on_slack_enabled_changed(
                qt_widgets,
                section,
                enabled,
                on_enabled_changed,
            ),
        )
    )
    enabled_row.addStretch(1)
    section_layout.addLayout(enabled_row)

    details = qt_widgets.QWidget()
    set_fixed_horizontal_size_policy(qt_widgets, details)
    details_layout = qt_widgets.QVBoxLayout(details)
    set_details_margins = getattr(details_layout, "setContentsMargins", None)
    if set_details_margins is not None:
        set_details_margins(0, 2, 0, 0)
    set_details_spacing = getattr(details_layout, "setSpacing", None)
    if set_details_spacing is not None:
        set_details_spacing(4)

    slack = config.connectors.slack
    details_layout.addWidget(
        _build_slack_field_row(
            qt_widgets,
            label="Publish webhook",
            object_name=SETTINGS_SLACK_PUBLISH_WEBHOOK_INPUT_OBJECT_NAME,
            value=slack.publish_webhook_url,
            placeholder="https://hooks.slack.com/services/.../publish",
            secret=True,
            on_changed=on_settings_changed,
        )
    )
    details_layout.addWidget(
        _build_slack_field_row(
            qt_widgets,
            label="Deadline webhook",
            object_name=SETTINGS_SLACK_DEADLINE_WEBHOOK_INPUT_OBJECT_NAME,
            value=slack.deadline_webhook_url,
            placeholder="https://hooks.slack.com/services/.../deadline",
            secret=True,
            on_changed=on_settings_changed,
        )
    )

    notify_row = qt_widgets.QHBoxLayout()
    set_notify_margins = getattr(notify_row, "setContentsMargins", None)
    if set_notify_margins is not None:
        set_notify_margins(0, 0, 0, 0)
    set_notify_spacing = getattr(notify_row, "setSpacing", None)
    if set_notify_spacing is not None:
        set_notify_spacing(8)
    notify_caption = qt_widgets.QLabel("Notify on")
    set_fixed_horizontal_size_policy(qt_widgets, notify_caption)
    set_caption_width = getattr(notify_caption, "setFixedWidth", None)
    if set_caption_width is not None:
        set_caption_width(_SLACK_LABEL_WIDTH)
    notify_row.addWidget(notify_caption)
    for event_id, label in SLACK_NOTIFY_EVENTS:
        checkbox = qt_widgets.QCheckBox(label)
        checkbox.setObjectName(_SLACK_NOTIFY_CHECKBOX_OBJECT_NAMES[event_id])
        set_checked = getattr(checkbox, "setChecked", None)
        if set_checked is not None:
            set_checked(event_id in slack.notify_on)
        wire_checkbox_changed(checkbox, on_settings_changed)
        notify_row.addWidget(checkbox)
    notify_row.addStretch(1)
    add_notify_layout = getattr(details_layout, "addLayout", None)
    if add_notify_layout is not None:
        add_notify_layout(notify_row)

    report_row = qt_widgets.QHBoxLayout()
    set_report_margins = getattr(report_row, "setContentsMargins", None)
    if set_report_margins is not None:
        set_report_margins(0, 0, 0, 0)
    report_checkbox = qt_widgets.QCheckBox("Include report link from render_root")
    report_checkbox.setObjectName(SETTINGS_SLACK_INCLUDE_REPORT_LINK_CHECKBOX_OBJECT_NAME)
    set_checked = getattr(report_checkbox, "setChecked", None)
    if set_checked is not None:
        set_checked(slack.include_report_link)
    wire_checkbox_changed(report_checkbox, on_settings_changed)
    report_row.addWidget(report_checkbox)
    report_row.addStretch(1)
    add_report_layout = getattr(details_layout, "addLayout", None)
    if add_report_layout is not None:
        add_report_layout(report_row)

    details_row = qt_widgets.QWidget()
    details_row.setObjectName(SETTINGS_SLACK_DETAILS_OBJECT_NAME)
    details_row_layout = qt_widgets.QHBoxLayout(details_row)
    set_row_margins = getattr(details_row_layout, "setContentsMargins", None)
    if set_row_margins is not None:
        set_row_margins(0, 0, 0, 0)
    set_row_spacing = getattr(details_row_layout, "setSpacing", None)
    if set_row_spacing is not None:
        set_row_spacing(0)
    add_details = getattr(details_row_layout, "addWidget", None)
    add_stretch = getattr(details_row_layout, "addStretch", None)
    align_left = qt_align_left(qt_widgets)
    if add_details is not None:
        if align_left is not None:
            add_details(details, 0, align_left)
        else:
            add_details(details)
    if add_stretch is not None:
        add_stretch(1)
    section_layout.addWidget(details_row)
    _set_slack_details_visible(details_row, config.connectors.slack.enabled)

    hint = qt_widgets.QLabel(
        "Route publish and Deadline block events to separate Slack incoming webhooks. "
        "Optional report links use studio_environment.render_root when enabled."
    )
    hint.setWordWrap(True)
    section_layout.addWidget(hint)
    return section


def read_slack_connector_from_view(view: Any, qt_widgets: Any) -> SlackConnectorSettings:
    toggle = find_child(view, qt_widgets.QWidget, SETTINGS_SLACK_ENABLED_TOGGLE_OBJECT_NAME)
    enabled = bool(getattr(toggle, "isChecked", lambda: False)()) if toggle is not None else False
    notify_on = tuple(
        event_id
        for event_id, _label in SLACK_NOTIFY_EVENTS
        if checkbox_checked(view, qt_widgets, _SLACK_NOTIFY_CHECKBOX_OBJECT_NAMES[event_id])
    )
    return SlackConnectorSettings(
        enabled=enabled,
        publish_webhook_url=line_edit_text(
            view,
            qt_widgets,
            SETTINGS_SLACK_PUBLISH_WEBHOOK_INPUT_OBJECT_NAME,
        ),
        deadline_webhook_url=line_edit_text(
            view,
            qt_widgets,
            SETTINGS_SLACK_DEADLINE_WEBHOOK_INPUT_OBJECT_NAME,
        ),
        notify_on=notify_on,
        include_report_link=checkbox_checked(
            view,
            qt_widgets,
            SETTINGS_SLACK_INCLUDE_REPORT_LINK_CHECKBOX_OBJECT_NAME,
        ),
    )


def update_slack_connector_view(
    view: Any,
    qt_widgets: Any,
    slack: SlackConnectorSettings,
) -> None:
    toggle = find_child(view, qt_widgets.QWidget, SETTINGS_SLACK_ENABLED_TOGGLE_OBJECT_NAME)
    if toggle is not None:
        from shader_health.ui.settings_widgets import apply_toggle_style, toggle_label

        set_checked = getattr(toggle, "setChecked", None)
        if set_checked is not None:
            set_checked(slack.enabled)
        toggle.setText(toggle_label(slack.enabled))
        apply_toggle_style(toggle, slack.enabled)

    details = find_child(view, qt_widgets.QWidget, SETTINGS_SLACK_DETAILS_OBJECT_NAME)
    if details is not None:
        _set_slack_details_visible(details, slack.enabled)

    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_SLACK_PUBLISH_WEBHOOK_INPUT_OBJECT_NAME,
        slack.publish_webhook_url,
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_SLACK_DEADLINE_WEBHOOK_INPUT_OBJECT_NAME,
        slack.deadline_webhook_url,
    )
    for event_id, _label in SLACK_NOTIFY_EVENTS:
        set_checkbox_checked(
            view,
            qt_widgets,
            _SLACK_NOTIFY_CHECKBOX_OBJECT_NAMES[event_id],
            event_id in slack.notify_on,
        )
    set_checkbox_checked(
        view,
        qt_widgets,
        SETTINGS_SLACK_INCLUDE_REPORT_LINK_CHECKBOX_OBJECT_NAME,
        slack.include_report_link,
    )


def get_slack_settings(connectors: ConnectorSettings) -> SlackConnectorSettings:
    return connectors.slack


def apply_slack_settings(
    connectors: ConnectorSettings,
    settings: SlackConnectorSettings,
) -> ConnectorSettings:
    return replace(connectors, slack=settings)


def _on_slack_enabled_changed(
    qt_widgets: Any,
    section: Any,
    enabled: bool,
    on_enabled_changed: Optional[Callable[[bool], None]],
) -> None:
    details = find_child(section, qt_widgets.QWidget, SETTINGS_SLACK_DETAILS_OBJECT_NAME)
    if details is not None:
        _set_slack_details_visible(details, enabled)
    if on_enabled_changed is not None:
        on_enabled_changed(enabled)


def _build_slack_field_row(
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
    set_fixed_horizontal_size_policy(qt_widgets, caption)
    set_caption_width = getattr(caption, "setFixedWidth", None)
    if set_caption_width is not None:
        set_caption_width(_SLACK_LABEL_WIDTH)
    row_layout.addWidget(caption)

    field = qt_widgets.QLineEdit(value)
    field.setObjectName(object_name)
    set_placeholder = getattr(field, "setPlaceholderText", None)
    if set_placeholder is not None and placeholder:
        set_placeholder(placeholder)
    set_fixed_width = getattr(field, "setFixedWidth", None)
    if set_fixed_width is not None:
        set_fixed_width(_SLACK_FIELD_WIDTH)
    set_fixed_horizontal_size_policy(qt_widgets, field)
    if secret:
        apply_password_echo_mode(qt_widgets, field)
    wire_line_edit_finished(field, on_changed)
    row_layout.addWidget(field)
    row_layout.addStretch(1)
    return row


def _set_slack_details_visible(details: Any, visible: bool) -> None:
    set_visible = getattr(details, "setVisible", None)
    if set_visible is not None:
        set_visible(visible)
