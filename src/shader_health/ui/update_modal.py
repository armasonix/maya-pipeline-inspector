"""Check for Updates modal shell for the Maya panel header."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from shader_health import __version__
from shader_health.ui.settings_widgets import wire_button

UPDATE_MODAL_OBJECT_NAME = "shaderHealthInspectorUpdateModal"
UPDATE_MODAL_TITLE_LABEL_OBJECT_NAME = "shaderHealthInspectorUpdateModalTitleLabel"
UPDATE_MODAL_VERSION_LABEL_OBJECT_NAME = "shaderHealthInspectorUpdateModalVersionLabel"
UPDATE_MODAL_STATUS_LABEL_OBJECT_NAME = "shaderHealthInspectorUpdateModalStatusLabel"
UPDATE_MODAL_STAGES_WIDGET_OBJECT_NAME = "shaderHealthInspectorUpdateModalStagesWidget"
UPDATE_MODAL_PROGRESS_BAR_OBJECT_NAME = "shaderHealthInspectorUpdateModalProgressBar"
UPDATE_MODAL_CLOSE_BUTTON_OBJECT_NAME = "shaderHealthInspectorUpdateModalCloseButton"

UPDATE_STAGE_LABEL_OBJECT_NAME_PREFIX = "shaderHealthInspectorUpdateModalStageLabel"

UPDATE_STAGE_LABELS: tuple[str, ...] = (
    "Query GitHub Releases for the latest version",
    "Compare installed version with release tag",
    "Download release package to staging",
    "Install update and preserve studio/user config",
    "Show manual Maya restart checklist",
)

UPDATE_MODAL_SHELL_STATUS = (
    "Shell preview — automated update wizard ships in Milestone 37."
)


@dataclass(frozen=True)
class UpdateModalStage:
    """One staged progress row in the update modal."""

    index: int
    label: str
    state: str


def update_stage_object_name(index: int) -> str:
    return f"{UPDATE_STAGE_LABEL_OBJECT_NAME_PREFIX}{index}"


def build_update_stage_rows(
    *,
    active_index: int = 0,
    stage_labels: Sequence[str] = UPDATE_STAGE_LABELS,
) -> tuple[UpdateModalStage, ...]:
    rows: list[UpdateModalStage] = []
    for index, label in enumerate(stage_labels):
        if index < active_index:
            state = "complete"
        elif index == active_index:
            state = "active"
        else:
            state = "pending"
        rows.append(UpdateModalStage(index=index, label=label, state=state))
    return tuple(rows)


def format_update_stage_text(stage: UpdateModalStage) -> str:
    prefix = {
        "complete": "[done]",
        "active": "[current]",
        "pending": "[pending]",
    }.get(stage.state, "[pending]")
    return f"{prefix} {stage.index + 1}. {stage.label}"


def build_update_modal_shell(
    qt_widgets: Any,
    *,
    installed_version: str = __version__,
    active_stage_index: int = 0,
    status_message: str = UPDATE_MODAL_SHELL_STATUS,
) -> Any:
    """Build the Check for Updates modal shell with staged progress labels."""

    dialog = qt_widgets.QDialog()
    dialog.setObjectName(UPDATE_MODAL_OBJECT_NAME)
    set_window_title = getattr(dialog, "setWindowTitle", None)
    if set_window_title is not None:
        set_window_title("Check for Updates")

    layout = qt_widgets.QVBoxLayout(dialog)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(8)

    title = qt_widgets.QLabel("Shader Health Inspector — Check for Updates")
    title.setObjectName(UPDATE_MODAL_TITLE_LABEL_OBJECT_NAME)
    layout.addWidget(title)

    version_label = qt_widgets.QLabel(f"Installed version: v{installed_version}")
    version_label.setObjectName(UPDATE_MODAL_VERSION_LABEL_OBJECT_NAME)
    layout.addWidget(version_label)

    status_label = qt_widgets.QLabel(status_message)
    status_label.setObjectName(UPDATE_MODAL_STATUS_LABEL_OBJECT_NAME)
    set_word_wrap = getattr(status_label, "setWordWrap", None)
    if set_word_wrap is not None:
        set_word_wrap(True)
    layout.addWidget(status_label)

    stages_widget = qt_widgets.QWidget()
    stages_widget.setObjectName(UPDATE_MODAL_STAGES_WIDGET_OBJECT_NAME)
    stages_layout = qt_widgets.QVBoxLayout(stages_widget)
    set_stage_margins = getattr(stages_layout, "setContentsMargins", None)
    if set_stage_margins is not None:
        set_stage_margins(0, 0, 0, 0)
    for stage in build_update_stage_rows(active_index=active_stage_index):
        stage_label = qt_widgets.QLabel(format_update_stage_text(stage))
        stage_label.setObjectName(update_stage_object_name(stage.index))
        stages_layout.addWidget(stage_label)
    layout.addWidget(stages_widget)

    progress_bar = qt_widgets.QProgressBar()
    progress_bar.setObjectName(UPDATE_MODAL_PROGRESS_BAR_OBJECT_NAME)
    set_text_visible = getattr(progress_bar, "setTextVisible", None)
    if set_text_visible is not None:
        set_text_visible(False)
    set_range = getattr(progress_bar, "setRange", None)
    if set_range is not None:
        set_range(0, 0)
    layout.addWidget(progress_bar)

    button_row = qt_widgets.QHBoxLayout()
    button_row.addStretch(1)
    close_button = qt_widgets.QPushButton("Close")
    close_button.setObjectName(UPDATE_MODAL_CLOSE_BUTTON_OBJECT_NAME)
    wire_button(close_button, lambda: _close_dialog(dialog))
    button_row.addWidget(close_button)
    layout.addLayout(button_row)

    return dialog


def show_update_modal_shell(
    qt_widgets: Any,
    *,
    parent: Any | None = None,
    installed_version: str = __version__,
) -> Any:
    """Display the Check for Updates modal shell."""

    dialog = build_update_modal_shell(
        qt_widgets,
        installed_version=installed_version,
    )
    if parent is not None:
        set_parent = getattr(dialog, "setParent", None)
        if set_parent is not None:
            set_parent(parent)

    window_modality = getattr(qt_widgets, "Qt", None)
    if window_modality is not None:
        application_modal = getattr(window_modality, "ApplicationModal", None)
        set_modality = getattr(dialog, "setWindowModality", None)
        if application_modal is not None and set_modality is not None:
            set_modality(application_modal)

    exec_fn = getattr(dialog, "exec_", None) or getattr(dialog, "exec", None)
    if exec_fn is not None:
        exec_fn()
        return dialog

    show = getattr(dialog, "show", None)
    if show is not None:
        show()
    return dialog


def _close_dialog(dialog: Any) -> None:
    reject = getattr(dialog, "reject", None)
    if reject is not None:
        reject()
        return
    close = getattr(dialog, "close", None)
    if close is not None:
        close()
