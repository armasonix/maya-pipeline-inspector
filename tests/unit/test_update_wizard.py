from __future__ import annotations

import json
from pathlib import Path

from shader_health.integrations.update.download import select_update_asset
from shader_health.integrations.update.github_releases import (
    GitHubReleasesResponse,
    HttpRequest,
    ReleaseAsset,
)
from shader_health.studio_config import StudioConfig, StudioUpdatesSettings
from shader_health.ui.update_progress_dialog import UpdateProgressDialog
from shader_health.ui.update_wizard import (
    UPDATE_WIZARD_STAGE_RESTART,
    UPDATE_WIZARD_STATUS_RESTART,
    UPDATE_WIZARD_STATUS_UP_TO_DATE,
    run_update_wizard_flow,
    show_update_wizard,
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
        self.show_called = False

    def exec_(self) -> int:
        self.exec_called = True
        return 0

    def show(self) -> None:
        self.show_called = True
        self.visible = True


class FakeApplication:
    def __init__(self) -> None:
        self.process_events_calls = 0

    def processEvents(self) -> None:
        self.process_events_calls += 1


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
    QApplication = FakeApplication


def _release_payload(*, tag_name: str = "v0.5.0", version: str | None = None) -> dict[str, object]:
    resolved = version or tag_name.lstrip("v")
    return {
        "tag_name": tag_name,
        "name": f"v{resolved} release",
        "html_url": f"https://github.com/example/repo/releases/tag/{tag_name}",
        "published_at": "2026-07-11T07:00:00Z",
        "body": "Release notes",
        "assets": [
            {
                "id": 1,
                "name": f"maya-shader-health-inspector-{tag_name.lstrip('v')}.zip",
                "browser_download_url": f"https://example.test/{tag_name}.zip",
                "size": 128,
                "content_type": "application/zip",
            }
        ],
    }


def _github_transport(payload: dict[str, object]):
    def transport(_request: HttpRequest, _timeout: float) -> GitHubReleasesResponse:
        return GitHubReleasesResponse(
            status_code=200,
            body=json.dumps(payload),
            json_data=payload,
        )

    return transport


def test_select_update_asset_prefers_maya_module_zip():
    assets = (
        ReleaseAsset("shader_health_inspector.mll", "https://x/mll", 1, "bin", 1),
        ReleaseAsset("maya-shader-health-inspector-0.5.0.zip", "https://x/zip", 2, "zip", 2),
    )

    selected = select_update_asset(assets)

    assert selected is not None
    assert selected.name.endswith(".zip")


def test_run_update_wizard_flow_reports_up_to_date_and_enables_close():
    controller = UpdateProgressDialog.build(FakeQtWidgets, installed_version="0.5.0")

    result = run_update_wizard_flow(
        controller,
        installed_version="0.5.0",
        transport=_github_transport(_release_payload(tag_name="v0.5.0")),
    )

    assert result.up_to_date is True
    assert result.completed is True
    assert UPDATE_WIZARD_STATUS_UP_TO_DATE.format(installed_version="0.5.0") in (
        controller.status_label.text
    )
    assert controller.close_button.enabled is True
    assert controller.spinner.visible is False


def test_run_update_wizard_flow_advances_through_download_install_and_restart(tmp_path: Path):
    controller = UpdateProgressDialog.build(FakeQtWidgets, installed_version="0.4.0")
    install_messages: list[str] = []

    def install_handler(staging_path: Path, _release) -> object:
        install_messages.append(str(staging_path))
        from shader_health.ui.update_wizard import UpdateInstallOutcome

        return UpdateInstallOutcome(success=True, deferred=True, message="Install deferred.")

    result = run_update_wizard_flow(
        controller,
        installed_version="0.4.0",
        transport=_github_transport(_release_payload(tag_name="v0.5.0")),
        staging_root=tmp_path,
        download_transport=lambda _url, _timeout: b"zip-bytes",
        install_handler=install_handler,
    )

    assert result.completed is True
    assert result.update_available is True
    assert result.staging_path.endswith(".zip")
    assert install_messages
    assert controller.status_label.text == UPDATE_WIZARD_STATUS_RESTART
    assert controller.step_labels[UPDATE_WIZARD_STAGE_RESTART].text.startswith("[current] 5.")
    assert controller.step_descriptions[UPDATE_WIZARD_STAGE_RESTART].text == (
        UPDATE_WIZARD_STATUS_RESTART
    )


def test_run_update_wizard_flow_honors_studio_disabled_policy():
    controller = UpdateProgressDialog.build(FakeQtWidgets, installed_version="0.4.0")
    studio = StudioConfig(updates=StudioUpdatesSettings(allow_check=False))

    result = run_update_wizard_flow(
        controller,
        installed_version="0.4.0",
        studio_config=studio,
        transport=_github_transport(_release_payload(tag_name="v0.5.0")),
    )

    assert result.skipped_reason == "disabled"
    assert controller.status_label.text == "Studio policy disables in-app update checks."


def test_show_update_wizard_runs_modal_flow_with_parent_and_process_events():
    parent = FakeWidget()
    app = FakeApplication()
    FakeQtWidgets.QApplication = type(
        "FakeApplicationClass",
        (),
        {"instance": staticmethod(lambda: app)},
    )

    session = show_update_wizard(
        FakeQtWidgets,
        parent=parent,
        installed_version="0.5.0",
        transport=_github_transport(_release_payload(tag_name="v0.5.0")),
    )

    assert session.dialog.exec_called is True
    assert session.dialog.show_called is True
    assert session.dialog.parent is parent
    assert session.result.up_to_date is True
    assert app.process_events_calls >= 1
