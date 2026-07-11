"""Check for Updates modal and wizard entry points for the Maya panel header."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from shader_health import __version__
from shader_health.integrations.update.github_releases import HttpTransport
from shader_health.studio_config import StudioConfig
from shader_health.ui.update_progress_dialog import (
    UPDATE_PROGRESS_SHELL_STATUS,
    UPDATE_STAGE_LABELS,
    UpdateProgressDialog,
    UpdateProgressStage,
    UpdateProgressStep,
    build_update_progress_stages,
    format_update_progress_stage_label,
    update_progress_step_label_object_name,
)
from shader_health.ui.update_wizard import (
    InstallHandler,
    UpdateWizardResult,
    UpdateWizardSession,
    show_update_wizard,
)

UPDATE_MODAL_OBJECT_NAME = "shaderHealthInspectorUpdateModal"
UPDATE_MODAL_TITLE_LABEL_OBJECT_NAME = "shaderHealthInspectorUpdateProgressTitleLabel"
UPDATE_MODAL_VERSION_LABEL_OBJECT_NAME = "shaderHealthInspectorUpdateProgressVersionLabel"
UPDATE_MODAL_STATUS_LABEL_OBJECT_NAME = "shaderHealthInspectorUpdateProgressStatusLabel"
UPDATE_MODAL_STAGES_WIDGET_OBJECT_NAME = "shaderHealthInspectorUpdateProgressStepsWidget"
UPDATE_MODAL_PROGRESS_BAR_OBJECT_NAME = "shaderHealthInspectorUpdateProgressSpinner"
UPDATE_MODAL_CLOSE_BUTTON_OBJECT_NAME = "shaderHealthInspectorUpdateProgressCloseButton"
UPDATE_STAGE_LABEL_OBJECT_NAME_PREFIX = "shaderHealthInspectorUpdateProgressStepLabel"

UPDATE_MODAL_SHELL_STATUS = UPDATE_PROGRESS_SHELL_STATUS

UpdateModalStage = UpdateProgressStage


def update_stage_object_name(index: int) -> str:
    return update_progress_step_label_object_name(index)


def build_update_stage_rows(
    *,
    active_index: int = 0,
    stage_labels: tuple[str, ...] = UPDATE_STAGE_LABELS,
) -> tuple[UpdateProgressStage, ...]:
    steps = tuple(UpdateProgressStep(label=label) for label in stage_labels)
    return build_update_progress_stages(steps, active_index=active_index)


def format_update_stage_text(stage: UpdateProgressStage) -> str:
    return format_update_progress_stage_label(stage)


def build_update_modal_shell(
    qt_widgets: Any,
    *,
    installed_version: str = __version__,
    active_stage_index: int = 0,
    status_message: str = UPDATE_MODAL_SHELL_STATUS,
) -> Any:
    """Build the Check for Updates dialog without running the wizard flow."""

    return UpdateProgressDialog.build(
        qt_widgets,
        installed_version=installed_version,
        status_message=status_message,
        active_stage_index=active_stage_index,
    ).dialog


def show_update_modal_shell(
    qt_widgets: Any,
    *,
    parent: Any | None = None,
    installed_version: str = __version__,
    studio_config: StudioConfig | None = None,
    transport: HttpTransport | None = None,
    staging_root: Path | None = None,
    install_handler: InstallHandler | None = None,
    download_transport: Callable[[str, float], bytes] | None = None,
) -> Any:
    """Display the Check for Updates wizard and return the dialog widget."""

    session = show_update_wizard(
        qt_widgets,
        parent=parent,
        installed_version=installed_version,
        studio_config=studio_config,
        transport=transport,
        staging_root=staging_root,
        install_handler=install_handler,
        download_transport=download_transport,
    )
    return session.dialog


__all__ = [
    "UpdateWizardResult",
    "UpdateWizardSession",
    "build_update_modal_shell",
    "build_update_stage_rows",
    "format_update_stage_text",
    "show_update_modal_shell",
    "show_update_wizard",
    "update_stage_object_name",
]
