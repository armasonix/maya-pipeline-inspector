"""Rule browser and safe field editor dialog for packaged rules."""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from shader_health.core.rule_browser import (
    SAFE_SEVERITIES,
    RuleBrowserEntry,
    build_session_override_from_edits,
    editable_fields_for_rule,
    effective_rule,
    validate_effective_rule,
    validate_session_overrides,
)
from shader_health.core.rule_loader import RuleOverride
from shader_health.core.rule_pack_validation import RuleValidationFailure
from shader_health.ui.settings_widgets import wire_button

RULE_EDITOR_DIALOG_OBJECT_NAME = "shaderHealthInspectorRuleEditorDialog"
RULE_BROWSER_LIST_OBJECT_NAME = "shaderHealthInspectorRuleBrowserList"
RULE_EDITOR_NAME_LABEL_OBJECT_NAME = "shaderHealthInspectorRuleEditorNameLabel"
RULE_EDITOR_SOURCE_LABEL_OBJECT_NAME = "shaderHealthInspectorRuleEditorSourceLabel"
RULE_EDITOR_ENABLED_TOGGLE_OBJECT_NAME = "shaderHealthInspectorRuleEditorEnabledToggle"
RULE_EDITOR_SEVERITY_COMBO_OBJECT_NAME = "shaderHealthInspectorRuleEditorSeverityCombo"
RULE_EDITOR_THRESHOLD_INPUT_OBJECT_NAME = "shaderHealthInspectorRuleEditorThresholdInput"
RULE_EDITOR_THRESHOLD_LABEL_OBJECT_NAME = "shaderHealthInspectorRuleEditorThresholdLabel"
RULE_EDITOR_STATUS_LABEL_OBJECT_NAME = "shaderHealthInspectorRuleEditorStatusLabel"
RULE_EDITOR_APPLY_BUTTON_OBJECT_NAME = "shaderHealthInspectorRuleEditorApplyButton"
RULE_EDITOR_SAVE_BUTTON_OBJECT_NAME = "shaderHealthInspectorRuleEditorSaveButton"
RULE_EDITOR_CLOSE_BUTTON_OBJECT_NAME = "shaderHealthInspectorRuleEditorCloseButton"

RULE_EDITOR_INTRO = (
    "Browse packaged validation rules and edit the safe enabled, severity, and threshold "
    "subset. Save runs the same schema checks as tools/validate_rules.py before applying "
    "session overrides for the current Maya session."
)

_RULE_EDITOR_LABEL_WIDTH = 88
_RULE_EDITOR_FIELD_WIDTH = 140


