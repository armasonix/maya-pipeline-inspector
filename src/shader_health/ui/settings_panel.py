"""Settings screen for the Maya Shader Health Inspector panel."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Optional

from shader_health.studio_config import (
    ConnectorSettings,
    DeadlineConnectorSettings,
    StudioConfig,
)

SETTINGS_VIEW_OBJECT_NAME = "shaderHealthInspectorSettingsView"
SETTINGS_TAB_WIDGET_OBJECT_NAME = "shaderHealthInspectorSettingsTabWidget"
SETTINGS_BACK_BUTTON_OBJECT_NAME = "shaderHealthInspectorSettingsBackButton"
SETTINGS_STATUS_LABEL_OBJECT_NAME = "shaderHealthInspectorSettingsStatusLabel"
SETTINGS_SAVE_BUTTON_OBJECT_NAME = "shaderHealthInspectorSettingsSaveButton"
SETTINGS_LOAD_BUTTON_OBJECT_NAME = "shaderHealthInspectorSettingsLoadButton"
SETTINGS_CONFIG_PATH_LABEL_OBJECT_NAME = "shaderHealthInspectorSettingsConfigPathLabel"

SETTINGS_PIPELINE_SECTION_OBJECT_NAME = "shaderHealthInspectorSettingsPipelineSection"
SETTINGS_REQUIRE_TX_TOGGLE_OBJECT_NAME = "shaderHealthInspectorSettingsRequireTxToggle"

SETTINGS_DEADLINE_SECTION_OBJECT_NAME = "shaderHealthInspectorSettingsDeadlineSection"
SETTINGS_DEADLINE_ENABLED_TOGGLE_OBJECT_NAME = "shaderHealthInspectorSettingsDeadlineEnabledToggle"
SETTINGS_DEADLINE_DETAILS_OBJECT_NAME = "shaderHealthInspectorSettingsDeadlineDetails"
SETTINGS_DEADLINE_LEFT_COLUMN_OBJECT_NAME = "shaderHealthInspectorSettingsDeadlineLeftColumn"
SETTINGS_DEADLINE_RIGHT_COLUMN_OBJECT_NAME = "shaderHealthInspectorSettingsDeadlineRightColumn"
SETTINGS_DEADLINE_HOST_INPUT_OBJECT_NAME = "shaderHealthInspectorSettingsDeadlineHostInput"
SETTINGS_DEADLINE_PORT_INPUT_OBJECT_NAME = "shaderHealthInspectorSettingsDeadlinePortInput"
SETTINGS_DEADLINE_REPO_ROOT_INPUT_OBJECT_NAME = "shaderHealthInspectorSettingsDeadlineRepoRootInput"
SETTINGS_DEADLINE_TIMEOUT_INPUT_OBJECT_NAME = "shaderHealthInspectorSettingsDeadlineTimeoutInput"
SETTINGS_DEADLINE_PROFILE_ID_INPUT_OBJECT_NAME = (
    "shaderHealthInspectorSettingsDeadlineProfileIdInput"
)
SETTINGS_DEADLINE_MAYAPY_INPUT_OBJECT_NAME = "shaderHealthInspectorSettingsDeadlineMayapyInput"
SETTINGS_DEADLINE_QUEUE_INPUT_OBJECT_NAME = "shaderHealthInspectorSettingsDeadlineQueueInput"
SETTINGS_DEADLINE_POOL_INPUT_OBJECT_NAME = "shaderHealthInspectorSettingsDeadlinePoolInput"
SETTINGS_DEADLINE_GROUP_INPUT_OBJECT_NAME = "shaderHealthInspectorSettingsDeadlineGroupInput"
SETTINGS_DEADLINE_USER_INPUT_OBJECT_NAME = "shaderHealthInspectorSettingsDeadlineUserInput"

_TOGGLE_OFF_STYLE = (
    "QPushButton { background-color: #4a4a4a; color: #d0d0d0; border: 1px solid #666; "
    "padding: 4px 14px; border-radius: 10px; font-weight: bold; }"
)
_TOGGLE_ON_STYLE = (
    "QPushButton { background-color: #2ecc71; color: #102010; border: 1px solid #27ae60; "
    "padding: 4px 14px; border-radius: 10px; font-weight: bold; }"
)

_DEADLINE_LABEL_WIDTH = 44
_DEADLINE_PAIR_GAP = 12
_DEADLINE_FIELD_HOST_WIDTH = 108
_DEADLINE_FIELD_PORT_WIDTH = 52
_DEADLINE_FIELD_REPO_WIDTH = 292
_DEADLINE_FIELD_TIMEOUT_WIDTH = 52
_DEADLINE_FIELD_PROFILE_WIDTH = 118
_DEADLINE_FIELD_MAYAPY_WIDTH = 292
_DEADLINE_FIELD_SMALL_WIDTH = 96
_DEADLINE_COLUMNS_GAP = 14


@dataclass(frozen=True)
class SettingsActionCallbacks:
    """Callbacks for the settings screen."""

    on_back: Optional[Callable[[], None]] = None
    on_require_tx_changed: Optional[Callable[[bool], None]] = None
    on_deadline_enabled_changed: Optional[Callable[[bool], None]] = None
    on_deadline_settings_changed: Optional[Callable[[], None]] = None
    on_save_settings: Optional[Callable[[], None]] = None
    on_load_settings: Optional[Callable[[], None]] = None


def build_settings_view(
    qt_widgets: Any,
    *,
    config: Optional[StudioConfig] = None,
    callbacks: Optional[SettingsActionCallbacks] = None,
) -> Any:
    """Build the settings screen with category tabs and studio pipeline controls."""

    studio_config = config or StudioConfig.default()
    settings_callbacks = callbacks or SettingsActionCallbacks()

    view = qt_widgets.QWidget()
    view.setObjectName(SETTINGS_VIEW_OBJECT_NAME)

    layout = qt_widgets.QVBoxLayout(view)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)

    top_row = qt_widgets.QHBoxLayout()
    back_button = qt_widgets.QPushButton("Back")
    back_button.setObjectName(SETTINGS_BACK_BUTTON_OBJECT_NAME)
    _wire_button(back_button, settings_callbacks.on_back)
    top_row.addWidget(back_button)
    top_row.addStretch(1)
    layout.addLayout(top_row)

    tabs = qt_widgets.QTabWidget()
    tabs.setObjectName(SETTINGS_TAB_WIDGET_OBJECT_NAME)
    tabs.addTab(_build_basic_tab(qt_widgets), "Basic")
    tabs.addTab(_build_advanced_tab(qt_widgets), "Advanced")
    tabs.addTab(
        _build_connectors_tab(qt_widgets, studio_config, settings_callbacks),
        "Connectors",
    )
    tabs.addTab(
        _build_studio_tab(qt_widgets, studio_config, settings_callbacks),
        "Studio",
    )
    layout.addWidget(tabs)

    config_path_label = qt_widgets.QLabel(_config_path_text(studio_config))
    config_path_label.setObjectName(SETTINGS_CONFIG_PATH_LABEL_OBJECT_NAME)
    config_path_label.setWordWrap(True)
    layout.addWidget(config_path_label)

    status_label = qt_widgets.QLabel("Adjust settings, then save a studio config file for rollout.")
    status_label.setObjectName(SETTINGS_STATUS_LABEL_OBJECT_NAME)
    status_label.setWordWrap(True)
    layout.addWidget(status_label)

    actions_row = qt_widgets.QHBoxLayout()
    save_button = qt_widgets.QPushButton("Save Settings")
    save_button.setObjectName(SETTINGS_SAVE_BUTTON_OBJECT_NAME)
    _wire_button(save_button, settings_callbacks.on_save_settings)
    actions_row.addWidget(save_button)

    load_button = qt_widgets.QPushButton("Load Settings")
    load_button.setObjectName(SETTINGS_LOAD_BUTTON_OBJECT_NAME)
    _wire_button(load_button, settings_callbacks.on_load_settings)
    actions_row.addWidget(load_button)
    actions_row.addStretch(1)
    layout.addLayout(actions_row)

    return view


def build_settings_toggle(
    qt_widgets: Any,
    *,
    object_name: str,
    enabled: bool,
    on_changed: Optional[Callable[[bool], None]] = None,
) -> Any:
    """Build a green/gray ON/OFF toggle button."""

    button = qt_widgets.QPushButton(_toggle_label(enabled))
    button.setObjectName(object_name)
    button.setCheckable(True)
    button.setChecked(enabled)
    _apply_toggle_style(button, enabled)

    clicked = getattr(button, "clicked", None)
    connect = getattr(clicked, "connect", None)
    if connect is not None:

        def _handle_clicked() -> None:
            checked = bool(getattr(button, "isChecked", lambda: enabled)())
            button.setText(_toggle_label(checked))
            _apply_toggle_style(button, checked)
            if on_changed is not None:
                on_changed(checked)

        connect(_handle_clicked)

    return button


def build_require_tx_toggle(
    qt_widgets: Any,
    *,
    enabled: bool,
    on_changed: Optional[Callable[[bool], None]] = None,
) -> Any:
    """Build a green/gray toggle button for the .tx pipeline policy."""

    return build_settings_toggle(
        qt_widgets,
        object_name=SETTINGS_REQUIRE_TX_TOGGLE_OBJECT_NAME,
        enabled=enabled,
        on_changed=on_changed,
    )


def read_connectors_from_settings_view(view: Any, qt_widgets: Any) -> ConnectorSettings:
    """Read connector settings currently shown in the settings UI."""

    deadline = _read_deadline_connector_from_view(view, qt_widgets)
    return ConnectorSettings(deadline=deadline)


def update_settings_view(
    view: Any,
    qt_widgets: Any,
    *,
    config: StudioConfig,
    status_message: str = "",
) -> None:
    """Refresh settings controls from the active studio config."""

    toggle = _find_child(view, qt_widgets.QWidget, SETTINGS_REQUIRE_TX_TOGGLE_OBJECT_NAME)
    if toggle is not None:
        set_checked = getattr(toggle, "setChecked", None)
        if set_checked is not None:
            set_checked(config.pipeline.require_tx_derivatives)
        toggle.setText(_toggle_label(config.pipeline.require_tx_derivatives))
        _apply_toggle_style(toggle, config.pipeline.require_tx_derivatives)

    _update_deadline_connector_view(view, qt_widgets, config.connectors.deadline)

    path_label = _find_child(view, qt_widgets.QLabel, SETTINGS_CONFIG_PATH_LABEL_OBJECT_NAME)
    if path_label is not None:
        path_label.setText(_config_path_text(config))

    if status_message:
        status_label = _find_child(view, qt_widgets.QLabel, SETTINGS_STATUS_LABEL_OBJECT_NAME)
        if status_label is not None:
            status_label.setText(status_message)


def _build_basic_tab(qt_widgets: Any) -> Any:
    tab = qt_widgets.QWidget()
    layout = qt_widgets.QVBoxLayout(tab)
    layout.setContentsMargins(8, 8, 8, 8)
    label = qt_widgets.QLabel(
        "Basic plugin preferences will live here (default profile, UI density, scan defaults)."
    )
    label.setWordWrap(True)
    layout.addWidget(label)
    layout.addStretch(1)
    return tab


def _build_advanced_tab(qt_widgets: Any) -> Any:
    tab = qt_widgets.QWidget()
    layout = qt_widgets.QVBoxLayout(tab)
    layout.setContentsMargins(8, 8, 8, 8)
    label = qt_widgets.QLabel(
        "Advanced options will live here (extra rule roots, debug logging, performance caps)."
    )
    label.setWordWrap(True)
    layout.addWidget(label)
    layout.addStretch(1)
    return tab


def _build_connectors_tab(
    qt_widgets: Any,
    config: StudioConfig,
    callbacks: SettingsActionCallbacks,
) -> Any:
    tab = qt_widgets.QWidget()
    layout = qt_widgets.QVBoxLayout(tab)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(8)

    section = qt_widgets.QWidget()
    section.setObjectName(SETTINGS_DEADLINE_SECTION_OBJECT_NAME)
    section_layout = qt_widgets.QVBoxLayout(section)
    section_layout.setContentsMargins(0, 0, 0, 0)
    section_layout.setSpacing(6)

    title = qt_widgets.QLabel("Thinkbox Deadline")
    set_style = getattr(title, "setStyleSheet", None)
    if set_style is not None:
        set_style("font-size: 11pt; font-weight: bold;")
    section_layout.addWidget(title)

    remote_row = qt_widgets.QHBoxLayout()
    set_remote_margins = getattr(remote_row, "setContentsMargins", None)
    if set_remote_margins is not None:
        set_remote_margins(0, 0, 0, 0)
    set_remote_spacing = getattr(remote_row, "setSpacing", None)
    if set_remote_spacing is not None:
        set_remote_spacing(4)
    remote_row.addWidget(qt_widgets.QLabel("Remote Farm"))
    remote_row.addWidget(
        build_settings_toggle(
            qt_widgets,
            object_name=SETTINGS_DEADLINE_ENABLED_TOGGLE_OBJECT_NAME,
            enabled=config.connectors.deadline.enabled,
            on_changed=lambda enabled: _on_deadline_enabled_changed(
                qt_widgets,
                section,
                enabled,
                callbacks,
            ),
        )
    )
    remote_row.addStretch(1)
    section_layout.addLayout(remote_row)

    details = qt_widgets.QWidget()
    _set_fixed_horizontal_size_policy(qt_widgets, details)

    deadline = config.connectors.deadline
    columns_row = qt_widgets.QHBoxLayout()
    set_columns_margins = getattr(columns_row, "setContentsMargins", None)
    if set_columns_margins is not None:
        set_columns_margins(0, 0, 0, 0)
    set_columns_spacing = getattr(columns_row, "setSpacing", None)
    if set_columns_spacing is not None:
        set_columns_spacing(_DEADLINE_COLUMNS_GAP)

    left_column = qt_widgets.QWidget()
    left_column.setObjectName(SETTINGS_DEADLINE_LEFT_COLUMN_OBJECT_NAME)
    _set_fixed_horizontal_size_policy(qt_widgets, left_column)
    left_layout = _create_deadline_grid_layout(qt_widgets, left_column)

    right_column = qt_widgets.QWidget()
    right_column.setObjectName(SETTINGS_DEADLINE_RIGHT_COLUMN_OBJECT_NAME)
    _set_fixed_horizontal_size_policy(qt_widgets, right_column)
    right_layout = _create_deadline_grid_layout(qt_widgets, right_column)

    add_column = getattr(columns_row, "addWidget", None)
    if add_column is not None:
        add_column(left_column)
        add_column(right_column)

    _add_deadline_grid_pair(
        qt_widgets,
        left_layout,
        row=0,
        left_label="Host",
        left_object_name=SETTINGS_DEADLINE_HOST_INPUT_OBJECT_NAME,
        left_value=deadline.web_service_host,
        left_placeholder="10.0.0.5",
        left_width=_DEADLINE_FIELD_HOST_WIDTH,
        right_label="Port",
        right_object_name=SETTINGS_DEADLINE_PORT_INPUT_OBJECT_NAME,
        right_value=str(deadline.web_service_port),
        right_placeholder="8081",
        right_width=_DEADLINE_FIELD_PORT_WIDTH,
        on_changed=callbacks.on_deadline_settings_changed,
    )
    _add_deadline_grid_field(
        qt_widgets,
        left_layout,
        row=1,
        column=0,
        label="Repo",
        object_name=SETTINGS_DEADLINE_REPO_ROOT_INPUT_OBJECT_NAME,
        value=deadline.repo_root,
        placeholder="\\\\farm\\DeadlineRepository10",
        width=_DEADLINE_FIELD_REPO_WIDTH,
        column_span=4,
        on_changed=callbacks.on_deadline_settings_changed,
    )
    _add_deadline_grid_pair(
        qt_widgets,
        left_layout,
        row=2,
        left_label="Timeout",
        left_object_name=SETTINGS_DEADLINE_TIMEOUT_INPUT_OBJECT_NAME,
        left_value=str(deadline.timeout_seconds),
        left_placeholder="30",
        left_width=_DEADLINE_FIELD_TIMEOUT_WIDTH,
        right_label="Profile",
        right_object_name=SETTINGS_DEADLINE_PROFILE_ID_INPUT_OBJECT_NAME,
        right_value=deadline.profile_id,
        right_placeholder="deadline_critical",
        right_width=_DEADLINE_FIELD_PROFILE_WIDTH,
        on_changed=callbacks.on_deadline_settings_changed,
    )
    _add_deadline_grid_field(
        qt_widgets,
        right_layout,
        row=0,
        column=0,
        label="mayapy",
        object_name=SETTINGS_DEADLINE_MAYAPY_INPUT_OBJECT_NAME,
        value=deadline.mayapy,
        placeholder="C:/Program Files/Autodesk/Maya2025/bin/mayapy.exe",
        width=_DEADLINE_FIELD_MAYAPY_WIDTH,
        column_span=4,
        on_changed=callbacks.on_deadline_settings_changed,
    )
    _add_deadline_grid_pair(
        qt_widgets,
        right_layout,
        row=1,
        left_label="Queue",
        left_object_name=SETTINGS_DEADLINE_QUEUE_INPUT_OBJECT_NAME,
        left_value=deadline.queue,
        left_placeholder="",
        left_width=_DEADLINE_FIELD_SMALL_WIDTH,
        right_label="Pool",
        right_object_name=SETTINGS_DEADLINE_POOL_INPUT_OBJECT_NAME,
        right_value=deadline.pool,
        right_placeholder="",
        right_width=_DEADLINE_FIELD_SMALL_WIDTH,
        on_changed=callbacks.on_deadline_settings_changed,
    )
    _add_deadline_grid_pair(
        qt_widgets,
        right_layout,
        row=2,
        left_label="Group",
        left_object_name=SETTINGS_DEADLINE_GROUP_INPUT_OBJECT_NAME,
        left_value=deadline.group,
        left_placeholder="",
        left_width=_DEADLINE_FIELD_SMALL_WIDTH,
        right_label="User",
        right_object_name=SETTINGS_DEADLINE_USER_INPUT_OBJECT_NAME,
        right_value=deadline.user_name,
        right_placeholder="",
        right_width=_DEADLINE_FIELD_SMALL_WIDTH,
        on_changed=callbacks.on_deadline_settings_changed,
    )
    _configure_deadline_grid(qt_widgets, left_layout)
    _configure_deadline_grid(qt_widgets, right_layout)

    details_layout = qt_widgets.QVBoxLayout(details)
    set_details_margins = getattr(details_layout, "setContentsMargins", None)
    if set_details_margins is not None:
        set_details_margins(0, 2, 0, 0)
    add_columns = getattr(details_layout, "addLayout", None)
    if add_columns is not None:
        add_columns(columns_row)

    details_row = qt_widgets.QWidget()
    details_row.setObjectName(SETTINGS_DEADLINE_DETAILS_OBJECT_NAME)
    details_row_layout = qt_widgets.QHBoxLayout(details_row)
    set_row_margins = getattr(details_row_layout, "setContentsMargins", None)
    if set_row_margins is not None:
        set_row_margins(0, 0, 0, 0)
    set_row_spacing = getattr(details_row_layout, "setSpacing", None)
    if set_row_spacing is not None:
        set_row_spacing(0)
    add_details = getattr(details_row_layout, "addWidget", None)
    add_stretch = getattr(details_row_layout, "addStretch", None)
    align_left = _qt_align_left(qt_widgets)
    if add_details is not None:
        if align_left is not None:
            add_details(details, 0, align_left)
        else:
            add_details(details)
    if add_stretch is not None:
        add_stretch(1)
    section_layout.addWidget(details_row)
    _set_deadline_details_visible(details_row, config.connectors.deadline.enabled)

    hint = qt_widgets.QLabel(
        "When Remote Farm is enabled, the Farm tab goes online using these Deadline settings. "
        "When disabled, the Farm tab stays offline until the connector is turned on."
    )
    hint.setWordWrap(True)
    section_layout.addWidget(hint)
    layout.addWidget(section)
    layout.addStretch(1)
    return tab


def _build_studio_tab(
    qt_widgets: Any,
    config: StudioConfig,
    callbacks: SettingsActionCallbacks,
) -> Any:
    tab = qt_widgets.QWidget()
    layout = qt_widgets.QVBoxLayout(tab)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(8)

    pipeline_section = qt_widgets.QWidget()
    pipeline_section.setObjectName(SETTINGS_PIPELINE_SECTION_OBJECT_NAME)
    pipeline_layout = qt_widgets.QVBoxLayout(pipeline_section)
    pipeline_layout.setContentsMargins(0, 0, 0, 0)
    pipeline_layout.setSpacing(4)

    title = qt_widgets.QLabel("Pipeline")
    set_style = getattr(title, "setStyleSheet", None)
    if set_style is not None:
        set_style("font-weight: bold;")
    pipeline_layout.addWidget(title)

    row = qt_widgets.QHBoxLayout()
    row.addWidget(
        qt_widgets.QLabel("Require .tx optimized texture derivatives")
    )
    row.addStretch(1)
    row.addWidget(
        build_require_tx_toggle(
            qt_widgets,
            enabled=config.pipeline.require_tx_derivatives,
            on_changed=callbacks.on_require_tx_changed,
        )
    )
    pipeline_layout.addLayout(row)

    hint = qt_widgets.QLabel(
        "When enabled, validation checks that raster textures have matching .tx files. "
        "Disable for studios that do not bake or use OpenImageIO derivatives."
    )
    hint.setWordWrap(True)
    pipeline_layout.addWidget(hint)
    layout.addWidget(pipeline_section)
    layout.addStretch(1)
    return tab


def _on_deadline_enabled_changed(
    qt_widgets: Any,
    section: Any,
    enabled: bool,
    callbacks: SettingsActionCallbacks,
) -> None:
    details = _find_child(section, qt_widgets.QWidget, SETTINGS_DEADLINE_DETAILS_OBJECT_NAME)
    if details is not None:
        _set_deadline_details_visible(details, enabled)
    if callbacks.on_deadline_enabled_changed is not None:
        callbacks.on_deadline_enabled_changed(enabled)


def _update_deadline_connector_view(
    view: Any,
    qt_widgets: Any,
    deadline: DeadlineConnectorSettings,
) -> None:
    toggle = _find_child(view, qt_widgets.QWidget, SETTINGS_DEADLINE_ENABLED_TOGGLE_OBJECT_NAME)
    if toggle is not None:
        set_checked = getattr(toggle, "setChecked", None)
        if set_checked is not None:
            set_checked(deadline.enabled)
        toggle.setText(_toggle_label(deadline.enabled))
        _apply_toggle_style(toggle, deadline.enabled)

    details = _find_child(view, qt_widgets.QWidget, SETTINGS_DEADLINE_DETAILS_OBJECT_NAME)
    if details is not None:
        _set_deadline_details_visible(details, deadline.enabled)

    _set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_DEADLINE_HOST_INPUT_OBJECT_NAME,
        deadline.web_service_host,
    )
    _set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_DEADLINE_PORT_INPUT_OBJECT_NAME,
        str(deadline.web_service_port),
    )
    _set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_DEADLINE_REPO_ROOT_INPUT_OBJECT_NAME,
        deadline.repo_root,
    )
    _set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_DEADLINE_TIMEOUT_INPUT_OBJECT_NAME,
        str(deadline.timeout_seconds),
    )
    _set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_DEADLINE_PROFILE_ID_INPUT_OBJECT_NAME,
        deadline.profile_id,
    )
    _set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_DEADLINE_MAYAPY_INPUT_OBJECT_NAME,
        deadline.mayapy,
    )
    _set_line_edit_text(view, qt_widgets, SETTINGS_DEADLINE_QUEUE_INPUT_OBJECT_NAME, deadline.queue)
    _set_line_edit_text(view, qt_widgets, SETTINGS_DEADLINE_POOL_INPUT_OBJECT_NAME, deadline.pool)
    _set_line_edit_text(view, qt_widgets, SETTINGS_DEADLINE_GROUP_INPUT_OBJECT_NAME, deadline.group)
    _set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_DEADLINE_USER_INPUT_OBJECT_NAME,
        deadline.user_name,
    )


def _read_deadline_connector_from_view(view: Any, qt_widgets: Any) -> DeadlineConnectorSettings:
    toggle = _find_child(view, qt_widgets.QWidget, SETTINGS_DEADLINE_ENABLED_TOGGLE_OBJECT_NAME)
    enabled = bool(getattr(toggle, "isChecked", lambda: False)()) if toggle is not None else False
    port_text = (
        _line_edit_text(view, qt_widgets, SETTINGS_DEADLINE_PORT_INPUT_OBJECT_NAME) or "8081"
    )
    timeout_text = (
        _line_edit_text(view, qt_widgets, SETTINGS_DEADLINE_TIMEOUT_INPUT_OBJECT_NAME) or "30"
    )
    try:
        port = int(port_text)
    except ValueError:
        port = 8081
    try:
        timeout_seconds = float(timeout_text)
    except ValueError:
        timeout_seconds = 30.0
    return DeadlineConnectorSettings(
        enabled=enabled,
        web_service_host=_line_edit_text(
            view,
            qt_widgets,
            SETTINGS_DEADLINE_HOST_INPUT_OBJECT_NAME,
        ),
        web_service_port=port,
        repo_root=_line_edit_text(view, qt_widgets, SETTINGS_DEADLINE_REPO_ROOT_INPUT_OBJECT_NAME),
        timeout_seconds=timeout_seconds,
        profile_id=_line_edit_text(
            view,
            qt_widgets,
            SETTINGS_DEADLINE_PROFILE_ID_INPUT_OBJECT_NAME,
        ),
        mayapy=_line_edit_text(view, qt_widgets, SETTINGS_DEADLINE_MAYAPY_INPUT_OBJECT_NAME),
        queue=_line_edit_text(view, qt_widgets, SETTINGS_DEADLINE_QUEUE_INPUT_OBJECT_NAME),
        pool=_line_edit_text(view, qt_widgets, SETTINGS_DEADLINE_POOL_INPUT_OBJECT_NAME),
        group=_line_edit_text(view, qt_widgets, SETTINGS_DEADLINE_GROUP_INPUT_OBJECT_NAME),
        user_name=_line_edit_text(view, qt_widgets, SETTINGS_DEADLINE_USER_INPUT_OBJECT_NAME),
    )


def _create_deadline_grid_layout(qt_widgets: Any, parent: Any) -> Any:
    grid_layout = qt_widgets.QGridLayout(parent)
    set_grid_margins = getattr(grid_layout, "setContentsMargins", None)
    if set_grid_margins is not None:
        set_grid_margins(0, 0, 0, 0)
    set_h_spacing = getattr(grid_layout, "setHorizontalSpacing", None)
    if set_h_spacing is not None:
        set_h_spacing(3)
    set_v_spacing = getattr(grid_layout, "setVerticalSpacing", None)
    if set_v_spacing is not None:
        set_v_spacing(2)
    return grid_layout


def _add_deadline_grid_pair(
    qt_widgets: Any,
    grid_layout: Any,
    *,
    row: int,
    left_label: str,
    left_object_name: str,
    left_value: str,
    left_placeholder: str,
    left_width: int,
    right_label: str,
    right_object_name: str,
    right_value: str,
    right_placeholder: str,
    right_width: int,
    on_changed: Optional[Callable[[], None]],
) -> None:
    _add_deadline_grid_field(
        qt_widgets,
        grid_layout,
        row=row,
        column=0,
        label=left_label,
        object_name=left_object_name,
        value=left_value,
        placeholder=left_placeholder,
        width=left_width,
        on_changed=on_changed,
    )
    _add_deadline_grid_field(
        qt_widgets,
        grid_layout,
        row=row,
        column=3,
        label=right_label,
        object_name=right_object_name,
        value=right_value,
        placeholder=right_placeholder,
        width=right_width,
        on_changed=on_changed,
    )


def _add_deadline_grid_field(
    qt_widgets: Any,
    grid_layout: Any,
    *,
    row: int,
    column: int,
    label: str,
    object_name: str,
    value: str,
    placeholder: str,
    width: int,
    on_changed: Optional[Callable[[], None]],
    column_span: int = 1,
) -> None:
    caption = _build_deadline_label(qt_widgets, label)
    field = _build_deadline_line_edit(
        qt_widgets,
        object_name=object_name,
        value=value,
        placeholder=placeholder,
        width=width,
        on_changed=on_changed,
    )
    add_widget = getattr(grid_layout, "addWidget", None)
    if add_widget is None:
        return
    align_right = _qt_align_right_vcenter(qt_widgets)
    align_left = _qt_align_left_vcenter(qt_widgets)
    if column_span > 1:
        if align_right is not None:
            add_widget(caption, row, column, align_right)
        else:
            add_widget(caption, row, column)
        if align_left is not None:
            add_widget(field, row, column + 1, 1, column_span, align_left)
        else:
            add_widget(field, row, column + 1, 1, column_span)
        return
    if align_right is not None:
        add_widget(caption, row, column, align_right)
    else:
        add_widget(caption, row, column)
    if align_left is not None:
        add_widget(field, row, column + 1, align_left)
    else:
        add_widget(field, row, column + 1)


def _build_deadline_label(qt_widgets: Any, text: str) -> Any:
    label = qt_widgets.QLabel(text)
    _set_fixed_horizontal_size_policy(qt_widgets, label)
    set_fixed_width = getattr(label, "setFixedWidth", None)
    if set_fixed_width is not None:
        set_fixed_width(_DEADLINE_LABEL_WIDTH)
    return label


def _build_deadline_line_edit(
    qt_widgets: Any,
    *,
    object_name: str,
    value: str,
    placeholder: str,
    width: int,
    on_changed: Optional[Callable[[], None]],
) -> Any:
    field = qt_widgets.QLineEdit(value)
    field.setObjectName(object_name)
    set_placeholder = getattr(field, "setPlaceholderText", None)
    if set_placeholder is not None and placeholder:
        set_placeholder(placeholder)
    set_fixed_width = getattr(field, "setFixedWidth", None)
    if set_fixed_width is not None:
        set_fixed_width(width)
    _set_fixed_horizontal_size_policy(qt_widgets, field)
    editing_finished = getattr(field, "editingFinished", None)
    connect = getattr(editing_finished, "connect", None)
    if connect is not None and on_changed is not None:
        connect(on_changed)
    return field


def _configure_deadline_grid(qt_widgets: Any, grid_layout: Any) -> None:
    set_column_stretch = getattr(grid_layout, "setColumnStretch", None)
    if set_column_stretch is not None:
        for column in range(5):
            set_column_stretch(column, 0)
    set_column_minimum_width = getattr(grid_layout, "setColumnMinimumWidth", None)
    if set_column_minimum_width is not None:
        set_column_minimum_width(0, _DEADLINE_LABEL_WIDTH)
        set_column_minimum_width(2, _DEADLINE_PAIR_GAP)
        set_column_minimum_width(3, _DEADLINE_LABEL_WIDTH)


def _set_fixed_horizontal_size_policy(qt_widgets: Any, widget: Any) -> None:
    size_policy = getattr(qt_widgets, "QSizePolicy", None)
    set_policy = getattr(widget, "setSizePolicy", None)
    if size_policy is None or set_policy is None:
        return
    fixed = getattr(size_policy, "Fixed", None)
    if fixed is not None:
        set_policy(fixed, fixed)


def _qt_align_left(qt_widgets: Any) -> Any:
    qt = getattr(qt_widgets, "Qt", None)
    if qt is None:
        return None
    return getattr(qt, "AlignLeft", None)


def _qt_align_left_vcenter(qt_widgets: Any) -> Any:
    qt = getattr(qt_widgets, "Qt", None)
    if qt is None:
        return None
    align_left = getattr(qt, "AlignLeft", None)
    align_vcenter = getattr(qt, "AlignVCenter", None)
    if align_left is None or align_vcenter is None:
        return align_left
    return align_left | align_vcenter


def _qt_align_right_vcenter(qt_widgets: Any) -> Any:
    qt = getattr(qt_widgets, "Qt", None)
    if qt is None:
        return None
    align_right = getattr(qt, "AlignRight", None)
    align_vcenter = getattr(qt, "AlignVCenter", None)
    if align_right is None or align_vcenter is None:
        return align_right
    return align_right | align_vcenter


def _set_deadline_details_visible(details: Any, visible: bool) -> None:
    set_visible = getattr(details, "setVisible", None)
    if set_visible is not None:
        set_visible(visible)


def _set_line_edit_text(
    view: Any,
    qt_widgets: Any,
    object_name: str,
    text: str,
) -> None:
    field = _find_child(view, qt_widgets.QLineEdit, object_name)
    if field is None:
        return
    set_text = getattr(field, "setText", None)
    if set_text is not None:
        set_text(text)


def _line_edit_text(view: Any, qt_widgets: Any, object_name: str) -> str:
    field = _find_child(view, qt_widgets.QLineEdit, object_name)
    if field is None:
        return ""
    text_fn = getattr(field, "text", None)
    if text_fn is None:
        return ""
    return str(text_fn()).strip()


def _toggle_label(enabled: bool) -> str:
    return "ON" if enabled else "OFF"


def _apply_toggle_style(button: Any, enabled: bool) -> None:
    set_style = getattr(button, "setStyleSheet", None)
    if set_style is not None:
        set_style(_TOGGLE_ON_STYLE if enabled else _TOGGLE_OFF_STYLE)


def _config_path_text(config: StudioConfig) -> str:
    if config.config_path is None:
        return "Active config: in-session defaults (no file loaded)."
    return f"Active config: {config.config_path}"


def _wire_button(button: Any, callback: Optional[Callable[[], None]]) -> None:
    if callback is None:
        return
    clicked = getattr(button, "clicked", None)
    connect = getattr(clicked, "connect", None)
    if connect is not None:
        connect(callback)


def _find_child(root: Any, widget_type: Any, object_name: str) -> Any | None:
    finder = getattr(root, "findChild", None)
    if finder is not None:
        found = finder(widget_type, object_name)
        if found is not None:
            return found
    stack = [root]
    while stack:
        current = stack.pop()
        if getattr(current, "object_name", None) == object_name:
            return current
        stack.extend(getattr(current, "children", []))
    return None
