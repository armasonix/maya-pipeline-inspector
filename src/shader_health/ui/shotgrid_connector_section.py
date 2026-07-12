"""ShotGrid connector section for the Settings Connectors tab."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any, Optional

from shader_health.studio_config import (
    ConnectorSettings,
    ShotGridConnectorSettings,
    StudioConfig,
)
from shader_health.ui.settings_widgets import (
    apply_password_echo_mode,
    build_settings_toggle,
    find_child,
    line_edit_text,
    qt_align_left,
    set_fixed_horizontal_size_policy,
    set_line_edit_text,
    wire_line_edit_finished,
)

SETTINGS_SHOTGRID_SECTION_OBJECT_NAME = "shaderHealthInspectorSettingsShotGridSection"
SETTINGS_SHOTGRID_ENABLED_TOGGLE_OBJECT_NAME = "shaderHealthInspectorSettingsShotGridEnabledToggle"
SETTINGS_SHOTGRID_DETAILS_OBJECT_NAME = "shaderHealthInspectorSettingsShotGridDetails"
SETTINGS_SHOTGRID_SITE_URL_INPUT_OBJECT_NAME = "shaderHealthInspectorSettingsShotGridSiteUrlInput"
SETTINGS_SHOTGRID_SCRIPT_NAME_INPUT_OBJECT_NAME = (
    "shaderHealthInspectorSettingsShotGridScriptNameInput"
)
SETTINGS_SHOTGRID_API_KEY_INPUT_OBJECT_NAME = "shaderHealthInspectorSettingsShotGridApiKeyInput"
SETTINGS_SHOTGRID_PROJECT_INPUT_OBJECT_NAME = "shaderHealthInspectorSettingsShotGridProjectInput"
SETTINGS_SHOTGRID_ENTITY_TYPE_INPUT_OBJECT_NAME = (
    "shaderHealthInspectorSettingsShotGridEntityTypeInput"
)

_SHOTGRID_LABEL_WIDTH = 84
_SHOTGRID_FIELD_WIDTH = 292

def build_shotgrid_connector_section(
    qt_widgets: Any,
    config: StudioConfig,
    *,
    on_enabled_changed: Optional[Callable[[bool], None]] = None,
    on_settings_changed: Optional[Callable[[], None]] = None,
) -> Any:
    """Build the ShotGrid connector section widget."""

    section = qt_widgets.QWidget()
    section.setObjectName(SETTINGS_SHOTGRID_SECTION_OBJECT_NAME)
    section_layout = qt_widgets.QVBoxLayout(section)
    section_layout.setContentsMargins(0, 0, 0, 0)
    section_layout.setSpacing(6)

    title = qt_widgets.QLabel("ShotGrid")
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
    enabled_row.addWidget(qt_widgets.QLabel("Task tracker"))
    enabled_row.addWidget(
        build_settings_toggle(
            qt_widgets,
            object_name=SETTINGS_SHOTGRID_ENABLED_TOGGLE_OBJECT_NAME,
            enabled=config.connectors.shotgrid.enabled,
            on_changed=lambda enabled: _on_shotgrid_enabled_changed(
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

    shotgrid = config.connectors.shotgrid
    details_layout.addWidget(
        _build_shotgrid_field_row(
            qt_widgets,
            label="Site URL",
            object_name=SETTINGS_SHOTGRID_SITE_URL_INPUT_OBJECT_NAME,
            value=shotgrid.site_url,
            placeholder="https://studio.shotgrid.autodesk.com",
            on_changed=on_settings_changed,
        )
    )
    details_layout.addWidget(
        _build_shotgrid_field_row(
            qt_widgets,
            label="Script name",
            object_name=SETTINGS_SHOTGRID_SCRIPT_NAME_INPUT_OBJECT_NAME,
            value=shotgrid.script_name,
            placeholder="shader_health",
            on_changed=on_settings_changed,
        )
    )
    details_layout.addWidget(
        _build_shotgrid_field_row(
            qt_widgets,
            label="API key",
            object_name=SETTINGS_SHOTGRID_API_KEY_INPUT_OBJECT_NAME,
            value=shotgrid.api_key,
            placeholder="shotgrid-api-key",
            secret=True,
            on_changed=on_settings_changed,
        )
    )
    details_layout.addWidget(
        _build_shotgrid_field_row(
            qt_widgets,
            label="Project",
            object_name=SETTINGS_SHOTGRID_PROJECT_INPUT_OBJECT_NAME,
            value=shotgrid.project,
            placeholder="Demo Project",
            on_changed=on_settings_changed,
        )
    )
    details_layout.addWidget(
        _build_shotgrid_field_row(
            qt_widgets,
            label="Entity type",
            object_name=SETTINGS_SHOTGRID_ENTITY_TYPE_INPUT_OBJECT_NAME,
            value=shotgrid.entity_type,
            placeholder="Shot",
            on_changed=on_settings_changed,
        )
    )

    details_row = qt_widgets.QWidget()
    details_row.setObjectName(SETTINGS_SHOTGRID_DETAILS_OBJECT_NAME)
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
    _set_shotgrid_details_visible(details_row, config.connectors.shotgrid.enabled)

    hint = qt_widgets.QLabel(
        "When enabled, Shader Health can publish validation summaries as ShotGrid "
        "notes on Assets or Shots. Script credentials and project are stored in "
        "the studio config."
    )
    hint.setWordWrap(True)
    section_layout.addWidget(hint)
    return section

def read_shotgrid_connector_from_view(view: Any, qt_widgets: Any) -> ShotGridConnectorSettings:
    toggle = find_child(view, qt_widgets.QWidget, SETTINGS_SHOTGRID_ENABLED_TOGGLE_OBJECT_NAME)
    enabled = bool(getattr(toggle, "isChecked", lambda: False)()) if toggle is not None else False
    return ShotGridConnectorSettings(
        enabled=enabled,
        site_url=line_edit_text(view, qt_widgets, SETTINGS_SHOTGRID_SITE_URL_INPUT_OBJECT_NAME),
        script_name=line_edit_text(
            view,
            qt_widgets,
            SETTINGS_SHOTGRID_SCRIPT_NAME_INPUT_OBJECT_NAME,
        ),
        api_key=line_edit_text(view, qt_widgets, SETTINGS_SHOTGRID_API_KEY_INPUT_OBJECT_NAME),
        project=line_edit_text(view, qt_widgets, SETTINGS_SHOTGRID_PROJECT_INPUT_OBJECT_NAME),
        entity_type=line_edit_text(
            view,
            qt_widgets,
            SETTINGS_SHOTGRID_ENTITY_TYPE_INPUT_OBJECT_NAME,
        )
        or "Shot",
    )

def update_shotgrid_connector_view(
    view: Any,
    qt_widgets: Any,
    shotgrid: ShotGridConnectorSettings,
) -> None:
    toggle = find_child(view, qt_widgets.QWidget, SETTINGS_SHOTGRID_ENABLED_TOGGLE_OBJECT_NAME)
    if toggle is not None:
        from shader_health.ui.settings_widgets import apply_toggle_style, toggle_label

        set_checked = getattr(toggle, "setChecked", None)
        if set_checked is not None:
            set_checked(shotgrid.enabled)
        toggle.setText(toggle_label(shotgrid.enabled))
        apply_toggle_style(toggle, shotgrid.enabled)

    details = find_child(view, qt_widgets.QWidget, SETTINGS_SHOTGRID_DETAILS_OBJECT_NAME)
    if details is not None:
        _set_shotgrid_details_visible(details, shotgrid.enabled)

    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_SHOTGRID_SITE_URL_INPUT_OBJECT_NAME,
        shotgrid.site_url,
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_SHOTGRID_SCRIPT_NAME_INPUT_OBJECT_NAME,
        shotgrid.script_name,
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_SHOTGRID_API_KEY_INPUT_OBJECT_NAME,
        shotgrid.api_key,
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_SHOTGRID_PROJECT_INPUT_OBJECT_NAME,
        shotgrid.project,
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_SHOTGRID_ENTITY_TYPE_INPUT_OBJECT_NAME,
        shotgrid.entity_type,
    )

def get_shotgrid_settings(connectors: ConnectorSettings) -> ShotGridConnectorSettings:
    return connectors.shotgrid

def apply_shotgrid_settings(
    connectors: ConnectorSettings,
    settings: ShotGridConnectorSettings,
) -> ConnectorSettings:
    return replace(connectors, shotgrid=settings)

def _on_shotgrid_enabled_changed(
    qt_widgets: Any,
    section: Any,
    enabled: bool,
    on_enabled_changed: Optional[Callable[[bool], None]],
) -> None:
    details = find_child(section, qt_widgets.QWidget, SETTINGS_SHOTGRID_DETAILS_OBJECT_NAME)
    if details is not None:
        _set_shotgrid_details_visible(details, enabled)
    if on_enabled_changed is not None:
        on_enabled_changed(enabled)

def _build_shotgrid_field_row(
    qt_widgets: Any,
    *,
    label: str,
    object_name: str,
    value: str,
    placeholder: str,
    secret: bool = False,
    on_changed: Optional[Callable[[], None]] = None,
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
        set_caption_width(_SHOTGRID_LABEL_WIDTH)
    row_layout.addWidget(caption)

    field = qt_widgets.QLineEdit(value)
    field.setObjectName(object_name)
    set_placeholder = getattr(field, "setPlaceholderText", None)
    if set_placeholder is not None and placeholder:
        set_placeholder(placeholder)
    set_fixed_width = getattr(field, "setFixedWidth", None)
    if set_fixed_width is not None:
        set_fixed_width(_SHOTGRID_FIELD_WIDTH)
    set_fixed_horizontal_size_policy(qt_widgets, field)
    if secret:
        apply_password_echo_mode(qt_widgets, field)
    wire_line_edit_finished(field, on_changed)
    row_layout.addWidget(field)
    row_layout.addStretch(1)
    return row

def _set_shotgrid_details_visible(details: Any, visible: bool) -> None:
    set_visible = getattr(details, "setVisible", None)
    if set_visible is not None:
        set_visible(visible)
