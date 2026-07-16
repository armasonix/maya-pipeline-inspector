"""Shared Settings UI helpers for connector notification triggers."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional

from pipeline_inspector.integrations.notification_triggers import CONNECTOR_NOTIFY_EVENTS
from pipeline_inspector.ui.settings_widgets import (
    checkbox_checked,
    set_checkbox_checked,
    set_fixed_horizontal_size_policy,
    wire_checkbox_changed,
    wire_line_edit_finished,
)


def notify_checkbox_object_name(connector_prefix: str, event_id: str) -> str:
    """Return a stable object name for a connector notify-on checkbox."""

    suffix = "".join(part.capitalize() for part in event_id.split("_"))
    return f"pipelineInspectorSettings{connector_prefix}Notify{suffix}Checkbox"


def notify_score_below_input_object_name(connector_prefix: str) -> str:
    return f"pipelineInspectorSettings{connector_prefix}NotifyScoreBelowInput"


def build_notify_trigger_controls(
    qt_widgets: Any,
    *,
    connector_prefix: str,
    notify_on: tuple[str, ...],
    notify_score_below: int | None,
    label_width: int,
    on_settings_changed: Optional[Callable[[], None]] = None,
) -> tuple[Any, Any]:
    """Build notify-on checkboxes and score-threshold field widgets."""

    notify_container = qt_widgets.QWidget()
    notify_layout = qt_widgets.QVBoxLayout(notify_container)
    set_notify_margins = getattr(notify_layout, "setContentsMargins", None)
    if set_notify_margins is not None:
        set_notify_margins(0, 0, 0, 0)
    set_notify_spacing = getattr(notify_layout, "setSpacing", None)
    if set_notify_spacing is not None:
        set_notify_spacing(4)

    notify_row = qt_widgets.QHBoxLayout()
    set_row_margins = getattr(notify_row, "setContentsMargins", None)
    if set_row_margins is not None:
        set_row_margins(0, 0, 0, 0)
    set_row_spacing = getattr(notify_row, "setSpacing", None)
    if set_row_spacing is not None:
        set_row_spacing(8)

    notify_caption = qt_widgets.QLabel("Notify on")
    set_fixed_horizontal_size_policy(qt_widgets, notify_caption)
    set_caption_width = getattr(notify_caption, "setFixedWidth", None)
    if set_caption_width is not None:
        set_caption_width(label_width)
    notify_row.addWidget(notify_caption)

    for event_id, label in CONNECTOR_NOTIFY_EVENTS:
        checkbox = qt_widgets.QCheckBox(label)
        checkbox.setObjectName(notify_checkbox_object_name(connector_prefix, event_id))
        set_checked = getattr(checkbox, "setChecked", None)
        if set_checked is not None:
            set_checked(event_id in notify_on)
        wire_checkbox_changed(checkbox, on_settings_changed)
        notify_row.addWidget(checkbox)
    notify_row.addStretch(1)
    add_notify_layout = getattr(notify_layout, "addLayout", None)
    if add_notify_layout is not None:
        add_notify_layout(notify_row)

    threshold_row = qt_widgets.QHBoxLayout()
    set_threshold_margins = getattr(threshold_row, "setContentsMargins", None)
    if set_threshold_margins is not None:
        set_threshold_margins(0, 0, 0, 0)
    set_threshold_spacing = getattr(threshold_row, "setSpacing", None)
    if set_threshold_spacing is not None:
        set_threshold_spacing(4)

    threshold_caption = qt_widgets.QLabel("Score below")
    set_fixed_horizontal_size_policy(qt_widgets, threshold_caption)
    set_threshold_caption_width = getattr(threshold_caption, "setFixedWidth", None)
    if set_threshold_caption_width is not None:
        set_threshold_caption_width(label_width)
    threshold_row.addWidget(threshold_caption)

    threshold_input = qt_widgets.QLineEdit(
        "" if notify_score_below is None else str(notify_score_below)
    )
    threshold_input.setObjectName(notify_score_below_input_object_name(connector_prefix))
    set_placeholder = getattr(threshold_input, "setPlaceholderText", None)
    if set_placeholder is not None:
        set_placeholder("Disabled")
    set_fixed_width = getattr(threshold_input, "setFixedWidth", None)
    if set_fixed_width is not None:
        set_fixed_width(72)
    wire_line_edit_finished(threshold_input, on_settings_changed)
    threshold_row.addWidget(threshold_input)
    threshold_hint = qt_widgets.QLabel(
        "Send score_below notifications when health score drops under this value."
    )
    threshold_hint.setWordWrap(True)
    threshold_row.addWidget(threshold_hint)
    threshold_row.addStretch(1)
    if add_notify_layout is not None:
        add_notify_layout(threshold_row)

    return notify_container, threshold_input


def read_notify_on_from_view(
    view: Any,
    qt_widgets: Any,
    *,
    connector_prefix: str,
) -> tuple[str, ...]:
    return tuple(
        event_id
        for event_id, _label in CONNECTOR_NOTIFY_EVENTS
        if checkbox_checked(
            view,
            qt_widgets,
            notify_checkbox_object_name(connector_prefix, event_id),
        )
    )


def read_notify_score_below_from_view(
    view: Any,
    qt_widgets: Any,
    *,
    connector_prefix: str,
) -> int | None:
    from pipeline_inspector.ui.settings_widgets import line_edit_text

    raw = line_edit_text(
        view,
        qt_widgets,
        notify_score_below_input_object_name(connector_prefix),
    ).strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def update_notify_trigger_view(
    view: Any,
    qt_widgets: Any,
    *,
    connector_prefix: str,
    notify_on: tuple[str, ...],
    notify_score_below: int | None,
) -> None:
    from pipeline_inspector.ui.settings_widgets import set_line_edit_text

    for event_id, _label in CONNECTOR_NOTIFY_EVENTS:
        set_checkbox_checked(
            view,
            qt_widgets,
            notify_checkbox_object_name(connector_prefix, event_id),
            event_id in notify_on,
        )
    set_line_edit_text(
        view,
        qt_widgets,
        notify_score_below_input_object_name(connector_prefix),
        "" if notify_score_below is None else str(notify_score_below),
    )
