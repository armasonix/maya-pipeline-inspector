"""Advanced user preferences section for the Settings Advanced tab."""
from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, Optional

from shader_health.ui.settings_widgets import (
    build_settings_toggle,
    find_child,
    set_line_edit_text,
    wire_button,
    wire_line_edit_finished,
    wire_plain_text_changed,
)
from shader_health.user_config import DEFAULT_MAX_ISSUES_DISPLAYED, UserPreferences

SETTINGS_ADVANCED_SECTION_OBJECT_NAME = "shaderHealthInspectorSettingsAdvancedSection"
SETTINGS_EXTRA_RULE_PATHS_INPUT_OBJECT_NAME = (
    "shaderHealthInspectorSettingsExtraRulePathsInput"
)
SETTINGS_DEBUG_LOGGING_TOGGLE_OBJECT_NAME = "shaderHealthInspectorSettingsDebugLoggingToggle"
SETTINGS_MAX_ISSUES_INPUT_OBJECT_NAME = "shaderHealthInspectorSettingsMaxIssuesInput"
SETTINGS_MAYAPY_PATH_INPUT_OBJECT_NAME = "shaderHealthInspectorSettingsMayapyPathInput"
SETTINGS_RULE_EDITOR_BUTTON_OBJECT_NAME = "shaderHealthInspectorSettingsRuleEditorButton"
SETTINGS_BROWSE_RULES_BUTTON_OBJECT_NAME = SETTINGS_RULE_EDITOR_BUTTON_OBJECT_NAME
SETTINGS_NEW_RULE_WIZARD_BUTTON_OBJECT_NAME = "shaderHealthInspectorSettingsNewRuleWizardButton"

_MIN_MAX_ISSUES_DISPLAYED = 1
_MAX_MAX_ISSUES_DISPLAYED = 5000


