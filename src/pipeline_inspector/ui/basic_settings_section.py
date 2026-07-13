"""Basic user preferences section for the Settings Basic tab."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Optional

from pipeline_inspector.maya.validation_pipeline import (
    ASSET_CLASS_NONE_ID,
    ProfileOption,
    list_asset_class_profile_options,
    list_workflow_profile_options,
)
from pipeline_inspector.ui.settings_widgets import (
    find_child,
    wire_combo_changed,
    wire_line_edit_finished,
)
from pipeline_inspector.user_config import (
    DEFAULT_USER_DOCS_URL,
    SUPPORTED_SCAN_SCOPES,
    SUPPORTED_UI_DENSITIES,
    SUPPORTED_USER_THEMES,
    UserPreferences,
)

SETTINGS_BASIC_SECTION_OBJECT_NAME = "pipelineInspectorSettingsBasicSection"
SETTINGS_DEFAULT_PROFILE_COMBO_OBJECT_NAME = "pipelineInspectorSettingsDefaultProfileCombo"
SETTINGS_DEFAULT_ASSET_CLASS_COMBO_OBJECT_NAME = (
    "pipelineInspectorSettingsDefaultAssetClassCombo"
)
SETTINGS_DEFAULT_SCAN_SCOPE_COMBO_OBJECT_NAME = (
    "pipelineInspectorSettingsDefaultScanScopeCombo"
)
SETTINGS_UI_DENSITY_COMBO_OBJECT_NAME = "pipelineInspectorSettingsUiDensityCombo"
SETTINGS_THEME_COMBO_OBJECT_NAME = "pipelineInspectorSettingsThemeCombo"
SETTINGS_DOCS_URL_INPUT_OBJECT_NAME = "pipelineInspectorSettingsDocsUrlInput"

_DEFAULT_WORKFLOW_PROFILE_ID = "artist_relaxed"
_SCAN_SCOPE_OPTIONS = (
    ("Scene", "scene"),
    ("Selection", "selection"),
)
_UI_DENSITY_OPTIONS = (
    ("Comfortable", "comfortable"),
    ("Compact", "compact"),
)
_THEME_OPTIONS = (
    ("Classic", "classic"),
    ("Dark", "dark"),
)


def build_basic_settings_section(
    qt_widgets: Any,
    user_config: UserPreferences,
    *,
    on_preferences_changed: Optional[Callable[[], None]] = None,
    on_theme_changed: Optional[Callable[[], None]] = None,
) -> Any:
    """Build the Basic settings tab content."""

    section = qt_widgets.QWidget()
    section.setObjectName(SETTINGS_BASIC_SECTION_OBJECT_NAME)
    layout = qt_widgets.QVBoxLayout(section)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    intro = qt_widgets.QLabel(
        "Per-user defaults stored in user.json. Applied when the panel opens and "
        "when you click Save User Preferences."
    )
    intro.setWordWrap(True)
    layout.addWidget(intro)

    form = qt_widgets.QFormLayout()
    set_form_margins = getattr(form, "setContentsMargins", None)
    if set_form_margins is not None:
        set_form_margins(0, 0, 0, 0)

    workflow_options = _workflow_profile_options()
    profile_combo = _build_profile_combo(
        qt_widgets,
        object_name=SETTINGS_DEFAULT_PROFILE_COMBO_OBJECT_NAME,
        options=workflow_options,
        selected_id=_resolved_default_profile_id(user_config.default_profile_id),
        tooltip="Default workflow profile selected on panel open.",
    )
    wire_combo_changed(profile_combo, on_preferences_changed)
    form.addRow("Default workflow profile", profile_combo)

    asset_class_options = _asset_class_profile_options()
    asset_class_combo = _build_asset_class_combo(
        qt_widgets,
        object_name=SETTINGS_DEFAULT_ASSET_CLASS_COMBO_OBJECT_NAME,
        options=asset_class_options,
        selected_id=user_config.default_asset_class_id,
        tooltip="Default asset class overlay selected on panel open.",
    )
    wire_combo_changed(asset_class_combo, on_preferences_changed)
    form.addRow("Default asset class", asset_class_combo)

    scan_scope_combo = _build_value_combo(
        qt_widgets,
        object_name=SETTINGS_DEFAULT_SCAN_SCOPE_COMBO_OBJECT_NAME,
        options=_SCAN_SCOPE_OPTIONS,
        selected_value=user_config.default_scan_scope,
        tooltip="Default scan scope used for automatic revalidation.",
    )
    wire_combo_changed(scan_scope_combo, on_preferences_changed)
    form.addRow("Default scan scope", scan_scope_combo)

    density_combo = _build_value_combo(
        qt_widgets,
        object_name=SETTINGS_UI_DENSITY_COMBO_OBJECT_NAME,
        options=_UI_DENSITY_OPTIONS,
        selected_value=user_config.ui_density,
        tooltip="Compact reduces panel padding for smaller dock heights.",
    )
    wire_combo_changed(density_combo, on_preferences_changed)
    form.addRow("UI density", density_combo)

    theme_combo = _build_value_combo(
        qt_widgets,
        object_name=SETTINGS_THEME_COMBO_OBJECT_NAME,
        options=_THEME_OPTIONS,
        selected_value=user_config.theme,
        tooltip="Panel color theme. Changes apply immediately for live preview.",
    )
    def _on_theme_combo_changed() -> None:
        if on_theme_changed is not None:
            on_theme_changed()

    wire_combo_changed(theme_combo, _on_theme_combo_changed)
    form.addRow("UI theme", theme_combo)

    docs_url_input = qt_widgets.QLineEdit(user_config.docs_url)
    docs_url_input.setObjectName(SETTINGS_DOCS_URL_INPUT_OBJECT_NAME)
    docs_url_input.setPlaceholderText(DEFAULT_USER_DOCS_URL)
    docs_url_input.setToolTip(
        "Documentation opened by the panel header Documentation button."
    )
    wire_line_edit_finished(docs_url_input, on_preferences_changed)
    form.addRow("Documentation URL", docs_url_input)

    layout.addLayout(form)
    layout.addStretch(1)
    return section


def read_basic_user_preferences_from_view(
    view: Any,
    qt_widgets: Any,
    *,
    base: UserPreferences | None = None,
) -> UserPreferences:
    """Read Basic tab fields into a UserPreferences object."""

    current = base or UserPreferences.default()
    profile_combo = find_child(
        view,
        qt_widgets.QComboBox,
        SETTINGS_DEFAULT_PROFILE_COMBO_OBJECT_NAME,
    )
    asset_class_combo = find_child(
        view,
        qt_widgets.QComboBox,
        SETTINGS_DEFAULT_ASSET_CLASS_COMBO_OBJECT_NAME,
    )
    scan_scope_combo = find_child(
        view,
        qt_widgets.QComboBox,
        SETTINGS_DEFAULT_SCAN_SCOPE_COMBO_OBJECT_NAME,
    )
    density_combo = find_child(view, qt_widgets.QComboBox, SETTINGS_UI_DENSITY_COMBO_OBJECT_NAME)
    theme_combo = find_child(view, qt_widgets.QComboBox, SETTINGS_THEME_COMBO_OBJECT_NAME)
    docs_url_input = find_child(view, qt_widgets.QLineEdit, SETTINGS_DOCS_URL_INPUT_OBJECT_NAME)

    default_profile_id = _combo_data(profile_combo)
    default_asset_class_id = _combo_data(asset_class_combo)
    default_scan_scope = _combo_data(scan_scope_combo, options=_SCAN_SCOPE_OPTIONS) or "scene"
    ui_density = _combo_data(density_combo, options=_UI_DENSITY_OPTIONS) or "comfortable"
    theme = _combo_data(theme_combo, options=_THEME_OPTIONS) or "classic"

    if default_scan_scope not in SUPPORTED_SCAN_SCOPES:
        default_scan_scope = "scene"
    if ui_density not in SUPPORTED_UI_DENSITIES:
        ui_density = "comfortable"
    if theme not in SUPPORTED_USER_THEMES:
        theme = "classic"
    docs_url = _line_edit_text(docs_url_input) or DEFAULT_USER_DOCS_URL

    return current.with_updates(
        default_profile_id=default_profile_id,
        default_asset_class_id=default_asset_class_id,
        default_scan_scope=default_scan_scope,
        ui_density=ui_density,
        theme=theme,
        docs_url=docs_url,
    )


def update_basic_settings_view(
    view: Any,
    qt_widgets: Any,
    user_config: UserPreferences,
) -> None:
    """Refresh Basic tab controls from user preferences."""

    workflow_options = _workflow_profile_options()
    _set_profile_combo_selection(
        find_child(view, qt_widgets.QComboBox, SETTINGS_DEFAULT_PROFILE_COMBO_OBJECT_NAME),
        workflow_options,
        _resolved_default_profile_id(user_config.default_profile_id),
    )
    _set_asset_class_combo_selection(
        find_child(view, qt_widgets.QComboBox, SETTINGS_DEFAULT_ASSET_CLASS_COMBO_OBJECT_NAME),
        _asset_class_profile_options(),
        user_config.default_asset_class_id,
    )
    _set_value_combo_selection(
        find_child(view, qt_widgets.QComboBox, SETTINGS_DEFAULT_SCAN_SCOPE_COMBO_OBJECT_NAME),
        _SCAN_SCOPE_OPTIONS,
        user_config.default_scan_scope,
    )
    _set_value_combo_selection(
        find_child(view, qt_widgets.QComboBox, SETTINGS_UI_DENSITY_COMBO_OBJECT_NAME),
        _UI_DENSITY_OPTIONS,
        user_config.ui_density,
    )
    _set_value_combo_selection(
        find_child(view, qt_widgets.QComboBox, SETTINGS_THEME_COMBO_OBJECT_NAME),
        _THEME_OPTIONS,
        user_config.theme,
    )
    docs_url_input = find_child(view, qt_widgets.QLineEdit, SETTINGS_DOCS_URL_INPUT_OBJECT_NAME)
    if docs_url_input is not None:
        set_text = getattr(docs_url_input, "setText", None)
        if set_text is not None:
            set_text(user_config.docs_url)


def prepare_basic_settings_interactions(
    view: Any,
    qt_widgets: Any,
    user_config: UserPreferences,
    *,
    on_preferences_changed: Optional[Callable[[], None]] = None,
    on_theme_changed: Optional[Callable[[], None]] = None,
) -> None:
    """Refresh Basic tab controls and ensure live theme preview wiring."""

    update_basic_settings_view(view, qt_widgets, user_config)

    if on_preferences_changed is not None:
        density_combo = find_child(
            view,
            qt_widgets.QComboBox,
            SETTINGS_UI_DENSITY_COMBO_OBJECT_NAME,
        )
        if density_combo is not None:
            wire_combo_changed(density_combo, on_preferences_changed)

    theme_combo = find_child(view, qt_widgets.QComboBox, SETTINGS_THEME_COMBO_OBJECT_NAME)
    if theme_combo is None:
        return

    def _on_theme_combo_changed() -> None:
        if on_theme_changed is not None:
            on_theme_changed()
        if on_preferences_changed is not None:
            on_preferences_changed()

    wire_combo_changed(theme_combo, _on_theme_combo_changed)


def _workflow_profile_options() -> tuple[ProfileOption, ...]:
    options = list_workflow_profile_options()
    if options:
        return options
    return (
        ProfileOption("artist_relaxed", "Artist Relaxed"),
        ProfileOption("publish_strict", "Publish Strict"),
        ProfileOption("deadline_critical", "Deadline Critical"),
        ProfileOption("supervisor_full", "Supervisor Full"),
    )


def _asset_class_profile_options() -> tuple[ProfileOption, ...]:
    return list_asset_class_profile_options()


def _resolved_default_profile_id(profile_id: str) -> str:
    normalized = profile_id.strip()
    return normalized or _DEFAULT_WORKFLOW_PROFILE_ID


def _build_profile_combo(
    qt_widgets: Any,
    *,
    object_name: str,
    options: Sequence[ProfileOption],
    selected_id: str,
    tooltip: str,
) -> Any:
    combo = qt_widgets.QComboBox()
    combo.setObjectName(object_name)
    for option in options:
        combo.addItem(option.display_name, option.profile_id)
    _set_profile_combo_selection(combo, options, selected_id)
    combo.setToolTip(tooltip)
    return combo


def _build_asset_class_combo(
    qt_widgets: Any,
    *,
    object_name: str,
    options: Sequence[ProfileOption],
    selected_id: str,
    tooltip: str,
) -> Any:
    combo = qt_widgets.QComboBox()
    combo.setObjectName(object_name)
    combo.addItem("None", ASSET_CLASS_NONE_ID)
    for option in options:
        combo.addItem(option.display_name, option.profile_id)
    _set_asset_class_combo_selection(combo, options, selected_id)
    combo.setToolTip(tooltip)
    return combo


def _build_value_combo(
    qt_widgets: Any,
    *,
    object_name: str,
    options: Sequence[tuple[str, str]],
    selected_value: str,
    tooltip: str,
) -> Any:
    combo = qt_widgets.QComboBox()
    combo.setObjectName(object_name)
    for label, value in options:
        combo.addItem(label, value)
    _set_value_combo_selection(combo, options, selected_value)
    combo.setToolTip(tooltip)
    return combo


def _set_profile_combo_selection(
    combo: Any | None,
    options: Sequence[ProfileOption],
    selected_id: str,
) -> None:
    if combo is None:
        return
    if _set_combo_data(combo, selected_id):
        return
    for option in options:
        if option.profile_id == selected_id:
            set_text = getattr(combo, "setCurrentText", None)
            if set_text is not None:
                set_text(option.display_name)
            return


def _set_asset_class_combo_selection(
    combo: Any | None,
    options: Sequence[ProfileOption],
    selected_id: str,
) -> None:
    if combo is None:
        return
    normalized = selected_id.strip() or ASSET_CLASS_NONE_ID
    if normalized == ASSET_CLASS_NONE_ID:
        set_index = getattr(combo, "setCurrentIndex", None)
        if set_index is not None:
            set_index(0)
        return
    _set_profile_combo_selection(combo, options, normalized)


def _set_value_combo_selection(
    combo: Any | None,
    options: Sequence[tuple[str, str]],
    selected_value: str,
) -> None:
    if combo is None:
        return
    if _set_combo_data(combo, selected_value):
        return
    for index, (_label, value) in enumerate(options):
        if value != selected_value:
            continue
        set_current_index = getattr(combo, "setCurrentIndex", None)
        block_signals = getattr(combo, "blockSignals", None)
        if set_current_index is None:
            break
        blocked = False
        if block_signals is not None:
            blocked = bool(block_signals(True))
        try:
            set_current_index(index)
        finally:
            if block_signals is not None and blocked:
                block_signals(False)
        return


def _set_combo_data(combo: Any, data: str) -> bool:
    find_data = getattr(combo, "findData", None)
    set_current_index = getattr(combo, "setCurrentIndex", None)
    block_signals = getattr(combo, "blockSignals", None)
    if find_data is None or set_current_index is None:
        return False
    index = find_data(data)
    if index is None or index < 0:
        return False
    blocked = False
    if block_signals is not None:
        blocked = bool(block_signals(True))
    try:
        set_current_index(index)
    finally:
        if block_signals is not None and blocked:
            block_signals(False)
    return True


def _combo_data(
    combo: Any | None,
    *,
    options: Sequence[tuple[str, str]] | None = None,
) -> str:
    if combo is None:
        return ""
    current_data = getattr(combo, "currentData", None)
    if current_data is not None:
        data = current_data()
        if data is not None:
            return str(data)
    current_text = getattr(combo, "currentText", lambda: "")()
    text = str(current_text or "").strip()
    if options:
        for label, value in options:
            if text.casefold() == label.casefold():
                return value
        for _label, value in options:
            if text.casefold() == value.casefold():
                return value
    return text


def _line_edit_text(field: Any | None) -> str:
    if field is None:
        return ""
    text_fn = getattr(field, "text", None)
    if text_fn is None:
        return ""
    return str(text_fn() or "").strip()
