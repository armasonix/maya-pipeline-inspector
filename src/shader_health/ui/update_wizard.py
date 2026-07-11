"""Check for Updates wizard flow for the Maya panel."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shader_health import __version__
from shader_health.integrations.update.download import (
    download_release_asset,
    select_update_asset,
)
from shader_health.integrations.update.github_releases import (
    GitHubRelease,
    GitHubReleasesClient,
    GitHubReleasesClientError,
    HttpTransport,
    UpdateCheckResult,
)
from shader_health.studio_config import StudioConfig
from shader_health.ui.update_progress_dialog import UpdateProgressDialog

UPDATE_WIZARD_STAGE_QUERY = 0
UPDATE_WIZARD_STAGE_COMPARE = 1
UPDATE_WIZARD_STAGE_DOWNLOAD = 2
UPDATE_WIZARD_STAGE_INSTALL = 3
UPDATE_WIZARD_STAGE_RESTART = 4

UPDATE_WIZARD_STATUS_QUERY = "Contacting GitHub Releases for the latest release tag..."
UPDATE_WIZARD_STATUS_COMPARE = "Comparing the installed plugin version with the published tag."
UPDATE_WIZARD_STATUS_UP_TO_DATE = (
    "Shader Health Inspector is already up to date on v{installed_version}."
)
UPDATE_WIZARD_STATUS_UPDATE_AVAILABLE = (
    "Update available: v{installed_version} → v{latest_version} ({tag_name})."
)
UPDATE_WIZARD_STATUS_DOWNLOAD = "Downloading {asset_name} to the local staging directory..."
UPDATE_WIZARD_STATUS_DOWNLOAD_COMPLETE = (
    "Release package saved to {staging_path}."
)
UPDATE_WIZARD_STATUS_INSTALL = (
    "Preparing install while preserving shader_health_studio.json and user.json..."
)
UPDATE_WIZARD_STATUS_INSTALL_SUCCESS = (
    "Update installed to {install_root}. shader_health_studio.json and user.json preserved."
)
UPDATE_WIZARD_STATUS_INSTALL_FAILED = (
    "Install failed and previous plugin files were restored: {error}"
)
UPDATE_WIZARD_STATUS_RESTART = (
    "Manual Maya restart checklist: save your scene, close Maya, relaunch Maya, "
    "and reopen Shader Health Inspector."
)
UPDATE_WIZARD_STATUS_DISABLED = "Studio policy disables in-app update checks."
UPDATE_WIZARD_STATUS_PINNED = (
    "Studio policy pins Shader Health Inspector to v{pinned_version}; skipping download."
)
UPDATE_WIZARD_STATUS_QUERY_FAILED = "Could not query GitHub Releases: {error}"
UPDATE_WIZARD_STATUS_NO_ASSETS = "Latest release {tag_name} has no downloadable assets."
UPDATE_WIZARD_STATUS_DOWNLOAD_FAILED = "Download failed: {error}"

InstallHandler = Callable[[Path, GitHubRelease], "UpdateInstallOutcome"]
ProcessUiCallback = Callable[[], None]


@dataclass(frozen=True)
class UpdateInstallOutcome:
    """Outcome from the install stage of the update wizard."""

    success: bool
    message: str
    deferred: bool = False


@dataclass(frozen=True)
class UpdateWizardResult:
    """Summary outcome after running the update wizard flow."""

    completed: bool
    update_available: bool = False
    installed_version: str = ""
    latest_version: str = ""
    tag_name: str = ""
    staging_path: str = ""
    up_to_date: bool = False
    skipped_reason: str = ""
    error_message: str = ""


def default_install_handler(
    staging_path: Path,
    release: GitHubRelease,
) -> UpdateInstallOutcome:
    """Install a staged update package with config preservation and rollback."""

    from shader_health.integrations.update.install import install_staged_update

    result = install_staged_update(
        staging_path,
        tag_name=release.tag_name,
    )
    if result.success:
        return UpdateInstallOutcome(
            success=True,
            message=result.message,
        )
    return UpdateInstallOutcome(
        success=False,
        message=result.message,
    )


@dataclass(frozen=True)
class UpdateWizardSession:
    """Dialog widget and outcome from a completed update wizard run."""

    dialog: Any
    result: UpdateWizardResult


def run_update_wizard_flow(
    controller: UpdateProgressDialog,
    *,
    installed_version: str = __version__,
    studio_config: StudioConfig | None = None,
    releases_client: GitHubReleasesClient | None = None,
    transport: HttpTransport | None = None,
    staging_root: Path | None = None,
    install_handler: InstallHandler | None = None,
    download_transport: Callable[[str, float], bytes] | None = None,
    process_ui: ProcessUiCallback | None = None,
) -> UpdateWizardResult:
    """Advance the update dialog through check, download, install, and restart stages."""

    _refresh_ui = process_ui or (lambda: None)
    client = releases_client or GitHubReleasesClient(transport=transport)
    installer = install_handler or default_install_handler
    updates_policy = _updates_policy(studio_config)

    if not updates_policy.allow_check:
        controller.set_active_stage(
            UPDATE_WIZARD_STAGE_QUERY,
            status_message=UPDATE_WIZARD_STATUS_DISABLED,
        )
        _finish_wizard(controller, process_ui=_refresh_ui)
        return UpdateWizardResult(
            completed=True,
            installed_version=installed_version,
            skipped_reason="disabled",
            error_message=UPDATE_WIZARD_STATUS_DISABLED,
        )

    controller.set_close_enabled(False)
    controller.set_spinner_running(True)

    controller.set_active_stage(
        UPDATE_WIZARD_STAGE_QUERY,
        status_message=UPDATE_WIZARD_STATUS_QUERY,
        step_descriptions=(UPDATE_WIZARD_STATUS_QUERY, "", "", "", ""),
    )
    _refresh_ui()

    try:
        release = client.fetch_latest_release()
    except GitHubReleasesClientError as exc:
        message = UPDATE_WIZARD_STATUS_QUERY_FAILED.format(error=exc)
        controller.set_active_stage(
            UPDATE_WIZARD_STAGE_QUERY,
            status_message=message,
        )
        _finish_wizard(controller, process_ui=_refresh_ui)
        return UpdateWizardResult(
            completed=False,
            installed_version=installed_version,
            error_message=message,
        )

    check_result = client.check_for_update(installed_version)
    compare_description = UPDATE_WIZARD_STATUS_COMPARE
    if check_result.update_available:
        compare_status = UPDATE_WIZARD_STATUS_UPDATE_AVAILABLE.format(
            installed_version=installed_version,
            latest_version=check_result.latest_version,
            tag_name=check_result.tag_name,
        )
    else:
        compare_status = UPDATE_WIZARD_STATUS_UP_TO_DATE.format(
            installed_version=installed_version,
        )

    controller.set_active_stage(
        UPDATE_WIZARD_STAGE_COMPARE,
        status_message=compare_status,
        step_descriptions=(
            f"Latest release tag: {release.tag_name}",
            compare_description,
            "",
            "",
            "",
        ),
    )
    _refresh_ui()

    if not check_result.update_available:
        _finish_wizard(controller, process_ui=_refresh_ui)
        return UpdateWizardResult(
            completed=True,
            update_available=False,
            up_to_date=True,
            installed_version=installed_version,
            latest_version=check_result.latest_version,
            tag_name=check_result.tag_name,
        )

    pinned_version = updates_policy.pinned_version.strip()
    if pinned_version and not _pinned_allows_update(pinned_version, check_result):
        message = UPDATE_WIZARD_STATUS_PINNED.format(pinned_version=pinned_version)
        controller.set_active_stage(
            UPDATE_WIZARD_STAGE_COMPARE,
            status_message=message,
        )
        _finish_wizard(controller, process_ui=_refresh_ui)
        return UpdateWizardResult(
            completed=True,
            update_available=True,
            installed_version=installed_version,
            latest_version=check_result.latest_version,
            tag_name=check_result.tag_name,
            skipped_reason="pinned",
            error_message=message,
        )

    asset = select_update_asset(release.assets)
    if asset is None:
        message = UPDATE_WIZARD_STATUS_NO_ASSETS.format(tag_name=release.tag_name)
        controller.set_active_stage(
            UPDATE_WIZARD_STAGE_DOWNLOAD,
            status_message=message,
        )
        _finish_wizard(controller, process_ui=_refresh_ui)
        return UpdateWizardResult(
            completed=False,
            update_available=True,
            installed_version=installed_version,
            latest_version=check_result.latest_version,
            tag_name=check_result.tag_name,
            error_message=message,
        )

    download_status = UPDATE_WIZARD_STATUS_DOWNLOAD.format(asset_name=asset.name)
    controller.set_active_stage(
        UPDATE_WIZARD_STAGE_DOWNLOAD,
        status_message=download_status,
        step_descriptions=(
            f"Latest release tag: {release.tag_name}",
            compare_status,
            download_status,
            "",
            "",
        ),
    )
    _refresh_ui()

    try:
        staging_path = download_release_asset(
            asset,
            tag_name=release.tag_name,
            staging_root=staging_root,
            transport=download_transport,
        )
    except (OSError, RuntimeError) as exc:
        message = UPDATE_WIZARD_STATUS_DOWNLOAD_FAILED.format(error=exc)
        controller.set_active_stage(
            UPDATE_WIZARD_STAGE_DOWNLOAD,
            status_message=message,
        )
        _finish_wizard(controller, process_ui=_refresh_ui)
        return UpdateWizardResult(
            completed=False,
            update_available=True,
            installed_version=installed_version,
            latest_version=check_result.latest_version,
            tag_name=check_result.tag_name,
            error_message=message,
        )

    download_complete = UPDATE_WIZARD_STATUS_DOWNLOAD_COMPLETE.format(
        staging_path=staging_path,
    )
    controller.set_active_stage(
        UPDATE_WIZARD_STAGE_DOWNLOAD,
        status_message=download_complete,
        step_descriptions=(
            f"Latest release tag: {release.tag_name}",
            compare_status,
            download_complete,
            "",
            "",
        ),
    )
    _refresh_ui()

    controller.set_active_stage(
        UPDATE_WIZARD_STAGE_INSTALL,
        status_message=UPDATE_WIZARD_STATUS_INSTALL,
        step_descriptions=(
            f"Latest release tag: {release.tag_name}",
            compare_status,
            download_complete,
            UPDATE_WIZARD_STATUS_INSTALL,
            "",
        ),
    )
    _refresh_ui()

    install_outcome = installer(staging_path, release)
    if not install_outcome.success:
        install_status = install_outcome.message or UPDATE_WIZARD_STATUS_INSTALL_FAILED.format(
            error="unknown install error"
        )
        controller.set_active_stage(
            UPDATE_WIZARD_STAGE_INSTALL,
            status_message=install_status,
        )
        _finish_wizard(controller, process_ui=_refresh_ui)
        return UpdateWizardResult(
            completed=False,
            update_available=True,
            installed_version=installed_version,
            latest_version=check_result.latest_version,
            tag_name=check_result.tag_name,
            staging_path=str(staging_path),
            error_message=install_status,
        )

    install_status = install_outcome.message or UPDATE_WIZARD_STATUS_INSTALL_SUCCESS.format(
        install_root=staging_path.parent,
    )
    controller.set_active_stage(
        UPDATE_WIZARD_STAGE_INSTALL,
        status_message=install_status,
        step_descriptions=(
            f"Latest release tag: {release.tag_name}",
            compare_status,
            download_complete,
            install_status,
            "",
        ),
    )
    _refresh_ui()

    controller.set_active_stage(
        UPDATE_WIZARD_STAGE_RESTART,
        status_message=UPDATE_WIZARD_STATUS_RESTART,
        step_descriptions=(
            f"Latest release tag: {release.tag_name}",
            compare_status,
            download_complete,
            install_status,
            UPDATE_WIZARD_STATUS_RESTART,
        ),
    )
    _finish_wizard(controller, process_ui=_refresh_ui)
    return UpdateWizardResult(
        completed=True,
        update_available=True,
        installed_version=installed_version,
        latest_version=check_result.latest_version,
        tag_name=check_result.tag_name,
        staging_path=str(staging_path),
    )


def show_update_wizard(
    qt_widgets: Any,
    *,
    parent: Any | None = None,
    installed_version: str = __version__,
    studio_config: StudioConfig | None = None,
    transport: HttpTransport | None = None,
    staging_root: Path | None = None,
    install_handler: InstallHandler | None = None,
    download_transport: Callable[[str, float], bytes] | None = None,
) -> UpdateWizardSession:
    """Build the update dialog, run the wizard flow, and wait for the artist to close it."""

    controller = UpdateProgressDialog.build(
        qt_widgets,
        installed_version=installed_version,
        status_message=UPDATE_WIZARD_STATUS_QUERY,
        active_stage_index=UPDATE_WIZARD_STAGE_QUERY,
    )
    if parent is not None:
        set_parent = getattr(controller.dialog, "setParent", None)
        if set_parent is not None:
            set_parent(parent)
        window_modality = getattr(qt_widgets, "Qt", None)
        if window_modality is not None:
            application_modal = getattr(window_modality, "ApplicationModal", None)
            set_modality = getattr(controller.dialog, "setWindowModality", None)
            if application_modal is not None and set_modality is not None:
                set_modality(application_modal)

    show = getattr(controller.dialog, "show", None)
    if show is not None:
        show()

    process_ui = _build_process_ui_callback(qt_widgets)
    result = run_update_wizard_flow(
        controller,
        installed_version=installed_version,
        studio_config=studio_config,
        transport=transport,
        staging_root=staging_root,
        install_handler=install_handler,
        download_transport=download_transport,
        process_ui=process_ui,
    )

    exec_fn = getattr(controller.dialog, "exec_", None) or getattr(controller.dialog, "exec", None)
    if exec_fn is not None:
        exec_fn()
    return UpdateWizardSession(dialog=controller.dialog, result=result)


def _finish_wizard(
    controller: UpdateProgressDialog,
    *,
    process_ui: ProcessUiCallback,
) -> None:
    controller.set_spinner_running(False)
    controller.set_close_enabled(True)
    process_ui()


def _build_process_ui_callback(qt_widgets: Any) -> ProcessUiCallback:
    application_cls = getattr(qt_widgets, "QApplication", None)
    if application_cls is None:
        return lambda: None
    instance = getattr(application_cls, "instance", None)
    if instance is None:
        return lambda: None

    def _process_ui() -> None:
        app = instance()
        if app is None:
            return
        process_events = getattr(app, "processEvents", None)
        if process_events is not None:
            process_events()

    return _process_ui


@dataclass(frozen=True)
class _UpdatesPolicy:
    allow_check: bool
    pinned_version: str


def _updates_policy(studio_config: StudioConfig | None) -> _UpdatesPolicy:
    if studio_config is None:
        return _UpdatesPolicy(allow_check=True, pinned_version="")
    updates = studio_config.updates
    return _UpdatesPolicy(
        allow_check=bool(updates.allow_check),
        pinned_version=str(updates.pinned_version or ""),
    )


def _pinned_allows_update(pinned_version: str, check_result: UpdateCheckResult) -> bool:
    from shader_health.integrations.update.github_releases import compare_semver

    latest = check_result.latest_version or normalize_pinned_version(pinned_version)
    pinned = normalize_pinned_version(pinned_version)
    if not pinned:
        return True
    return compare_semver(latest, pinned) <= 0


def normalize_pinned_version(version: str) -> str:
    from shader_health.integrations.update.github_releases import normalize_release_tag

    return normalize_release_tag(version.strip())
