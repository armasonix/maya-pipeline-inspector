"""Farm tab UI for Deadline integration in the Maya panel."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Optional

FARM_TAB_OBJECT_NAME = "pipelineInspectorFarmTab"
FARM_CONNECTION_LABEL_OBJECT_NAME = "pipelineInspectorFarmConnectionLabel"
FARM_SCENE_STATE_LABEL_OBJECT_NAME = "pipelineInspectorFarmSceneStateLabel"
FARM_ELIGIBILITY_LABEL_OBJECT_NAME = "pipelineInspectorFarmEligibilityLabel"
FARM_LAST_REPORT_LABEL_OBJECT_NAME = "pipelineInspectorFarmLastReportLabel"
FARM_LAST_JOB_LABEL_OBJECT_NAME = "pipelineInspectorFarmLastJobLabel"
FARM_STATUS_LABEL_OBJECT_NAME = "pipelineInspectorFarmStatusLabel"
FARM_CONNECTION_STATUS_LABEL_OBJECT_NAME = "pipelineInspectorFarmConnectionStatusLabel"
FARM_CONNECTION_LAMP_OBJECT_NAME = "pipelineInspectorFarmConnectionLamp"
FARM_CONNECTION_STATUS_VALUE_LABEL_OBJECT_NAME = (
    "pipelineInspectorFarmConnectionStatusValueLabel"
)
FARM_REFRESH_CONNECTION_BUTTON_OBJECT_NAME = "pipelineInspectorFarmRefreshConnectionButton"
FARM_RUN_PREFLIGHT_BUTTON_OBJECT_NAME = "pipelineInspectorFarmPreflightButton"
FARM_SUBMIT_BUTTON_OBJECT_NAME = "pipelineInspectorFarmSubmitButton"

@dataclass(frozen=True)
class FarmTabState:
    """Display data for the Farm tab."""

    integration_enabled: bool = True
    api_url: str = "http://localhost:8081"
    connection_status: str = "Unknown"
    connection_reachable: bool = False
    scene_saved: bool = True
    renderer_plugin_loaded: bool = True
    eligibility_decision: str = "unknown"
    eligibility_allowed: bool = False
    last_report_path: str = ""
    last_job_id: str = ""
    status_message: str = "Run Farm Preflight to evaluate deadline_critical readiness."

@dataclass(frozen=True)
class FarmActionCallbacks:
    """Callbacks for Farm tab actions."""

    on_refresh_connection: Optional[Callable[[], None]] = None
    on_run_farm_preflight: Optional[Callable[[], None]] = None
    on_submit_to_farm: Optional[Callable[[], None]] = None

def build_farm_tab(
    qt_widgets: Any,
    callbacks: Optional[FarmActionCallbacks] = None,
    state: Optional[FarmTabState] = None,
) -> Any:
    """Build the Farm tab with Deadline status and submit actions."""

    farm_callbacks = callbacks or FarmActionCallbacks()
    farm_state = state or FarmTabState()
    tab = qt_widgets.QWidget()
    tab.setObjectName(FARM_TAB_OBJECT_NAME)

    layout = qt_widgets.QVBoxLayout(tab)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(6)

    connection_label = qt_widgets.QLabel(_connection_text(farm_state))
    connection_label.setObjectName(FARM_CONNECTION_LABEL_OBJECT_NAME)
    connection_label.setWordWrap(True)
    layout.addWidget(connection_label)

    scene_state_label = qt_widgets.QLabel(_scene_state_text(farm_state))
    scene_state_label.setObjectName(FARM_SCENE_STATE_LABEL_OBJECT_NAME)
    scene_state_label.setWordWrap(True)
    layout.addWidget(scene_state_label)

    eligibility_label = qt_widgets.QLabel(_eligibility_text(farm_state))
    eligibility_label.setObjectName(FARM_ELIGIBILITY_LABEL_OBJECT_NAME)
    eligibility_label.setWordWrap(True)
    layout.addWidget(eligibility_label)

    last_report_label = qt_widgets.QLabel(_last_report_text(farm_state))
    last_report_label.setObjectName(FARM_LAST_REPORT_LABEL_OBJECT_NAME)
    last_report_label.setWordWrap(True)
    layout.addWidget(last_report_label)

    last_job_label = qt_widgets.QLabel(_last_job_text(farm_state))
    last_job_label.setObjectName(FARM_LAST_JOB_LABEL_OBJECT_NAME)
    last_job_label.setWordWrap(True)
    layout.addWidget(last_job_label)

    actions_section = qt_widgets.QWidget()
    actions_section_layout = qt_widgets.QVBoxLayout(actions_section)
    actions_section_layout.setContentsMargins(0, 0, 0, 0)
    actions_section_layout.setSpacing(2)
    status_group = _build_connection_status_group(qt_widgets, farm_state)
    add_status = actions_section_layout.addWidget
    alignment = _qt_align_left(qt_widgets)
    if alignment is not None:
        add_status(status_group, 0, alignment)
    else:
        add_status(status_group)

    buttons_row = qt_widgets.QWidget()
    buttons_layout = qt_widgets.QHBoxLayout(buttons_row)
    buttons_layout.setContentsMargins(0, 0, 0, 0)
    buttons_layout.setSpacing(4)
    buttons_layout.addWidget(
        _farm_button(
            qt_widgets,
            "Refresh Connection",
            FARM_REFRESH_CONNECTION_BUTTON_OBJECT_NAME,
            "Ping the configured Deadline Web Service.",
            farm_callbacks.on_refresh_connection,
        )
    )
    buttons_layout.addWidget(
        _farm_button(
            qt_widgets,
            "Run Farm Preflight",
            FARM_RUN_PREFLIGHT_BUTTON_OBJECT_NAME,
            "Validate the scene with deadline_critical and evaluate farm eligibility.",
            farm_callbacks.on_run_farm_preflight,
        )
    )
    buttons_layout.addWidget(
        _farm_button(
            qt_widgets,
            "Submit to Farm",
            FARM_SUBMIT_BUTTON_OBJECT_NAME,
            (
                "Submit a CommandScript utility job that runs Pipeline Inspector "
                "validation on a worker."
            ),
            farm_callbacks.on_submit_to_farm,
        )
    )
    buttons_layout.addStretch(1)
    actions_section_layout.addWidget(buttons_row)
    layout.addWidget(actions_section)

    status_label = qt_widgets.QLabel(farm_state.status_message)
    status_label.setObjectName(FARM_STATUS_LABEL_OBJECT_NAME)
    status_label.setWordWrap(True)
    layout.addWidget(status_label)
    layout.addStretch(1)
    _update_farm_action_buttons(tab, qt_widgets, farm_state)
    return tab

def update_farm_tab(
    tab_root: Any,
    qt_widgets: Any,
    state: FarmTabState,
) -> None:
    """Refresh Farm tab labels from the latest state."""

    _set_label(tab_root, qt_widgets, FARM_CONNECTION_LABEL_OBJECT_NAME, _connection_text(state))
    _set_label(tab_root, qt_widgets, FARM_SCENE_STATE_LABEL_OBJECT_NAME, _scene_state_text(state))
    _set_label(tab_root, qt_widgets, FARM_ELIGIBILITY_LABEL_OBJECT_NAME, _eligibility_text(state))
    _set_label(tab_root, qt_widgets, FARM_LAST_REPORT_LABEL_OBJECT_NAME, _last_report_text(state))
    _set_label(tab_root, qt_widgets, FARM_LAST_JOB_LABEL_OBJECT_NAME, _last_job_text(state))
    _set_label(tab_root, qt_widgets, FARM_STATUS_LABEL_OBJECT_NAME, state.status_message)
    _update_connection_indicator(tab_root, qt_widgets, state)
    _update_farm_action_buttons(tab_root, qt_widgets, state)

def _build_connection_status_group(qt_widgets: Any, state: FarmTabState) -> Any:
    """Build Status label, colored lamp, and connection status text."""

    group = qt_widgets.QWidget()
    group_layout = qt_widgets.QHBoxLayout(group)
    group_layout.setContentsMargins(0, 0, 8, 0)
    group_layout.setSpacing(4)

    status_caption = qt_widgets.QLabel("Status:")
    status_caption.setObjectName(FARM_CONNECTION_STATUS_LABEL_OBJECT_NAME)
    group_layout.addWidget(status_caption)

    lamp = qt_widgets.QLabel("")
    lamp.setObjectName(FARM_CONNECTION_LAMP_OBJECT_NAME)
    _apply_connection_lamp_style(lamp, state)
    group_layout.addWidget(lamp)

    status_value = qt_widgets.QLabel(_connection_status_value_text(state))
    status_value.setObjectName(FARM_CONNECTION_STATUS_VALUE_LABEL_OBJECT_NAME)
    group_layout.addWidget(status_value)
    group_layout.addStretch(1)
    _set_compact_horizontal(qt_widgets, status_caption)
    _set_compact_horizontal(qt_widgets, status_value)
    return group

def _update_connection_indicator(tab_root: Any, qt_widgets: Any, state: FarmTabState) -> None:
    lamp = _find_child(tab_root, qt_widgets.QLabel, FARM_CONNECTION_LAMP_OBJECT_NAME)
    if lamp is not None:
        _apply_connection_lamp_style(lamp, state)
    _set_label(
        tab_root,
        qt_widgets,
        FARM_CONNECTION_STATUS_VALUE_LABEL_OBJECT_NAME,
        _connection_status_value_text(state),
    )

def _qt_align_left(qt_widgets: Any) -> Any:
    qt = getattr(qt_widgets, "Qt", None)
    if qt is None:
        return None
    return getattr(qt, "AlignLeft", None)

def _set_compact_horizontal(qt_widgets: Any, widget: Any) -> None:
    size_policy = getattr(qt_widgets, "QSizePolicy", None)
    set_policy = getattr(widget, "setSizePolicy", None)
    if size_policy is None or set_policy is None:
        return
    fixed = getattr(size_policy, "Fixed", None)
    if fixed is not None:
        set_policy(fixed, fixed)

def _connection_status_value_text(state: FarmTabState) -> str:
    if not state.integration_enabled:
        return "Offline"
    return "Online" if state.connection_reachable else "Offline"

def _connection_lamp_color(state: FarmTabState) -> str:
    if state.integration_enabled and state.connection_reachable:
        return "#2ecc71"
    return "#e74c3c"

def _apply_connection_lamp_style(lamp: Any, state: FarmTabState) -> None:
    color = _connection_lamp_color(state)
    set_style = getattr(lamp, "setStyleSheet", None)
    if set_style is not None:
        set_style(
            "background-color: "
            f"{color}; border-radius: 7px; min-width: 14px; max-width: 14px; "
            "min-height: 14px; max-height: 14px;"
        )
    set_fixed_size = getattr(lamp, "setFixedSize", None)
    if set_fixed_size is not None:
        set_fixed_size(14, 14)
    set_tooltip = getattr(lamp, "setToolTip", None)
    if set_tooltip is not None:
        set_tooltip(
            f"Deadline Web Service: {_connection_status_value_text(state)} "
            f"({state.connection_status})"
        )

def _connection_text(state: FarmTabState) -> str:
    if not state.integration_enabled:
        return (
            "Thinkbox Deadline: integration disabled "
            "(enable Remote Farm under Settings → Connectors)"
        )
    status = "reachable" if state.connection_reachable else "unreachable"
    return f"Deadline Web Service: {state.api_url} ({status}; {state.connection_status})"

def _scene_state_text(state: FarmTabState) -> str:
    saved = "yes" if state.scene_saved else "no"
    plugin = "loaded" if state.renderer_plugin_loaded else "missing"
    return f"Scene saved: {saved}   Renderer plug-in: {plugin}"

def _eligibility_text(state: FarmTabState) -> str:
    allowed = "yes" if state.eligibility_allowed else "no"
    return f"Farm eligibility: {state.eligibility_decision} (submit allowed: {allowed})"

def _last_report_text(state: FarmTabState) -> str:
    report = state.last_report_path or "none"
    return f"Last farm report: {report}"

def _last_job_text(state: FarmTabState) -> str:
    job_id = state.last_job_id or "none"
    return f"Last Deadline job id: {job_id}"

def _farm_button(
    qt_widgets: Any,
    label: str,
    object_name: str,
    tooltip: str,
    callback: Optional[Callable[[], None]],
) -> Any:
    from pipeline_inspector.ui.main_window import _compact_button

    return _compact_button(qt_widgets, label, object_name, tooltip, callback)

def _update_farm_action_buttons(tab_root: Any, qt_widgets: Any, state: FarmTabState) -> None:
    actions_enabled = state.integration_enabled
    for object_name in (
        FARM_REFRESH_CONNECTION_BUTTON_OBJECT_NAME,
        FARM_RUN_PREFLIGHT_BUTTON_OBJECT_NAME,
        FARM_SUBMIT_BUTTON_OBJECT_NAME,
    ):
        button = _find_child(tab_root, qt_widgets.QPushButton, object_name)
        if button is None:
            continue
        set_enabled = getattr(button, "setEnabled", None)
        if set_enabled is not None:
            set_enabled(actions_enabled)

def _set_label(tab_root: Any, qt_widgets: Any, object_name: str, text: str) -> None:
    widget = _find_child(tab_root, qt_widgets.QLabel, object_name)
    if widget is None:
        return
    set_text = getattr(widget, "setText", None)
    if set_text is not None:
        set_text(text)

def _find_child(root: Any, widget_type: Any, object_name: str) -> Any:
    if root is None:
        return None
    if _widget_object_name(root) == object_name:
        return root
    children_attr = getattr(root, "children", None)
    if children_attr is None:
        children: list[Any] = []
    elif callable(children_attr):
        children = children_attr()
    else:
        children = list(children_attr)
    for child in children:
        if isinstance(child, widget_type) and _widget_object_name(child) == object_name:
            return child
        if hasattr(child, "children"):
            found = _find_child(child, widget_type, object_name)
            if found is not None:
                return found
    find_children = getattr(root, "findChildren", None)
    if find_children is not None:
        matches = find_children(widget_type)
        for match in matches:
            if _widget_object_name(match) == object_name:
                return match
    return None

def _widget_object_name(widget: Any) -> str:
    object_name_fn = getattr(widget, "objectName", None)
    if callable(object_name_fn):
        return str(object_name_fn() or "")
    return str(getattr(widget, "object_name", "") or "")
