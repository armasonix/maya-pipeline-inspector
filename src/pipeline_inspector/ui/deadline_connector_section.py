"""Thinkbox Deadline connector section for the Settings Connectors tab."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any, Optional

from pipeline_inspector.studio_config import (
    ConnectorSettings,
    DeadlineConnectorSettings,
    StudioConfig,
)
from pipeline_inspector.ui.settings_widgets import (
    build_settings_toggle,
    find_child,
    line_edit_text,
    qt_align_left,
    qt_align_left_vcenter,
    qt_align_right_vcenter,
    set_fixed_horizontal_size_policy,
    set_line_edit_text,
)

SETTINGS_DEADLINE_SECTION_OBJECT_NAME = "pipelineInspectorSettingsDeadlineSection"
SETTINGS_DEADLINE_ENABLED_TOGGLE_OBJECT_NAME = "pipelineInspectorSettingsDeadlineEnabledToggle"
SETTINGS_DEADLINE_DETAILS_OBJECT_NAME = "pipelineInspectorSettingsDeadlineDetails"
SETTINGS_DEADLINE_LEFT_COLUMN_OBJECT_NAME = "pipelineInspectorSettingsDeadlineLeftColumn"
SETTINGS_DEADLINE_RIGHT_COLUMN_OBJECT_NAME = "pipelineInspectorSettingsDeadlineRightColumn"
SETTINGS_DEADLINE_HOST_INPUT_OBJECT_NAME = "pipelineInspectorSettingsDeadlineHostInput"
SETTINGS_DEADLINE_PORT_INPUT_OBJECT_NAME = "pipelineInspectorSettingsDeadlinePortInput"
SETTINGS_DEADLINE_REPO_ROOT_INPUT_OBJECT_NAME = "pipelineInspectorSettingsDeadlineRepoRootInput"
SETTINGS_DEADLINE_TIMEOUT_INPUT_OBJECT_NAME = "pipelineInspectorSettingsDeadlineTimeoutInput"
SETTINGS_DEADLINE_PROFILE_ID_INPUT_OBJECT_NAME = (
    "pipelineInspectorSettingsDeadlineProfileIdInput"
)
SETTINGS_DEADLINE_MAYAPY_INPUT_OBJECT_NAME = "pipelineInspectorSettingsDeadlineMayapyInput"
SETTINGS_DEADLINE_QUEUE_INPUT_OBJECT_NAME = "pipelineInspectorSettingsDeadlineQueueInput"
SETTINGS_DEADLINE_POOL_INPUT_OBJECT_NAME = "pipelineInspectorSettingsDeadlinePoolInput"
SETTINGS_DEADLINE_GROUP_INPUT_OBJECT_NAME = "pipelineInspectorSettingsDeadlineGroupInput"
SETTINGS_DEADLINE_USER_INPUT_OBJECT_NAME = "pipelineInspectorSettingsDeadlineUserInput"

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

def build_deadline_connector_section(
    qt_widgets: Any,
    config: StudioConfig,
    *,
    on_enabled_changed: Optional[Callable[[bool], None]] = None,
    on_settings_changed: Optional[Callable[[], None]] = None,
) -> Any:
    """Build the Deadline connector section widget."""

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
                on_enabled_changed,
            ),
        )
    )
    remote_row.addStretch(1)
    section_layout.addLayout(remote_row)

    details = qt_widgets.QWidget()
    set_fixed_horizontal_size_policy(qt_widgets, details)

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
    set_fixed_horizontal_size_policy(qt_widgets, left_column)
    left_layout = _create_deadline_grid_layout(qt_widgets, left_column)

    right_column = qt_widgets.QWidget()
    right_column.setObjectName(SETTINGS_DEADLINE_RIGHT_COLUMN_OBJECT_NAME)
    set_fixed_horizontal_size_policy(qt_widgets, right_column)
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
        on_changed=on_settings_changed,
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
        on_changed=on_settings_changed,
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
        on_changed=on_settings_changed,
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
        on_changed=on_settings_changed,
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
        on_changed=on_settings_changed,
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
        on_changed=on_settings_changed,
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
    align_left = qt_align_left(qt_widgets)
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
        "Submission qualities live on the Farm tab; render presets live under Settings → Render."
    )
    hint.setWordWrap(True)
    section_layout.addWidget(hint)
    return section

def read_deadline_connector_from_view(
    view: Any,
    qt_widgets: Any,
    *,
    base: DeadlineConnectorSettings | None = None,
) -> DeadlineConnectorSettings:
    current = base or DeadlineConnectorSettings()
    toggle = find_child(view, qt_widgets.QWidget, SETTINGS_DEADLINE_ENABLED_TOGGLE_OBJECT_NAME)
    enabled = bool(getattr(toggle, "isChecked", lambda: False)()) if toggle is not None else False
    port_text = line_edit_text(view, qt_widgets, SETTINGS_DEADLINE_PORT_INPUT_OBJECT_NAME) or "8081"
    timeout_text = (
        line_edit_text(view, qt_widgets, SETTINGS_DEADLINE_TIMEOUT_INPUT_OBJECT_NAME) or "30"
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
        web_service_host=line_edit_text(view, qt_widgets, SETTINGS_DEADLINE_HOST_INPUT_OBJECT_NAME),
        web_service_port=port,
        repo_root=line_edit_text(view, qt_widgets, SETTINGS_DEADLINE_REPO_ROOT_INPUT_OBJECT_NAME),
        timeout_seconds=timeout_seconds,
        profile_id=line_edit_text(
            view,
            qt_widgets,
            SETTINGS_DEADLINE_PROFILE_ID_INPUT_OBJECT_NAME,
        ),
        mayapy=line_edit_text(view, qt_widgets, SETTINGS_DEADLINE_MAYAPY_INPUT_OBJECT_NAME),
        queue=line_edit_text(view, qt_widgets, SETTINGS_DEADLINE_QUEUE_INPUT_OBJECT_NAME),
        pool=line_edit_text(view, qt_widgets, SETTINGS_DEADLINE_POOL_INPUT_OBJECT_NAME),
        group=line_edit_text(view, qt_widgets, SETTINGS_DEADLINE_GROUP_INPUT_OBJECT_NAME),
        user_name=line_edit_text(view, qt_widgets, SETTINGS_DEADLINE_USER_INPUT_OBJECT_NAME),
        allow_draft_submit=current.allow_draft_submit,
        allow_production_submit=current.allow_production_submit,
    )

def update_deadline_connector_view(
    view: Any,
    qt_widgets: Any,
    deadline: DeadlineConnectorSettings,
) -> None:
    toggle = find_child(view, qt_widgets.QWidget, SETTINGS_DEADLINE_ENABLED_TOGGLE_OBJECT_NAME)
    if toggle is not None:
        from pipeline_inspector.ui.settings_widgets import apply_toggle_style, toggle_label

        set_checked = getattr(toggle, "setChecked", None)
        if set_checked is not None:
            set_checked(deadline.enabled)
        toggle.setText(toggle_label(deadline.enabled))
        apply_toggle_style(toggle, deadline.enabled)

    details = find_child(view, qt_widgets.QWidget, SETTINGS_DEADLINE_DETAILS_OBJECT_NAME)
    if details is not None:
        _set_deadline_details_visible(details, deadline.enabled)

    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_DEADLINE_HOST_INPUT_OBJECT_NAME,
        deadline.web_service_host,
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_DEADLINE_PORT_INPUT_OBJECT_NAME,
        str(deadline.web_service_port),
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_DEADLINE_REPO_ROOT_INPUT_OBJECT_NAME,
        deadline.repo_root,
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_DEADLINE_TIMEOUT_INPUT_OBJECT_NAME,
        str(deadline.timeout_seconds),
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_DEADLINE_PROFILE_ID_INPUT_OBJECT_NAME,
        deadline.profile_id,
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_DEADLINE_MAYAPY_INPUT_OBJECT_NAME,
        deadline.mayapy,
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_DEADLINE_QUEUE_INPUT_OBJECT_NAME,
        deadline.queue,
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_DEADLINE_POOL_INPUT_OBJECT_NAME,
        deadline.pool,
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_DEADLINE_GROUP_INPUT_OBJECT_NAME,
        deadline.group,
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_DEADLINE_USER_INPUT_OBJECT_NAME,
        deadline.user_name,
    )

def get_deadline_settings(connectors: ConnectorSettings) -> DeadlineConnectorSettings:
    return connectors.deadline

def apply_deadline_settings(
    connectors: ConnectorSettings,
    settings: DeadlineConnectorSettings,
) -> ConnectorSettings:
    return replace(connectors, deadline=settings)

def _on_deadline_enabled_changed(
    qt_widgets: Any,
    section: Any,
    enabled: bool,
    on_enabled_changed: Optional[Callable[[bool], None]],
) -> None:
    details = find_child(section, qt_widgets.QWidget, SETTINGS_DEADLINE_DETAILS_OBJECT_NAME)
    if details is not None:
        _set_deadline_details_visible(details, enabled)
    if on_enabled_changed is not None:
        on_enabled_changed(enabled)

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
    align_right = qt_align_right_vcenter(qt_widgets)
    align_left = qt_align_left_vcenter(qt_widgets)
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
    set_fixed_horizontal_size_policy(qt_widgets, label)
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
    set_fixed_horizontal_size_policy(qt_widgets, field)
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

def _set_deadline_details_visible(details: Any, visible: bool) -> None:
    set_visible = getattr(details, "setVisible", None)
    if set_visible is not None:
        set_visible(visible)
