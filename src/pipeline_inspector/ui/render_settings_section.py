"""Render-quality preset controls for the Settings Render tab."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional

from pipeline_inspector.core.render_presets import (
    ArnoldRenderQualitySettings,
    CommonRenderQualitySettings,
    RenderQualityPreset,
    RenderSettings,
    VrayRenderQualitySettings,
)
from pipeline_inspector.studio_config import StudioConfig
from pipeline_inspector.ui.settings_widgets import (
    line_edit_text,
    qt_align_left,
    qt_align_left_vcenter,
    qt_align_right_vcenter,
    set_fixed_horizontal_size_policy,
    set_line_edit_text,
    wire_button,
    wire_line_edit_finished,
)

SETTINGS_RENDER_SECTION_OBJECT_NAME = "pipelineInspectorSettingsRenderSection"
SETTINGS_RENDER_CONTENT_OBJECT_NAME = "pipelineInspectorSettingsRenderContent"

_RENDER_LABEL_WIDTH = 100
_RENDER_FIELD_WIDTH = 60
_RENDER_PAIR_GAP = 16
_RENDER_GRID_COLUMNS = 5
_RENDER_GRID_HORIZONTAL_SPACING = 4
_RENDER_GRID_CONTENT_WIDTH = (
    _RENDER_LABEL_WIDTH * 2
    + _RENDER_FIELD_WIDTH * 2
    + _RENDER_PAIR_GAP
    + _RENDER_GRID_HORIZONTAL_SPACING * (_RENDER_GRID_COLUMNS - 1)
)
_RENDER_SECTION_MIN_HEIGHT = 640


def build_render_settings_section(
    qt_widgets: Any,
    config: StudioConfig,
    *,
    on_settings_changed: Optional[Callable[[], None]] = None,
    on_apply_preset: Optional[Callable[[str], None]] = None,
) -> Any:
    """Build Draft/Production render-quality controls for V-Ray and Arnold."""

    section = qt_widgets.QWidget()
    section.setObjectName(SETTINGS_RENDER_SECTION_OBJECT_NAME)
    layout = qt_widgets.QVBoxLayout(section)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)

    intro = qt_widgets.QLabel(
        "Studio render-quality targets stored in pipeline_inspector_studio.json. "
        "Values map to Maya Render Settings: Resolution (defaultResolution), "
        "V-Ray (vraySettings), and Arnold (defaultArnoldRenderOptions). "
        "Saving settings does not change the open scene — use Apply to Scene to push "
        "Draft/Production into Maya and sync the render frame range from the timeline."
    )
    intro.setWordWrap(True)
    _add_left_aligned_widget(layout, intro, qt_widgets)

    content = qt_widgets.QWidget()
    content.setObjectName(SETTINGS_RENDER_CONTENT_OBJECT_NAME)
    set_min_height = getattr(content, "setMinimumHeight", None)
    if set_min_height is not None:
        set_min_height(_RENDER_SECTION_MIN_HEIGHT)
    content_layout = qt_widgets.QVBoxLayout(content)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(8)

    content_layout.addWidget(
        _build_quality_block(
            qt_widgets,
            title="Draft",
            quality_id="draft",
            preset=config.render.draft,
            on_changed=on_settings_changed,
            on_apply=on_apply_preset,
        )
    )
    content_layout.addWidget(
        _build_quality_block(
            qt_widgets,
            title="Production",
            quality_id="production",
            preset=config.render.production,
            on_changed=on_settings_changed,
            on_apply=on_apply_preset,
        )
    )

    _add_left_aligned_widget(layout, content, qt_widgets)
    layout.addStretch(0)
    return section


def read_render_settings_from_view(
    view: Any,
    qt_widgets: Any,
    *,
    base: RenderSettings,
) -> RenderSettings:
    """Read render-quality fields from the Settings Render tab."""

    _ = base
    return RenderSettings(
        draft=_read_quality_preset_from_view(view, qt_widgets, quality_id="draft"),
        production=_read_quality_preset_from_view(view, qt_widgets, quality_id="production"),
    )


def update_render_settings_view(
    view: Any,
    qt_widgets: Any,
    render: RenderSettings,
) -> None:
    """Refresh render-quality controls from studio config."""

    _update_quality_preset_view(view, qt_widgets, quality_id="draft", preset=render.draft)
    _update_quality_preset_view(
        view,
        qt_widgets,
        quality_id="production",
        preset=render.production,
    )


def _build_quality_block(
    qt_widgets: Any,
    *,
    title: str,
    quality_id: str,
    preset: RenderQualityPreset,
    on_changed: Optional[Callable[[], None]],
    on_apply: Optional[Callable[[str], None]] = None,
) -> Any:
    block = qt_widgets.QWidget()
    block_layout = qt_widgets.QVBoxLayout(block)
    block_layout.setContentsMargins(0, 0, 0, 0)
    block_layout.setSpacing(4)

    caption = qt_widgets.QLabel(title)
    set_style = getattr(caption, "setStyleSheet", None)
    if set_style is not None:
        set_style("font-size: 11pt; font-weight: bold;")
    block_layout.addWidget(caption)

    grid_host = qt_widgets.QWidget()
    grid_layout = _create_render_grid_layout(qt_widgets, grid_host)
    row = 0
    for subsection_title, renderer_id, fields in (
        ("Common / Resolution", "common", _COMMON_FIELDS),
        ("V-Ray", "vray", _VRAY_FIELDS),
        ("Arnold", "arnold", _ARNOLD_FIELDS),
    ):
        row = _add_subsection_header(qt_widgets, grid_layout, row=row, title=subsection_title)
        row = _add_fields_to_grid(
            qt_widgets,
            grid_layout,
            row=row,
            quality_id=quality_id,
            renderer_id=renderer_id,
            fields=fields,
            preset=preset,
            on_changed=on_changed,
        )

    _configure_render_grid(grid_layout)
    block_layout.addWidget(_wrap_left_aligned(qt_widgets, grid_host))
    if on_apply is not None:
        apply_button = qt_widgets.QPushButton(f"Apply {title} to Scene")
        apply_button.setObjectName(f"pipelineInspectorApplyRender{title.replace(' ', '')}Button")
        def _apply_quality(_checked: bool = False, *, selected_quality: str = quality_id) -> None:
            on_apply(selected_quality)

        wire_button(apply_button, _apply_quality)
        block_layout.addWidget(apply_button)
    return block


def _add_left_aligned_widget(layout: Any, widget: Any, qt_widgets: Any) -> None:
    align_left = qt_align_left(qt_widgets)
    add_widget = getattr(layout, "addWidget", None)
    if add_widget is None:
        return
    if align_left is not None:
        add_widget(widget, 0, align_left)
    else:
        add_widget(widget)


def _wrap_left_aligned(qt_widgets: Any, widget: Any) -> Any:
    host = qt_widgets.QWidget()
    row = qt_widgets.QHBoxLayout(host)
    set_margins = getattr(row, "setContentsMargins", None)
    if set_margins is not None:
        set_margins(0, 0, 0, 0)
    set_spacing = getattr(row, "setSpacing", None)
    if set_spacing is not None:
        set_spacing(0)
    set_fixed_horizontal_size_policy(qt_widgets, widget)
    set_max_width = getattr(widget, "setMaximumWidth", None)
    if set_max_width is not None:
        set_max_width(_RENDER_GRID_CONTENT_WIDTH)
    row.addWidget(widget)
    add_stretch = getattr(row, "addStretch", None)
    if add_stretch is not None:
        add_stretch(1)
    return host


def _add_subsection_header(
    qt_widgets: Any,
    grid_layout: Any,
    *,
    row: int,
    title: str,
) -> int:
    subtitle = qt_widgets.QLabel(title)
    set_sub_style = getattr(subtitle, "setStyleSheet", None)
    if set_sub_style is not None:
        set_sub_style("font-weight: bold;")
    add_widget = getattr(grid_layout, "addWidget", None)
    if add_widget is not None:
        add_widget(subtitle, row, 0, 1, _RENDER_GRID_COLUMNS)
    return row + 1


def _add_fields_to_grid(
    qt_widgets: Any,
    grid_layout: Any,
    *,
    row: int,
    quality_id: str,
    renderer_id: str,
    fields: tuple[tuple[str, str, str], ...],
    preset: RenderQualityPreset,
    on_changed: Optional[Callable[[], None]],
) -> int:
    pending_pair: list[tuple[str, str, str, str]] = []
    for field_key, label, placeholder in fields:
        value = _field_value(preset, renderer_id, field_key)
        object_name = _field_object_name(quality_id, renderer_id, field_key)
        pending_pair.append((label, object_name, value, placeholder))
        if len(pending_pair) == 2:
            left = pending_pair.pop(0)
            right = pending_pair.pop(0)
            _add_render_grid_pair(
                qt_widgets,
                grid_layout,
                row=row,
                left_label=left[0],
                left_object_name=left[1],
                left_value=left[2],
                left_placeholder=left[3],
                right_label=right[0],
                right_object_name=right[1],
                right_value=right[2],
                right_placeholder=right[3],
                on_changed=on_changed,
            )
            row += 1
    if pending_pair:
        label, object_name, value, placeholder = pending_pair[0]
        _add_render_grid_field(
            qt_widgets,
            grid_layout,
            row=row,
            column=0,
            label=label,
            object_name=object_name,
            value=value,
            placeholder=placeholder,
            on_changed=on_changed,
        )
        row += 1
    return row


def _create_render_grid_layout(qt_widgets: Any, parent: Any) -> Any:
    grid_layout = qt_widgets.QGridLayout(parent)
    set_grid_margins = getattr(grid_layout, "setContentsMargins", None)
    if set_grid_margins is not None:
        set_grid_margins(0, 0, 0, 0)
    set_h_spacing = getattr(grid_layout, "setHorizontalSpacing", None)
    if set_h_spacing is not None:
        set_h_spacing(_RENDER_GRID_HORIZONTAL_SPACING)
    set_v_spacing = getattr(grid_layout, "setVerticalSpacing", None)
    if set_v_spacing is not None:
        set_v_spacing(4)
    return grid_layout


def _add_render_grid_pair(
    qt_widgets: Any,
    grid_layout: Any,
    *,
    row: int,
    left_label: str,
    left_object_name: str,
    left_value: str,
    left_placeholder: str,
    right_label: str,
    right_object_name: str,
    right_value: str,
    right_placeholder: str,
    on_changed: Optional[Callable[[], None]],
) -> None:
    _add_render_grid_field(
        qt_widgets,
        grid_layout,
        row=row,
        column=0,
        label=left_label,
        object_name=left_object_name,
        value=left_value,
        placeholder=left_placeholder,
        on_changed=on_changed,
    )
    _add_render_grid_field(
        qt_widgets,
        grid_layout,
        row=row,
        column=3,
        label=right_label,
        object_name=right_object_name,
        value=right_value,
        placeholder=right_placeholder,
        on_changed=on_changed,
    )


def _add_render_grid_field(
    qt_widgets: Any,
    grid_layout: Any,
    *,
    row: int,
    column: int,
    label: str,
    object_name: str,
    value: str,
    placeholder: str,
    on_changed: Optional[Callable[[], None]],
) -> None:
    caption = _build_render_label(qt_widgets, label)
    field = _build_render_line_edit(
        qt_widgets,
        object_name=object_name,
        value=value,
        placeholder=placeholder,
        on_changed=on_changed,
    )
    add_widget = getattr(grid_layout, "addWidget", None)
    if add_widget is None:
        return
    align_right = qt_align_right_vcenter(qt_widgets)
    align_left = qt_align_left_vcenter(qt_widgets)
    if align_right is not None:
        add_widget(caption, row, column, align_right)
    else:
        add_widget(caption, row, column)
    if align_left is not None:
        add_widget(field, row, column + 1, align_left)
    else:
        add_widget(field, row, column + 1)


def _build_render_label(qt_widgets: Any, text: str) -> Any:
    label = qt_widgets.QLabel(text)
    set_fixed_horizontal_size_policy(qt_widgets, label)
    set_fixed_width = getattr(label, "setFixedWidth", None)
    if set_fixed_width is not None:
        set_fixed_width(_RENDER_LABEL_WIDTH)
    return label


def _build_render_line_edit(
    qt_widgets: Any,
    *,
    object_name: str,
    value: str,
    placeholder: str,
    on_changed: Optional[Callable[[], None]],
) -> Any:
    field = qt_widgets.QLineEdit(value)
    field.setObjectName(object_name)
    set_placeholder = getattr(field, "setPlaceholderText", None)
    if set_placeholder is not None and placeholder:
        set_placeholder(placeholder)
    set_fixed_width = getattr(field, "setFixedWidth", None)
    if set_fixed_width is not None:
        set_fixed_width(_RENDER_FIELD_WIDTH)
    set_fixed_horizontal_size_policy(qt_widgets, field)
    wire_line_edit_finished(field, on_changed)
    return field


def _configure_render_grid(grid_layout: Any) -> None:
    set_column_stretch = getattr(grid_layout, "setColumnStretch", None)
    if set_column_stretch is not None:
        for column in range(_RENDER_GRID_COLUMNS):
            set_column_stretch(column, 0)
    set_column_minimum_width = getattr(grid_layout, "setColumnMinimumWidth", None)
    if set_column_minimum_width is not None:
        set_column_minimum_width(0, _RENDER_LABEL_WIDTH)
        set_column_minimum_width(1, _RENDER_FIELD_WIDTH)
        set_column_minimum_width(2, _RENDER_PAIR_GAP)
        set_column_minimum_width(3, _RENDER_LABEL_WIDTH)
        set_column_minimum_width(4, _RENDER_FIELD_WIDTH)


def _read_quality_preset_from_view(
    view: Any,
    qt_widgets: Any,
    *,
    quality_id: str,
) -> RenderQualityPreset:
    common_values = {
        field_key: _read_field_text(view, qt_widgets, quality_id, "common", field_key)
        for field_key, _, _ in _COMMON_FIELDS
    }
    vray_values = {
        field_key: _read_field_text(view, qt_widgets, quality_id, "vray", field_key)
        for field_key, _, _ in _VRAY_FIELDS
    }
    arnold_values = {
        field_key: _read_field_text(view, qt_widgets, quality_id, "arnold", field_key)
        for field_key, _, _ in _ARNOLD_FIELDS
    }
    return RenderQualityPreset(
        common=CommonRenderQualitySettings(
            width=_parse_int(common_values.get("width", "")),
            height=_parse_int(common_values.get("height", "")),
            device_aspect_ratio=_parse_float(common_values.get("device_aspect_ratio", "")),
            pixel_aspect=_parse_float(common_values.get("pixel_aspect", "")),
        ),
        vray=VrayRenderQualitySettings(
            image_sampler_type=_parse_int(vray_values.get("image_sampler_type", "")),
            min_subdivs=_parse_int(vray_values.get("min_subdivs", "")),
            max_subdivs=_parse_int(vray_values.get("max_subdivs", "")),
            ray_depth=_parse_int(vray_values.get("ray_depth", "")),
            gi_depth=_parse_int(vray_values.get("gi_depth", "")),
        ),
        arnold=ArnoldRenderQualitySettings(
            aa_samples=_parse_int(arnold_values.get("aa_samples", "")),
            gi_diffuse_samples=_parse_int(arnold_values.get("gi_diffuse_samples", "")),
            gi_specular_samples=_parse_int(arnold_values.get("gi_specular_samples", "")),
            gi_transmission_samples=_parse_int(
                arnold_values.get("gi_transmission_samples", "")
            ),
            gi_sss_samples=_parse_int(arnold_values.get("gi_sss_samples", "")),
        ),
    )


def _update_quality_preset_view(
    view: Any,
    qt_widgets: Any,
    *,
    quality_id: str,
    preset: RenderQualityPreset,
) -> None:
    for renderer_id, fields in (
        ("common", _COMMON_FIELDS),
        ("vray", _VRAY_FIELDS),
        ("arnold", _ARNOLD_FIELDS),
    ):
        for field_key, _, _ in fields:
            set_line_edit_text(
                view,
                qt_widgets,
                _field_object_name(quality_id, renderer_id, field_key),
                _field_value(preset, renderer_id, field_key),
            )


def _field_object_name(quality_id: str, renderer_id: str, field_key: str) -> str:
    quality = quality_id.title()
    renderer = renderer_id.title()
    field = field_key.title()
    return f"pipelineInspectorSettingsRender{quality}{renderer}{field}Input"


def _read_field_text(
    view: Any,
    qt_widgets: Any,
    quality_id: str,
    renderer_id: str,
    field_key: str,
) -> str:
    return line_edit_text(
        view,
        qt_widgets,
        _field_object_name(quality_id, renderer_id, field_key),
        fallback="",
    )


def _field_value(preset: RenderQualityPreset, renderer_id: str, field_key: str) -> str:
    if renderer_id == "common":
        value = getattr(preset.common, field_key)
    elif renderer_id == "vray":
        value = getattr(preset.vray, field_key)
    else:
        value = getattr(preset.arnold, field_key)
    if value in (0, 0.0):
        return ""
    if isinstance(value, float):
        return str(value)
    return str(value)


def _parse_int(text: str) -> int:
    normalized = str(text or "").strip()
    if not normalized:
        return 0
    try:
        return int(normalized)
    except ValueError:
        return 0


def _parse_float(text: str) -> float:
    normalized = str(text or "").strip()
    if not normalized:
        return 0.0
    try:
        return float(normalized)
    except ValueError:
        return 0.0


_COMMON_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("width", "Width", "1280"),
    ("height", "Height", "720"),
    ("device_aspect_ratio", "Device aspect", "1.0"),
    ("pixel_aspect", "Pixel aspect", "1.0"),
)

_VRAY_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("image_sampler_type", "Sampler type", "3"),
    ("min_subdivs", "Min subdivs", "1"),
    ("max_subdivs", "Max subdivs", "8"),
    ("ray_depth", "Ray depth", "5"),
    ("gi_depth", "GI depth", "3"),
)

_ARNOLD_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("aa_samples", "AA samples", "3"),
    ("gi_diffuse_samples", "GI diffuse", "2"),
    ("gi_specular_samples", "GI specular", "2"),
    ("gi_transmission_samples", "GI transmission", "2"),
    ("gi_sss_samples", "GI SSS", "2"),
)
