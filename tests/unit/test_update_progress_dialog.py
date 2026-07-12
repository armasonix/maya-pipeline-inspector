from __future__ import annotations

from pipeline_inspector import __version__
from pipeline_inspector.ui.update_progress_dialog import (
    UPDATE_PROGRESS_CLOSE_BUTTON_OBJECT_NAME,
    UPDATE_PROGRESS_SHELL_STATUS,
    UPDATE_PROGRESS_SPINNER_OBJECT_NAME,
    UPDATE_PROGRESS_STEPS_WIDGET_OBJECT_NAME,
    UPDATE_PROGRESS_VERSION_LABEL_OBJECT_NAME,
    UPDATE_STAGE_LABELS,
    UpdateProgressDialog,
    UpdateProgressStep,
    build_update_progress_stages,
    default_update_progress_steps,
    show_update_progress_dialog,
    update_progress_step_description_object_name,
)


class FakeWidget:
    def __init__(self) -> None:
        self.object_name: str | None = None
        self.children: list[object] = []
        self.layout: object | None = None
        self.window_title = ""
        self.parent: object | None = None
        self.modality: object | None = None
        self.visible = True
        self.enabled = True
        self.rejected = False

    def setObjectName(self, object_name: str) -> None:
        self.object_name = object_name

    def setWindowTitle(self, title: str) -> None:
        self.window_title = title

    def setParent(self, parent: object) -> None:
        self.parent = parent

    def setWindowModality(self, modality: object) -> None:
        self.modality = modality

    def setVisible(self, visible: bool) -> None:
        self.visible = visible

    def setEnabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def reject(self) -> None:
        self.rejected = True


