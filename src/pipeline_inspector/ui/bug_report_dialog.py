"""Bug report submission dialog for the Maya panel header."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pipeline_inspector.integrations.bug_report.relay_client import BugReportRelayResult
from pipeline_inspector.integrations.bug_report.status import (
    format_bug_report_failure_status,
    format_bug_report_success_headline,
)
from pipeline_inspector.ui.settings_widgets import wire_button

BUG_REPORT_DIALOG_OBJECT_NAME = "pipelineInspectorBugReportDialog"
BUG_REPORT_INTRO_LABEL_OBJECT_NAME = "pipelineInspectorBugReportIntroLabel"
BUG_REPORT_TITLE_INPUT_OBJECT_NAME = "pipelineInspectorBugReportTitleInput"
BUG_REPORT_DESCRIPTION_INPUT_OBJECT_NAME = "pipelineInspectorBugReportDescriptionInput"
BUG_REPORT_STEPS_INPUT_OBJECT_NAME = "pipelineInspectorBugReportStepsInput"
BUG_REPORT_ATTACH_SCREENSHOT_CHECKBOX_OBJECT_NAME = (
    "pipelineInspectorBugReportAttachScreenshotCheckbox"
)
BUG_REPORT_SCREENSHOT_ROW_OBJECT_NAME = "pipelineInspectorBugReportScreenshotRow"
BUG_REPORT_SCREENSHOT_PATH_INPUT_OBJECT_NAME = (
    "pipelineInspectorBugReportScreenshotPathInput"
)
BUG_REPORT_SCREENSHOT_BROWSE_BUTTON_OBJECT_NAME = (
    "pipelineInspectorBugReportScreenshotBrowseButton"
)
BUG_REPORT_FORM_WIDGET_OBJECT_NAME = "pipelineInspectorBugReportFormWidget"
BUG_REPORT_SUCCESS_WIDGET_OBJECT_NAME = "pipelineInspectorBugReportSuccessWidget"
BUG_REPORT_STATUS_LABEL_OBJECT_NAME = "pipelineInspectorBugReportStatusLabel"
BUG_REPORT_ISSUE_URL_LABEL_OBJECT_NAME = "pipelineInspectorBugReportIssueUrlLabel"
BUG_REPORT_ISSUE_URL_CAPTION_LABEL_OBJECT_NAME = (
    "pipelineInspectorBugReportIssueUrlCaptionLabel"
)
BUG_REPORT_SUBMIT_BUTTON_OBJECT_NAME = "pipelineInspectorBugReportSubmitButton"
BUG_REPORT_CLOSE_BUTTON_OBJECT_NAME = "pipelineInspectorBugReportCloseButton"

BUG_REPORT_DIALOG_INTRO = (
    "Report a bug in Maya Pipeline Inspector to the plugin maintainers. "
    "Your studio relay creates a GitHub issue and notifies the development team so "
    "the problem can be triaged and patched. "
    "Include plugin version, scene basename, and optional validation context."
)
BUG_REPORT_ISSUE_URL_CAPTION = "GitHub issue for maintainers to track the fix:"

@dataclass(frozen=True)
class BugReportFormValues:
    """Artist-entered bug report form fields."""

    title: str
    description: str
    steps_to_reproduce: str = ""
    attach_screenshot: bool = False
    screenshot_path: str = ""

@dataclass
class BugReportDialog:
    """Controller for the bug report submission dialog."""

    dialog: Any
    intro_label: Any
    form_widget: Any
    success_widget: Any
    title_input: Any
    description_input: Any
    steps_input: Any
    attach_screenshot_checkbox: Any
    screenshot_row: Any
    screenshot_path_input: Any
    screenshot_browse_button: Any
    status_label: Any
    issue_url_caption: Any
    issue_url_label: Any
    submit_button: Any
    close_button: Any

    @classmethod
    def build(
        cls,
        qt_widgets: Any,
        *,
        on_submit: Callable[[BugReportFormValues], BugReportRelayResult] | None = None,
        window_title: str = "Report Plugin Bug",
    ) -> BugReportDialog:
        dialog = qt_widgets.QDialog()
        dialog.setObjectName(BUG_REPORT_DIALOG_OBJECT_NAME)
        set_window_title = getattr(dialog, "setWindowTitle", None)
        if set_window_title is not None:
            set_window_title(window_title)

        layout = qt_widgets.QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        intro = qt_widgets.QLabel(BUG_REPORT_DIALOG_INTRO)
        intro.setObjectName(BUG_REPORT_INTRO_LABEL_OBJECT_NAME)
        set_intro_word_wrap = getattr(intro, "setWordWrap", None)
        if set_intro_word_wrap is not None:
            set_intro_word_wrap(True)
        layout.addWidget(intro)

        form_widget = qt_widgets.QWidget()
        form_widget.setObjectName(BUG_REPORT_FORM_WIDGET_OBJECT_NAME)
        form_layout = qt_widgets.QVBoxLayout(form_widget)
        set_form_margins = getattr(form_layout, "setContentsMargins", None)
        if set_form_margins is not None:
            set_form_margins(0, 0, 0, 0)

        title_input = _build_line_edit(
            qt_widgets,
            object_name=BUG_REPORT_TITLE_INPUT_OBJECT_NAME,
            placeholder="What went wrong in Pipeline Inspector?",
        )
        form_layout.addWidget(qt_widgets.QLabel("Title"))
        form_layout.addWidget(title_input)

        description_input = _build_text_edit(
            qt_widgets,
            object_name=BUG_REPORT_DESCRIPTION_INPUT_OBJECT_NAME,
            placeholder="Describe the plugin bug: expected behavior vs what happened in the panel.",
        )
        form_layout.addWidget(qt_widgets.QLabel("Description"))
        form_layout.addWidget(description_input)

        steps_input = _build_text_edit(
            qt_widgets,
            object_name=BUG_REPORT_STEPS_INPUT_OBJECT_NAME,
            placeholder="Optional steps to reproduce.",
        )
        form_layout.addWidget(qt_widgets.QLabel("Steps to reproduce"))
        form_layout.addWidget(steps_input)

        attach_screenshot_checkbox = qt_widgets.QCheckBox(
            "Attach screenshot (optional)"
        )
        attach_screenshot_checkbox.setObjectName(
            BUG_REPORT_ATTACH_SCREENSHOT_CHECKBOX_OBJECT_NAME
        )
        form_layout.addWidget(attach_screenshot_checkbox)

        screenshot_row = qt_widgets.QWidget()
        screenshot_row.setObjectName(BUG_REPORT_SCREENSHOT_ROW_OBJECT_NAME)
        screenshot_row_layout = qt_widgets.QHBoxLayout(screenshot_row)
        set_row_margins = getattr(screenshot_row_layout, "setContentsMargins", None)
        if set_row_margins is not None:
            set_row_margins(0, 0, 0, 0)

        screenshot_path_input = _build_line_edit(
            qt_widgets,
            object_name=BUG_REPORT_SCREENSHOT_PATH_INPUT_OBJECT_NAME,
            placeholder="Browse for PNG or JPEG screenshot",
        )
        set_read_only = getattr(screenshot_path_input, "setReadOnly", None)
        if set_read_only is not None:
            set_read_only(True)

        screenshot_browse_button = qt_widgets.QPushButton("Browse...")
        screenshot_browse_button.setObjectName(BUG_REPORT_SCREENSHOT_BROWSE_BUTTON_OBJECT_NAME)
        screenshot_row_layout.addWidget(screenshot_path_input, 1)
        screenshot_row_layout.addWidget(screenshot_browse_button)
        form_layout.addWidget(screenshot_row)
        _set_widget_visible(screenshot_row, False)

        def _on_attach_screenshot_toggled(checked: bool) -> None:
            _set_widget_visible(screenshot_row, checked)
            if not checked:
                _set_line_edit_text(screenshot_path_input, "")

        toggled = getattr(attach_screenshot_checkbox, "toggled", None)
        if toggled is not None:
            connect_toggled = getattr(toggled, "connect", None)
            if connect_toggled is not None:
                connect_toggled(_on_attach_screenshot_toggled)
        else:
            state_changed = getattr(attach_screenshot_checkbox, "stateChanged", None)
            if state_changed is not None:
                connect_state = getattr(state_changed, "connect", None)
                if connect_state is not None:
                    connect_state(
                        lambda _state: _on_attach_screenshot_toggled(
                            _checkbox_checked(attach_screenshot_checkbox)
                        )
                    )

        wire_button(
            screenshot_browse_button,
            lambda: _pick_screenshot_file(
                qt_widgets,
                dialog,
                screenshot_path_input,
            ),
        )
        layout.addWidget(form_widget)

        success_widget = qt_widgets.QWidget()
        success_widget.setObjectName(BUG_REPORT_SUCCESS_WIDGET_OBJECT_NAME)
        success_layout = qt_widgets.QVBoxLayout(success_widget)
        set_success_margins = getattr(success_layout, "setContentsMargins", None)
        if set_success_margins is not None:
            set_success_margins(0, 0, 0, 0)

        status_label = qt_widgets.QLabel("")
        status_label.setObjectName(BUG_REPORT_STATUS_LABEL_OBJECT_NAME)
        set_status_word_wrap = getattr(status_label, "setWordWrap", None)
        if set_status_word_wrap is not None:
            set_status_word_wrap(True)
        success_layout.addWidget(status_label)

        issue_url_caption = qt_widgets.QLabel(BUG_REPORT_ISSUE_URL_CAPTION)
        issue_url_caption.setObjectName(BUG_REPORT_ISSUE_URL_CAPTION_LABEL_OBJECT_NAME)
        set_caption_word_wrap = getattr(issue_url_caption, "setWordWrap", None)
        if set_caption_word_wrap is not None:
            set_caption_word_wrap(True)
        success_layout.addWidget(issue_url_caption)

        issue_url_label = qt_widgets.QLabel("")
        issue_url_label.setObjectName(BUG_REPORT_ISSUE_URL_LABEL_OBJECT_NAME)
        set_issue_word_wrap = getattr(issue_url_label, "setWordWrap", None)
        if set_issue_word_wrap is not None:
            set_issue_word_wrap(True)
        set_text_interaction = getattr(issue_url_label, "setTextInteractionFlags", None)
        text_selectable = getattr(qt_widgets, "Qt", None)
        if set_text_interaction is not None and text_selectable is not None:
            selectable = getattr(
                getattr(text_selectable, "TextSelectableByMouse", None),
                "value",
                None,
            )
            if selectable is not None:
                set_text_interaction(selectable)
        success_layout.addWidget(issue_url_label)
        _set_widget_visible(success_widget, False)
        layout.addWidget(success_widget)

        button_row = qt_widgets.QHBoxLayout()
        button_row.addStretch(1)
        submit_button = qt_widgets.QPushButton("Submit Report")
        submit_button.setObjectName(BUG_REPORT_SUBMIT_BUTTON_OBJECT_NAME)
        close_button = qt_widgets.QPushButton("Close")
        close_button.setObjectName(BUG_REPORT_CLOSE_BUTTON_OBJECT_NAME)
        wire_button(close_button, lambda: _close_dialog(dialog))
        button_row.addWidget(submit_button)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

        controller = cls(
            dialog=dialog,
            intro_label=intro,
            form_widget=form_widget,
            success_widget=success_widget,
            title_input=title_input,
            description_input=description_input,
            steps_input=steps_input,
            attach_screenshot_checkbox=attach_screenshot_checkbox,
            screenshot_row=screenshot_row,
            screenshot_path_input=screenshot_path_input,
            screenshot_browse_button=screenshot_browse_button,
            status_label=status_label,
            issue_url_caption=issue_url_caption,
            issue_url_label=issue_url_label,
            submit_button=submit_button,
            close_button=close_button,
        )
        if on_submit is not None:
            wire_button(submit_button, lambda: controller._handle_submit(on_submit))
        return controller

    def read_form_values(self) -> BugReportFormValues:
        attach_screenshot = _checkbox_checked(self.attach_screenshot_checkbox)
        screenshot_path = (
            _read_line_edit_text(self.screenshot_path_input)
            if attach_screenshot
            else ""
        )
        return BugReportFormValues(
            title=_read_line_edit_text(self.title_input),
            description=_read_text_edit_text(self.description_input),
            steps_to_reproduce=_read_text_edit_text(self.steps_input),
            attach_screenshot=attach_screenshot,
            screenshot_path=screenshot_path,
        )

    def apply_submit_result(self, result: BugReportRelayResult) -> None:
        if result.submitted and result.issue_url:
            self._show_success(result.issue_url)
            return
        self._show_failure(format_bug_report_failure_status(result))

    def _handle_submit(
        self,
        on_submit: Callable[[BugReportFormValues], BugReportRelayResult],
    ) -> None:
        values = self.read_form_values()
        if not values.title or not values.description:
            self._show_failure("Title and description are required.")
            return
        result = on_submit(values)
        self.apply_submit_result(result)

    def _show_success(self, issue_url: str) -> None:
        _ = issue_url
        _set_widget_visible(self.intro_label, False)
        _set_widget_visible(self.form_widget, False)
        _set_widget_visible(self.success_widget, True)
        _set_label_text(self.status_label, format_bug_report_success_headline())
        _set_widget_visible(self.issue_url_caption, False)
        _set_widget_visible(self.issue_url_label, False)
        _set_label_text(self.issue_url_label, "")
        _set_widget_visible(self.submit_button, False)
        _compact_bug_report_dialog(self.dialog)

    def _show_failure(self, message: str) -> None:
        _set_widget_visible(self.form_widget, True)
        _set_widget_visible(self.success_widget, True)
        _set_label_text(self.status_label, message)
        _set_label_text(self.issue_url_label, "")
        _set_widget_visible(self.issue_url_caption, False)

def show_bug_report_dialog(
    qt_widgets: Any,
    *,
    parent: Any | None = None,
    on_submit: Callable[[BugReportFormValues], BugReportRelayResult] | None = None,
) -> Any:
    """Display the bug report dialog and return the dialog widget."""

    controller = BugReportDialog.build(qt_widgets, on_submit=on_submit)
    dialog = controller.dialog
    from pipeline_inspector.ui.settings_widgets import show_modal_dialog

    show_modal_dialog(
        dialog,
        qt_widgets,
        parent=parent,
        singleton_key=BUG_REPORT_DIALOG_OBJECT_NAME,
    )
    return dialog


def _build_line_edit(
    qt_widgets: Any,
    *,
    object_name: str,
    placeholder: str,
) -> Any:
    line_edit = qt_widgets.QLineEdit()
    line_edit.setObjectName(object_name)
    set_placeholder = getattr(line_edit, "setPlaceholderText", None)
    if set_placeholder is not None:
        set_placeholder(placeholder)
    return line_edit

def _build_text_edit(
    qt_widgets: Any,
    *,
    object_name: str,
    placeholder: str,
) -> Any:
    text_edit = qt_widgets.QTextEdit()
    text_edit.setObjectName(object_name)
    set_placeholder = getattr(text_edit, "setPlaceholderText", None)
    if set_placeholder is not None:
        set_placeholder(placeholder)
    return text_edit

def _read_line_edit_text(widget: Any) -> str:
    read_text = getattr(widget, "text", None)
    if callable(read_text):
        return str(read_text() or "").strip()
    return ""

def _read_text_edit_text(widget: Any) -> str:
    to_plain_text = getattr(widget, "toPlainText", None)
    if callable(to_plain_text):
        return str(to_plain_text() or "").strip()
    return ""


def _set_line_edit_text(widget: Any, text: str) -> None:
    set_text = getattr(widget, "setText", None)
    if set_text is not None:
        set_text(text)


def _pick_screenshot_file(qt_widgets: Any, parent: Any, path_input: Any) -> None:
    file_dialog = getattr(qt_widgets, "QFileDialog", None)
    get_open = getattr(file_dialog, "getOpenFileName", None) if file_dialog is not None else None
    if get_open is None:
        return
    selected, _filter = get_open(
        parent,
        "Attach Screenshot",
        _read_line_edit_text(path_input),
        "Images (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*)",
    )
    if selected:
        _set_line_edit_text(path_input, str(selected))


def _checkbox_checked(widget: Any) -> bool:
    is_checked = getattr(widget, "isChecked", None)
    if is_checked is None:
        return False
    return bool(is_checked())

def _set_label_text(widget: Any, text: str) -> None:
    set_text = getattr(widget, "setText", None)
    if set_text is not None:
        set_text(text)

def _set_button_enabled(widget: Any, enabled: bool) -> None:
    set_enabled = getattr(widget, "setEnabled", None)
    if set_enabled is not None:
        set_enabled(enabled)

def _set_button_text(widget: Any, text: str) -> None:
    set_text = getattr(widget, "setText", None)
    if set_text is not None:
        set_text(text)

def _set_widget_visible(widget: Any, visible: bool) -> None:
    set_visible = getattr(widget, "setVisible", None)
    if set_visible is not None:
        set_visible(visible)

def _compact_bug_report_dialog(dialog: Any) -> None:
    adjust_size = getattr(dialog, "adjustSize", None)
    if adjust_size is not None:
        adjust_size()
    size_hint = getattr(dialog, "sizeHint", None)
    set_fixed_size = getattr(dialog, "setFixedSize", None)
    if size_hint is None or set_fixed_size is None:
        return
    hint = size_hint()
    width_fn = getattr(hint, "width", None)
    height_fn = getattr(hint, "height", None)
    if width_fn is None or height_fn is None:
        return
    width = max(int(width_fn()), 320)
    height = max(int(height_fn()), 100)
    set_fixed_size(width, min(height, 160))


def _close_dialog(dialog: Any) -> None:
    reject = getattr(dialog, "reject", None)
    if reject is not None:
        reject()
        return
    close = getattr(dialog, "close", None)
    if close is not None:
        close()
