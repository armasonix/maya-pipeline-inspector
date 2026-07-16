from __future__ import annotations

from typing import Any

from tests.unit.test_maya_summary_header import FakeLabel
from tests.unit.test_telegram_connector_section import FakeQtWidgets, FakeWidget, _find

from pipeline_inspector.integrations.bug_report.relay_client import BugReportRelayResult
from pipeline_inspector.ui.bug_report_dialog import (
    BUG_REPORT_ATTACH_SCREENSHOT_CHECKBOX_OBJECT_NAME,
    BUG_REPORT_DESCRIPTION_INPUT_OBJECT_NAME,
    BUG_REPORT_FORM_WIDGET_OBJECT_NAME,
    BUG_REPORT_ISSUE_URL_LABEL_OBJECT_NAME,
    BUG_REPORT_SCREENSHOT_BROWSE_BUTTON_OBJECT_NAME,
    BUG_REPORT_SCREENSHOT_PATH_INPUT_OBJECT_NAME,
    BUG_REPORT_SCREENSHOT_ROW_OBJECT_NAME,
    BUG_REPORT_STATUS_LABEL_OBJECT_NAME,
    BUG_REPORT_STEPS_INPUT_OBJECT_NAME,
    BUG_REPORT_SUCCESS_WIDGET_OBJECT_NAME,
    BUG_REPORT_TITLE_INPUT_OBJECT_NAME,
    BugReportDialog,
    BugReportFormValues,
)


class FakeSignal:
    def __init__(self) -> None:
        self.handlers: list[Any] = []

    def connect(self, handler: Any) -> None:
        self.handlers.append(handler)

    def emit(self, *args: Any) -> None:
        for handler in self.handlers:
            handler(*args)


