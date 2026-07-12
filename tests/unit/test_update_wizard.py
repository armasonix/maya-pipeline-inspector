from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

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


def _write_install_tree(root: Path, *, version: str) -> None:
    maya_module = root / "maya_module"
    package = root / "src" / "shader_health"
    maya_module.mkdir(parents=True)
    package.mkdir(parents=True)
    (maya_module / "shader_health_inspector.mod").write_text(
        f"+ shader_health_inspector {version} .\n",
        encoding="utf-8",
    )
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "version_marker.txt").write_text(version, encoding="utf-8")


def _write_zip_from_payload(zip_path: Path, payload_root: Path) -> None:
    with zipfile.ZipFile(zip_path, "w") as archive:
        for path in payload_root.rglob("*"):
            if path.is_file():
                archive.write(path, arcname=str(path.relative_to(payload_root.parent)))


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


def test_run_update_wizard_flow_advances_through_download_install_and_restart(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    install_root = tmp_path / "install"
    _write_install_tree(install_root, version="0.4.0")
    payload_root = tmp_path / "package" / "maya-shader-health-inspector"
    _write_install_tree(payload_root, version="0.5.0")
    zip_path = tmp_path / "package" / "maya-shader-health-inspector-0.5.0.zip"
    _write_zip_from_payload(zip_path, payload_root)

    controller = UpdateProgressDialog.build(FakeQtWidgets, installed_version="0.4.0")

    def install_handler(staging_path: Path, release) -> object:
        from shader_health.integrations.update.install import install_staged_update
        from shader_health.ui.update_wizard import UpdateInstallOutcome

        result = install_staged_update(
            staging_path,
            tag_name=release.tag_name,
            install_root=install_root,
            backup_root=tmp_path / "backups",
        )
        return UpdateInstallOutcome(success=result.success, message=result.message)

    result = run_update_wizard_flow(
        controller,
        installed_version="0.4.0",
        transport=_github_transport(_release_payload(tag_name="v0.5.0")),
        staging_root=tmp_path / "staging",
        download_transport=lambda _url, _timeout: zip_path.read_bytes(),
        install_handler=install_handler,
    )

    assert result.completed is True
    assert result.update_available is True
    assert (
        install_root / "src" / "shader_health" / "version_marker.txt"
    ).read_text(encoding="utf-8") == "0.5.0"
    assert controller.status_label.text == UPDATE_WIZARD_STATUS_RESTART
    assert controller.step_labels[UPDATE_WIZARD_STAGE_RESTART].text.startswith("[current] 5.")


def test_run_update_wizard_flow_stops_on_install_failure(tmp_path: Path):
    install_root = tmp_path / "install"
    _write_install_tree(install_root, version="0.4.0")
    payload_root = tmp_path / "package" / "maya-shader-health-inspector"
    _write_install_tree(payload_root, version="0.5.0")
    zip_path = tmp_path / "package" / "maya-shader-health-inspector-0.5.0.zip"
    _write_zip_from_payload(zip_path, payload_root)
    controller = UpdateProgressDialog.build(FakeQtWidgets, installed_version="0.4.0")

    def install_handler(_staging_path: Path, _release) -> object:
        from shader_health.ui.update_wizard import UpdateInstallOutcome

        return UpdateInstallOutcome(success=False, message="Install failed in test.")

    result = run_update_wizard_flow(
        controller,
        installed_version="0.4.0",
        transport=_github_transport(_release_payload(tag_name="v0.5.0")),
        staging_root=tmp_path / "staging",
        download_transport=lambda _url, _timeout: zip_path.read_bytes(),
        install_handler=install_handler,
    )

    assert result.completed is False
    assert "Install failed in test." in result.error_message
    assert controller.status_label.text == "Install failed in test."
    assert controller.close_button.enabled is True


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
    assert session.dialog.parent is parent
    assert session.dialog.window_flags == (
        FakeQt.Dialog | FakeQt.WindowTitleHint | FakeQt.WindowCloseButtonHint
    )
    assert session.result.up_to_date is True
    assert app.process_events_calls >= 1
