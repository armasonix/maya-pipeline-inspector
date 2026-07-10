"""Check for Updates modal shell for the Maya panel header."""
from __future__ import annotations

from typing import Any

from shader_health import __version__
from shader_health.ui.update_progress_dialog import (
    UPDATE_PROGRESS_SHELL_STATUS,
    UPDATE_STAGE_LABELS,
    UpdateProgressDialog,
    UpdateProgressStage,
    UpdateProgressStep,
    build_update_progress_stages,
    format_update_progress_stage_label,
    show_update_progress_dialog,
    update_progress_step_label_object_name,
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
    """Build the Check for Updates modal shell with staged progress labels."""

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
) -> Any:
    """Display the Check for Updates modal shell."""

    dialog = show_update_progress_dialog(
        qt_widgets,
        parent=parent,
        installed_version=installed_version,
        status_message=UPDATE_MODAL_SHELL_STATUS,
        active_stage_index=0,
    )
    return dialog.dialog
