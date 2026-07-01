from __future__ import annotations

from typing import Any, Optional

from shader_health.ui import main_window


class FakeWidget:
    def __init__(self) -> None:
        self.object_name: Optional[str] = None
        self.children: list[Any] = []
        self.layout: Optional[FakeVBoxLayout] = None

    def setObjectName(self, object_name: str) -> None:
        self.object_name = object_name


class FakeLabel(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.text = text
        self.word_wrap = False

    def setWordWrap(self, enabled: bool) -> None:
        self.word_wrap = enabled


class FakeComboBox(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[str] = []
        self.current_text = ""
        self.tooltip = ""

    def addItems(self, items: list[str]) -> None:
        self.items.extend(items)

    def setCurrentText(self, text: str) -> None:
        self.current_text = text

    def setToolTip(self, text: str) -> None:
        self.tooltip = text


class FakePushButton(FakeLabel):
    def __init__(self, text: str = "") -> None:
        super().__init__(text)
        self.enabled = True
        self.tooltip = ""

    def setEnabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def setToolTip(self, text: str) -> None:
        self.tooltip = text


class FakeVBoxLayout:
    def __init__(self, parent: FakeWidget) -> None:
        self.parent = parent
        self.parent.layout = self
        self.margins: Optional[tuple[int, int, int, int]] = None
        self.spacing: Optional[int] = None
        self.widgets: list[Any] = []
        self.stretches: list[int] = []

    def setContentsMargins(self, left: int, top: int, right: int, bottom: int) -> None:
        self.margins = (left, top, right, bottom)

    def setSpacing(self, spacing: int) -> None:
        self.spacing = spacing

    def addWidget(self, widget: Any) -> None:
        self.widgets.append(widget)
        self.parent.children.append(widget)

    def addStretch(self, stretch: int) -> None:
        self.stretches.append(stretch)


class FakeQtWidgets:
    QWidget = FakeWidget
    QLabel = FakeLabel
    QComboBox = FakeComboBox
    QPushButton = FakePushButton
    QVBoxLayout = FakeVBoxLayout


def test_summary_header_defaults_show_score_counts_blocks_and_profile_dropdown():
    header = main_window.build_summary_header(FakeQtWidgets)

    assert _find(header, main_window.HEALTH_SCORE_LABEL_OBJECT_NAME).text == "Health: 100 / 100"
    assert (
        _find(header, main_window.SEVERITY_COUNTS_LABEL_OBJECT_NAME).text
        == "Critical: 0   Error: 0   Warning: 0   Info: 0"
    )
    assert (
        _find(header, main_window.BLOCK_STATUS_LABEL_OBJECT_NAME).text
        == "Publish Block: NO   Deadline Block: NO"
    )
    profile_dropdown = _find(header, main_window.PROFILE_DROPDOWN_OBJECT_NAME)
    assert profile_dropdown.items == list(main_window.DEFAULT_PROFILE_OPTIONS)
    assert profile_dropdown.current_text == "artist_relaxed"


def test_summary_header_formats_failed_blocking_state():
    state = main_window.SummaryHeaderState(
        health_score=42,
        critical_count=2,
        error_count=4,
        warning_count=7,
        info_count=11,
        block_publish=True,
        block_deadline=True,
        profile_id="deadline_critical",
    )

    header = main_window.build_summary_header(FakeQtWidgets, state=state)

    assert _find(header, main_window.HEALTH_SCORE_LABEL_OBJECT_NAME).text == "Health: 42 / 100"
    assert (
        _find(header, main_window.SEVERITY_COUNTS_LABEL_OBJECT_NAME).text
        == "Critical: 2   Error: 4   Warning: 7   Info: 11"
    )
    assert (
        _find(header, main_window.BLOCK_STATUS_LABEL_OBJECT_NAME).text
        == "Publish Block: YES   Deadline Block: YES"
    )
    assert _find(header, main_window.PROFILE_DROPDOWN_OBJECT_NAME).current_text == "deadline_critical"


def test_summary_header_accepts_custom_profile_options():
    state = main_window.SummaryHeaderState(profile_id="show_publish")

    header = main_window.build_summary_header(
        FakeQtWidgets,
        state=state,
        profile_options=("artist_relaxed", "show_publish"),
    )

    profile_dropdown = _find(header, main_window.PROFILE_DROPDOWN_OBJECT_NAME)
    assert profile_dropdown.items == ["artist_relaxed", "show_publish"]
    assert profile_dropdown.current_text == "show_publish"


def test_main_widget_contains_summary_header():
    widget = main_window.build_main_widget(FakeQtWidgets)

    summary_header = _find(widget, main_window.SUMMARY_HEADER_OBJECT_NAME)
    assert summary_header.object_name == main_window.SUMMARY_HEADER_OBJECT_NAME


def _find(widget: Any, object_name: str) -> Any:
    if getattr(widget, "object_name", None) == object_name:
        return widget
    for child in getattr(widget, "children", []):
        try:
            return _find(child, object_name)
        except AssertionError:
            pass
    raise AssertionError(f"Could not find object named {object_name!r}")
