from __future__ import annotations

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
from shader_health.ui.rule_editor_dialog import (
    RULE_BROWSER_LIST_OBJECT_NAME,
    RULE_EDITOR_DIALOG_OBJECT_NAME,
    RULE_EDITOR_SAVE_BUTTON_OBJECT_NAME,
    RULE_EDITOR_STATUS_LABEL_OBJECT_NAME,
    RuleEditorDialog,
)


class FakeListWidgetItem(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.text = text
        self.data: dict[int, object] = {}

    def setData(self, role: int, value: object) -> None:
        self.data[role] = value


class FakeListWidget(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[FakeListWidgetItem] = []
        self.current_row = -1
        self.currentRowChanged = FakeSignal()

    def addItem(self, item: FakeListWidgetItem) -> None:
        self.items.append(item)

    def setCurrentRow(self, row: int) -> None:
        self.current_row = row

    def currentRow(self) -> int:
        return self.current_row


class FakeComboBox(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[str] = []
        self.current = ""

    def addItems(self, items: list[str]) -> None:
        self.items.extend(items)
        if items and not self.current:
            self.current = items[0]

    def setCurrentText(self, value: str) -> None:
        self.current = value

    def currentText(self) -> str:
        return self.current


class FakeDialog(FakeWidget):
    def reject(self) -> None:
        self.rejected = True


class RuleEditorFakeQtWidgets:
    QDialog = FakeDialog
    QWidget = FakeWidget
    QLabel = FakeLabel
    QVBoxLayout = FakeVBoxLayout
    QHBoxLayout = FakeHBoxLayout
    QFormLayout = FakeFormLayout
    QListWidget = FakeListWidget
    QListWidgetItem = FakeListWidgetItem
    QComboBox = FakeComboBox
    QLineEdit = FakeLineEdit
    QPushButton = FakePushButton


def test_rule_editor_dialog_builds_catalog_list():
    catalog = load_packaged_rules_catalog()
    controller = RuleEditorDialog.build(RuleEditorFakeQtWidgets, catalog=catalog[:3])

    assert controller.dialog.object_name == RULE_EDITOR_DIALOG_OBJECT_NAME
    assert len(controller.rule_list.items) == 3
    _find(controller.dialog, RULE_BROWSER_LIST_OBJECT_NAME)
    assert controller.rule_list.currentRowChanged.handlers
    hash(controller.rule_list.currentRowChanged.handlers[0])


def test_rule_editor_dialog_apply_saves_session_override():
    entry = next(
        item
        for item in load_packaged_rules_catalog()
        if item.rule.id == "common.shader_complexity.graph_nodes.max"
    )
    controller = RuleEditorDialog.build(RuleEditorFakeQtWidgets, catalog=(entry,))
    controller.enabled_toggle.setChecked(False)
    controller.severity_combo.setCurrentText("error")
    controller.threshold_input.setText("48")
    controller.apply_selected_rule()

    assert entry.rule.id in controller.session_overrides
    assert controller.session_overrides[entry.rule.id].enabled is False
    assert controller.session_overrides[entry.rule.id].severity == "error"
    assert controller.session_overrides[entry.rule.id].check_params == {"max": 48}


def test_rule_editor_dialog_save_validates_and_invokes_callback():
    entry = next(
        item
        for item in load_packaged_rules_catalog()
        if item.rule.id == "common.shader_complexity.graph_nodes.max"
    )
    saved: list[dict[str, object]] = []

    controller = RuleEditorDialog.build(
        RuleEditorFakeQtWidgets,
        catalog=(entry,),
        on_save=lambda overrides: saved.append(dict(overrides)),
    )
    controller.enabled_toggle.setChecked(False)
    controller.apply_selected_rule()
    save_button = _find(controller.dialog, RULE_EDITOR_SAVE_BUTTON_OBJECT_NAME)
    save_button.clicked.handlers[0]()

    assert len(saved) == 1
    assert entry.rule.id in saved[0]
    status = _find(controller.dialog, RULE_EDITOR_STATUS_LABEL_OBJECT_NAME)
    assert "validate_rules" in status.text.lower()


def test_rule_editor_dialog_apply_clears_override_when_defaults_restored():
    entry = next(
        item
        for item in load_packaged_rules_catalog()
        if item.rule.id == "common.shader_complexity.graph_nodes.max"
    )
    controller = RuleEditorDialog.build(RuleEditorFakeQtWidgets, catalog=(entry,))
    controller.enabled_toggle.setChecked(False)
    controller.apply_selected_rule()
    assert entry.rule.id in controller.session_overrides

    controller.enabled_toggle.setChecked(True)
    controller.severity_combo.setCurrentText(entry.rule.severity)
    controller.threshold_input.setText(str(entry.rule.check.params["max"]))
    controller.apply_selected_rule()

    assert entry.rule.id not in controller.session_overrides
    status = _find(controller.dialog, RULE_EDITOR_STATUS_LABEL_OBJECT_NAME)
    assert "packaged defaults" in status.text.lower()
