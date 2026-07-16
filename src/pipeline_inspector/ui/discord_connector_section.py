"""Discord connector section for the Settings Connectors tab."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any, Optional

from pipeline_inspector.studio_config import (
    ConnectorSettings,
    DiscordConnectorSettings,
    StudioConfig,
)
from pipeline_inspector.ui.notify_trigger_widgets import (
    build_notify_trigger_controls,
    notify_checkbox_object_name,
    read_notify_on_from_view,
    read_notify_score_below_from_view,
    update_notify_trigger_view,
)
from pipeline_inspector.ui.settings_widgets import (
    apply_password_echo_mode,
    build_settings_toggle,
    find_child,
    line_edit_text,
    qt_align_left,
    set_fixed_horizontal_size_policy,
    set_line_edit_text,
    wire_line_edit_finished,
)

SETTINGS_DISCORD_SECTION_OBJECT_NAME = "pipelineInspectorSettingsDiscordSection"
SETTINGS_DISCORD_ENABLED_TOGGLE_OBJECT_NAME = "pipelineInspectorSettingsDiscordEnabledToggle"
SETTINGS_DISCORD_DETAILS_OBJECT_NAME = "pipelineInspectorSettingsDiscordDetails"
SETTINGS_DISCORD_WEBHOOK_URL_INPUT_OBJECT_NAME = (
    "pipelineInspectorSettingsDiscordWebhookUrlInput"
)
SETTINGS_DISCORD_NOTIFY_BLOCK_PUBLISH_CHECKBOX_OBJECT_NAME = notify_checkbox_object_name(
    "Discord",
    "block_publish",
)
SETTINGS_DISCORD_NOTIFY_BLOCK_DEADLINE_CHECKBOX_OBJECT_NAME = notify_checkbox_object_name(
    "Discord",
    "block_deadline",
)

_DISCORD_LABEL_WIDTH = 88
_DISCORD_FIELD_WIDTH = 292

def build_discord_connector_section(
    qt_widgets: Any,
    config: StudioConfig,
    *,
    on_enabled_changed: Optional[Callable[[bool], None]] = None,
    on_settings_changed: Optional[Callable[[], None]] = None,
) -> Any:
    """Build the Discord connector section widget."""

    section = qt_widgets.QWidget()
    section.setObjectName(SETTINGS_DISCORD_SECTION_OBJECT_NAME)
    section_layout = qt_widgets.QVBoxLayout(section)
    section_layout.setContentsMargins(0, 0, 0, 0)
    section_layout.setSpacing(6)

    title = qt_widgets.QLabel("Discord")
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
            object_name=SETTINGS_DISCORD_ENABLED_TOGGLE_OBJECT_NAME,
            enabled=config.connectors.discord.enabled,
            on_changed=lambda enabled: _on_discord_enabled_changed(
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

    discord = config.connectors.discord
    details_layout.addWidget(
        _build_discord_field_row(
            qt_widgets,
            label="Webhook URL",
            object_name=SETTINGS_DISCORD_WEBHOOK_URL_INPUT_OBJECT_NAME,
            value=discord.webhook_url,
            placeholder="https://discord.com/api/webhooks/...",
            secret=True,
            on_changed=on_settings_changed,
        )
    )

    details_layout.addWidget(
        build_notify_trigger_controls(
            qt_widgets,
            connector_prefix="Discord",
            notify_on=discord.notify_on,
            notify_score_below=discord.notify_score_below,
            label_width=_DISCORD_LABEL_WIDTH,
            on_settings_changed=on_settings_changed,
        )[0]
    )

    details_row = qt_widgets.QWidget()
    details_row.setObjectName(SETTINGS_DISCORD_DETAILS_OBJECT_NAME)
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
    _set_discord_details_visible(details_row, config.connectors.discord.enabled)

    hint = qt_widgets.QLabel(
        "When enabled, Pipeline Inspector can send validation, readiness, and farm "
        "notifications to Discord. Use notify_targets in studio JSON for per-target routing."
    )
    hint.setWordWrap(True)
    section_layout.addWidget(hint)
    return section

def read_discord_connector_from_view(view: Any, qt_widgets: Any) -> DiscordConnectorSettings:
    toggle = find_child(view, qt_widgets.QWidget, SETTINGS_DISCORD_ENABLED_TOGGLE_OBJECT_NAME)
    enabled = bool(getattr(toggle, "isChecked", lambda: False)()) if toggle is not None else False
    return DiscordConnectorSettings(
        enabled=enabled,
        webhook_url=line_edit_text(
            view,
            qt_widgets,
            SETTINGS_DISCORD_WEBHOOK_URL_INPUT_OBJECT_NAME,
        ),
        notify_on=read_notify_on_from_view(view, qt_widgets, connector_prefix="Discord"),
        notify_score_below=read_notify_score_below_from_view(
            view,
            qt_widgets,
            connector_prefix="Discord",
        ),
    )

def update_discord_connector_view(
    view: Any,
    qt_widgets: Any,
    discord: DiscordConnectorSettings,
) -> None:
    toggle = find_child(view, qt_widgets.QWidget, SETTINGS_DISCORD_ENABLED_TOGGLE_OBJECT_NAME)
    if toggle is not None:
        from pipeline_inspector.ui.settings_widgets import apply_toggle_style, toggle_label

        set_checked = getattr(toggle, "setChecked", None)
        if set_checked is not None:
            set_checked(discord.enabled)
        toggle.setText(toggle_label(discord.enabled))
        apply_toggle_style(toggle, discord.enabled)

    details = find_child(view, qt_widgets.QWidget, SETTINGS_DISCORD_DETAILS_OBJECT_NAME)
    if details is not None:
        _set_discord_details_visible(details, discord.enabled)

    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_DISCORD_WEBHOOK_URL_INPUT_OBJECT_NAME,
        discord.webhook_url,
    )
    update_notify_trigger_view(
        view,
        qt_widgets,
        connector_prefix="Discord",
        notify_on=discord.notify_on,
        notify_score_below=discord.notify_score_below,
    )

def get_discord_settings(connectors: ConnectorSettings) -> DiscordConnectorSettings:
    return connectors.discord

def apply_discord_settings(
    connectors: ConnectorSettings,
    settings: DiscordConnectorSettings,
) -> ConnectorSettings:
    return replace(connectors, discord=settings)

def _on_discord_enabled_changed(
    qt_widgets: Any,
    section: Any,
    enabled: bool,
    on_enabled_changed: Optional[Callable[[bool], None]],
) -> None:
    details = find_child(section, qt_widgets.QWidget, SETTINGS_DISCORD_DETAILS_OBJECT_NAME)
    if details is not None:
        _set_discord_details_visible(details, enabled)
    if on_enabled_changed is not None:
        on_enabled_changed(enabled)

def _build_discord_field_row(
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
        set_caption_width(_DISCORD_LABEL_WIDTH)
    row_layout.addWidget(caption)

    field = qt_widgets.QLineEdit(value)
    field.setObjectName(object_name)
    set_placeholder = getattr(field, "setPlaceholderText", None)
    if set_placeholder is not None and placeholder:
        set_placeholder(placeholder)
    set_fixed_width = getattr(field, "setFixedWidth", None)
    if set_fixed_width is not None:
        set_fixed_width(_DISCORD_FIELD_WIDTH)
    set_fixed_horizontal_size_policy(qt_widgets, field)
    if secret:
        apply_password_echo_mode(qt_widgets, field)
    wire_line_edit_finished(field, on_changed)
    row_layout.addWidget(field)
    row_layout.addStretch(1)
    return row

def _set_discord_details_visible(details: Any, visible: bool) -> None:
    set_visible = getattr(details, "setVisible", None)
    if set_visible is not None:
        set_visible(visible)
