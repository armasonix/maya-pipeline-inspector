"""Shared Qt widget helpers for the settings screen."""
from __future__ import annotations

import contextlib
from collections.abc import Callable
from typing import Any, Optional

_TOGGLE_STYLE_BASE = (
    "min-width: 52px; min-height: 24px; padding: 3px 10px; border-radius: 7px; "
    "font-weight: bold; font-size: 11px; margin: 0px;"
)
_TOGGLE_OFF_STYLE = (
    "QPushButton { background-color: #4a4a4a; color: #d0d0d0; border: 1px solid #666; "
    f"{_TOGGLE_STYLE_BASE} }}"
)
_TOGGLE_ON_STYLE = (
    "QPushButton { background-color: #2ecc71; color: #102010; border: 1px solid #27ae60; "
    f"{_TOGGLE_STYLE_BASE} }}"
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
    _apply_toggle_size_policy(qt_widgets, button)

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


def _apply_toggle_size_policy(qt_widgets: Any, button: Any) -> None:
    """Keep toggles compact without hard-clipping label text in Maya."""

    _ = qt_widgets
    set_min_width = getattr(button, "setMinimumWidth", None)
    if set_min_width is not None:
        set_min_width(52)
    set_min_height = getattr(button, "setMinimumHeight", None)
    if set_min_height is not None:
        set_min_height(24)


def wire_button(button: Any, callback: Optional[Callable[[], None]]) -> None:
    if callback is None:
        return
    clicked = getattr(button, "clicked", None)
    connect = getattr(clicked, "connect", None)
    if connect is not None:
        connect(callback)


_ACTIVE_MAYA_MODAL_DIALOGS: dict[str, Any] = {}


def configure_maya_modal_dialog(
    dialog: Any,
    qt_widgets: Any,
) -> None:
    """Prepare a top-level native window suitable for Maya modal dialogs."""

    qt_namespace = getattr(qt_widgets, "Qt", None)
    if qt_namespace is None:
        return

    window_flag = getattr(qt_namespace, "Window", None)
    dialog_flag = getattr(qt_namespace, "Dialog", None)
    title_hint = getattr(qt_namespace, "WindowTitleHint", None)
    close_hint = getattr(qt_namespace, "WindowCloseButtonHint", None)
    stay_on_top_hint = getattr(qt_namespace, "WindowStaysOnTopHint", None)
    set_window_flags = getattr(dialog, "setWindowFlags", None)
    if set_window_flags is None:
        return

    base_flag = window_flag if window_flag is not None else dialog_flag
    if base_flag is None:
        return

    flags = base_flag
    if title_hint is not None and isinstance(flags, int) and isinstance(title_hint, int):
        flags |= title_hint
    if close_hint is not None and isinstance(flags, int) and isinstance(close_hint, int):
        flags |= close_hint
    if stay_on_top_hint is not None and isinstance(flags, int) and isinstance(
        stay_on_top_hint, int
    ):
        flags |= stay_on_top_hint
    set_window_flags(flags)

    application_modal = getattr(qt_namespace, "ApplicationModal", None)
    set_modality = getattr(dialog, "setWindowModality", None)
    if application_modal is not None and set_modality is not None:
        set_modality(application_modal)

    delete_on_close = getattr(qt_namespace, "WA_DeleteOnClose", None)
    set_attribute = getattr(dialog, "setAttribute", None)
    if delete_on_close is not None and set_attribute is not None:
        set_attribute(delete_on_close, True)


def try_reactivate_modal_dialog(singleton_key: str) -> bool:
    """Raise an already-visible modal dialog registered under ``singleton_key``."""

    existing = _ACTIVE_MAYA_MODAL_DIALOGS.get(singleton_key)
    if existing is None or not _dialog_is_visible(existing):
        return False

    _raise_dialog(existing)
    return True


def _dialog_is_visible(dialog: Any) -> bool:
    is_visible = getattr(dialog, "isVisible", None)
    if is_visible is None:
        return False
    return bool(is_visible())


def _raise_dialog(dialog: Any) -> None:
    raise_dialog = getattr(dialog, "raise_", None)
    if raise_dialog is not None:
        raise_dialog()
    activate = getattr(dialog, "activateWindow", None)
    if activate is not None:
        activate()


def show_modal_dialog(
    dialog: Any,
    qt_widgets: Any,
    *,
    parent: Any | None = None,
    singleton_key: str | None = None,
) -> None:
    """Show a modal dialog as a Maya-safe top-level window."""

    if singleton_key:
        existing = _ACTIVE_MAYA_MODAL_DIALOGS.get(singleton_key)
        if existing is not None and _dialog_is_visible(existing):
            _raise_dialog(existing)
            return

    configure_maya_modal_dialog(dialog, qt_widgets)

    if singleton_key:
        _ACTIVE_MAYA_MODAL_DIALOGS[singleton_key] = dialog

    exec_fn = getattr(dialog, "exec_", None) or getattr(dialog, "exec", None)
    try:
        if exec_fn is not None:
            exec_fn()
        else:
            show = getattr(dialog, "show", None)
            if show is not None:
                show()
            _raise_dialog(dialog)
    finally:
        if singleton_key:
            _ACTIVE_MAYA_MODAL_DIALOGS.pop(singleton_key, None)


def show_maya_information_dialog(
    qt_widgets: Any,
    title: str,
    message: str,
    *,
    singleton_key: str | None = None,
) -> None:
    """Display a Maya-safe information message box."""

    message_box_cls = getattr(qt_widgets, "QMessageBox", None)
    if message_box_cls is None:
        return

    information_icon = getattr(message_box_cls, "Information", None)
    ok_button = getattr(message_box_cls, "Ok", None)
    if information_icon is None or ok_button is None:
        information = getattr(message_box_cls, "information", None)
        if information is not None:
            information(None, title, message)
        return

    dialog = message_box_cls(information_icon, title, message, ok_button)
    show_modal_dialog(dialog, qt_widgets, singleton_key=singleton_key)


_COMBO_CALLBACK_SLOT = "_pipeline_inspector_combo_callback"


def wire_combo_changed(combo: Any, callback: Optional[Callable[[], None]]) -> None:
    if callback is None:
        return

    def _invoke_callback(*_args: Any) -> None:
        callback()

    previous_slots = getattr(combo, _COMBO_CALLBACK_SLOT, None)
    if not isinstance(previous_slots, dict):
        previous_slots = {}

    connected_slots: dict[str, Any] = {}
    for signal_name in ("currentIndexChanged",):
        signal = getattr(combo, signal_name, None)
        connect = getattr(signal, "connect", None)
        disconnect = getattr(signal, "disconnect", None)
        previous_handler = previous_slots.get(signal_name)
        if disconnect is not None and previous_handler is not None:
            with contextlib.suppress(TypeError, RuntimeError):
                disconnect(previous_handler)
        if connect is not None:
            connect(_invoke_callback)
            connected_slots[signal_name] = _invoke_callback

    setattr(combo, _COMBO_CALLBACK_SLOT, connected_slots)


def wire_line_edit_finished(field: Any, callback: Optional[Callable[[], None]]) -> None:
    if callback is None:
        return
    for signal_name in ("editingFinished", "textChanged"):
        signal = getattr(field, signal_name, None)
        connect = getattr(signal, "connect", None)
        if connect is not None:
            connect(lambda *_args: callback())


def wire_checkbox_changed(checkbox: Any, callback: Optional[Callable[[], None]]) -> None:
    if callback is None:
        return
    state_changed = getattr(checkbox, "stateChanged", None)
    connect = getattr(state_changed, "connect", None)
    if connect is not None:
        connect(lambda *_args: callback())


def apply_password_echo_mode(qt_widgets: Any, field: Any) -> None:
    """Mask secret connector fields in the settings UI."""

    line_edit_class = getattr(qt_widgets, "QLineEdit", None)
    if line_edit_class is None:
        return
    password_mode = getattr(line_edit_class, "Password", None)
    set_echo_mode = getattr(field, "setEchoMode", None)
    if password_mode is not None and set_echo_mode is not None:
        set_echo_mode(password_mode)


def checkbox_checked(view: Any, qt_widgets: Any, object_name: str) -> bool:
    checkbox = find_child(view, qt_widgets.QCheckBox, object_name)
    if checkbox is None:
        return False
    is_checked = getattr(checkbox, "isChecked", None)
    if is_checked is None:
        return False
    return bool(is_checked())


def set_checkbox_checked(
    view: Any,
    qt_widgets: Any,
    object_name: str,
    checked: bool,
) -> None:
    checkbox = find_child(view, qt_widgets.QCheckBox, object_name)
    if checkbox is None:
        return
    set_checked = getattr(checkbox, "setChecked", None)
    if set_checked is not None:
        set_checked(checked)


def widget_has_focus(widget: Any) -> bool:
    """Return True when a Qt widget currently owns keyboard focus."""

    has_focus = getattr(widget, "hasFocus", None)
    if has_focus is None:
        return False
    return bool(has_focus())


def wire_plain_text_changed(field: Any, callback: Optional[Callable[[], None]]) -> None:
    if callback is None:
        return
    for signal_name in ("textChanged", "plainTextChanged"):
        changed = getattr(field, signal_name, None)
        connect = getattr(changed, "connect", None)
        if connect is not None:
            connect(lambda *_args: callback())
            return


def _widget_object_name(widget: Any) -> str:
    object_name_fn = getattr(widget, "objectName", None)
    if callable(object_name_fn):
        return str(object_name_fn() or "")
    return str(getattr(widget, "object_name", "") or "")


def _widget_children(widget: Any) -> list[Any]:
    children_attr = getattr(widget, "children", None)
    if callable(children_attr):
        try:
            return list(children_attr())
        except TypeError:
            return []
    if isinstance(children_attr, list):
        return children_attr
    return []


def find_child(root: Any, widget_type: Any, object_name: str) -> Any | None:
    if not object_name:
        return None

    finder = getattr(root, "findChild", None)
    if finder is not None:
        found = finder(widget_type, object_name)
        if found is not None:
            return found

    find_children = getattr(root, "findChildren", None)
    if find_children is not None:
        try:
            matches = find_children(widget_type, object_name)
            if matches:
                return matches[0]
        except TypeError:
            pass
        try:
            for child in find_children(widget_type):
                if _widget_object_name(child) == object_name:
                    return child
        except TypeError:
            pass

    stack = [root]
    while stack:
        current = stack.pop()
        if _widget_object_name(current) == object_name:
            return current
        stack.extend(_widget_children(current))
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


def line_edit_text(
    view: Any,
    qt_widgets: Any,
    object_name: str,
    *,
    fallback: str | None = None,
) -> str:
    field = find_child(view, qt_widgets.QLineEdit, object_name)
    if field is None:
        return "" if fallback is None else fallback
    text_fn = getattr(field, "text", None)
    if text_fn is None:
        return "" if fallback is None else fallback
    return str(text_fn()).strip()


def configure_compact_line_edit(qt_widgets: Any, field: Any, width: int) -> None:
    set_fixed_width = getattr(field, "setFixedWidth", None)
    if set_fixed_width is not None:
        set_fixed_width(width)
    set_fixed_horizontal_size_policy(qt_widgets, field)


def build_labeled_toggle_row(
    qt_widgets: Any,
    label_text: str,
    toggle: Any,
    *,
    label_width: int = 228,
    gap: int = 12,
) -> Any:
    """Build a left-aligned label + toggle row used across settings tabs."""

    host = qt_widgets.QWidget()
    grid = qt_widgets.QGridLayout(host)
    set_grid_margins = getattr(grid, "setContentsMargins", None)
    if set_grid_margins is not None:
        set_grid_margins(0, 0, 0, 0)
    set_horizontal_spacing = getattr(grid, "setHorizontalSpacing", None)
    if set_horizontal_spacing is not None:
        set_horizontal_spacing(gap)
    set_vertical_spacing = getattr(grid, "setVerticalSpacing", None)
    if set_vertical_spacing is not None:
        set_vertical_spacing(0)

    caption = qt_widgets.QLabel(label_text)
    set_word_wrap = getattr(caption, "setWordWrap", None)
    if set_word_wrap is not None:
        set_word_wrap(True)
    set_fixed_width = getattr(caption, "setFixedWidth", None)
    if set_fixed_width is not None:
        set_fixed_width(label_width)
    set_fixed_horizontal_size_policy(qt_widgets, caption)

    toggle_alignment = qt_align_left_vcenter(qt_widgets)
    add_widget = getattr(grid, "addWidget", None)
    if add_widget is not None:
        add_widget(caption, 0, 0)
        if toggle_alignment is not None:
            add_widget(toggle, 0, 1, toggle_alignment)
        else:
            add_widget(toggle, 0, 1)

    set_column_stretch = getattr(grid, "setColumnStretch", None)
    if set_column_stretch is not None:
        set_column_stretch(0, 0)
        set_column_stretch(1, 0)
        set_column_stretch(2, 1)
    return host


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
