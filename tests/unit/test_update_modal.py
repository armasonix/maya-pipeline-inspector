from __future__ import annotations

import json

from shader_health.integrations.update.github_releases import GitHubReleasesResponse, HttpRequest
from shader_health.ui.update_modal import (
    UPDATE_MODAL_CLOSE_BUTTON_OBJECT_NAME,
    UPDATE_MODAL_PROGRESS_BAR_OBJECT_NAME,
    UPDATE_MODAL_SHELL_STATUS,
    UPDATE_MODAL_STAGES_WIDGET_OBJECT_NAME,
    UPDATE_MODAL_STATUS_LABEL_OBJECT_NAME,
    UPDATE_MODAL_VERSION_LABEL_OBJECT_NAME,
    UPDATE_STAGE_LABELS,
    build_update_modal_shell,
    build_update_stage_rows,
    format_update_stage_text,
    show_update_modal_shell,
    update_stage_object_name,
)
from shader_health.ui.update_progress_dialog import (
    update_progress_step_description_object_name,
)
from shader_health.ui.update_wizard import UPDATE_WIZARD_STATUS_UP_TO_DATE
from shader_health.integrations.update.github_releases import GitHubReleasesResponse, HttpRequest
from shader_health.ui.update_wizard import UPDATE_WIZARD_STATUS_UP_TO_DATE


class FakeWidget:
    def __init__(self) -> None:
        self.object_name: str | None = None
        self.children: list[object] = []
        self.layout: object | None = None
        self.window_title = ""
        self.parent: object | None = None
        self.modality: object | None = None
        self.visible = False
        self.rejected = False

    def setObjectName(self, object_name: str) -> None:
        self.object_name = object_name

    def setWindowTitle(self, title: str) -> None:
        self.window_title = title

    def setParent(self, parent: object) -> None:
        self.parent = parent

    def setWindowModality(self, modality: object) -> None:
        self.modality = modality

    def reject(self) -> None:
        self.rejected = True

    def exec_(self) -> int:
        return 0


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
        self.show_called = False
        self.window_flags: object | None = None

    def exec_(self) -> int:
        self.show()
        self.exec_called = True
        FakeQTimer.run_pending()
        return 0

    def show(self) -> None:
        self.show_called = True
        self.visible = True

    def setWindowFlags(self, flags: object) -> None:
        self.window_flags = flags

    def raise_(self) -> None:
        return

    def activateWindow(self) -> None:
        return


class FakeApplication:
    def __init__(self) -> None:
        self.process_events_calls = 0

    def processEvents(self) -> None:
        self.process_events_calls += 1


class FakeQt:
    ApplicationModal = 32
    Dialog = 2
    WindowTitleHint = 4
    WindowCloseButtonHint = 8


class FakeQTimer:
    _pending: list[object] = []

    @classmethod
    def singleShot(cls, _delay_ms: int, callback: object) -> None:
        cls._pending.append(callback)

    @classmethod
    def run_pending(cls) -> None:
        pending = cls._pending[:]
        cls._pending.clear()
        for callback in pending:
            callback()


class FakeQtWidgets:
    QDialog = FakeDialog
    QWidget = FakeWidget
    QLabel = FakeLabel
    QPushButton = FakePushButton
    QVBoxLayout = FakeVBoxLayout
    QHBoxLayout = FakeHBoxLayout
    QProgressBar = FakeProgressBar
    Qt = FakeQt
    QApplication = FakeApplication
    QTimer = FakeQTimer


def _find(root: FakeWidget, object_name: str) -> FakeWidget:
    stack = [root]
    while stack:
        current = stack.pop()
        if getattr(current, "object_name", None) == object_name:
            return current
        stack.extend(getattr(current, "children", []))
    raise AssertionError(f"Widget not found: {object_name}")


def test_build_update_stage_rows_marks_first_stage_active_by_default():
    rows = build_update_stage_rows()

    assert len(rows) == len(UPDATE_STAGE_LABELS)
    assert rows[0].state == "active"
    assert rows[1].state == "pending"
    assert format_update_stage_text(rows[0]).startswith("[current] 1.")


def test_build_update_modal_shell_exposes_staged_progress_labels():
    dialog = build_update_modal_shell(FakeQtWidgets, installed_version="0.4.0")

    assert dialog.window_title == "Check for Updates"
    assert _find(dialog, UPDATE_MODAL_VERSION_LABEL_OBJECT_NAME).text == (
        "Installed version: v0.4.0"
    )
    assert _find(dialog, UPDATE_MODAL_STATUS_LABEL_OBJECT_NAME).text == (
        UPDATE_MODAL_SHELL_STATUS
    )
    stages = _find(dialog, UPDATE_MODAL_STAGES_WIDGET_OBJECT_NAME)
    stage_labels = [
        _find(stages, update_stage_object_name(index))
        for index in range(len(UPDATE_STAGE_LABELS))
    ]
    assert len(stage_labels) == len(UPDATE_STAGE_LABELS)
    assert "[current] 1." in stage_labels[0].text
    assert UPDATE_STAGE_LABELS[1] in stage_labels[1].text
    assert (
        _find(stages, update_progress_step_description_object_name(0)).text
        != ""
    )
    progress = _find(dialog, UPDATE_MODAL_PROGRESS_BAR_OBJECT_NAME)
    assert progress.minimum == 0
    assert progress.maximum == 0
    assert progress.text_visible is False


def _github_transport(payload: dict[str, object]):
    def transport(_request: HttpRequest, _timeout: float) -> GitHubReleasesResponse:
        return GitHubReleasesResponse(
            status_code=200,
            body=json.dumps(payload),
            json_data=payload,
        )

    return transport


def test_show_update_modal_shell_uses_modal_exec_and_parent():
    parent = FakeWidget()
    session = show_update_modal_shell(
        FakeQtWidgets,
        parent=parent,
        installed_version="0.5.0",
        transport=_github_transport(
            {
                "tag_name": "v0.5.0",
                "name": "v0.5.0",
                "html_url": "https://github.com/example/releases/tag/v0.5.0",
                "published_at": "2026-07-11T07:00:00Z",
                "body": "",
                "assets": [],
            }
        ),
    )
    dialog = session.dialog

    assert dialog.exec_called is True
    assert dialog.show_called is True
    assert dialog.parent is parent
    assert dialog.modality == FakeQt.ApplicationModal
    assert session.result.up_to_date is True
    assert UPDATE_WIZARD_STATUS_UP_TO_DATE.format(installed_version="0.5.0") in (
        _find(dialog, UPDATE_MODAL_STATUS_LABEL_OBJECT_NAME).text
    )


def test_update_modal_close_button_rejects_dialog():
    dialog = build_update_modal_shell(FakeQtWidgets)
    close_button = _find(dialog, UPDATE_MODAL_CLOSE_BUTTON_OBJECT_NAME)

    close_button.clicked.emit()

    assert dialog.rejected is True
