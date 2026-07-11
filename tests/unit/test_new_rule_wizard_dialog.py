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

from shader_health.core.rule_wizard import (
    RULE_TEMPLATE_PATH_EXISTS,
    NewRuleDraftInput,
    build_rule_draft,
)
from shader_health.ui.new_rule_wizard_dialog import (
    NEW_RULE_WIZARD_DIALOG_OBJECT_NAME,
    NEW_RULE_WIZARD_STATUS_LABEL_OBJECT_NAME,
    NewRuleWizardDialog,
)


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


class FakeDialog(FakeWidget):
    def reject(self) -> None:
        self.rejected = True


class NewRuleWizardFakeQtWidgets:
    QDialog = FakeDialog
    QWidget = FakeWidget
    QLabel = FakeLabel
    QVBoxLayout = FakeVBoxLayout
    QHBoxLayout = FakeHBoxLayout
    QFormLayout = FakeFormLayout
    QComboBox = FakeComboBox
    QLineEdit = FakeLineEdit
    QPushButton = FakePushButton


def test_new_rule_wizard_dialog_builds_template_fields():
    controller = NewRuleWizardDialog.build(NewRuleWizardFakeQtWidgets)

    assert controller.dialog.object_name == NEW_RULE_WIZARD_DIALOG_OBJECT_NAME
    assert controller.template_combo.items
    assert controller.field_inputs["rule_id"].value


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


def test_new_rule_wizard_dialog_save_writes_json(tmp_path: Path):
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
