"""Cerebro connector section for the Settings Connectors tab."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any, Optional

from shader_health.studio_config import (
    CerebroConnectorSettings,
    ConnectorSettings,
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

SETTINGS_CEREBRO_SECTION_OBJECT_NAME = "shaderHealthInspectorSettingsCerebroSection"
SETTINGS_CEREBRO_ENABLED_TOGGLE_OBJECT_NAME = "shaderHealthInspectorSettingsCerebroEnabledToggle"
SETTINGS_CEREBRO_DETAILS_OBJECT_NAME = "shaderHealthInspectorSettingsCerebroDetails"
SETTINGS_CEREBRO_SERVER_URL_INPUT_OBJECT_NAME = "shaderHealthInspectorSettingsCerebroServerUrlInput"
SETTINGS_CEREBRO_API_USER_INPUT_OBJECT_NAME = "shaderHealthInspectorSettingsCerebroApiUserInput"
SETTINGS_CEREBRO_API_PASSWORD_INPUT_OBJECT_NAME = (
    "shaderHealthInspectorSettingsCerebroApiPasswordInput"
)
SETTINGS_CEREBRO_PROJECT_INPUT_OBJECT_NAME = "shaderHealthInspectorSettingsCerebroProjectInput"
SETTINGS_CEREBRO_SERVICE_TOOLS_PATH_INPUT_OBJECT_NAME = (
    "shaderHealthInspectorSettingsCerebroServiceToolsPathInput"
)

_CEREBRO_LABEL_WIDTH = 84
_CEREBRO_FIELD_WIDTH = 292


def build_cerebro_connector_section(
    qt_widgets: Any,
    config: StudioConfig,
    *,
    on_enabled_changed: Optional[Callable[[bool], None]] = None,
    on_settings_changed: Optional[Callable[[], None]] = None,
) -> Any:
    """Build the Cerebro connector section widget."""

    section = qt_widgets.QWidget()
    section.setObjectName(SETTINGS_CEREBRO_SECTION_OBJECT_NAME)
    section_layout = qt_widgets.QVBoxLayout(section)
    section_layout.setContentsMargins(0, 0, 0, 0)
    section_layout.setSpacing(6)

    title = qt_widgets.QLabel("Cerebro")
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
            object_name=SETTINGS_CEREBRO_ENABLED_TOGGLE_OBJECT_NAME,
            enabled=config.connectors.cerebro.enabled,
            on_changed=lambda enabled: _on_cerebro_enabled_changed(
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

    cerebro = config.connectors.cerebro
    details_layout.addWidget(
        _build_cerebro_field_row(
            qt_widgets,
            label="Database host",
            object_name=SETTINGS_CEREBRO_SERVER_URL_INPUT_OBJECT_NAME,
            value=cerebro.server_url,
            placeholder="https://db5.cerebrohq.com/dapi5/rpc.php",
            tooltip=(
                "Server API URL from Cerebro web (for example "
                "https://db5.cerebrohq.com/dapi5/rpc.php). Host:45432 is derived automatically."
            ),
            on_changed=on_settings_changed,
        )
    )
    details_layout.addWidget(
        _build_cerebro_field_row(
            qt_widgets,
            label="API user",
            object_name=SETTINGS_CEREBRO_API_USER_INPUT_OBJECT_NAME,
            value=cerebro.api_user,
            placeholder="api@studio",
            tooltip="API Users email from Cerebro web, not your personal login.",
            on_changed=on_settings_changed,
        )
    )
    details_layout.addWidget(
        _build_cerebro_field_row(
            qt_widgets,
            label="Access token",
            object_name=SETTINGS_CEREBRO_API_PASSWORD_INPUT_OBJECT_NAME,
            value=cerebro.api_password,
            placeholder="paste access token",
            secret=True,
            tooltip="Access token copied from the same Cerebro API Users page.",
            on_changed=on_settings_changed,
        )
    )
    details_layout.addWidget(
        _build_cerebro_field_row(
            qt_widgets,
            label="Project",
            object_name=SETTINGS_CEREBRO_PROJECT_INPUT_OBJECT_NAME,
            value=cerebro.project,
            placeholder="Demo Project",
            tooltip="Exact Cerebro project name used for task lookup.",
            on_changed=on_settings_changed,
        )
    )
    details_layout.addWidget(
        _build_cerebro_field_row(
            qt_widgets,
            label="Service tools",
            object_name=SETTINGS_CEREBRO_SERVICE_TOOLS_PATH_INPUT_OBJECT_NAME,
            value=cerebro.service_tools_path,
            placeholder=r"C:\tools\service-tools",
            tooltip=(
                "Folder containing py_cerebro from Cerebro service-tools.zip. "
                "One-time Maya setup: mayapy -m pip install psycopg2-binary."
            ),
            on_changed=on_settings_changed,
        )
    )

    details_row = qt_widgets.QWidget()
    details_row.setObjectName(SETTINGS_CEREBRO_DETAILS_OBJECT_NAME)
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
    _set_cerebro_details_visible(details_row, config.connectors.cerebro.enabled)

    hint = qt_widgets.QLabel(
        "When enabled, Shader Health publishes validation summaries as Cerebro task notes. "
        "Database host, API user, and access token come from Cerebro web API Users. "
        "Connection is tested when you save or edit Cerebro settings."
    )
    hint.setWordWrap(True)
    section_layout.addWidget(hint)
    return section


def read_cerebro_connector_from_view(view: Any, qt_widgets: Any) -> CerebroConnectorSettings:
    toggle = find_child(view, qt_widgets.QWidget, SETTINGS_CEREBRO_ENABLED_TOGGLE_OBJECT_NAME)
    enabled = bool(getattr(toggle, "isChecked", lambda: False)()) if toggle is not None else False
    return CerebroConnectorSettings(
        enabled=enabled,
        server_url=line_edit_text(view, qt_widgets, SETTINGS_CEREBRO_SERVER_URL_INPUT_OBJECT_NAME),
        api_user=line_edit_text(view, qt_widgets, SETTINGS_CEREBRO_API_USER_INPUT_OBJECT_NAME),
        api_password=line_edit_text(
            view,
            qt_widgets,
            SETTINGS_CEREBRO_API_PASSWORD_INPUT_OBJECT_NAME,
        ),
        project=line_edit_text(view, qt_widgets, SETTINGS_CEREBRO_PROJECT_INPUT_OBJECT_NAME),
        service_tools_path=line_edit_text(
            view,
            qt_widgets,
            SETTINGS_CEREBRO_SERVICE_TOOLS_PATH_INPUT_OBJECT_NAME,
        ),
    )


def update_cerebro_connector_view(
    view: Any,
    qt_widgets: Any,
    cerebro: CerebroConnectorSettings,
) -> None:
    toggle = find_child(view, qt_widgets.QWidget, SETTINGS_CEREBRO_ENABLED_TOGGLE_OBJECT_NAME)
    if toggle is not None:
        from shader_health.ui.settings_widgets import apply_toggle_style, toggle_label

        set_checked = getattr(toggle, "setChecked", None)
        if set_checked is not None:
            set_checked(cerebro.enabled)
        toggle.setText(toggle_label(cerebro.enabled))
        apply_toggle_style(toggle, cerebro.enabled)

    details = find_child(view, qt_widgets.QWidget, SETTINGS_CEREBRO_DETAILS_OBJECT_NAME)
    if details is not None:
        _set_cerebro_details_visible(details, cerebro.enabled)

    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_CEREBRO_SERVER_URL_INPUT_OBJECT_NAME,
        cerebro.server_url,
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_CEREBRO_API_USER_INPUT_OBJECT_NAME,
        cerebro.api_user,
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_CEREBRO_API_PASSWORD_INPUT_OBJECT_NAME,
        cerebro.api_password,
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_CEREBRO_PROJECT_INPUT_OBJECT_NAME,
        cerebro.project,
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_CEREBRO_SERVICE_TOOLS_PATH_INPUT_OBJECT_NAME,
        cerebro.service_tools_path,
    )


def get_cerebro_settings(connectors: ConnectorSettings) -> CerebroConnectorSettings:
    return connectors.cerebro


def apply_cerebro_settings(
    connectors: ConnectorSettings,
    settings: CerebroConnectorSettings,
) -> ConnectorSettings:
    return replace(connectors, cerebro=settings)


def _on_cerebro_enabled_changed(
    qt_widgets: Any,
    section: Any,
    enabled: bool,
    on_enabled_changed: Optional[Callable[[bool], None]],
) -> None:
    details = find_child(section, qt_widgets.QWidget, SETTINGS_CEREBRO_DETAILS_OBJECT_NAME)
    if details is not None:
        _set_cerebro_details_visible(details, enabled)
    if on_enabled_changed is not None:
        on_enabled_changed(enabled)


def _build_cerebro_field_row(
    qt_widgets: Any,
    *,
    label: str,
    object_name: str,
    value: str,
    placeholder: str,
    secret: bool = False,
    tooltip: str = "",
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
        set_caption_width(_CEREBRO_LABEL_WIDTH)
    row_layout.addWidget(caption)

    field = qt_widgets.QLineEdit(value)
    field.setObjectName(object_name)
    set_placeholder = getattr(field, "setPlaceholderText", None)
    if set_placeholder is not None and placeholder:
        set_placeholder(placeholder)
    set_tooltip = getattr(field, "setToolTip", None)
    if set_tooltip is not None and tooltip:
        set_tooltip(tooltip)
    set_fixed_width = getattr(field, "setFixedWidth", None)
    if set_fixed_width is not None:
        set_fixed_width(_CEREBRO_FIELD_WIDTH)
    set_fixed_horizontal_size_policy(qt_widgets, field)
    if secret:
        apply_password_echo_mode(qt_widgets, field)
    wire_line_edit_finished(field, on_changed)
    row_layout.addWidget(field)
    row_layout.addStretch(1)
    return row


def _set_cerebro_details_visible(details: Any, visible: bool) -> None:
    set_visible = getattr(details, "setVisible", None)
    if set_visible is not None:
        set_visible(visible)
