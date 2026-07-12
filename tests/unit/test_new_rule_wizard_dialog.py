from __future__ import annotations

from pathlib import Path

from tests.unit.test_advanced_settings_section import (
    FakeFormLayout,
    FakeHBoxLayout,
    FakeLabel,
    FakeLineEdit,
    FakePushButton,
    FakeSignal,
    FakeVBoxLayout,
    FakeWidget,
)
from tests.unit.test_telegram_connector_section import _find

from shader_health.core.rule_browser import load_packaged_rules_catalog
from shader_health.core.rule_schema import RuleResult
from shader_health.core.rule_wizard import (
    RULE_TEMPLATE_NUMERIC_MAX,
    RULE_TEMPLATE_PATH_EXISTS,
    build_draft_prefill_from_issue,
    optional_fields_for_template,
)
from shader_health.ui.new_rule_wizard_dialog import (
    NEW_RULE_WIZARD_DIALOG_OBJECT_NAME,
    NEW_RULE_WIZARD_EXPORT_STUDIO_BUTTON_OBJECT_NAME,
    NEW_RULE_WIZARD_STATUS_LABEL_OBJECT_NAME,
    NewRuleWizardDialog,
)


class VisibleFakeLabel(FakeLabel):
    def __init__(self, text: str = "") -> None:
        super().__init__(text)
        self.visible = True

    def setVisible(self, visible: bool) -> None:
        self.visible = visible


class VisibleFakeLineEdit(FakeLineEdit):
    def __init__(self, text: str = "") -> None:
        super().__init__(text)
        self.visible = True

    def setVisible(self, visible: bool) -> None:
        self.visible = visible


