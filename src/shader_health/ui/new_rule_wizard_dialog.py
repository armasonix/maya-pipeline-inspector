"""New rule wizard dialog for creating JSON rule drafts from templates."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shader_health.core.rule_schema import SEVERITIES
from shader_health.core.rule_wizard import (
    NewRuleDraftInput,
    RuleDraftValidationResult,
    RuleTemplateSpec,
    build_rule_draft,
    default_draft_input_for_template,
    list_rule_templates,
    validate_new_rule_draft,
    write_rule_draft_file,
)
from shader_health.ui.settings_widgets import wire_button

NEW_RULE_WIZARD_DIALOG_OBJECT_NAME = "shaderHealthInspectorNewRuleWizardDialog"
NEW_RULE_WIZARD_TEMPLATE_COMBO_OBJECT_NAME = "shaderHealthInspectorNewRuleWizardTemplateCombo"
NEW_RULE_WIZARD_STATUS_LABEL_OBJECT_NAME = "shaderHealthInspectorNewRuleWizardStatusLabel"
NEW_RULE_WIZARD_OUTPUT_PATH_INPUT_OBJECT_NAME = (
    "shaderHealthInspectorNewRuleWizardOutputPathInput"
)
NEW_RULE_WIZARD_VALIDATE_BUTTON_OBJECT_NAME = (
    "shaderHealthInspectorNewRuleWizardValidateButton"
)
NEW_RULE_WIZARD_SAVE_BUTTON_OBJECT_NAME = "shaderHealthInspectorNewRuleWizardSaveButton"
NEW_RULE_WIZARD_CLOSE_BUTTON_OBJECT_NAME = "shaderHealthInspectorNewRuleWizardCloseButton"

NEW_RULE_WIZARD_INTRO = (
    "Create a JSON rule draft from a starter template. Validation uses the same schema "
    "checks as tools/validate_rules.py and rejects duplicate rule ids already loaded "
    "from packaged rules and extra rule roots."
)

_COMMON_FIELD_SPECS: tuple[tuple[str, str], ...] = (
    ("rule_id", "Rule id"),
    ("name", "Name"),
    ("message", "Message"),
    ("why", "Why"),
    ("severity", "Severity"),
    ("owner", "Owner"),
    ("scope", "Scope"),
    ("output_path", "Output JSON path"),
)


@dataclass
class NewRuleWizardDialog:
    """Controller for the new rule wizard dialog."""

    dialog: Any
    template_combo: Any
    field_inputs: dict[str, Any]
    status_label: Any
    validate_button: Any
    save_button: Any
    templates: tuple[RuleTemplateSpec, ...]
    known_rule_ids: frozenset[str]
    last_validation: RuleDraftValidationResult | None = None

    @classmethod
    def build(
        cls,
        qt_widgets: Any,
        *,
        known_rule_ids: Iterable[str] = (),
        default_output_path: str = "",
        window_title: str = "New Rule Wizard",
    ) -> NewRuleWizardDialog:
        templates = list_rule_templates()
        dialog = qt_widgets.QDialog()
        dialog.setObjectName(NEW_RULE_WIZARD_DIALOG_OBJECT_NAME)
        set_window_title = getattr(dialog, "setWindowTitle", None)
        if set_window_title is not None:
            set_window_title(window_title)

        layout = qt_widgets.QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        intro = qt_widgets.QLabel(NEW_RULE_WIZARD_INTRO)
        set_word_wrap = getattr(intro, "setWordWrap", None)
        if set_word_wrap is not None:
            set_word_wrap(True)
        layout.addWidget(intro)

        form = qt_widgets.QFormLayout()
        set_form_margins = getattr(form, "setContentsMargins", None)
        if set_form_margins is not None:
            set_form_margins(0, 0, 0, 0)

        template_combo = qt_widgets.QComboBox()
        template_combo.setObjectName(NEW_RULE_WIZARD_TEMPLATE_COMBO_OBJECT_NAME)
        add_items = getattr(template_combo, "addItems", None)
        if add_items is not None:
            add_items([template.label for template in templates])
        form.addRow("Template", template_combo)

        field_inputs: dict[str, Any] = {}
        for field_name, label in _COMMON_FIELD_SPECS:
            if field_name == "severity":
                widget = qt_widgets.QComboBox()
                add_severity = getattr(widget, "addItems", None)
                if add_severity is not None:
                    add_severity(list(sorted(SEVERITIES)))
            else:
                widget = qt_widgets.QLineEdit()
            widget.setObjectName(_field_object_name(field_name))
            field_inputs[field_name] = widget
            form.addRow(label, widget)

        for field_name, label in (
            ("attribute", "Attribute"),
            ("expected", "Expected value"),
            ("max_value", "Maximum"),
            ("dependency_kind", "Dependency kind"),
        ):
            widget = qt_widgets.QLineEdit()
            widget.setObjectName(_field_object_name(field_name))
            field_inputs[field_name] = widget
            form.addRow(label, widget)

        layout.addLayout(form)

        status_label = qt_widgets.QLabel("")
        status_label.setObjectName(NEW_RULE_WIZARD_STATUS_LABEL_OBJECT_NAME)
        set_status_word_wrap = getattr(status_label, "setWordWrap", None)
        if set_status_word_wrap is not None:
            set_status_word_wrap(True)
        layout.addWidget(status_label)

        button_row = qt_widgets.QHBoxLayout()
        validate_button = qt_widgets.QPushButton("Validate Draft")
        validate_button.setObjectName(NEW_RULE_WIZARD_VALIDATE_BUTTON_OBJECT_NAME)
        save_button = qt_widgets.QPushButton("Save Draft")
        save_button.setObjectName(NEW_RULE_WIZARD_SAVE_BUTTON_OBJECT_NAME)
        close_button = qt_widgets.QPushButton("Close")
        close_button.setObjectName(NEW_RULE_WIZARD_CLOSE_BUTTON_OBJECT_NAME)
        button_row.addWidget(validate_button)
        button_row.addWidget(save_button)
        button_row.addStretch(1)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

        controller = cls(
            dialog=dialog,
            template_combo=template_combo,
            field_inputs=field_inputs,
            status_label=status_label,
            validate_button=validate_button,
            save_button=save_button,
            templates=templates,
            known_rule_ids=frozenset(known_rule_ids),
        )
        def _validate_draft() -> None:
            controller.validate_draft()

        def _save_draft() -> None:
            controller.save_draft()

        wire_button(close_button, lambda: _close_dialog(dialog))
        wire_button(validate_button, _validate_draft)
        wire_button(save_button, _save_draft)
        current_index_changed = getattr(template_combo, "currentIndexChanged", None)
        if current_index_changed is not None:
            current_index_changed.connect(controller.load_template_defaults)
        controller.load_template_defaults(0)
        if default_output_path:
            controller.field_inputs["output_path"].setText(default_output_path)
        return controller

    def selected_template(self) -> RuleTemplateSpec:
        index = getattr(self.template_combo, "currentIndex", lambda: 0)()
        if index < 0 or index >= len(self.templates):
            return self.templates[0]
        return self.templates[index]

    def load_template_defaults(self, _index: int = 0) -> None:
        template = self.selected_template()
        defaults = default_draft_input_for_template(template.template_id)
        self._set_field_text("rule_id", defaults.rule_id)
        self._set_field_text("name", defaults.name)
        self._set_field_text("message", defaults.message)
        self._set_field_text("why", defaults.why)
        self._set_combo_text("severity", defaults.severity)
        self._set_field_text("owner", defaults.owner)
        self._set_field_text("scope", defaults.scope)
        self._set_field_text("attribute", defaults.attribute)
        self._set_field_text("expected", defaults.expected)
        if defaults.max_value is not None:
            self._set_field_text("max_value", str(defaults.max_value))
        else:
            self._set_field_text("max_value", "")
        self._set_field_text("dependency_kind", defaults.dependency_kind)
        self.last_validation = None
        self.set_status_message(f"Loaded template: {template.label}")

    def read_draft_input(self) -> NewRuleDraftInput:
        max_value = _parse_optional_number(self._field_text("max_value"))
        return NewRuleDraftInput(
            rule_id=self._field_text("rule_id"),
            name=self._field_text("name"),
            message=self._field_text("message"),
            why=self._field_text("why"),
            severity=self._combo_text("severity") or "warning",
            owner=self._field_text("owner") or "shader_td",
            scope=self._field_text("scope"),
            attribute=self._field_text("attribute"),
            expected=self._field_text("expected"),
            max_value=max_value,
            dependency_kind=self._field_text("dependency_kind") or "texture",
        )

    def build_draft(self) -> dict[str, Any]:
        return build_rule_draft(
            self.selected_template().template_id,
            self.read_draft_input(),
        )

    def validate_draft(self) -> RuleDraftValidationResult:
        try:
            draft = self.build_draft()
        except ValueError as exc:
            result = RuleDraftValidationResult(valid=False, rule=None, errors=(str(exc),))
            self.last_validation = result
            self.set_status_message(str(exc))
            return result

        result = validate_new_rule_draft(
            draft,
            known_rule_ids=self.known_rule_ids,
        )
        self.last_validation = result
        if result.valid:
            self.set_status_message(f"Draft valid for rule id {draft['id']!r}.")
        elif result.errors:
            self.set_status_message(result.errors[0])
        return result

    def save_draft(self) -> Path | None:
        result = self.validate_draft()
        if not result.valid or result.rule is None:
            return None

        output_path = self._field_text("output_path").strip()
        if not output_path:
            self.set_status_message("Output JSON path is required before saving.")
            return None

        try:
            saved_path = write_rule_draft_file(Path(output_path), result.rule.to_dict())
        except OSError as exc:
            self.set_status_message(f"Could not save draft: {exc}")
            return None

        self.set_status_message(f"Saved rule draft to {saved_path}")
        return saved_path

    def set_status_message(self, message: str) -> None:
        set_text = getattr(self.status_label, "setText", None)
        if set_text is not None:
            set_text(message)

    def show(self, *, parent: Any | None = None, modal: bool = True) -> None:
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

    def _field_text(self, field_name: str) -> str:
        widget = self.field_inputs.get(field_name)
        if widget is None:
            return ""
        text = getattr(widget, "text", None)
        if text is not None:
            return str(text() or "")
        return _combo_text(widget)

    def _set_field_text(self, field_name: str, value: str) -> None:
        widget = self.field_inputs.get(field_name)
        if widget is None:
            return
        set_text = getattr(widget, "setText", None)
        if set_text is not None:
            set_text(value)

    def _set_combo_text(self, field_name: str, value: str) -> None:
        widget = self.field_inputs.get(field_name)
        if widget is None:
            return
        set_current_text = getattr(widget, "setCurrentText", None)
        if set_current_text is not None:
            set_current_text(value)

    def _combo_text(self, field_name: str) -> str:
        widget = self.field_inputs.get(field_name)
        if widget is None:
            return ""
        return _combo_text(widget)


def show_new_rule_wizard_dialog(
    qt_widgets: Any,
    *,
    parent: Any | None = None,
    known_rule_ids: Iterable[str] = (),
    default_output_path: str = "",
) -> None:
    """Display the new rule wizard dialog."""

    dialog = NewRuleWizardDialog.build(
        qt_widgets,
        known_rule_ids=known_rule_ids,
        default_output_path=default_output_path,
    )
    dialog.show(parent=parent, modal=True)


def _field_object_name(field_name: str) -> str:
    suffix = "".join(part.capitalize() for part in field_name.split("_"))
    return f"shaderHealthInspectorNewRuleWizard{suffix}Input"


def _combo_text(combo: Any) -> str:
    current_text = getattr(combo, "currentText", None)
    if current_text is not None:
        return str(current_text() or "")
    return ""


def _parse_optional_number(text: str) -> int | float | None:
    normalized = text.strip()
    if not normalized:
        return None
    if "." in normalized:
        return float(normalized)
    return int(normalized)


def _close_dialog(dialog: Any) -> None:
    reject = getattr(dialog, "reject", None)
    if reject is not None:
        reject()
        return
    close = getattr(dialog, "close", None)
    if close is not None:
        close()
