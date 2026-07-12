from __future__ import annotations

from shader_health.ui import settings_widgets


class FakeQt:
    Window = 1
    Dialog = 2
    WindowTitleHint = 4
    WindowCloseButtonHint = 8
    WindowStaysOnTopHint = 16
    ApplicationModal = 32
    WA_DeleteOnClose = 64


class FakeDialog:
    def __init__(self) -> None:
        self.window_flags = 0
        self.modality = None
        self.attributes: dict[int, bool] = {}
        self.visible = False
        self.exec_count = 0
        self.raised = False

    def setWindowFlags(self, flags: int) -> None:
        self.window_flags = flags

    def setWindowModality(self, modality: int) -> None:
        self.modality = modality

    def setAttribute(self, attribute: int, enabled: bool) -> None:
        self.attributes[attribute] = enabled

    def isVisible(self) -> bool:
        return self.visible

    def exec_(self) -> int:
        self.exec_count += 1
        self.visible = True
        self.visible = False
        return 0

    def raise_(self) -> None:
        self.raised = True

    def activateWindow(self) -> None:
        return None


class FakeQtWidgets:
    Qt = FakeQt


def setup_function() -> None:
    settings_widgets._ACTIVE_MAYA_MODAL_DIALOGS.clear()


def test_show_modal_dialog_uses_top_level_window_flags():
    dialog = FakeDialog()

    settings_widgets.show_modal_dialog(
        dialog,
        FakeQtWidgets(),
        singleton_key="test-dialog",
    )

    assert dialog.window_flags == (
        FakeQt.Window
        | FakeQt.WindowTitleHint
        | FakeQt.WindowCloseButtonHint
        | FakeQt.WindowStaysOnTopHint
    )
    assert dialog.modality == FakeQt.ApplicationModal
    assert dialog.attributes[FakeQt.WA_DeleteOnClose] is True
    assert dialog.exec_count == 1


def test_show_modal_dialog_reactivates_existing_singleton():
    first = FakeDialog()
    second = FakeDialog()

    settings_widgets._ACTIVE_MAYA_MODAL_DIALOGS["test-dialog"] = first
    first.visible = True

    settings_widgets.show_modal_dialog(
        second,
        FakeQtWidgets(),
        singleton_key="test-dialog",
    )

    assert first.raised is True
    assert second.exec_count == 0
