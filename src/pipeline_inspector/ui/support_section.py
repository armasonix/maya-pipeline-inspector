"""Support and Roles settings plus readiness requirements for the Studio tab."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Optional

from pipeline_inspector.studio_config import (
    ReadinessCheckRequirements,
    ReadinessSettings,
    ReadinessSupportContacts,
    StudioConfig,
)
from pipeline_inspector.ui.settings_widgets import (
    find_child,
    line_edit_text,
    qt_align_left_vcenter,
    set_fixed_horizontal_size_policy,
    set_line_edit_text,
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

_FIELD_WIDTH = 292


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
        "One requirement per line. Software versions use PRODUCT=VERSION "
        "(for example maya=2025 or mtoa=5.4.0)."
    )
    checks_intro.setWordWrap(True)
    layout.addWidget(checks_intro)

    layout.addWidget(
        _labeled_plain_text_row(
            qt_widgets,
            "Maya plugins",
            _build_plain_text_input(
                qt_widgets,
                SETTINGS_READINESS_PLUGINS_INPUT_OBJECT_NAME,
                _lines(readiness.checks.maya_plugins),
                "mtoa\nvrayformaya",
                on_settings_changed,
            ),
        )
    )
    layout.addWidget(
        _labeled_plain_text_row(
            qt_widgets,
            "Mapped drives",
            _build_plain_text_input(
                qt_widgets,
                SETTINGS_READINESS_DRIVES_INPUT_OBJECT_NAME,
                _lines(readiness.checks.mapped_drives),
                "Z:\nY:",
                on_settings_changed,
            ),
        )
    )
    layout.addWidget(
        _labeled_plain_text_row(
            qt_widgets,
            "Env vars",
            _build_plain_text_input(
                qt_widgets,
                SETTINGS_READINESS_ENV_VARS_INPUT_OBJECT_NAME,
                _lines(readiness.checks.env_vars),
                "PIPELINE_ROOT\nSTUDIO_TEXTURE_ROOT",
                on_settings_changed,
            ),
        )
    )
    layout.addWidget(
        _labeled_plain_text_row(
            qt_widgets,
            "Network paths",
            _build_plain_text_input(
                qt_widgets,
                SETTINGS_READINESS_NETWORK_PATHS_INPUT_OBJECT_NAME,
                _lines(readiness.checks.network_paths),
                "\\\\farm\\textures",
                on_settings_changed,
            ),
        )
    )
    layout.addWidget(
        _labeled_plain_text_row(
            qt_widgets,
            "Software versions",
            _build_plain_text_input(
                qt_widgets,
                SETTINGS_READINESS_SOFTWARE_VERSIONS_INPUT_OBJECT_NAME,
                _software_version_lines(readiness.checks.software_versions),
                "maya=2025",
                on_settings_changed,
            ),
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
            software_versions=parse_software_version_lines(
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
    _set_plain_text(
        find_child(
            view,
            _plain_text_widget_type(qt_widgets),
            SETTINGS_READINESS_PLUGINS_INPUT_OBJECT_NAME,
        ),
        _lines(readiness.checks.maya_plugins),
    )
    _set_plain_text(
        find_child(
            view,
            _plain_text_widget_type(qt_widgets),
            SETTINGS_READINESS_DRIVES_INPUT_OBJECT_NAME,
        ),
        _lines(readiness.checks.mapped_drives),
    )
    _set_plain_text(
        find_child(
            view,
            _plain_text_widget_type(qt_widgets),
            SETTINGS_READINESS_ENV_VARS_INPUT_OBJECT_NAME,
        ),
        _lines(readiness.checks.env_vars),
    )
    _set_plain_text(
        find_child(
            view,
            _plain_text_widget_type(qt_widgets),
            SETTINGS_READINESS_NETWORK_PATHS_INPUT_OBJECT_NAME,
        ),
        _lines(readiness.checks.network_paths),
    )
    _set_plain_text(
        find_child(
            view,
            _plain_text_widget_type(qt_widgets),
            SETTINGS_READINESS_SOFTWARE_VERSIONS_INPUT_OBJECT_NAME,
        ),
        _software_version_lines(readiness.checks.software_versions),
    )


def parse_software_version_lines(text: str) -> dict[str, str]:
    """Parse PRODUCT=VERSION lines from the settings UI."""

    versions: dict[str, str] = {}
    for line in text.replace("\r\n", "\n").split("\n"):
        entry = line.strip()
        if not entry or "=" not in entry:
            continue
        product, version = entry.split("=", 1)
        product_text = product.strip()
        version_text = version.strip()
        if product_text and version_text:
            versions[product_text] = version_text
    return versions


def _lines(values: Mapping[str, str] | tuple[str, ...]) -> str:
    if isinstance(values, Mapping):
        return _software_version_lines(values)
    return "\n".join(values)


def _software_version_lines(versions: Mapping[str, str]) -> str:
    return "\n".join(f"{product}={version}" for product, version in versions.items())


def _section_title(qt_widgets: Any, text: str) -> Any:
    label = qt_widgets.QLabel(text)
    set_bold = getattr(label, "setStyleSheet", None)
    if set_bold is not None:
        set_bold("font-weight: 600;")
    return label


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


def _labeled_plain_text_row(qt_widgets: Any, label: str, field: Any) -> Any:
    row = qt_widgets.QWidget()
    row_layout = qt_widgets.QVBoxLayout(row)
    row_layout.setContentsMargins(0, 0, 0, 0)
    row_layout.setSpacing(2)
    row_layout.addWidget(qt_widgets.QLabel(label))
    row_layout.addWidget(field)
    return row


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
) -> Any:
    plain_text_class = _plain_text_widget_type(qt_widgets)
    widget = plain_text_class()
    widget.setObjectName(object_name)
    _set_plain_text(widget, value)
    set_placeholder = getattr(widget, "setPlaceholderText", None)
    if set_placeholder is not None:
        set_placeholder(placeholder)
    wire_plain_text_changed(widget, on_settings_changed)
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