@dataclass(eq=False)
class RuleEditorDialog:
    """Controller for the rule browser and safe field editor."""

    dialog: Any
    rule_list: Any
    name_label: Any
    source_label: Any
    enabled_toggle: Any
    severity_combo: Any
    threshold_label: Any
    threshold_input: Any
    threshold_row: Any
    status_label: Any
    entries: tuple[RuleBrowserEntry, ...]
    session_overrides: dict[str, RuleOverride]
    on_save: Callable[[dict[str, RuleOverride]], None] | None = None

    @classmethod
    def build(
        cls,
        qt_widgets: Any,
        *,
        catalog: Sequence[RuleBrowserEntry],
        session_overrides: Mapping[str, RuleOverride] | None = None,
        on_save: Callable[[dict[str, RuleOverride]], None] | None = None,
        window_title: str = "Rule Editor",
    ) -> RuleEditorDialog:
        dialog = qt_widgets.QDialog()
        dialog.setObjectName(RULE_EDITOR_DIALOG_OBJECT_NAME)
        set_window_title = getattr(dialog, "setWindowTitle", None)
        if set_window_title is not None:
            set_window_title(window_title)

        layout = qt_widgets.QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        intro = qt_widgets.QLabel(RULE_EDITOR_INTRO)
        set_word_wrap = getattr(intro, "setWordWrap", None)
        if set_word_wrap is not None:
            set_word_wrap(True)
        layout.addWidget(intro)

        rule_list = qt_widgets.QListWidget()
        rule_list.setObjectName(RULE_BROWSER_LIST_OBJECT_NAME)
        for entry in catalog:
            item = qt_widgets.QListWidgetItem(_rule_list_label(entry))
            set_data = getattr(item, "setData", None)
            if set_data is not None:
                set_data(256, entry.rule.id)
            add_item = getattr(rule_list, "addItem", None)
            if add_item is not None:
                add_item(item)
        layout.addWidget(rule_list)

        name_label = qt_widgets.QLabel("")
        name_label.setObjectName(RULE_EDITOR_NAME_LABEL_OBJECT_NAME)
        set_name_word_wrap = getattr(name_label, "setWordWrap", None)
        if set_name_word_wrap is not None:
            set_name_word_wrap(True)
        layout.addWidget(name_label)

        source_label = qt_widgets.QLabel("")
        source_label.setObjectName(RULE_EDITOR_SOURCE_LABEL_OBJECT_NAME)
        set_source_word_wrap = getattr(source_label, "setWordWrap", None)
        if set_source_word_wrap is not None:
            set_source_word_wrap(True)
        layout.addWidget(source_label)

        enabled_toggle = _build_enabled_toggle(qt_widgets)
        layout.addWidget(
            _rule_editor_field_row(qt_widgets, "Enabled", enabled_toggle),
        )

        severity_combo = qt_widgets.QComboBox()
        severity_combo.setObjectName(RULE_EDITOR_SEVERITY_COMBO_OBJECT_NAME)
        add_items = getattr(severity_combo, "addItems", None)
        if add_items is not None:
            add_items(list(SAFE_SEVERITIES))
        set_fixed_width = getattr(severity_combo, "setFixedWidth", None)
        if set_fixed_width is not None:
            set_fixed_width(_RULE_EDITOR_FIELD_WIDTH)
        layout.addWidget(
            _rule_editor_field_row(qt_widgets, "Severity", severity_combo),
        )

        threshold_label = qt_widgets.QLabel("Threshold")
        threshold_label.setObjectName(RULE_EDITOR_THRESHOLD_LABEL_OBJECT_NAME)
        threshold_input = qt_widgets.QLineEdit()
        threshold_input.setObjectName(RULE_EDITOR_THRESHOLD_INPUT_OBJECT_NAME)
        set_threshold_width = getattr(threshold_input, "setFixedWidth", None)
        if set_threshold_width is not None:
            set_threshold_width(_RULE_EDITOR_FIELD_WIDTH)
        threshold_row = _rule_editor_field_row(
            qt_widgets,
            threshold_label,
            threshold_input,
        )
        layout.addWidget(threshold_row)

        status_label = qt_widgets.QLabel("")
        status_label.setObjectName(RULE_EDITOR_STATUS_LABEL_OBJECT_NAME)
        set_status_word_wrap = getattr(status_label, "setWordWrap", None)
        if set_status_word_wrap is not None:
            set_status_word_wrap(True)
        layout.addWidget(status_label)

        button_row = qt_widgets.QHBoxLayout()
        apply_button = qt_widgets.QPushButton("Apply")
        apply_button.setObjectName(RULE_EDITOR_APPLY_BUTTON_OBJECT_NAME)
        save_button = qt_widgets.QPushButton("Save")
        save_button.setObjectName(RULE_EDITOR_SAVE_BUTTON_OBJECT_NAME)
        close_button = qt_widgets.QPushButton("Close")
        close_button.setObjectName(RULE_EDITOR_CLOSE_BUTTON_OBJECT_NAME)
        button_row.addWidget(apply_button)
        button_row.addWidget(save_button)
        button_row.addStretch(1)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

        controller = cls(
            dialog=dialog,
            rule_list=rule_list,
            name_label=name_label,
            source_label=source_label,
            enabled_toggle=enabled_toggle,
            severity_combo=severity_combo,
            threshold_label=threshold_label,
            threshold_input=threshold_input,
            threshold_row=threshold_row,
            status_label=status_label,
            entries=tuple(catalog),
            session_overrides=dict(session_overrides or {}),
            on_save=on_save,
        )
        wire_button(close_button, lambda: _close_dialog(dialog))

        def _apply_selected_rule() -> None:
            controller.apply_selected_rule()

        def _save_session_overrides() -> None:
            controller.save_session_overrides()

        wire_button(apply_button, _apply_selected_rule)
        wire_button(save_button, _save_session_overrides)
        current_row_changed = getattr(rule_list, "currentRowChanged", None)
        if current_row_changed is not None:
            current_row_changed.connect(lambda row: controller.load_selected_rule(row))
        if controller.entries:
            set_current_row = getattr(rule_list, "setCurrentRow", None)
            if set_current_row is not None:
                set_current_row(0)
            controller.load_selected_rule(0)
        else:
            controller.set_status_message("No packaged rules found.")
        return controller

    def selected_entry(self) -> RuleBrowserEntry | None:
        current_row = getattr(self.rule_list, "currentRow", lambda: -1)()
        if current_row < 0 or current_row >= len(self.entries):
            return None
        return self.entries[current_row]

    def load_selected_rule(self, _row: int = 0) -> None:
        entry = self.selected_entry()
        if entry is None:
            return
        override = self.session_overrides.get(entry.rule.id)
        rule = effective_rule(entry, override)
        fields = editable_fields_for_rule(rule)
        self.name_label.setText(f"{rule.name} ({rule.id})")
        self.source_label.setText(f"Source: {entry.source_label}")
        _set_toggle_checked(self.enabled_toggle, fields.enabled)
        _set_combo_text(self.severity_combo, fields.severity)
        threshold_visible = fields.threshold_editable
        _set_widget_visible(self.threshold_row, threshold_visible)
        if threshold_visible and fields.threshold_value is not None:
            self.threshold_label.setText(f"Threshold ({fields.threshold_key})")
            self.threshold_input.setText(str(fields.threshold_value))
            set_enabled = getattr(self.threshold_input, "setEnabled", None)
            if set_enabled is not None:
                set_enabled(True)
        else:
            self.threshold_label.setText("Threshold")
            self.threshold_input.setText("")
            set_enabled = getattr(self.threshold_input, "setEnabled", None)
            if set_enabled is not None:
                set_enabled(False)
        if override is None:
            self.set_status_message("Using packaged defaults.")
        else:
            self.set_status_message("Session override active for this rule.")

    def apply_selected_rule(self) -> None:
        entry = self.selected_entry()
        if entry is None:
            self.set_status_message("Select a rule to edit.")
            return
        try:
            enabled = _toggle_checked(self.enabled_toggle)
            severity = _combo_text(self.severity_combo)
            threshold_key = ""
            threshold_value: int | float | None = None
            fields = editable_fields_for_rule(entry.rule)
            if fields.threshold_editable:
                threshold_key = fields.threshold_key
                threshold_value = _parse_threshold_text(
                    _line_edit_text(self.threshold_input),
                )
            override = build_session_override_from_edits(
                entry.rule,
                enabled=enabled,
                severity=severity,
                threshold_key=threshold_key,
                threshold_value=threshold_value,
            )
        except ValueError as exc:
            self.set_status_message(str(exc))
            return

        try:
            validate_effective_rule(entry, override)
        except RuleValidationFailure as exc:
            self.set_status_message(f"validate_rules check failed: {exc}")
            return

        if override is None:
            self.session_overrides.pop(entry.rule.id, None)
            self.set_status_message("Session override cleared; packaged defaults restored.")
        else:
            self.session_overrides[entry.rule.id] = override
            self.set_status_message("Session override saved for this rule.")
        self.load_selected_rule(getattr(self.rule_list, "currentRow", lambda: 0)())

    def save_session_overrides(self) -> bool:
        """Apply pending edits, validate overrides, and persist to the panel session."""

        self.apply_selected_rule()
        errors = validate_session_overrides(self.entries, self.session_overrides)
        if errors:
            self.set_status_message(errors[0])
            return False

        if self.on_save is not None:
            self.on_save(dict(self.session_overrides))

        count = len(self.session_overrides)
        if count:
            self.set_status_message(
                f"Saved {count} session override(s) after validate_rules checks."
            )
        else:
            self.set_status_message("Saved with no active session overrides.")
        return True

    def set_status_message(self, message: str) -> None:
        set_text = getattr(self.status_label, "setText", None)
        if set_text is not None:
            set_text(message)

    def show(
        self,
        *,
        parent: Any | None = None,
        modal: bool = True,
        qt_widgets: Any | None = None,
    ) -> None:
        if modal and qt_widgets is not None:
            from shader_health.ui.settings_widgets import show_modal_dialog

            show_modal_dialog(self.dialog, qt_widgets, singleton_key=RULE_EDITOR_DIALOG_OBJECT_NAME)
            return
        if parent is not None:
            set_parent = getattr(self.dialog, "setParent", None)
            if set_parent is not None:
                set_parent(parent)
        exec_fn = getattr(self.dialog, "exec_", None) or getattr(self.dialog, "exec", None)
        if modal and exec_fn is not None:
            exec_fn()
            return
        show = getattr(self.dialog, "show", None)
        if show is not None:
            show()


