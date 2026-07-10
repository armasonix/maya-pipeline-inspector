"""Shared Qt widget helpers for the settings screen."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional

_TOGGLE_OFF_STYLE = (
    "QPushButton { background-color: #4a4a4a; color: #d0d0d0; border: 1px solid #666; "
    "padding: 4px 14px; border-radius: 10px; font-weight: bold; }"
)
_TOGGLE_ON_STYLE = (
    "QPushButton { background-color: #2ecc71; color: #102010; border: 1px solid #27ae60; "
    "padding: 4px 14px; border-radius: 10px; font-weight: bold; }"
)


def build_settings_toggle(
    qt_widgets: Any,
    *,
    object_name: str,
    enabled: bool,
    on_changed: Optional[Callable[[bool], None]] = None,
) -> Any:
    """Build a green/gray ON/OFF toggle button."""

    button = qt_widgets.QPushButton(toggle_label(enabled))
    button.setObjectName(object_name)
    button.setCheckable(True)
    button.setChecked(enabled)
    apply_toggle_style(button, enabled)

    clicked = getattr(button, "clicked", None)
    connect = getattr(clicked, "connect", None)
    if connect is not None:

        def _handle_clicked() -> None:
            checked = bool(getattr(button, "isChecked", lambda: enabled)())
            button.setText(toggle_label(checked))
            apply_toggle_style(button, checked)
            if on_changed is not None:
                on_changed(checked)

        connect(_handle_clicked)

    return button


def toggle_label(enabled: bool) -> str:
    return "ON" if enabled else "OFF"


def apply_toggle_style(button: Any, enabled: bool) -> None:
    set_style = getattr(button, "setStyleSheet", None)
    if set_style is not None:
        set_style(_TOGGLE_ON_STYLE if enabled else _TOGGLE_OFF_STYLE)


def wire_button(button: Any, callback: Optional[Callable[[], None]]) -> None:
    if callback is None:
        return
    clicked = getattr(button, "clicked", None)
    connect = getattr(clicked, "connect", None)
    if connect is not None:
        connect(callback)


def wire_combo_changed(combo: Any, callback: Optional[Callable[[], None]]) -> None:
    if callback is None:
        return
    changed = getattr(combo, "currentIndexChanged", None)
    connect = getattr(changed, "connect", None)
    if connect is not None:
        connect(lambda _index: callback())


def wire_line_edit_finished(field: Any, callback: Optional[Callable[[], None]]) -> None:
    if callback is None:
        return
    finished = getattr(field, "editingFinished", None)
    connect = getattr(finished, "connect", None)
    if connect is not None:
        connect(callback)


def wire_plain_text_changed(field: Any, callback: Optional[Callable[[], None]]) -> None:
    if callback is None:
        return
    for signal_name in ("textChanged", "plainTextChanged"):
        changed = getattr(field, signal_name, None)
        connect = getattr(changed, "connect", None)
        if connect is not None:
            connect(lambda *_args: callback())
            return


def find_child(root: Any, widget_type: Any, object_name: str) -> Any | None:
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


def set_line_edit_text(
    view: Any,
    qt_widgets: Any,
    object_name: str,
    text: str,
) -> None:
    field = find_child(view, qt_widgets.QLineEdit, object_name)
    if field is None:
        return
    set_text = getattr(field, "setText", None)
    if set_text is not None:
        set_text(text)


def line_edit_text(view: Any, qt_widgets: Any, object_name: str) -> str:
    field = find_child(view, qt_widgets.QLineEdit, object_name)
    if field is None:
        return ""
    text_fn = getattr(field, "text", None)
    if text_fn is None:
        return ""
    return str(text_fn()).strip()


def set_fixed_horizontal_size_policy(qt_widgets: Any, widget: Any) -> None:
    size_policy = getattr(qt_widgets, "QSizePolicy", None)
    set_policy = getattr(widget, "setSizePolicy", None)
    if size_policy is None or set_policy is None:
        return
    fixed = getattr(size_policy, "Fixed", None)
    if fixed is not None:
        set_policy(fixed, fixed)


def qt_align_left(qt_widgets: Any) -> Any:
    qt = getattr(qt_widgets, "Qt", None)
    if qt is None:
        return None
    return getattr(qt, "AlignLeft", None)


def qt_align_left_vcenter(qt_widgets: Any) -> Any:
    qt = getattr(qt_widgets, "Qt", None)
    if qt is None:
        return None
    align_left = getattr(qt, "AlignLeft", None)
    align_vcenter = getattr(qt, "AlignVCenter", None)
    if align_left is None or align_vcenter is None:
        return align_left
    return align_left | align_vcenter


def qt_align_right_vcenter(qt_widgets: Any) -> Any:
    qt = getattr(qt_widgets, "Qt", None)
    if qt is None:
        return None
    align_right = getattr(qt, "AlignRight", None)
    align_vcenter = getattr(qt, "AlignVCenter", None)
    if align_right is None or align_vcenter is None:
        return align_right
    return align_right | align_vcenter
