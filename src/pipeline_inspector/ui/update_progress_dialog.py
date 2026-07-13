"""Reusable update progress dialog for the Check for Updates wizard."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from pipeline_inspector import __version__
from pipeline_inspector.ui.settings_widgets import wire_button

UPDATE_PROGRESS_DIALOG_OBJECT_NAME = "pipelineInspectorUpdateProgressDialog"
UPDATE_PROGRESS_TITLE_LABEL_OBJECT_NAME = "pipelineInspectorUpdateProgressTitleLabel"
UPDATE_PROGRESS_VERSION_LABEL_OBJECT_NAME = "pipelineInspectorUpdateProgressVersionLabel"
UPDATE_PROGRESS_STATUS_LABEL_OBJECT_NAME = "pipelineInspectorUpdateProgressStatusLabel"
UPDATE_PROGRESS_STEPS_WIDGET_OBJECT_NAME = "pipelineInspectorUpdateProgressStepsWidget"
UPDATE_PROGRESS_SPINNER_OBJECT_NAME = "pipelineInspectorUpdateProgressSpinner"
UPDATE_PROGRESS_CLOSE_BUTTON_OBJECT_NAME = "pipelineInspectorUpdateProgressCloseButton"

UPDATE_PROGRESS_STEP_LABEL_OBJECT_NAME_PREFIX = "pipelineInspectorUpdateProgressStepLabel"
UPDATE_PROGRESS_STEP_DESCRIPTION_OBJECT_NAME_PREFIX = (
    "pipelineInspectorUpdateProgressStepDescription"
)

UPDATE_STAGE_LABELS: tuple[str, ...] = (
    "Query GitHub Releases for the latest version",
    "Compare installed version with release tag",
    "Download release package to staging",
    "Install update and preserve studio/user config",
    "Restart Maya to load the updated plugin",
)

DEFAULT_UPDATE_STEP_DESCRIPTIONS: tuple[str, ...] = (
    "Contacting GitHub Releases API for the latest release tag.",
    "Comparing the installed plugin version with the published tag.",
    "Downloading the release package to a local staging directory.",
    "Installing the update while preserving pipeline_inspector_studio.json and user.json.",
    "Maya will restart automatically in a few seconds. Save your scene now if needed.",
)

UPDATE_PROGRESS_SHELL_STATUS = (
    "Shell preview — automated update wizard ships in Milestone 37."
)

@dataclass(frozen=True)
class UpdateProgressStep:
    """One wizard step with a title and optional detail description."""

    label: str
    description: str = ""

@dataclass(frozen=True)
class UpdateProgressStage:
    """Rendered stage row state for the progress dialog."""

    index: int
    label: str
    description: str
    state: str

def update_progress_step_label_object_name(index: int) -> str:
    return f"{UPDATE_PROGRESS_STEP_LABEL_OBJECT_NAME_PREFIX}{index}"

def update_progress_step_description_object_name(index: int) -> str:
    return f"{UPDATE_PROGRESS_STEP_DESCRIPTION_OBJECT_NAME_PREFIX}{index}"

def default_update_progress_steps() -> tuple[UpdateProgressStep, ...]:
    return tuple(
        UpdateProgressStep(label=label, description=description)
        for label, description in zip(
            UPDATE_STAGE_LABELS,
            DEFAULT_UPDATE_STEP_DESCRIPTIONS,
        )
    )

def build_update_progress_stages(
    steps: Sequence[UpdateProgressStep],
    *,
    active_index: int,
    step_descriptions: Sequence[str] | None = None,
) -> tuple[UpdateProgressStage, ...]:
    rows: list[UpdateProgressStage] = []
    for index, step in enumerate(steps):
        if index < active_index:
            state = "complete"
        elif index == active_index:
            state = "active"
        else:
            state = "pending"
        description = step.description
        if step_descriptions is not None and index < len(step_descriptions):
            override = str(step_descriptions[index] or "").strip()
            if override:
                description = override
        rows.append(
            UpdateProgressStage(
                index=index,
                label=step.label,
                description=description,
                state=state,
            )
        )
    return tuple(rows)

def format_update_progress_stage_label(stage: UpdateProgressStage) -> str:
    prefix = {
        "complete": "[done]",
        "active": "[current]",
        "pending": "[pending]",
    }.get(stage.state, "[pending]")
    return f"{prefix} {stage.index + 1}. {stage.label}"

@dataclass
class UpdateProgressDialog:
    """Controller for the reusable update progress dialog widget."""

    dialog: Any
    status_label: Any
    spinner: Any
    close_button: Any
    step_labels: tuple[Any, ...]
    step_descriptions: tuple[Any, ...]
    steps: tuple[UpdateProgressStep, ...]

    @classmethod
    def build(
        cls,
        qt_widgets: Any,
        *,
        steps: Sequence[UpdateProgressStep] | None = None,
        installed_version: str = __version__,
        window_title: str = "Check for Updates",
        title_text: str = "Pipeline Inspector — Check for Updates",
        status_message: str = "",
        active_stage_index: int = 0,
    ) -> UpdateProgressDialog:
        resolved_steps = tuple(steps or default_update_progress_steps())

        dialog = qt_widgets.QDialog()
        dialog.setObjectName(UPDATE_PROGRESS_DIALOG_OBJECT_NAME)
        set_window_title = getattr(dialog, "setWindowTitle", None)
        if set_window_title is not None:
            set_window_title(window_title)
        set_minimum_size = getattr(dialog, "setMinimumSize", None)
        if set_minimum_size is not None:
            set_minimum_size(520, 420)

        layout = qt_widgets.QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = qt_widgets.QLabel(title_text)
        title.setObjectName(UPDATE_PROGRESS_TITLE_LABEL_OBJECT_NAME)
        layout.addWidget(title)

        version_label = qt_widgets.QLabel(f"Installed version: v{installed_version}")
        version_label.setObjectName(UPDATE_PROGRESS_VERSION_LABEL_OBJECT_NAME)
        layout.addWidget(version_label)

        status_label = qt_widgets.QLabel(status_message)
        status_label.setObjectName(UPDATE_PROGRESS_STATUS_LABEL_OBJECT_NAME)
        set_word_wrap = getattr(status_label, "setWordWrap", None)
        if set_word_wrap is not None:
            set_word_wrap(True)
        layout.addWidget(status_label)

        steps_widget = qt_widgets.QWidget()
        steps_widget.setObjectName(UPDATE_PROGRESS_STEPS_WIDGET_OBJECT_NAME)
        steps_layout = qt_widgets.QVBoxLayout(steps_widget)
        set_stage_margins = getattr(steps_layout, "setContentsMargins", None)
        if set_stage_margins is not None:
            set_stage_margins(0, 0, 0, 0)

        step_labels: list[Any] = []
        step_description_labels: list[Any] = []
        for stage in build_update_progress_stages(
            resolved_steps,
            active_index=active_stage_index,
        ):
            step_label = qt_widgets.QLabel(format_update_progress_stage_label(stage))
            step_label.setObjectName(update_progress_step_label_object_name(stage.index))
            steps_layout.addWidget(step_label)
            step_labels.append(step_label)

            description_label = qt_widgets.QLabel(stage.description)
            description_label.setObjectName(
                update_progress_step_description_object_name(stage.index)
            )
            set_description_word_wrap = getattr(description_label, "setWordWrap", None)
            if set_description_word_wrap is not None:
                set_description_word_wrap(True)
            steps_layout.addWidget(description_label)
            step_description_labels.append(description_label)

        layout.addWidget(steps_widget)

        spinner = qt_widgets.QProgressBar()
        spinner.setObjectName(UPDATE_PROGRESS_SPINNER_OBJECT_NAME)
        set_text_visible = getattr(spinner, "setTextVisible", None)
        if set_text_visible is not None:
            set_text_visible(False)
        set_range = getattr(spinner, "setRange", None)
        if set_range is not None:
            set_range(0, 0)
        layout.addWidget(spinner)

        button_row = qt_widgets.QHBoxLayout()
        button_row.addStretch(1)
        close_button = qt_widgets.QPushButton("Close")
        close_button.setObjectName(UPDATE_PROGRESS_CLOSE_BUTTON_OBJECT_NAME)
        wire_button(close_button, lambda: _close_dialog(dialog))
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

        controller = cls(
            dialog=dialog,
            status_label=status_label,
            spinner=spinner,
            close_button=close_button,
            step_labels=tuple(step_labels),
            step_descriptions=tuple(step_description_labels),
            steps=resolved_steps,
        )
        controller.set_active_stage(
            active_stage_index,
            status_message=status_message,
        )
        return controller

    def set_status_message(self, message: str) -> None:
        set_text = getattr(self.status_label, "setText", None)
        if set_text is not None:
            set_text(message)

    def set_spinner_running(self, running: bool) -> None:
        set_visible = getattr(self.spinner, "setVisible", None)
        if set_visible is not None:
            set_visible(running)
        if not running:
            return
        set_range = getattr(self.spinner, "setRange", None)
        if set_range is not None:
            set_range(0, 0)

    def set_close_enabled(self, enabled: bool) -> None:
        set_enabled = getattr(self.close_button, "setEnabled", None)
        if set_enabled is not None:
            set_enabled(enabled)

    def set_active_stage(
        self,
        index: int,
        *,
        status_message: str | None = None,
        step_descriptions: Sequence[str] | None = None,
    ) -> None:
        if index < 0 or index >= len(self.steps):
            raise ValueError(f"Update stage index out of range: {index}")

        stages = build_update_progress_stages(
            self.steps,
            active_index=index,
            step_descriptions=step_descriptions,
        )
        for stage, step_label, description_label in zip(
            stages,
            self.step_labels,
            self.step_descriptions,
        ):
            set_step_text = getattr(step_label, "setText", None)
            if set_step_text is not None:
                set_step_text(format_update_progress_stage_label(stage))
            set_description_text = getattr(description_label, "setText", None)
            if set_description_text is not None:
                set_description_text(stage.description)

        if status_message is not None:
            self.set_status_message(status_message)
        elif not str(getattr(self.status_label, "text", lambda: "")() or "").strip():
            active_stage = stages[index]
            if active_stage.description:
                self.set_status_message(active_stage.description)

        self.set_spinner_running(index < len(self.steps))

    def show(self, *, parent: Any | None = None, modal: bool = True) -> None:
        if parent is not None:
            set_parent = getattr(self.dialog, "setParent", None)
            if set_parent is not None:
                set_parent(parent)

        exec_fn = getattr(self.dialog, "exec_", None) or getattr(self.dialog, "exec", None)
        if modal and exec_fn is not None:
            exec_fn()
            return

        show = getattr(self.dialog, "show", None)
        if show is not None:
            show()

    def close(self) -> None:
        _close_dialog(self.dialog)

def show_update_progress_dialog(
    qt_widgets: Any,
    *,
    parent: Any | None = None,
    installed_version: str = __version__,
    status_message: str = UPDATE_PROGRESS_SHELL_STATUS,
    active_stage_index: int = 0,
) -> UpdateProgressDialog:
    """Build and display the default update progress dialog."""

    dialog = UpdateProgressDialog.build(
        qt_widgets,
        installed_version=installed_version,
        status_message=status_message,
        active_stage_index=active_stage_index,
    )
    if parent is not None:
        window_modality = getattr(qt_widgets, "Qt", None)
        if window_modality is not None:
            application_modal = getattr(window_modality, "ApplicationModal", None)
            set_modality = getattr(dialog.dialog, "setWindowModality", None)
            if application_modal is not None and set_modality is not None:
                set_modality(application_modal)
    dialog.show(parent=parent, modal=True)
    return dialog

def _close_dialog(dialog: Any) -> None:
    reject = getattr(dialog, "reject", None)
    if reject is not None:
        reject()
        return
    close = getattr(dialog, "close", None)
    if close is not None:
        close()