def show_rule_editor_dialog(
    qt_widgets: Any,
    *,
    parent: Any | None = None,
    catalog: Sequence[RuleBrowserEntry],
    session_overrides: Mapping[str, RuleOverride] | None = None,
    on_save: Callable[[dict[str, RuleOverride]], None] | None = None,
) -> dict[str, RuleOverride]:
    """Display the rule browser dialog and return the session override map."""

    dialog = RuleEditorDialog.build(
        qt_widgets,
        catalog=catalog,
        session_overrides=session_overrides,
        on_save=on_save,
    )
    dialog.show(parent=parent, modal=True, qt_widgets=qt_widgets)
    return dict(dialog.session_overrides)


def _rule_list_label(entry: RuleBrowserEntry) -> str:
    return f"{entry.rule.id} — {entry.rule.name}"


def _rule_editor_field_row(
    qt_widgets: Any,
    label: Any,
    field: Any,
) -> Any:
    from shader_health.ui.settings_widgets import set_fixed_horizontal_size_policy

    row = qt_widgets.QHBoxLayout()
    set_margins = getattr(row, "setContentsMargins", None)
    if set_margins is not None:
        set_margins(0, 0, 0, 0)
    set_spacing = getattr(row, "setSpacing", None)
    if set_spacing is not None:
        set_spacing(8)

    caption = qt_widgets.QLabel(label) if isinstance(label, str) else label
    set_fixed_width = getattr(caption, "setFixedWidth", None)
    if set_fixed_width is not None:
        set_fixed_width(_RULE_EDITOR_LABEL_WIDTH)
    set_word_wrap = getattr(caption, "setWordWrap", None)
    if set_word_wrap is not None:
        set_word_wrap(True)
    set_fixed_horizontal_size_policy(qt_widgets, caption)
    row.addWidget(caption, 0)
    set_fixed_horizontal_size_policy(qt_widgets, field)
    row.addWidget(field, 0)
    add_stretch = getattr(row, "addStretch", None)
    if add_stretch is not None:
        add_stretch(1)

    host = qt_widgets.QWidget()
    host.setLayout(row)
    return host