class FakeComboBox(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[str] = []
        self.current = ""
        self.currentIndexChanged = FakeSignal()

    def addItems(self, items: list[str]) -> None:
        self.items.extend(items)
        if items and not self.current:
            self.current = items[0]

    def setCurrentText(self, value: str) -> None:
        self.current = value

    def currentText(self) -> str:
        return self.current

    def currentIndex(self) -> int:
        if self.current in self.items:
            return self.items.index(self.current)
        return 0

    def setCurrentIndex(self, index: int) -> None:
        if 0 <= index < len(self.items):
            self.current = self.items[index]


class FakeDialog(FakeWidget):
    def reject(self) -> None:
        self.rejected = True


class NewRuleWizardFakeQtWidgets:
    QDialog = FakeDialog
    QWidget = FakeWidget
    QLabel = VisibleFakeLabel
    QVBoxLayout = FakeVBoxLayout
    QHBoxLayout = FakeHBoxLayout
    QFormLayout = FakeFormLayout
    QComboBox = FakeComboBox
    QLineEdit = VisibleFakeLineEdit
    QPushButton = FakePushButton


def test_new_rule_wizard_dialog_builds_template_fields():
    controller = NewRuleWizardDialog.build(NewRuleWizardFakeQtWidgets)

    assert controller.dialog.object_name == NEW_RULE_WIZARD_DIALOG_OBJECT_NAME
    assert controller.template_combo.items
    assert controller.field_inputs["rule_id"].value
    assert controller.template_combo.currentIndexChanged.handlers
    hash(controller.template_combo.currentIndexChanged.handlers[0])


def test_new_rule_wizard_hides_irrelevant_template_fields():
    controller = NewRuleWizardDialog.build(NewRuleWizardFakeQtWidgets)
    controller.template_combo.setCurrentIndex(2)
    controller.load_template_defaults(2)

    assert optional_fields_for_template(RULE_TEMPLATE_PATH_EXISTS) == frozenset(
        {"dependency_kind"}
    )
    assert controller.field_inputs["dependency_kind"].visible is True
    assert controller.field_inputs["attribute"].visible is False
    assert controller.field_inputs["expected"].visible is False
    assert controller.field_inputs["max_value"].visible is False

    controller.template_combo.setCurrentIndex(1)
    controller.load_template_defaults(1)

    assert optional_fields_for_template(RULE_TEMPLATE_NUMERIC_MAX) == frozenset(
        {"attribute", "max_value"}
    )
    assert controller.field_inputs["attribute"].visible is True
    assert controller.field_inputs["max_value"].visible is True
    assert controller.field_inputs["expected"].visible is False
    assert controller.field_inputs["dependency_kind"].visible is False


def test_new_rule_wizard_dialog_validate_reports_valid_draft():
    controller = NewRuleWizardDialog.build(
        NewRuleWizardFakeQtWidgets,
        known_rule_ids=frozenset(),
    )
    controller.field_inputs["rule_id"].setText("studio.custom.wizard.test")
    controller.field_inputs["name"].setText("Wizard test rule")
    controller.field_inputs["message"].setText("Failed.")
    controller.field_inputs["why"].setText("Because.")
    controller.field_inputs["attribute"].setText("colorSpace")
    controller.field_inputs["expected"].setText("Raw")
    controller.validate_draft()

    status = _find(controller.dialog, NEW_RULE_WIZARD_STATUS_LABEL_OBJECT_NAME)
    assert "valid" in status.text.lower()


def test_new_rule_wizard_dialog_applies_issue_prefill():
    rule = next(
        entry.rule
        for entry in load_packaged_rules_catalog()
        if entry.rule.id == "common.texture.colorspace.data_raw"
    )
    issue = RuleResult(
        rule_id=rule.id,
        severity=rule.severity,
        status="failed",
        title=rule.name,
        message=rule.message,
        why=rule.why,
        owner=rule.owner,
        expected_value="Raw",
    )
    prefill = build_draft_prefill_from_issue(issue, rule)
    controller = NewRuleWizardDialog.build(
        NewRuleWizardFakeQtWidgets,
        prefill=prefill,
    )

    assert controller.field_inputs["rule_id"].value == prefill.draft_input.rule_id
    assert controller.field_inputs["expected"].value == "Raw"
    assert "Prefilled" in controller.status_label.text


def test_new_rule_wizard_dialog_exports_to_studio_extra_rules(tmp_path: Path):
    from shader_health.core.rule_wizard import (
        RULE_TEMPLATE_PATH_EXISTS,
        IncidentRuleExportContext,
        NewRuleDraftInput,
        build_rule_draft,
    )

    controller = NewRuleWizardDialog.build(
        NewRuleWizardFakeQtWidgets,
        studio_extra_rules_folder=str(tmp_path / "extra_rules"),
        export_context=IncidentRuleExportContext(
            source_rule_id="common.texture.missing",
            scene_path=str(tmp_path / "demo.ma"),
        ),
    )
    draft = build_rule_draft(
        RULE_TEMPLATE_PATH_EXISTS,
        NewRuleDraftInput(
            rule_id="studio.incident.export.test",
            name="Export test",
            message="Missing file.",
            why="Farm risk.",
            severity="critical",
            dependency_kind="texture",
        ),
    )
    controller.field_inputs["rule_id"].setText(draft["id"])
    controller.field_inputs["name"].setText(draft["name"])
    controller.field_inputs["message"].setText(draft["message"])
    controller.field_inputs["why"].setText(draft["why"])
    controller.field_inputs["severity"].setCurrentText("critical")
    controller.field_inputs["dependency_kind"].setText("texture")

    export_button = _find(controller.dialog, NEW_RULE_WIZARD_EXPORT_STUDIO_BUTTON_OBJECT_NAME)
    export_button.clicked.handlers[0]()

    status = _find(controller.dialog, NEW_RULE_WIZARD_STATUS_LABEL_OBJECT_NAME)
    assert "Exported incident rule sidecar" in status.text
    assert (tmp_path / "extra_rules" / "studio.incident.export.test.json").is_file()


def test_new_rule_wizard_dialog_save_writes_json(tmp_path: Path):
    from shader_health.core.rule_wizard import (
        RULE_TEMPLATE_PATH_EXISTS,
        NewRuleDraftInput,
        build_rule_draft,
    )

    controller = NewRuleWizardDialog.build(
        NewRuleWizardFakeQtWidgets,
        known_rule_ids=frozenset(),
    )
    draft = build_rule_draft(
        RULE_TEMPLATE_PATH_EXISTS,
        NewRuleDraftInput(
            rule_id="studio.custom.path.exists",
            name="Path exists",
            message="Missing file.",
            why="Missing textures fail on farm.",
            severity="critical",
            dependency_kind="texture",
        ),
    )
    controller.field_inputs["rule_id"].setText(draft["id"])
    controller.field_inputs["name"].setText(draft["name"])
    controller.field_inputs["message"].setText(draft["message"])
    controller.field_inputs["why"].setText(draft["why"])
    controller.field_inputs["severity"].setCurrentText("critical")
    controller.field_inputs["dependency_kind"].setText("texture")
    controller.field_inputs["output_path"].setText(str(tmp_path / "draft.json"))

    saved = controller.save_draft()

    assert saved == (tmp_path / "draft.json").resolve()
    assert saved.is_file()
