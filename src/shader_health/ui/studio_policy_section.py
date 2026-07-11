"""Studio policy fields for the Settings Studio tab."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional

from shader_health.studio_config import (
    DEFAULT_WAIVER_EXPIRY_DAYS,
    PipelineSettings,
    StudioConfig,
    WaiverDefaultsSettings,
)
from shader_health.ui.settings_widgets import (
    apply_toggle_style,
    build_settings_toggle,
    find_child,
    line_edit_text,
    set_line_edit_text,
    toggle_label,
    wire_line_edit_finished,
    wire_plain_text_changed,
)

SETTINGS_REQUIRE_TX_TOGGLE_OBJECT_NAME = "shaderHealthInspectorSettingsRequireTxToggle"

SETTINGS_STUDIO_POLICY_SECTION_OBJECT_NAME = "shaderHealthInspectorSettingsStudioPolicySection"
SETTINGS_STUDIO_NAME_INPUT_OBJECT_NAME = "shaderHealthInspectorSettingsStudioNameInput"
SETTINGS_WAIVER_APPROVED_BY_INPUT_OBJECT_NAME = (
    "shaderHealthInspectorSettingsWaiverApprovedByInput"
)
SETTINGS_WAIVER_EXPIRY_DAYS_INPUT_OBJECT_NAME = (
    "shaderHealthInspectorSettingsWaiverExpiryDaysInput"
)
SETTINGS_ALLOW_CRITICAL_WAIVERS_TOGGLE_OBJECT_NAME = (
    "shaderHealthInspectorSettingsAllowCriticalWaiversToggle"
)
SETTINGS_MANIFEST_MAX_NEW_CHANGES_INPUT_OBJECT_NAME = (
    "shaderHealthInspectorSettingsManifestMaxNewChangesInput"
)
SETTINGS_MANIFEST_MAX_FINGERPRINT_CHANGES_INPUT_OBJECT_NAME = (
    "shaderHealthInspectorSettingsManifestMaxFingerprintChangesInput"
)
SETTINGS_MANIFEST_BLOCK_NEW_TEXTURES_TOGGLE_OBJECT_NAME = (
    "shaderHealthInspectorSettingsManifestBlockNewTexturesToggle"
)
SETTINGS_PINNED_WORKFLOW_PROFILES_INPUT_OBJECT_NAME = (
    "shaderHealthInspectorSettingsPinnedWorkflowProfilesInput"
)
SETTINGS_PINNED_ASSET_CLASS_PROFILES_INPUT_OBJECT_NAME = (
    "shaderHealthInspectorSettingsPinnedAssetClassProfilesInput"
)
SETTINGS_EXTRA_RULES_FOLDER_INPUT_OBJECT_NAME = (
    "shaderHealthInspectorSettingsExtraRulesFolderInput"
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
        "Studio-wide pipeline policy from shader_health_studio.json. "
        "Network paths live under Studio Environment; integrations under Connectors."
    )
    intro.setWordWrap(True)
    layout.addWidget(intro)

    form = qt_widgets.QFormLayout()
    set_form_margins = getattr(form, "setContentsMargins", None)
    if set_form_margins is not None:
        set_form_margins(0, 0, 0, 0)

    studio_name_input = qt_widgets.QLineEdit(config.studio_name)
    studio_name_input.setObjectName(SETTINGS_STUDIO_NAME_INPUT_OBJECT_NAME)
    studio_name_input.setPlaceholderText("Example Studio")
    studio_name_input.setToolTip("Display name for this studio deployment.")
    wire_line_edit_finished(studio_name_input, on_settings_changed)
    form.addRow("Studio name", studio_name_input)

    tx_row = qt_widgets.QHBoxLayout()
    tx_row.addWidget(
        qt_widgets.QLabel("Require .tx optimized texture derivatives")
    )
    tx_row.addStretch(1)
    tx_row.addWidget(
        build_settings_toggle(
            qt_widgets,
            object_name=SETTINGS_REQUIRE_TX_TOGGLE_OBJECT_NAME,
            enabled=config.pipeline.require_tx_derivatives,
            on_changed=on_require_tx_changed,
        )
    )
    form.addRow("Pipeline", _wrap_layout_widget(qt_widgets, tx_row))

    waiver_defaults = config.pipeline.waiver_defaults
    approved_by_input = qt_widgets.QLineEdit(waiver_defaults.default_approved_by)
    approved_by_input.setObjectName(SETTINGS_WAIVER_APPROVED_BY_INPUT_OBJECT_NAME)
    approved_by_input.setPlaceholderText("pipeline_td")
    approved_by_input.setToolTip("Default approver name prefilled in the waiver manager.")
    wire_line_edit_finished(approved_by_input, on_settings_changed)
    form.addRow("Default waiver approver", approved_by_input)

    expiry_input = qt_widgets.QLineEdit(str(waiver_defaults.default_expiry_days))
    expiry_input.setObjectName(SETTINGS_WAIVER_EXPIRY_DAYS_INPUT_OBJECT_NAME)
    expiry_input.setPlaceholderText(str(DEFAULT_WAIVER_EXPIRY_DAYS))
    expiry_input.setToolTip("Default waiver lifetime in days.")
    wire_line_edit_finished(expiry_input, on_settings_changed)
    form.addRow("Default waiver expiry (days)", expiry_input)

    critical_row = qt_widgets.QHBoxLayout()
    critical_row.addWidget(
        qt_widgets.QLabel("Allow waivers on critical farm-blocking issues")
    )
    critical_row.addStretch(1)
    critical_row.addWidget(
        build_settings_toggle(
            qt_widgets,
            object_name=SETTINGS_ALLOW_CRITICAL_WAIVERS_TOGGLE_OBJECT_NAME,
            enabled=waiver_defaults.allow_critical_waivers,
            on_changed=lambda _checked: on_settings_changed() if on_settings_changed else None,
        )
    )
    form.addRow("Waiver policy", _wrap_layout_widget(qt_widgets, critical_row))

    manifest_defaults = config.pipeline.manifest_gate_defaults
    max_new_input = qt_widgets.QLineEdit(str(manifest_defaults.max_new_changes))
    max_new_input.setObjectName(SETTINGS_MANIFEST_MAX_NEW_CHANGES_INPUT_OBJECT_NAME)
    max_new_input.setToolTip("Maximum new manifest entries allowed before gate blocks.")
    wire_line_edit_finished(max_new_input, on_settings_changed)
    form.addRow("Manifest gate max new entries", max_new_input)

    max_fingerprint_input = qt_widgets.QLineEdit(
        str(manifest_defaults.max_fingerprint_changes)
    )
    max_fingerprint_input.setObjectName(
        SETTINGS_MANIFEST_MAX_FINGERPRINT_CHANGES_INPUT_OBJECT_NAME
    )
    max_fingerprint_input.setToolTip(
        "Maximum graph fingerprint changes allowed before gate blocks."
    )
    wire_line_edit_finished(max_fingerprint_input, on_settings_changed)
    form.addRow("Manifest gate max fingerprint changes", max_fingerprint_input)

    block_textures_row = qt_widgets.QHBoxLayout()
    block_textures_row.addWidget(
        qt_widgets.QLabel("Block manifest gate when new textures appear")
    )
    block_textures_row.addStretch(1)
    block_textures_row.addWidget(
        build_settings_toggle(
            qt_widgets,
            object_name=SETTINGS_MANIFEST_BLOCK_NEW_TEXTURES_TOGGLE_OBJECT_NAME,
            enabled=manifest_defaults.block_on_new_textures,
            on_changed=lambda _checked: on_settings_changed() if on_settings_changed else None,
        )
    )
    form.addRow("Manifest gate", _wrap_layout_widget(qt_widgets, block_textures_row))

    pinned_workflow_input = _build_plain_text_input(
        qt_widgets,
        object_name=SETTINGS_PINNED_WORKFLOW_PROFILES_INPUT_OBJECT_NAME,
        text=format_profile_id_list(config.pipeline.pinned_workflow_profile_ids),
        placeholder="artist_relaxed\npublish_strict",
        tooltip=(
            "Optional allow-list of workflow profile ids. "
            "Leave blank to expose every packaged workflow profile."
        ),
    )
    wire_plain_text_changed(pinned_workflow_input, on_settings_changed)
    form.addRow("Pinned workflow profiles", pinned_workflow_input)

    pinned_asset_class_input = _build_plain_text_input(
        qt_widgets,
        object_name=SETTINGS_PINNED_ASSET_CLASS_PROFILES_INPUT_OBJECT_NAME,
        text=format_profile_id_list(config.pipeline.pinned_asset_class_profile_ids),
        placeholder="asset_class_hero\nasset_class_prop",
        tooltip=(
            "Optional allow-list of asset class overlay profile ids. "
            "Leave blank to expose every packaged asset class profile."
        ),
    )
    wire_plain_text_changed(pinned_asset_class_input, on_settings_changed)
    form.addRow("Pinned asset class profiles", pinned_asset_class_input)

    extra_rules_input = qt_widgets.QLineEdit(config.pipeline.extra_rules_folder)
    extra_rules_input.setObjectName(SETTINGS_EXTRA_RULES_FOLDER_INPUT_OBJECT_NAME)
    extra_rules_input.setPlaceholderText("//studio/share/shader_health/extra_rules")
    extra_rules_input.setToolTip(
        "Studio folder where incident rule draft sidecars are exported from the rule wizard."
    )
    wire_line_edit_finished(extra_rules_input, on_settings_changed)
    form.addRow("Extra rules folder", extra_rules_input)

    layout.addLayout(form)

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
        studio_name=line_edit_text(view, qt_widgets, SETTINGS_STUDIO_NAME_INPUT_OBJECT_NAME),
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
            ),
            default_expiry_days=_positive_int(
                line_edit_text(view, qt_widgets, SETTINGS_WAIVER_EXPIRY_DAYS_INPUT_OBJECT_NAME),
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
    _set_plain_text(
        find_child(
            view,
            _plain_text_widget_type(qt_widgets),
            SETTINGS_PINNED_WORKFLOW_PROFILES_INPUT_OBJECT_NAME,
        ),
        format_profile_id_list(pipeline.pinned_workflow_profile_ids),
    )
    _set_plain_text(
        find_child(
            view,
            _plain_text_widget_type(qt_widgets),
            SETTINGS_PINNED_ASSET_CLASS_PROFILES_INPUT_OBJECT_NAME,
        ),
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
    from shader_health.core.manifest_gate import ManifestGatePolicy

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


def _wrap_layout_widget(qt_widgets: Any, layout: Any) -> Any:
    host = qt_widgets.QWidget()
    host.setLayout(layout)
    return host


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