def build_advanced_settings_section(
    qt_widgets: Any,
    user_config: UserPreferences,
    *,
    on_preferences_changed: Optional[Callable[[], None]] = None,
    on_open_rule_editor: Optional[Callable[[], None]] = None,
    on_open_new_rule_wizard: Optional[Callable[[], None]] = None,
    on_open_rule_browser: Optional[Callable[[], None]] = None,
) -> Any:
    """Build the Advanced settings tab content."""

    section = qt_widgets.QWidget()
    section.setObjectName(SETTINGS_ADVANCED_SECTION_OBJECT_NAME)
    layout = qt_widgets.QVBoxLayout(section)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    intro = qt_widgets.QLabel(
        "TD-oriented options stored in user.json. Extra rule roots append packs at "
        "validation time; mayapy override is used for local headless tooling."
    )
    intro.setWordWrap(True)
    layout.addWidget(intro)

    form = qt_widgets.QFormLayout()
    set_form_margins = getattr(form, "setContentsMargins", None)
    if set_form_margins is not None:
        set_form_margins(0, 0, 0, 0)

    extra_paths_input = _build_plain_text_input(
        qt_widgets,
        object_name=SETTINGS_EXTRA_RULE_PATHS_INPUT_OBJECT_NAME,
        text=_format_extra_rule_paths(user_config.extra_rule_paths),
        placeholder="D:/show/rules/custom\n//farm/share/td_rules",
        tooltip="One folder or rule JSON path per line. Paths append to packaged rules.",
    )
    wire_plain_text_changed(extra_paths_input, on_preferences_changed)
    form.addRow("Extra rule roots", extra_paths_input)

    rule_editor_callback = on_open_rule_editor or on_open_rule_browser
    rule_editor_button = qt_widgets.QPushButton("Open Rule Editor…")
    rule_editor_button.setObjectName(SETTINGS_RULE_EDITOR_BUTTON_OBJECT_NAME)
    rule_editor_button.setToolTip(
        "Open the Rule Editor to browse packaged rules and save safe session overrides."
    )
    wire_button(rule_editor_button, rule_editor_callback)
    form.addRow("Rule Editor", rule_editor_button)

    new_rule_button = qt_widgets.QPushButton("New Rule…")
    new_rule_button.setObjectName(SETTINGS_NEW_RULE_WIZARD_BUTTON_OBJECT_NAME)
    new_rule_button.setToolTip(
        "Create a JSON rule draft from a starter template with validate_rules.py checks."
    )
    wire_button(new_rule_button, on_open_new_rule_wizard)
    form.addRow("Rule authoring", new_rule_button)

    debug_row = qt_widgets.QHBoxLayout()
    debug_row.addWidget(qt_widgets.QLabel("Enable verbose shader_health logging"))
    debug_row.addStretch(1)
    debug_toggle = build_settings_toggle(
        qt_widgets,
        object_name=SETTINGS_DEBUG_LOGGING_TOGGLE_OBJECT_NAME,
        enabled=user_config.debug_logging,
        on_changed=lambda _checked: on_preferences_changed() if on_preferences_changed else None,
    )
    debug_row.addWidget(debug_toggle)
    form.addRow("Debug logging", _wrap_layout_widget(qt_widgets, debug_row))

    max_issues_input = qt_widgets.QLineEdit()
    max_issues_input.setObjectName(SETTINGS_MAX_ISSUES_INPUT_OBJECT_NAME)
    max_issues_input.setText(str(user_config.max_issues_displayed))
    max_issues_input.setPlaceholderText(str(DEFAULT_MAX_ISSUES_DISPLAYED))
    max_issues_input.setToolTip(
        "Maximum failed issues shown in the Validate table after filtering."
    )
    wire_line_edit_finished(max_issues_input, on_preferences_changed)
    form.addRow("Max issues displayed", max_issues_input)

    mayapy_input = qt_widgets.QLineEdit()
    mayapy_input.setObjectName(SETTINGS_MAYAPY_PATH_INPUT_OBJECT_NAME)
    mayapy_input.setText(user_config.mayapy_path)
    mayapy_input.setPlaceholderText("C:/Program Files/Autodesk/Maya2025/bin/mayapy.exe")
    mayapy_input.setToolTip(
        "Optional local mayapy.exe override for headless validation on this machine."
    )
    wire_line_edit_finished(mayapy_input, on_preferences_changed)
    form.addRow("Local mayapy path", mayapy_input)

    layout.addLayout(form)
    layout.addStretch(1)
    return section


def read_advanced_user_preferences_from_view(
    view: Any,
    qt_widgets: Any,
    *,
    base: UserPreferences | None = None,
) -> UserPreferences:
    """Read Advanced tab fields into a UserPreferences object."""

    current = base or UserPreferences.default()
    extra_paths_input = find_child(
        view,
        _plain_text_widget_type(qt_widgets),
        SETTINGS_EXTRA_RULE_PATHS_INPUT_OBJECT_NAME,
    )
    max_issues_input = find_child(
        view,
        qt_widgets.QLineEdit,
        SETTINGS_MAX_ISSUES_INPUT_OBJECT_NAME,
    )
    mayapy_input = find_child(
        view,
        qt_widgets.QLineEdit,
        SETTINGS_MAYAPY_PATH_INPUT_OBJECT_NAME,
    )
    debug_toggle = find_child(
        view,
        qt_widgets.QWidget,
        SETTINGS_DEBUG_LOGGING_TOGGLE_OBJECT_NAME,
    )

    max_issues_text = ""
    if max_issues_input is not None:
        text_fn = getattr(max_issues_input, "text", None)
        if text_fn is not None:
            max_issues_text = str(text_fn())
    mayapy_text = ""
    if mayapy_input is not None:
        text_fn = getattr(mayapy_input, "text", None)
        if text_fn is not None:
            mayapy_text = str(text_fn()).strip()

    return current.with_updates(
        extra_rule_paths=parse_extra_rule_paths(_plain_text(extra_paths_input)),
        debug_logging=_toggle_checked(debug_toggle),
        max_issues_displayed=parse_max_issues_displayed(max_issues_text),
        mayapy_path=mayapy_text,
    )


