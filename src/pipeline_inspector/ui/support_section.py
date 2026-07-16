"""Support and Roles settings plus readiness requirements for the Studio tab."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional

from pipeline_inspector.studio_config import (
    ReadinessCheckRequirements,
    ReadinessSettings,
    ReadinessSupportContacts,
    SoftwareVersionRequirement,
    StudioConfig,
    parse_software_version_requirements,
)
from pipeline_inspector.ui.settings_widgets import (
    configure_plain_text_placeholder_field,
    find_child,
    line_edit_text,
    qt_align_left_vcenter,
    refresh_plain_text_placeholder,
    set_fixed_horizontal_size_policy,
    set_line_edit_text,
    widget_has_focus,
    wire_line_edit_finished,
    wire_plain_text_changed,
)
from pipeline_inspector.ui.studio_policy_section import parse_profile_id_list

SETTINGS_SUPPORT_SECTION_OBJECT_NAME = "pipelineInspectorSettingsSupportSection"
SETTINGS_SYSADMIN_CHAT_ID_INPUT_OBJECT_NAME = (
    "pipelineInspectorSettingsSysadminChatIdInput"
)
SETTINGS_SUPPORT_CHAT_ID_INPUT_OBJECT_NAME = (
    "pipelineInspectorSettingsSupportChatIdInput"
)
SETTINGS_READINESS_PLUGINS_INPUT_OBJECT_NAME = (
    "pipelineInspectorSettingsReadinessPluginsInput"
)
SETTINGS_READINESS_DRIVES_INPUT_OBJECT_NAME = (
    "pipelineInspectorSettingsReadinessDrivesInput"
)
SETTINGS_READINESS_ENV_VARS_INPUT_OBJECT_NAME = (
    "pipelineInspectorSettingsReadinessEnvVarsInput"
)
SETTINGS_READINESS_NETWORK_PATHS_INPUT_OBJECT_NAME = (
    "pipelineInspectorSettingsReadinessNetworkPathsInput"
)
SETTINGS_READINESS_SOFTWARE_VERSIONS_INPUT_OBJECT_NAME = (
    "pipelineInspectorSettingsReadinessSoftwareVersionsInput"
)
SETTINGS_READINESS_CHECKS_ROW_OBJECT_NAME = "pipelineInspectorSettingsReadinessChecksRow"

_FIELD_WIDTH = 146
_READINESS_FIELD_WIDTH = 120
_PLAIN_TEXT_WIDTH = 146
_READINESS_PLAIN_TEXT_WIDTH = _READINESS_FIELD_WIDTH
_PLAIN_TEXT_HEIGHT = 56



def build_support_and_roles_section(
    qt_widgets: Any,
    config: StudioConfig,
    *,
    on_settings_changed: Optional[Callable[[], None]] = None,
) -> Any:
    """Build Support and Roles plus readiness requirement controls."""

    readiness = config.readiness
    section = qt_widgets.QWidget()
    section.setObjectName(SETTINGS_SUPPORT_SECTION_OBJECT_NAME)
    layout = qt_widgets.QVBoxLayout(section)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    layout.addWidget(_section_title(qt_widgets, "Support and Roles"))
    intro = qt_widgets.QLabel(
        "Telegram chat IDs for machine readiness escalation. "
        "Reports reuse the studio Telegram bot token from Connectors."
    )
    intro.setWordWrap(True)
    layout.addWidget(intro)

    sysadmin_input = qt_widgets.QLineEdit(readiness.support.sysadmin_telegram_chat_id)
    sysadmin_input.setObjectName(SETTINGS_SYSADMIN_CHAT_ID_INPUT_OBJECT_NAME)
    sysadmin_input.setPlaceholderText("-1001234567890")
    _configure_line_edit(qt_widgets, sysadmin_input)
    wire_line_edit_finished(sysadmin_input, on_settings_changed)
    layout.addWidget(_labeled_field_row(qt_widgets, "Sysadmin chat ID", sysadmin_input))

    support_input = qt_widgets.QLineEdit(readiness.support.support_telegram_chat_id)
    support_input.setObjectName(SETTINGS_SUPPORT_CHAT_ID_INPUT_OBJECT_NAME)
    support_input.setPlaceholderText("-1009876543210")
    _configure_line_edit(qt_widgets, support_input)
    wire_line_edit_finished(support_input, on_settings_changed)
    layout.addWidget(_labeled_field_row(qt_widgets, "Support chat ID", support_input))

    layout.addWidget(_section_title(qt_widgets, "Readiness checks"))
    checks_intro = qt_widgets.QLabel(
        "One requirement per line. Repeat a product to require multiple installed "
        "versions (for example maya=2024 and maya=2025). Software versions use "
        "PRODUCT=VERSION (for example maya=2025 or mtoa=5.4.0)."
    )
    checks_intro.setWordWrap(True)
    layout.addWidget(checks_intro)

    layout.addWidget(
        _build_readiness_checks_row(
            qt_widgets,
            readiness.checks,
            on_settings_changed=on_settings_changed,
        )
    )
    return section


def read_readiness_from_view(
    view: Any,
    qt_widgets: Any,
    *,
    base: ReadinessSettings,
) -> ReadinessSettings:
    """Read readiness settings from the Studio tab."""

    return ReadinessSettings(
        checks=ReadinessCheckRequirements(
            maya_plugins=parse_profile_id_list(
                _plain_text(
                    find_child(
                        view,
                        _plain_text_widget_type(qt_widgets),
                        SETTINGS_READINESS_PLUGINS_INPUT_OBJECT_NAME,
                    )
                )
            ),
            mapped_drives=parse_profile_id_list(
                _plain_text(
                    find_child(
                        view,
                        _plain_text_widget_type(qt_widgets),
                        SETTINGS_READINESS_DRIVES_INPUT_OBJECT_NAME,
                    )
                )
            ),
            env_vars=parse_profile_id_list(
                _plain_text(
                    find_child(
                        view,
                        _plain_text_widget_type(qt_widgets),
                        SETTINGS_READINESS_ENV_VARS_INPUT_OBJECT_NAME,
                    )
                )
            ),
            network_paths=parse_profile_id_list(
                _plain_text(
                    find_child(
                        view,
                        _plain_text_widget_type(qt_widgets),
                        SETTINGS_READINESS_NETWORK_PATHS_INPUT_OBJECT_NAME,
                    )
                )
            ),
            software_version_requirements=parse_software_version_requirements(
                _plain_text(
                    find_child(
                        view,
                        _plain_text_widget_type(qt_widgets),
                        SETTINGS_READINESS_SOFTWARE_VERSIONS_INPUT_OBJECT_NAME,
                    )
                )
            ),
        ),
        support=ReadinessSupportContacts(
            sysadmin_telegram_chat_id=line_edit_text(
                view,
                qt_widgets,
                SETTINGS_SYSADMIN_CHAT_ID_INPUT_OBJECT_NAME,
                fallback=base.support.sysadmin_telegram_chat_id,
            ),
            support_telegram_chat_id=line_edit_text(
                view,
                qt_widgets,
                SETTINGS_SUPPORT_CHAT_ID_INPUT_OBJECT_NAME,
                fallback=base.support.support_telegram_chat_id,
            ),
        ),
    )


def update_support_and_roles_view(
    view: Any,
    qt_widgets: Any,
    readiness: ReadinessSettings,
) -> None:
    """Refresh Support and Roles controls from studio config."""

    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_SYSADMIN_CHAT_ID_INPUT_OBJECT_NAME,
        readiness.support.sysadmin_telegram_chat_id,
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_SUPPORT_CHAT_ID_INPUT_OBJECT_NAME,
        readiness.support.support_telegram_chat_id,
    )
    _set_plain_text_if_unfocused(
        find_child(
            view,
            _plain_text_widget_type(qt_widgets),
            SETTINGS_READINESS_PLUGINS_INPUT_OBJECT_NAME,
        ),
        _lines(readiness.checks.maya_plugins),
        field_name="maya_plugins",
        qt_widgets=qt_widgets,
    )
    _set_plain_text_if_unfocused(
        find_child(
            view,
            _plain_text_widget_type(qt_widgets),
            SETTINGS_READINESS_DRIVES_INPUT_OBJECT_NAME,
        ),
        _lines(readiness.checks.mapped_drives),
        field_name="mapped_drives",
        qt_widgets=qt_widgets,
    )
    _set_plain_text_if_unfocused(
        find_child(
            view,
            _plain_text_widget_type(qt_widgets),
            SETTINGS_READINESS_ENV_VARS_INPUT_OBJECT_NAME,
        ),
        _lines(readiness.checks.env_vars),
        field_name="env_vars",
        qt_widgets=qt_widgets,
    )
    _set_plain_text_if_unfocused(
        find_child(
            view,
            _plain_text_widget_type(qt_widgets),
            SETTINGS_READINESS_NETWORK_PATHS_INPUT_OBJECT_NAME,
        ),
        _lines(readiness.checks.network_paths),
        field_name="network_paths",
        qt_widgets=qt_widgets,
    )
    _set_plain_text_if_unfocused(
        find_child(
            view,
            _plain_text_widget_type(qt_widgets),
            SETTINGS_READINESS_SOFTWARE_VERSIONS_INPUT_OBJECT_NAME,
        ),
        _software_version_lines(readiness.checks.software_version_requirements),
        field_name="software_versions",
        qt_widgets=qt_widgets,
    )


def parse_software_version_lines(text: str) -> tuple[SoftwareVersionRequirement, ...]:
    """Parse PRODUCT=VERSION lines from the settings UI."""

    return parse_software_version_requirements(text)


def _lines(values: tuple[str, ...] | tuple[SoftwareVersionRequirement, ...]) -> str:
    if values and isinstance(values[0], SoftwareVersionRequirement):
        return _software_version_lines(values)  # type: ignore[arg-type]
    return "\n".join(values)  # type: ignore[arg-type]


def _software_version_lines(
    requirements: tuple[SoftwareVersionRequirement, ...],
) -> str:
    return "\n".join(
        f"{requirement.product}={requirement.version}" for requirement in requirements
    )


def _section_title(qt_widgets: Any, text: str) -> Any:
    label = qt_widgets.QLabel(text)
    set_style = getattr(label, "setStyleSheet", None)
    if set_style is not None:
        set_style("font-size: 11pt; font-weight: bold;")
    set_fixed_horizontal_size_policy(qt_widgets, label)
    return label


def _build_readiness_checks_row(
    qt_widgets: Any,
    checks: ReadinessCheckRequirements,
    *,
    on_settings_changed: Optional[Callable[[], None]] = None,
) -> Any:
    """Lay out readiness requirement editors left-to-right in one row."""

    row_host = qt_widgets.QWidget()
    row_host.setObjectName(SETTINGS_READINESS_CHECKS_ROW_OBJECT_NAME)
    row_layout = qt_widgets.QHBoxLayout(row_host)
    set_margins = getattr(row_layout, "setContentsMargins", None)
    if set_margins is not None:
        set_margins(0, 0, 0, 0)
    set_spacing = getattr(row_layout, "setSpacing", None)
    if set_spacing is not None:
        set_spacing(8)

    field_specs = (
        (
            "Maya plugins",
            SETTINGS_READINESS_PLUGINS_INPUT_OBJECT_NAME,
            _lines(checks.maya_plugins),
            "mtoa\nvrayformaya",
        ),
        (
            "Mapped drives",
            SETTINGS_READINESS_DRIVES_INPUT_OBJECT_NAME,
            _lines(checks.mapped_drives),
            "Z:\nY:",
        ),
        (
            "Env vars",
            SETTINGS_READINESS_ENV_VARS_INPUT_OBJECT_NAME,
            _lines(checks.env_vars),
            "PIPELINE_ROOT\nSTUDIO_TEXTURE_ROOT",
        ),
        (
            "Network paths",
            SETTINGS_READINESS_NETWORK_PATHS_INPUT_OBJECT_NAME,
            _lines(checks.network_paths),
            r"\\farm\textures",
        ),
        (
            "Software versions",
            SETTINGS_READINESS_SOFTWARE_VERSIONS_INPUT_OBJECT_NAME,
            _software_version_lines(checks.software_version_requirements),
            "maya=2025",
        ),
    )
    for label, object_name, value, placeholder in field_specs:
        field = _build_plain_text_input(
            qt_widgets,
            object_name,
            value,
            placeholder,
            on_settings_changed,
            width=_READINESS_PLAIN_TEXT_WIDTH,
        )
        row_layout.addWidget(_labeled_plain_text_column(qt_widgets, label, field))

    add_stretch = getattr(row_layout, "addStretch", None)
    if add_stretch is not None:
        add_stretch(1)

    return row_host


def _labeled_plain_text_column(qt_widgets: Any, label: str, field: Any) -> Any:
    column = qt_widgets.QWidget()
    column_layout = qt_widgets.QVBoxLayout(column)
    set_margins = getattr(column_layout, "setContentsMargins", None)
    if set_margins is not None:
        set_margins(0, 0, 0, 0)
    set_spacing = getattr(column_layout, "setSpacing", None)
    if set_spacing is not None:
        set_spacing(2)
    column_layout.addWidget(qt_widgets.QLabel(label))
    column_layout.addWidget(field)
    return column


def _labeled_field_row(qt_widgets: Any, label: str, field: Any) -> Any:
    row = qt_widgets.QHBoxLayout()
    set_margins = getattr(row, "setContentsMargins", None)
    if set_margins is not None:
        set_margins(0, 0, 0, 0)
    set_spacing = getattr(row, "setSpacing", None)
    if set_spacing is not None:
        set_spacing(8)
    caption = qt_widgets.QLabel(label)
    alignment = qt_align_left_vcenter(qt_widgets)
    if alignment is not None:
        row.addWidget(caption, 0, alignment)
        row.addWidget(field, 0, alignment)
    else:
        row.addWidget(caption)
        row.addWidget(field)
    row.addStretch(1)
    host = qt_widgets.QWidget()
    host.setLayout(row)
    return host


def _configure_line_edit(qt_widgets: Any, field: Any) -> None:
    set_fixed_width = getattr(field, "setFixedWidth", None)
    if set_fixed_width is not None:
        set_fixed_width(_FIELD_WIDTH)
    set_fixed_horizontal_size_policy(qt_widgets, field)


def _build_plain_text_input(
    qt_widgets: Any,
    object_name: str,
    value: str,
    placeholder: str,
    on_settings_changed: Optional[Callable[[], None]],
    *,
    width: int = _PLAIN_TEXT_WIDTH,
) -> Any:
    plain_text_class = _plain_text_widget_type(qt_widgets)
    widget = plain_text_class()
    widget.setObjectName(object_name)
    configure_plain_text_placeholder_field(
        qt_widgets,
        widget,
        value=value,
        placeholder=placeholder,
    )
    set_fixed_width = getattr(widget, "setFixedWidth", None)
    if set_fixed_width is not None:
        set_fixed_width(width)
    set_fixed_height = getattr(widget, "setFixedHeight", None)
    if set_fixed_height is not None:
        set_fixed_height(_PLAIN_TEXT_HEIGHT)
    set_fixed_horizontal_size_policy(qt_widgets, widget)

    def _on_plain_text_changed() -> None:
        if on_settings_changed is not None:
            on_settings_changed()

    wire_plain_text_changed(widget, _on_plain_text_changed)
    return widget


def _plain_text_widget_type(qt_widgets: Any) -> Any:
    plain_text = getattr(qt_widgets, "QPlainTextEdit", None)
    if plain_text is not None:
        return plain_text
    return qt_widgets.QTextEdit


def _plain_text(widget: Any | None) -> str:
    if widget is None:
        return ""
    plain_text = getattr(widget, "toPlainText", None)
    if plain_text is not None:
        return str(plain_text() or "")
    text = getattr(widget, "text", None)
    if text is not None:
        return str(text() or "")
    return ""


def _set_plain_text_if_unfocused(
    widget: Any | None,
    text: str,
    *,
    field_name: str,
    qt_widgets: Any | None = None,
) -> None:
    """Apply plain text only when the field is not being edited."""

    has_focus = widget_has_focus(widget) if widget is not None else False
    current_text = _plain_text(widget)
    skip_focus = has_focus
    skip_unchanged = current_text == text
    if skip_focus or skip_unchanged:
        return
    _set_plain_text(widget, text)
    if not text and qt_widgets is not None:
        refresh_plain_text_placeholder(qt_widgets, widget)


def _set_plain_text(widget: Any | None, text: str) -> None:
    if widget is None:
        return
    if not text:
        clear = getattr(widget, "clear", None)
        if clear is not None:
            clear()
            return
    set_plain = getattr(widget, "setPlainText", None)
    if set_plain is not None:
        set_plain(text)
        return
    set_text = getattr(widget, "setText", None)
    if set_text is not None:
        set_text(text)
