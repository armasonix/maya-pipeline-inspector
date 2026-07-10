"""Studio Environment network paths section for the Settings tab."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Optional

from shader_health.studio_config import StudioConfig, StudioEnvironmentSettings
from shader_health.ui.settings_widgets import (
    find_child,
    line_edit_text,
    qt_align_left_vcenter,
    qt_align_right_vcenter,
    set_fixed_horizontal_size_policy,
    set_line_edit_text,
    wire_line_edit_finished,
    wire_plain_text_changed,
)

SETTINGS_STUDIO_ENVIRONMENT_SECTION_OBJECT_NAME = (
    "shaderHealthInspectorSettingsStudioEnvironmentSection"
)
SETTINGS_STUDIO_ENVIRONMENT_GRID_OBJECT_NAME = (
    "shaderHealthInspectorSettingsStudioEnvironmentGrid"
)
SETTINGS_STUDIO_ENVIRONMENT_LEFT_COLUMN_OBJECT_NAME = (
    "shaderHealthInspectorSettingsStudioEnvironmentLeftColumn"
)
SETTINGS_STUDIO_ENVIRONMENT_RIGHT_COLUMN_OBJECT_NAME = (
    "shaderHealthInspectorSettingsStudioEnvironmentRightColumn"
)
SETTINGS_TEXTURE_ROOT_INPUT_OBJECT_NAME = "shaderHealthInspectorSettingsTextureRootInput"
SETTINGS_ASSET_ROOT_INPUT_OBJECT_NAME = "shaderHealthInspectorSettingsAssetRootInput"
SETTINGS_CACHE_ROOT_INPUT_OBJECT_NAME = "shaderHealthInspectorSettingsCacheRootInput"
SETTINGS_RENDER_ROOT_INPUT_OBJECT_NAME = "shaderHealthInspectorSettingsRenderRootInput"
SETTINGS_VARIABLE_ALIASES_INPUT_OBJECT_NAME = (
    "shaderHealthInspectorSettingsVariableAliasesInput"
)

_LABEL_WIDTH = 44
_PAIR_GAP = 12
_ROOT_FIELD_WIDTH = 292
_SMALL_ROOT_FIELD_WIDTH = 292
_COLUMNS_GAP = 14


def build_studio_environment_section(
    qt_widgets: Any,
    config: StudioConfig,
    *,
    on_settings_changed: Optional[Callable[[], None]] = None,
) -> Any:
    """Build the Studio Environment tab content."""

    environment = config.studio_environment
    section = qt_widgets.QWidget()
    section.setObjectName(SETTINGS_STUDIO_ENVIRONMENT_SECTION_OBJECT_NAME)
    section_layout = qt_widgets.QVBoxLayout(section)
    section_layout.setContentsMargins(0, 0, 0, 0)
    section_layout.setSpacing(6)

    intro = qt_widgets.QLabel(
        "Studio network path roots stored in shader_health_studio.json. "
        "Use ${STUDIO_TEXTURE_ROOT} and custom aliases in rules and fix plans."
    )
    intro.setWordWrap(True)
    section_layout.addWidget(intro)

    grid_host = qt_widgets.QWidget()
    grid_host.setObjectName(SETTINGS_STUDIO_ENVIRONMENT_GRID_OBJECT_NAME)
    set_fixed_horizontal_size_policy(qt_widgets, grid_host)
    columns_row = qt_widgets.QHBoxLayout()
    set_columns_margins = getattr(columns_row, "setContentsMargins", None)
    if set_columns_margins is not None:
        set_columns_margins(0, 0, 0, 0)
    set_columns_spacing = getattr(columns_row, "setSpacing", None)
    if set_columns_spacing is not None:
        set_columns_spacing(_COLUMNS_GAP)

    left_column = qt_widgets.QWidget()
    left_column.setObjectName(SETTINGS_STUDIO_ENVIRONMENT_LEFT_COLUMN_OBJECT_NAME)
    set_fixed_horizontal_size_policy(qt_widgets, left_column)
    left_layout = _create_grid_layout(qt_widgets, left_column)

    right_column = qt_widgets.QWidget()
    right_column.setObjectName(SETTINGS_STUDIO_ENVIRONMENT_RIGHT_COLUMN_OBJECT_NAME)
    set_fixed_horizontal_size_policy(qt_widgets, right_column)
    right_layout = _create_grid_layout(qt_widgets, right_column)

    add_column = getattr(columns_row, "addWidget", None)
    if add_column is not None:
        add_column(left_column)
        add_column(right_column)

    _add_grid_field(
        qt_widgets,
        left_layout,
        row=0,
        column=0,
        label="Texture",
        object_name=SETTINGS_TEXTURE_ROOT_INPUT_OBJECT_NAME,
        value=environment.texture_root,
        placeholder="\\\\farm\\textures",
        width=_ROOT_FIELD_WIDTH,
        column_span=4,
        on_changed=on_settings_changed,
    )
    _add_grid_field(
        qt_widgets,
        left_layout,
        row=1,
        column=0,
        label="Cache",
        object_name=SETTINGS_CACHE_ROOT_INPUT_OBJECT_NAME,
        value=environment.cache_root,
        placeholder="\\\\farm\\cache",
        width=_ROOT_FIELD_WIDTH,
        column_span=4,
        on_changed=on_settings_changed,
    )
    _add_grid_field(
        qt_widgets,
        right_layout,
        row=0,
        column=0,
        label="Asset",
        object_name=SETTINGS_ASSET_ROOT_INPUT_OBJECT_NAME,
        value=environment.asset_root,
        placeholder="\\\\farm\\assets",
        width=_SMALL_ROOT_FIELD_WIDTH,
        column_span=4,
        on_changed=on_settings_changed,
    )
    _add_grid_field(
        qt_widgets,
        right_layout,
        row=1,
        column=0,
        label="Render",
        object_name=SETTINGS_RENDER_ROOT_INPUT_OBJECT_NAME,
        value=environment.render_root,
        placeholder="\\\\farm\\render",
        width=_SMALL_ROOT_FIELD_WIDTH,
        column_span=4,
        on_changed=on_settings_changed,
    )
    _configure_grid(left_layout)
    _configure_grid(right_layout)

    grid_layout = qt_widgets.QVBoxLayout(grid_host)
    set_grid_margins = getattr(grid_layout, "setContentsMargins", None)
    if set_grid_margins is not None:
        set_grid_margins(0, 0, 0, 0)
    add_columns = getattr(grid_layout, "addLayout", None)
    if add_columns is not None:
        add_columns(columns_row)
    section_layout.addWidget(grid_host)

    aliases_label = qt_widgets.QLabel("Variable aliases")
    set_fixed_horizontal_size_policy(qt_widgets, aliases_label)
    section_layout.addWidget(aliases_label)

    aliases_input = _build_plain_text_input(
        qt_widgets,
        object_name=SETTINGS_VARIABLE_ALIASES_INPUT_OBJECT_NAME,
        text=format_variable_aliases(environment.variable_aliases),
        placeholder="STUDIO_TEXTURE_ROOT=\\\\farm\\textures",
        tooltip="One NAME=value alias per line. Overrides built-in ${STUDIO_*_ROOT} tokens.",
    )
    wire_plain_text_changed(aliases_input, on_settings_changed)
    section_layout.addWidget(aliases_input)

    hint = qt_widgets.QLabel(
        "Built-in tokens: ${STUDIO_TEXTURE_ROOT}, ${STUDIO_ASSET_ROOT}, "
        "${STUDIO_CACHE_ROOT}, ${STUDIO_RENDER_ROOT}."
    )
    hint.setWordWrap(True)
    section_layout.addWidget(hint)
    section_layout.addStretch(1)
    return section


def read_studio_environment_from_view(
    view: Any,
    qt_widgets: Any,
    *,
    base: StudioEnvironmentSettings | None = None,
) -> StudioEnvironmentSettings:
    """Read Studio Environment fields from the settings UI."""

    aliases_input = find_child(
        view,
        _plain_text_widget_type(qt_widgets),
        SETTINGS_VARIABLE_ALIASES_INPUT_OBJECT_NAME,
    )
    return StudioEnvironmentSettings(
        texture_root=line_edit_text(view, qt_widgets, SETTINGS_TEXTURE_ROOT_INPUT_OBJECT_NAME),
        asset_root=line_edit_text(view, qt_widgets, SETTINGS_ASSET_ROOT_INPUT_OBJECT_NAME),
        cache_root=line_edit_text(view, qt_widgets, SETTINGS_CACHE_ROOT_INPUT_OBJECT_NAME),
        render_root=line_edit_text(view, qt_widgets, SETTINGS_RENDER_ROOT_INPUT_OBJECT_NAME),
        variable_aliases=parse_variable_aliases(_plain_text(aliases_input)),
    )


def update_studio_environment_view(
    view: Any,
    qt_widgets: Any,
    environment: StudioEnvironmentSettings,
) -> None:
    """Refresh Studio Environment controls from studio config."""

    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_TEXTURE_ROOT_INPUT_OBJECT_NAME,
        environment.texture_root,
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_ASSET_ROOT_INPUT_OBJECT_NAME,
        environment.asset_root,
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_CACHE_ROOT_INPUT_OBJECT_NAME,
        environment.cache_root,
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_RENDER_ROOT_INPUT_OBJECT_NAME,
        environment.render_root,
    )
    aliases_input = find_child(
        view,
        _plain_text_widget_type(qt_widgets),
        SETTINGS_VARIABLE_ALIASES_INPUT_OBJECT_NAME,
    )
    _set_plain_text(aliases_input, format_variable_aliases(environment.variable_aliases))


def parse_variable_aliases(text: str) -> dict[str, str]:
    """Parse NAME=value aliases from the Studio Environment tab."""

    aliases: dict[str, str] = {}
    for line in text.replace("\r\n", "\n").split("\n"):
        normalized = line.strip()
        if not normalized or "=" not in normalized:
            continue
        name, value = normalized.split("=", 1)
        key = name.strip()
        if key:
            aliases[key] = value.strip()
    return aliases


def format_variable_aliases(aliases: Mapping[str, str]) -> str:
    """Format variable aliases for the Studio Environment plain-text field."""

    return "\n".join(
        f"{name}={value}"
        for name, value in sorted(aliases.items())
        if str(name).strip()
    )


def _create_grid_layout(qt_widgets: Any, parent: Any) -> Any:
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


def _add_grid_field(
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
    caption = _build_label(qt_widgets, label)
    field = _build_line_edit(
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


def _build_label(qt_widgets: Any, text: str) -> Any:
    label = qt_widgets.QLabel(text)
    set_fixed_horizontal_size_policy(qt_widgets, label)
    set_fixed_width = getattr(label, "setFixedWidth", None)
    if set_fixed_width is not None:
        set_fixed_width(_LABEL_WIDTH)
    return label


def _build_line_edit(
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
    wire_line_edit_finished(field, on_changed)
    return field


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


def _configure_grid(grid_layout: Any) -> None:
    set_column_stretch = getattr(grid_layout, "setColumnStretch", None)
    if set_column_stretch is not None:
        for column in range(5):
            set_column_stretch(column, 0)
    set_column_minimum_width = getattr(grid_layout, "setColumnMinimumWidth", None)
    if set_column_minimum_width is not None:
        set_column_minimum_width(0, _LABEL_WIDTH)
        set_column_minimum_width(2, _PAIR_GAP)


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