def update_advanced_settings_view(
    view: Any,
    qt_widgets: Any,
    user_config: UserPreferences,
) -> None:
    """Refresh Advanced tab controls from user preferences."""

    extra_paths_input = find_child(
        view,
        _plain_text_widget_type(qt_widgets),
        SETTINGS_EXTRA_RULE_PATHS_INPUT_OBJECT_NAME,
    )
    _set_plain_text(extra_paths_input, _format_extra_rule_paths(user_config.extra_rule_paths))

    debug_toggle = find_child(
        view,
        qt_widgets.QWidget,
        SETTINGS_DEBUG_LOGGING_TOGGLE_OBJECT_NAME,
    )
    if debug_toggle is not None:
        set_checked = getattr(debug_toggle, "setChecked", None)
        if set_checked is not None:
            set_checked(user_config.debug_logging)
        set_text = getattr(debug_toggle, "setText", None)
        if set_text is not None:
            from shader_health.ui.settings_widgets import apply_toggle_style, toggle_label

            set_text(toggle_label(user_config.debug_logging))
            apply_toggle_style(debug_toggle, user_config.debug_logging)

    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_MAX_ISSUES_INPUT_OBJECT_NAME,
        str(user_config.max_issues_displayed),
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_MAYAPY_PATH_INPUT_OBJECT_NAME,
        user_config.mayapy_path,
    )


def parse_extra_rule_paths(text: str) -> tuple[str, ...]:
    """Parse newline-separated extra rule roots from the Advanced tab."""

    paths: list[str] = []
    for line in text.replace("\r\n", "\n").split("\n"):
        normalized = line.strip()
        if normalized:
            paths.append(normalized)
    return tuple(paths)


def parse_max_issues_displayed(
    text: str,
    *,
    default: int = DEFAULT_MAX_ISSUES_DISPLAYED,
) -> int:
    """Parse and clamp the max issues displayed preference."""

    normalized = str(text or "").strip()
    if not normalized:
        return default
    try:
        value = int(normalized)
    except ValueError:
        return default
    return max(_MIN_MAX_ISSUES_DISPLAYED, min(value, _MAX_MAX_ISSUES_DISPLAYED))


def _format_extra_rule_paths(paths: Iterable[str]) -> str:
    return "\n".join(path.strip() for path in paths if path.strip())


def _build_plain_text_input(
    qt_widgets: Any,
    *,
    object_name: str,
    text: str,
    placeholder: str,
    tooltip: str,
) -> Any:
    plain_text_class = _plain_text_widget_type(qt_widgets)
    field = plain_text_class()
    field.setObjectName(object_name)
    set_plain = getattr(field, "setPlainText", None)
    if set_plain is not None:
        set_plain(text)
    set_placeholder = getattr(field, "setPlaceholderText", None)
    if set_placeholder is not None:
        set_placeholder(placeholder)
    field.setToolTip(tooltip)
    return field


def _plain_text_widget_type(qt_widgets: Any) -> Any:
    plain_text_edit = getattr(qt_widgets, "QPlainTextEdit", None)
    if plain_text_edit is not None:
        return plain_text_edit
    return qt_widgets.QTextEdit


def _plain_text(widget: Any | None) -> str:
    if widget is None:
        return ""
    plain_text_fn = getattr(widget, "toPlainText", None)
    if plain_text_fn is not None:
        return str(plain_text_fn())
    text_fn = getattr(widget, "text", None)
    if text_fn is None:
        return ""
    return str(text_fn())


def _set_plain_text(widget: Any | None, text: str) -> None:
    if widget is None:
        return
    set_plain = getattr(widget, "setPlainText", None)
    if set_plain is not None:
        set_plain(text)
        return
    set_text = getattr(widget, "setText", None)
    if set_text is not None:
        set_text(text)


def _toggle_checked(toggle: Any | None) -> bool:
    if toggle is None:
        return False
    is_checked = getattr(toggle, "isChecked", None)
    if is_checked is None:
        return False
    return bool(is_checked())


def _wrap_layout_widget(qt_widgets: Any, layout: Any) -> Any:
    host = qt_widgets.QWidget()
    host.setLayout(layout)
    return host
