"""Studio policy fields for the Settings Studio tab."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional

from pipeline_inspector.studio_config import (
    DEFAULT_WAIVER_EXPIRY_DAYS,
    PipelineSettings,
    StudioConfig,
    WaiverDefaultsSettings,
)
from pipeline_inspector.ui.settings_widgets import (
    apply_toggle_style,
    build_labeled_toggle_row,
    build_settings_toggle,
    configure_compact_line_edit,
    find_child,
    line_edit_text,
    set_fixed_horizontal_size_policy,
    set_line_edit_text,
    toggle_label,
    widget_has_focus,
    wire_line_edit_finished,
    wire_plain_text_changed,
)

_LABEL_WIDTH = 84
_FIELD_WIDTH = 240
_PLAIN_TEXT_WIDTH = 292
_PLAIN_TEXT_HEIGHT = 72
_STUDIO_TOGGLE_LABEL_WIDTH = 228
_STUDIO_TOGGLE_GAP = 12

SETTINGS_REQUIRE_TX_TOGGLE_OBJECT_NAME = "pipelineInspectorSettingsRequireTxToggle"

SETTINGS_STUDIO_POLICY_SECTION_OBJECT_NAME = "pipelineInspectorSettingsStudioPolicySection"
SETTINGS_STUDIO_NAME_INPUT_OBJECT_NAME = "pipelineInspectorSettingsStudioNameInput"
SETTINGS_WAIVER_APPROVED_BY_INPUT_OBJECT_NAME = (
    "pipelineInspectorSettingsWaiverApprovedByInput"
)
SETTINGS_WAIVER_EXPIRY_DAYS_INPUT_OBJECT_NAME = (
    "pipelineInspectorSettingsWaiverExpiryDaysInput"
)
SETTINGS_ALLOW_CRITICAL_WAIVERS_TOGGLE_OBJECT_NAME = (
    "pipelineInspectorSettingsAllowCriticalWaiversToggle"
)
SETTINGS_MANIFEST_MAX_NEW_CHANGES_INPUT_OBJECT_NAME = (
    "pipelineInspectorSettingsManifestMaxNewChangesInput"
)
SETTINGS_MANIFEST_MAX_FINGERPRINT_CHANGES_INPUT_OBJECT_NAME = (
    "pipelineInspectorSettingsManifestMaxFingerprintChangesInput"
)
SETTINGS_MANIFEST_BLOCK_NEW_TEXTURES_TOGGLE_OBJECT_NAME = (
    "pipelineInspectorSettingsManifestBlockNewTexturesToggle"
)
SETTINGS_PINNED_WORKFLOW_PROFILES_INPUT_OBJECT_NAME = (
    "pipelineInspectorSettingsPinnedWorkflowProfilesInput"
)
SETTINGS_PINNED_ASSET_CLASS_PROFILES_INPUT_OBJECT_NAME = (
    "pipelineInspectorSettingsPinnedAssetClassProfilesInput"
)
SETTINGS_EXTRA_RULES_FOLDER_INPUT_OBJECT_NAME = (
    "pipelineInspectorSettingsExtraRulesFolderInput"
)
SETTINGS_EXTRA_RULES_FOLDER_INPUT_OBJECT_NAME = (
    "pipelineInspectorSettingsExtraRulesFolderInput"
)


def build_studio_policy_section(
    qt_widgets: Any,
    config: StudioConfig,
    *,
    on_require_tx_changed: Optional[Callable[[bool], None]] = None,
    on_settings_changed: Optional[Callable[[], None]] = None,
) -> Any:
    """Build Studio tab policy controls."""

    section = qt_widgets.QWidget()
    section.setObjectName(SETTINGS_STUDIO_POLICY_SECTION_OBJECT_NAME)
    layout = qt_widgets.QVBoxLayout(section)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    intro = qt_widgets.QLabel(
        "Studio-wide pipeline policy from pipeline_inspector_studio.json. "
        "Network paths live under Studio Environment; integrations under Connectors."
    )
    intro.setWordWrap(True)
    layout.addWidget(intro)

    layout.addWidget(_section_title(qt_widgets, "Studio"))
    studio_name_input = qt_widgets.QLineEdit(config.studio_name)
    studio_name_input.setObjectName(SETTINGS_STUDIO_NAME_INPUT_OBJECT_NAME)
    studio_name_input.setPlaceholderText("Example Studio")
    set_fixed_width = getattr(studio_name_input, "setFixedWidth", None)
    if set_fixed_width is not None:
        set_fixed_width(_FIELD_WIDTH)
    set_fixed_horizontal_size_policy(qt_widgets, studio_name_input)
    studio_name_input.setToolTip(
        "Display name shown in Settings (Studio tab header) and studio config labels."
    )
    wire_line_edit_finished(studio_name_input, on_settings_changed)
    layout.addWidget(_labeled_field_row(qt_widgets, "Name", studio_name_input))

    studio_hint = qt_widgets.QLabel(
        "Studio name appears above the config file path on the Studio tab after you save."
    )
    studio_hint.setWordWrap(True)
    layout.addWidget(studio_hint)

    layout.addWidget(_section_title(qt_widgets, "Pipeline"))
    layout.addWidget(
        _labeled_toggle_row(
            qt_widgets,
            "Require .tx optimized texture derivatives",
            build_settings_toggle(
                qt_widgets,
                object_name=SETTINGS_REQUIRE_TX_TOGGLE_OBJECT_NAME,
                enabled=config.pipeline.require_tx_derivatives,
                on_changed=on_require_tx_changed,
            ),
        )
    )

    layout.addWidget(_section_title(qt_widgets, "Waiver defaults"))
    waiver_defaults = config.pipeline.waiver_defaults
    approved_by_input = qt_widgets.QLineEdit(waiver_defaults.default_approved_by)
    approved_by_input.setObjectName(SETTINGS_WAIVER_APPROVED_BY_INPUT_OBJECT_NAME)
    approved_by_input.setPlaceholderText("pipeline_td")
    approved_by_input.setToolTip("Default approver name prefilled in the waiver manager.")
    _configure_compact_line_edit(qt_widgets, approved_by_input, _FIELD_WIDTH)
    wire_line_edit_finished(approved_by_input, on_settings_changed)
    layout.addWidget(_labeled_field_row(qt_widgets, "Approver", approved_by_input))

    expiry_input = qt_widgets.QLineEdit(str(waiver_defaults.default_expiry_days))
    expiry_input.setObjectName(SETTINGS_WAIVER_EXPIRY_DAYS_INPUT_OBJECT_NAME)
    expiry_input.setPlaceholderText(str(DEFAULT_WAIVER_EXPIRY_DAYS))
    expiry_input.setToolTip("Default waiver lifetime in days.")
    _configure_compact_line_edit(qt_widgets, expiry_input, 72)
    wire_line_edit_finished(expiry_input, on_settings_changed)
    layout.addWidget(_labeled_field_row(qt_widgets, "Expiry days", expiry_input))

    layout.addWidget(
        _labeled_toggle_row(
            qt_widgets,
            "Allow waivers on critical farm-blocking issues",
            build_settings_toggle(
                qt_widgets,
                object_name=SETTINGS_ALLOW_CRITICAL_WAIVERS_TOGGLE_OBJECT_NAME,
                enabled=waiver_defaults.allow_critical_waivers,
                on_changed=lambda _checked: on_settings_changed() if on_settings_changed else None,
            ),
        )
    )

    layout.addWidget(_section_title(qt_widgets, "Manifest gate"))
    manifest_defaults = config.pipeline.manifest_gate_defaults
    max_new_input = qt_widgets.QLineEdit(str(manifest_defaults.max_new_changes))
    max_new_input.setObjectName(SETTINGS_MANIFEST_MAX_NEW_CHANGES_INPUT_OBJECT_NAME)
    max_new_input.setToolTip("Maximum new manifest entries allowed before gate blocks.")
    _configure_compact_line_edit(qt_widgets, max_new_input, 72)
    wire_line_edit_finished(max_new_input, on_settings_changed)
    layout.addWidget(_labeled_field_row(qt_widgets, "Max new", max_new_input))

    max_fingerprint_input = qt_widgets.QLineEdit(
        str(manifest_defaults.max_fingerprint_changes)
    )
    max_fingerprint_input.setObjectName(
        SETTINGS_MANIFEST_MAX_FINGERPRINT_CHANGES_INPUT_OBJECT_NAME
    )
    max_fingerprint_input.setToolTip(
        "Maximum graph fingerprint changes allowed before gate blocks."
    )
    _configure_compact_line_edit(qt_widgets, max_fingerprint_input, 72)
    wire_line_edit_finished(max_fingerprint_input, on_settings_changed)
    layout.addWidget(
        _labeled_field_row(qt_widgets, "Max fingerprint", max_fingerprint_input)
    )

    layout.addWidget(
        _labeled_toggle_row(
            qt_widgets,
            "Block manifest gate when new textures appear",
            build_settings_toggle(
                qt_widgets,
                object_name=SETTINGS_MANIFEST_BLOCK_NEW_TEXTURES_TOGGLE_OBJECT_NAME,
                enabled=manifest_defaults.block_on_new_textures,
                on_changed=lambda _checked: on_settings_changed() if on_settings_changed else None,
            ),
        )
    )

    layout.addWidget(_section_title(qt_widgets, "Profile allow-lists"))
    pinned_workflow_input = _build_plain_text_input(
        qt_widgets,
        object_name=SETTINGS_PINNED_WORKFLOW_PROFILES_INPUT_OBJECT_NAME,
        text=format_profile_id_list(config.pipeline.pinned_workflow_profile_ids),
        placeholder="artist_relaxed\npublish_strict",
        tooltip=(
            "Optional allow-list of workflow profile ids. "
            "Leave blank to expose every packaged workflow profile."
        ),
        width=_PLAIN_TEXT_WIDTH,
        height=_PLAIN_TEXT_HEIGHT,
    )
    wire_plain_text_changed(pinned_workflow_input, on_settings_changed)
    layout.addWidget(_labeled_field_row(qt_widgets, "Workflow", pinned_workflow_input))

    pinned_asset_class_input = _build_plain_text_input(
        qt_widgets,
        object_name=SETTINGS_PINNED_ASSET_CLASS_PROFILES_INPUT_OBJECT_NAME,
        text=format_profile_id_list(config.pipeline.pinned_asset_class_profile_ids),
        placeholder="asset_class_hero\nasset_class_prop",
        tooltip=(
            "Optional allow-list of asset class overlay profile ids. "
            "Leave blank to expose every packaged asset class profile."
        ),
        width=_PLAIN_TEXT_WIDTH,
        height=_PLAIN_TEXT_HEIGHT,
    )
    wire_plain_text_changed(pinned_asset_class_input, on_settings_changed)
    layout.addWidget(
        _labeled_field_row(qt_widgets, "Asset class", pinned_asset_class_input)
    )

    layout.addWidget(_section_title(qt_widgets, "Rule authoring"))
    extra_rules_input = qt_widgets.QLineEdit(config.pipeline.extra_rules_folder)
    extra_rules_input.setObjectName(SETTINGS_EXTRA_RULES_FOLDER_INPUT_OBJECT_NAME)
    extra_rules_input.setPlaceholderText("//studio/share/pipeline_inspector/extra_rules")
    extra_rules_input.setToolTip(
        "Studio folder where incident rule draft sidecars are exported from the rule wizard."
    )
    _configure_compact_line_edit(qt_widgets, extra_rules_input, _PLAIN_TEXT_WIDTH)
    wire_line_edit_finished(extra_rules_input, on_settings_changed)
    layout.addWidget(
        _labeled_field_row(qt_widgets, "Extra rules", extra_rules_input)
    )

    hint = qt_widgets.QLabel(
        "Pinned profile lists restrict which workflow and asset class profiles appear "
        "in the panel. Manifest gate defaults apply when the studio config overrides "
        "profile policy during gate checks."
    )
    hint.setWordWrap(True)
    layout.addWidget(hint)
    return section


def read_studio_policy_from_view(
    view: Any,
    qt_widgets: Any,
    *,
    base: StudioConfig,
) -> StudioConfig:
    """Read studio policy fields from the settings UI."""

    pipeline = read_pipeline_settings_from_view(view, qt_widgets, base=base.pipeline)
    return base.with_updates(
        studio_name=line_edit_text(
            view,
            qt_widgets,
            SETTINGS_STUDIO_NAME_INPUT_OBJECT_NAME,
            fallback=base.studio_name,
        ),
        pipeline=pipeline,
    )


def read_pipeline_settings_from_view(
    view: Any,
    qt_widgets: Any,
    *,
    base: PipelineSettings | None = None,
) -> PipelineSettings:
    """Read pipeline policy controls from the settings UI."""

    current = base or PipelineSettings()
    return PipelineSettings(
        require_tx_derivatives=_toggle_checked(
            view,
            qt_widgets,
            SETTINGS_REQUIRE_TX_TOGGLE_OBJECT_NAME,
            current.require_tx_derivatives,
        ),
        waiver_defaults=WaiverDefaultsSettings(
            default_approved_by=line_edit_text(
                view,
                qt_widgets,
                SETTINGS_WAIVER_APPROVED_BY_INPUT_OBJECT_NAME,
                fallback=current.waiver_defaults.default_approved_by,
            ),
            default_expiry_days=_positive_int(
                line_edit_text(
                    view,
                    qt_widgets,
                    SETTINGS_WAIVER_EXPIRY_DAYS_INPUT_OBJECT_NAME,
                    fallback=str(current.waiver_defaults.default_expiry_days),
                ),
                current.waiver_defaults.default_expiry_days,
            ),
            allow_critical_waivers=_toggle_checked(
                view,
                qt_widgets,
                SETTINGS_ALLOW_CRITICAL_WAIVERS_TOGGLE_OBJECT_NAME,
                current.waiver_defaults.allow_critical_waivers,
            ),
        ),
        manifest_gate_defaults=_read_manifest_gate_defaults(view, qt_widgets, current),
        pinned_workflow_profile_ids=parse_profile_id_list(
            _plain_text(
                find_child(
                    view,
                    _plain_text_widget_type(qt_widgets),
                    SETTINGS_PINNED_WORKFLOW_PROFILES_INPUT_OBJECT_NAME,
                )
            )
        ),
        pinned_asset_class_profile_ids=parse_profile_id_list(
            _plain_text(
                find_child(
                    view,
                    _plain_text_widget_type(qt_widgets),
                    SETTINGS_PINNED_ASSET_CLASS_PROFILES_INPUT_OBJECT_NAME,
                )
            )
        ),
        extra_rules_folder=line_edit_text(
            view,
            qt_widgets,
            SETTINGS_EXTRA_RULES_FOLDER_INPUT_OBJECT_NAME,
            fallback=current.extra_rules_folder,
        ),
    )


def update_studio_policy_view(view: Any, qt_widgets: Any, config: StudioConfig) -> None:
    """Refresh Studio policy controls from studio config."""

    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_STUDIO_NAME_INPUT_OBJECT_NAME,
        config.studio_name,
    )
    update_pipeline_settings_view(view, qt_widgets, config.pipeline)


def update_pipeline_settings_view(
    view: Any,
    qt_widgets: Any,
    pipeline: PipelineSettings,
) -> None:
    """Refresh pipeline policy controls from studio config."""

    toggle = find_child(view, qt_widgets.QWidget, SETTINGS_REQUIRE_TX_TOGGLE_OBJECT_NAME)
    if toggle is not None:
        set_checked = getattr(toggle, "setChecked", None)
        if set_checked is not None:
            set_checked(pipeline.require_tx_derivatives)
        toggle.setText(toggle_label(pipeline.require_tx_derivatives))
        apply_toggle_style(toggle, pipeline.require_tx_derivatives)

    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_WAIVER_APPROVED_BY_INPUT_OBJECT_NAME,
        pipeline.waiver_defaults.default_approved_by,
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_WAIVER_EXPIRY_DAYS_INPUT_OBJECT_NAME,
        str(pipeline.waiver_defaults.default_expiry_days),
    )
    _set_toggle_checked(
        view,
        qt_widgets,
        SETTINGS_ALLOW_CRITICAL_WAIVERS_TOGGLE_OBJECT_NAME,
        pipeline.waiver_defaults.allow_critical_waivers,
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_MANIFEST_MAX_NEW_CHANGES_INPUT_OBJECT_NAME,
        str(pipeline.manifest_gate_defaults.max_new_changes),
    )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_MANIFEST_MAX_FINGERPRINT_CHANGES_INPUT_OBJECT_NAME,
        str(pipeline.manifest_gate_defaults.max_fingerprint_changes),
    )
    _set_toggle_checked(
        view,
        qt_widgets,
        SETTINGS_MANIFEST_BLOCK_NEW_TEXTURES_TOGGLE_OBJECT_NAME,
        pipeline.manifest_gate_defaults.block_on_new_textures,
    )
    workflow_input = find_child(
        view,
        _plain_text_widget_type(qt_widgets),
        SETTINGS_PINNED_WORKFLOW_PROFILES_INPUT_OBJECT_NAME,
    )
    if workflow_input is not None and not widget_has_focus(workflow_input):
        _set_plain_text(
            workflow_input,
            format_profile_id_list(pipeline.pinned_workflow_profile_ids),
        )
    asset_class_input = find_child(
        view,
        _plain_text_widget_type(qt_widgets),
        SETTINGS_PINNED_ASSET_CLASS_PROFILES_INPUT_OBJECT_NAME,
    )
    if asset_class_input is not None and not widget_has_focus(asset_class_input):
        _set_plain_text(
            asset_class_input,
            format_profile_id_list(pipeline.pinned_asset_class_profile_ids),
        )
    set_line_edit_text(
        view,
        qt_widgets,
        SETTINGS_EXTRA_RULES_FOLDER_INPUT_OBJECT_NAME,
        pipeline.extra_rules_folder,
    )


def parse_profile_id_list(text: str) -> tuple[str, ...]:
    """Parse one profile id per line."""

    return tuple(
        line.strip()
        for line in text.replace("\r\n", "\n").split("\n")
        if line.strip()
    )


def format_profile_id_list(profile_ids: tuple[str, ...]) -> str:
    """Format pinned profile ids for the Studio tab plain-text fields."""

    return "\n".join(profile_id for profile_id in profile_ids if profile_id.strip())


def _read_manifest_gate_defaults(
    view: Any,
    qt_widgets: Any,
    base: PipelineSettings,
) -> Any:
    from pipeline_inspector.core.manifest_gate import ManifestGatePolicy

    return ManifestGatePolicy(
        max_new_changes=_non_negative_int(
            line_edit_text(view, qt_widgets, SETTINGS_MANIFEST_MAX_NEW_CHANGES_INPUT_OBJECT_NAME),
            base.manifest_gate_defaults.max_new_changes,
        ),
        max_fingerprint_changes=_non_negative_int(
            line_edit_text(
                view,
                qt_widgets,
                SETTINGS_MANIFEST_MAX_FINGERPRINT_CHANGES_INPUT_OBJECT_NAME,
            ),
            base.manifest_gate_defaults.max_fingerprint_changes,
        ),
        block_on_new_textures=_toggle_checked(
            view,
            qt_widgets,
            SETTINGS_MANIFEST_BLOCK_NEW_TEXTURES_TOGGLE_OBJECT_NAME,
            base.manifest_gate_defaults.block_on_new_textures,
        ),
    )


def _section_title(qt_widgets: Any, text: str) -> Any:
    label = qt_widgets.QLabel(text)
    set_style = getattr(label, "setStyleSheet", None)
    if set_style is not None:
        set_style("font-size: 11pt; font-weight: bold;")
    set_fixed_horizontal_size_policy(qt_widgets, label)
    return label


def _labeled_toggle_row(qt_widgets: Any, label_text: str, toggle: Any) -> Any:
    return build_labeled_toggle_row(
        qt_widgets,
        label_text,
        toggle,
        label_width=_STUDIO_TOGGLE_LABEL_WIDTH,
        gap=_STUDIO_TOGGLE_GAP,
    )


def _labeled_field_row(qt_widgets: Any, label_text: str, field: Any) -> Any:
    row = qt_widgets.QHBoxLayout()
    set_margins = getattr(row, "setContentsMargins", None)
    if set_margins is not None:
        set_margins(0, 0, 0, 0)
    set_spacing = getattr(row, "setSpacing", None)
    if set_spacing is not None:
        set_spacing(6)
    caption = qt_widgets.QLabel(label_text)
    set_fixed_width = getattr(caption, "setFixedWidth", None)
    if set_fixed_width is not None:
        set_fixed_width(_LABEL_WIDTH)
    set_fixed_horizontal_size_policy(qt_widgets, caption)
    row.addWidget(caption, 0)
    row.addWidget(field, 0)
    row.addStretch(1)
    host = qt_widgets.QWidget()
    host.setLayout(row)
    return host


def _configure_compact_line_edit(qt_widgets: Any, field: Any, width: int) -> None:
    configure_compact_line_edit(qt_widgets, field, width)


def _build_plain_text_input(
    qt_widgets: Any,
    *,
    object_name: str,
    text: str,
    placeholder: str,
    tooltip: str,
    width: int = _PLAIN_TEXT_WIDTH,
    height: int = _PLAIN_TEXT_HEIGHT,
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
    set_fixed_width = getattr(field, "setFixedWidth", None)
    if set_fixed_width is not None:
        set_fixed_width(width)
    set_fixed_height = getattr(field, "setFixedHeight", None)
    if set_fixed_height is not None:
        set_fixed_height(height)
    set_fixed_horizontal_size_policy(qt_widgets, field)
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


def _toggle_checked(
    view: Any,
    qt_widgets: Any,
    object_name: str,
    default: bool,
) -> bool:
    toggle = find_child(view, qt_widgets.QWidget, object_name)
    if toggle is None:
        return default
    is_checked = getattr(toggle, "isChecked", None)
    if is_checked is None:
        return default
    return bool(is_checked())


def _set_toggle_checked(
    view: Any,
    qt_widgets: Any,
    object_name: str,
    enabled: bool,
) -> None:
    toggle = find_child(view, qt_widgets.QWidget, object_name)
    if toggle is None:
        return
    set_checked = getattr(toggle, "setChecked", None)
    if set_checked is not None:
        set_checked(enabled)
    set_text = getattr(toggle, "setText", None)
    if set_text is not None:
        set_text(toggle_label(enabled))
    apply_toggle_style(toggle, enabled)


def _positive_int(text: str, default: int) -> int:
    parsed = _non_negative_int(text, default)
    return parsed if parsed > 0 else default


def _non_negative_int(text: str, default: int) -> int:
    normalized = str(text or "").strip()
    if not normalized:
        return default
    try:
        value = int(normalized)
    except ValueError:
        return default
    return max(0, value)