class FakeLabel(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.text = text
        self.word_wrap = False

    def setText(self, text: str) -> None:
        self.text = text

    def setWordWrap(self, enabled: bool) -> None:
        self.word_wrap = enabled


class FakeSignal:
    def __init__(self) -> None:
        self.handlers: list[object] = []

    def connect(self, handler: object) -> None:
        self.handlers.append(handler)

    def emit(self, *_args: object) -> None:
        for handler in self.handlers:
            handler()


class FakePushButton(FakeLabel):
    def __init__(self, text: str = "") -> None:
        super().__init__(text)
        self.clicked = FakeSignal()


class FakeProgressBar(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.text_visible = True
        self.minimum = 0
        self.maximum = 100

    def setTextVisible(self, visible: bool) -> None:
        self.text_visible = visible

    def setRange(self, minimum: int, maximum: int) -> None:
        self.minimum = minimum
        self.maximum = maximum


class FakeHBoxLayout:
    def __init__(self) -> None:
        self.widgets: list[object] = []
        self.stretches: list[int] = []

    def addStretch(self, _stretch: int = 0) -> None:
        self.stretches.append(_stretch)

    def addWidget(self, widget: object) -> None:
        self.widgets.append(widget)


class FakeVBoxLayout:
    def __init__(self, parent: FakeWidget | None = None) -> None:
        self.parent = parent
        self.widgets: list[object] = []
        self.layouts: list[object] = []
        if parent is not None:
            parent.layout = self

    def setContentsMargins(self, *_args: int) -> None:
        return

    def setSpacing(self, _spacing: int) -> None:
        return

    def addWidget(self, widget: object) -> None:
        self.widgets.append(widget)
        if self.parent is not None and widget not in self.parent.children:
            self.parent.children.append(widget)

    def addLayout(self, layout: object) -> None:
        self.layouts.append(layout)
        for widget in getattr(layout, "widgets", []):
            if self.parent is not None and widget not in self.parent.children:
                self.parent.children.append(widget)


class FakeDialog(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.exec_called = False

    def exec_(self) -> int:
        self.exec_called = True
        return 0


class FakeQt:
    ApplicationModal = "application-modal"


class FakeQtWidgets:
    QDialog = FakeDialog
    QWidget = FakeWidget
    QLabel = FakeLabel
    QPushButton = FakePushButton
    QVBoxLayout = FakeVBoxLayout
    QHBoxLayout = FakeHBoxLayout
    QProgressBar = FakeProgressBar
    Qt = FakeQt


def _find(root: FakeWidget, object_name: str) -> FakeWidget:
    stack = [root]
    while stack:
        current = stack.pop()
        if getattr(current, "object_name", None) == object_name:
            return current
        stack.extend(getattr(current, "children", []))
    raise AssertionError(f"Widget not found: {object_name}")


def test_default_update_progress_steps_align_labels_and_descriptions():
    steps = default_update_progress_steps()

    assert len(steps) == len(UPDATE_STAGE_LABELS)
    assert steps[0].label == UPDATE_STAGE_LABELS[0]
    assert steps[0].description


def test_build_update_progress_stages_supports_description_overrides():
    steps = (
        UpdateProgressStep("Check release", "Default detail"),
        UpdateProgressStep("Download package", "Default download detail"),
    )
    stages = build_update_progress_stages(
        steps,
        active_index=1,
        step_descriptions=("Custom check detail", "Custom download detail"),
    )

    assert stages[0].state == "complete"
    assert stages[1].state == "active"
    assert stages[0].description == "Custom check detail"
    assert stages[1].description == "Custom download detail"


def test_update_progress_dialog_build_exposes_spinner_and_step_descriptions():
    controller = UpdateProgressDialog.build(
        FakeQtWidgets,
        installed_version="0.4.0",
        status_message=UPDATE_PROGRESS_SHELL_STATUS,
        active_stage_index=0,
    )

    assert controller.dialog.window_title == "Check for Updates"
    assert _find(controller.dialog, UPDATE_PROGRESS_VERSION_LABEL_OBJECT_NAME).text == (
        "Installed version: v0.4.0"
    )
    assert controller.status_label.text == UPDATE_PROGRESS_SHELL_STATUS
    stages = _find(controller.dialog, UPDATE_PROGRESS_STEPS_WIDGET_OBJECT_NAME)
    assert (
        _find(stages, update_progress_step_description_object_name(0)).text
        == default_update_progress_steps()[0].description
    )
    spinner = _find(controller.dialog, UPDATE_PROGRESS_SPINNER_OBJECT_NAME)
    assert spinner.minimum == 0
    assert spinner.maximum == 0
    assert spinner.visible is True


def test_update_progress_dialog_set_active_stage_updates_labels_and_status():
    controller = UpdateProgressDialog.build(FakeQtWidgets, status_message="Starting")

    controller.set_active_stage(
        2,
        status_message="Downloading release package...",
        step_descriptions=("Done checking", "Done comparing", "Fetching zip asset"),
    )

    assert controller.status_label.text == "Downloading release package..."
    assert controller.step_labels[2].text.startswith("[current] 3.")
    assert controller.step_descriptions[2].text == "Fetching zip asset"
    assert controller.step_labels[0].text.startswith("[done]")


def test_update_progress_dialog_set_close_enabled_and_spinner_running():
    controller = UpdateProgressDialog.build(FakeQtWidgets)

    controller.set_close_enabled(False)
    controller.set_spinner_running(False)

    assert controller.close_button.enabled is False
    assert controller.spinner.visible is False


def test_show_update_progress_dialog_uses_modal_exec_and_parent():
    parent = FakeWidget()
    controller = show_update_progress_dialog(
        FakeQtWidgets,
        parent=parent,
        installed_version=__version__,
    )

    assert controller.dialog.exec_called is True
    assert controller.dialog.parent is parent
    assert controller.dialog.modality == FakeQt.ApplicationModal


def test_update_progress_close_button_rejects_dialog():
    controller = UpdateProgressDialog.build(FakeQtWidgets)
    close_button = _find(controller.dialog, UPDATE_PROGRESS_CLOSE_BUTTON_OBJECT_NAME)

    close_button.clicked.emit()

    assert controller.dialog.rejected is True