class FakeTextEdit(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.value = text

    def setPlaceholderText(self, text: str) -> None:
        _ = text

    def toPlainText(self) -> str:
        return self.value

    def setPlainText(self, text: str) -> None:
        self.value = text


class FakePushButton(FakeLabel):
    def __init__(self, text: str = "") -> None:
        super().__init__(text=text)
        self.clicked = FakeSignal()
        self.enabled = True

    def setEnabled(self, enabled: bool) -> None:
        self.enabled = enabled


class FakeCheckBox(FakeWidget):
    def __init__(self, text: str = "", checked: bool = False) -> None:
        super().__init__()
        self.text = text
        self.checked = checked
        self.toggled = FakeSignal()
        self.stateChanged = FakeSignal()

    def isChecked(self) -> bool:
        return self.checked

    def setChecked(self, checked: bool) -> None:
        self.checked = checked
        self.toggled.emit(checked)
        self.stateChanged.emit(2 if checked else 0)


class FakeDialog(FakeWidget):
    def exec(self) -> int:
        self.exec_called = True
        return 0

    def exec_(self) -> int:
        return self.exec()


class BugReportFakeQtWidgets(FakeQtWidgets):
    QDialog = FakeDialog
    QTextEdit = FakeTextEdit
    QPushButton = FakePushButton
    QCheckBox = FakeCheckBox


def test_bug_report_dialog_builds_form_fields():
    controller = BugReportDialog.build(BugReportFakeQtWidgets)

    assert controller.dialog.object_name == "pipelineInspectorBugReportDialog"
    _find(controller.dialog, BUG_REPORT_TITLE_INPUT_OBJECT_NAME)
    _find(controller.dialog, BUG_REPORT_DESCRIPTION_INPUT_OBJECT_NAME)
    _find(controller.dialog, BUG_REPORT_STEPS_INPUT_OBJECT_NAME)
    _find(controller.dialog, BUG_REPORT_ATTACH_SCREENSHOT_CHECKBOX_OBJECT_NAME)
    form = _find(controller.dialog, BUG_REPORT_FORM_WIDGET_OBJECT_NAME)
    success = _find(controller.dialog, BUG_REPORT_SUCCESS_WIDGET_OBJECT_NAME)
    assert form.visible is True
    assert success.visible is False


def test_bug_report_dialog_shows_issue_url_on_success():
    controller = BugReportDialog.build(BugReportFakeQtWidgets)
    controller.apply_submit_result(
        BugReportRelayResult(
            submitted=True,
            issue_url="https://github.com/org/repo/issues/42",
            status_code=201,
        )
    )

    form = _find(controller.dialog, BUG_REPORT_FORM_WIDGET_OBJECT_NAME)
    success = _find(controller.dialog, BUG_REPORT_SUCCESS_WIDGET_OBJECT_NAME)
    status = _find(controller.dialog, BUG_REPORT_STATUS_LABEL_OBJECT_NAME)
    issue_url = _find(controller.dialog, BUG_REPORT_ISSUE_URL_LABEL_OBJECT_NAME)
    submit = controller.submit_button

    assert form.visible is False
    assert success.visible is True
    assert "thank you" in status.text.lower()
    assert issue_url.visible is False
    assert submit.visible is False


def test_bug_report_dialog_submit_callback_receives_form_values():
    captured: list[BugReportFormValues] = []

    def submit(values: BugReportFormValues) -> BugReportRelayResult:
        captured.append(values)
        return BugReportRelayResult(
            submitted=True,
            issue_url="https://github.com/org/repo/issues/7",
            status_code=201,
        )

    controller = BugReportDialog.build(BugReportFakeQtWidgets, on_submit=submit)
    controller.title_input.setText("Crash on validate")
    controller.description_input.setPlainText("Panel freezes after Validate Scene.")
    controller.steps_input.setPlainText("Open scene\nValidate Scene")
    controller.submit_button.clicked.emit()

    assert len(captured) == 1
    assert captured[0].title == "Crash on validate"
    assert captured[0].description == "Panel freezes after Validate Scene."
    assert captured[0].steps_to_reproduce == "Open scene\nValidate Scene"
    assert captured[0].attach_screenshot is False
    issue_url = _find(controller.dialog, BUG_REPORT_ISSUE_URL_LABEL_OBJECT_NAME)
    assert issue_url.visible is False


def test_bug_report_dialog_requires_title_and_description():
    controller = BugReportDialog.build(
        BugReportFakeQtWidgets,
        on_submit=lambda _values: BugReportRelayResult(submitted=True, issue_url="https://x"),
    )
    controller.submit_button.clicked.emit()

    status = _find(controller.dialog, BUG_REPORT_STATUS_LABEL_OBJECT_NAME)
    assert "required" in status.text.lower()


def test_bug_report_dialog_screenshot_row_hidden_until_checkbox_checked():
    controller = BugReportDialog.build(BugReportFakeQtWidgets)

    assert controller.screenshot_row.object_name == BUG_REPORT_SCREENSHOT_ROW_OBJECT_NAME
    assert (
        controller.screenshot_path_input.object_name
        == BUG_REPORT_SCREENSHOT_PATH_INPUT_OBJECT_NAME
    )
    assert (
        controller.screenshot_browse_button.object_name
        == BUG_REPORT_SCREENSHOT_BROWSE_BUTTON_OBJECT_NAME
    )
    assert controller.screenshot_row.visible is False
    controller.attach_screenshot_checkbox.setChecked(True)
    assert controller.screenshot_row.visible is True
    controller.attach_screenshot_checkbox.setChecked(False)
    assert controller.screenshot_row.visible is False
    assert controller.screenshot_path_input.text() == ""


def test_bug_report_dialog_submit_includes_screenshot_path_when_attached():
    captured: list[BugReportFormValues] = []

    def submit(values: BugReportFormValues) -> BugReportRelayResult:
        captured.append(values)
        return BugReportRelayResult(
            submitted=True,
            issue_url="https://github.com/org/repo/issues/9",
            status_code=201,
        )

    controller = BugReportDialog.build(BugReportFakeQtWidgets, on_submit=submit)
    controller.title_input.setText("UI glitch")
    controller.description_input.setPlainText("Screenshot row missing.")
    controller.attach_screenshot_checkbox.setChecked(True)
    controller.screenshot_path_input.setText("C:/shots/bug.png")
    controller.submit_button.clicked.emit()

    assert len(captured) == 1
    assert captured[0].attach_screenshot is True
    assert captured[0].screenshot_path == "C:/shots/bug.png"