def _set_widget_visible(widget: Any, visible: bool) -> None:
    set_visible = getattr(widget, "setVisible", None)
    if set_visible is not None:
        set_visible(visible)


def _build_enabled_toggle(qt_widgets: Any) -> Any:
    from shader_health.ui.settings_widgets import build_settings_toggle

    return build_settings_toggle(
        qt_widgets,
        object_name=RULE_EDITOR_ENABLED_TOGGLE_OBJECT_NAME,
        enabled=True,
    )


def _set_toggle_checked(toggle: Any, enabled: bool) -> None:
    set_checked = getattr(toggle, "setChecked", None)
    if set_checked is not None:
        set_checked(enabled)
        return
    set_text = getattr(toggle, "setText", None)
    if set_text is not None:
        set_text("ON" if enabled else "OFF")


def _toggle_checked(toggle: Any) -> bool:
    is_checked = getattr(toggle, "isChecked", None)
    if is_checked is not None:
        return bool(is_checked())
    text = str(getattr(toggle, "text", lambda: "")() or "")
    return text.strip().upper() == "ON"


def _set_combo_text(combo: Any, value: str) -> None:
    set_current_text = getattr(combo, "setCurrentText", None)
    if set_current_text is not None:
        set_current_text(value)


def _combo_text(combo: Any) -> str:
    current_text = getattr(combo, "currentText", None)
    if current_text is not None:
        return str(current_text() or "")
    return ""


def _line_edit_text(line_edit: Any) -> str:
    text = getattr(line_edit, "text", None)
    if text is not None:
        return str(text() or "")
    return ""


def _parse_threshold_text(text: str) -> int | float:
    normalized = text.strip()
    if not normalized:
        raise ValueError("Threshold value is required.")
    if "." in normalized:
        value: int | float = float(normalized)
    else:
        value = int(normalized)
    if value < 0:
        raise ValueError("Threshold must be zero or greater.")
    return value


def _close_dialog(dialog: Any) -> None:
    reject = getattr(dialog, "reject", None)
    if reject is not None:
        reject()
        return
    close = getattr(dialog, "close", None)
    if close is not None:
        close()
