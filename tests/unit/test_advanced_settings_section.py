from __future__ import annotations

from shader_health.ui.advanced_settings_section import (
    SETTINGS_BROWSE_RULES_BUTTON_OBJECT_NAME,
    SETTINGS_DEBUG_LOGGING_TOGGLE_OBJECT_NAME,
    SETTINGS_EXTRA_RULE_PATHS_INPUT_OBJECT_NAME,
    SETTINGS_MAX_ISSUES_INPUT_OBJECT_NAME,
    SETTINGS_MAYAPY_PATH_INPUT_OBJECT_NAME,
    build_advanced_settings_section,
    parse_extra_rule_paths,
    parse_max_issues_displayed,
    read_advanced_user_preferences_from_view,
    update_advanced_settings_view,
)
from shader_health.user_config import DEFAULT_MAX_ISSUES_DISPLAYED, UserPreferences


class FakeWidget:
    def __init__(self) -> None:
        self.object_name: str | None = None
        self.children: list[object] = []
        self.layout: object | None = None
        self.tooltip = ""

    def setObjectName(self, object_name: str) -> None:
        self.object_name = object_name

    def setToolTip(self, text: str) -> None:
        self.tooltip = text

    def setLayout(self, layout: object) -> None:
        self.layout = layout
        for widget in getattr(layout, "widgets", []):
            if widget not in self.children:
                self.children.append(widget)


class FakeLabel(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.text = text
        self.word_wrap = False

    def setWordWrap(self, enabled: bool) -> None:
        self.word_wrap = enabled

    def setText(self, text: str) -> None:
        self.text = text


class FakeSignal:
    def __init__(self) -> None:
        self.handlers: list[object] = []

    def connect(self, handler: object) -> None:
        self.handlers.append(handler)


class FakeLineEdit(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.value = text
        self.placeholder = ""

    def setText(self, text: str) -> None:
        self.value = text

    def text(self) -> str:
        return self.value

    def setPlaceholderText(self, text: str) -> None:
        self.placeholder = text

    @property
    def editingFinished(self) -> FakeSignal:
        return FakeSignal()


class FakePlainTextEdit(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.value = text
        self.placeholder = ""
        self.plainTextChanged = FakeSignal()

    def setPlainText(self, text: str) -> None:
        self.value = text

    def toPlainText(self) -> str:
        return self.value

    def setPlaceholderText(self, text: str) -> None:
        self.placeholder = text


class FakePushButton(FakeLabel):
    def __init__(self, text: str = "") -> None:
        super().__init__(text)
        self.checkable = False
        self.checked = False
        self.style_sheet = ""
        self.clicked = FakeSignal()

    def setCheckable(self, enabled: bool) -> None:
        self.checkable = enabled

    def setChecked(self, checked: bool) -> None:
        self.checked = checked

    def isChecked(self) -> bool:
        return self.checked

    def setStyleSheet(self, style: str) -> None:
        self.style_sheet = style


class FakeVBoxLayout:
    def __init__(self, parent: FakeWidget | None = None) -> None:
        self.parent = parent
        self.widgets: list[object] = []
        self.layouts: list[object] = []
        self.stretches: list[int] = []
        if parent is not None:
            parent.layout = self

    def setContentsMargins(self, *_args: object) -> None:
        return

    def setSpacing(self, _spacing: int) -> None:
        return

    def addWidget(self, widget: object, *_args: object) -> None:
        self.widgets.append(widget)
        if self.parent is not None and widget not in self.parent.children:
            self.parent.children.append(widget)

    def addLayout(self, layout: object) -> None:
        self.layouts.append(layout)
        parent_widget = self.parent
        for _label, field in getattr(layout, "rows", []):
            if parent_widget is not None and field not in parent_widget.children:
                parent_widget.children.append(field)
        for widget in getattr(layout, "widgets", []):
            if parent_widget is not None and widget not in parent_widget.children:
                parent_widget.children.append(widget)

    def addStretch(self, stretch: int = 0) -> None:
        self.stretches.append(stretch)


class FakeHBoxLayout(FakeVBoxLayout):
    pass


class FakeFormLayout:
    def __init__(self) -> None:
        self.rows: list[tuple[str, object]] = []

    def setContentsMargins(self, *_args: object) -> None:
        return

    def addRow(self, label: str, field: object) -> None:
        self.rows.append((label, field))


class FakeQtWidgets:
    QWidget = FakeWidget
    QLabel = FakeLabel
    QLineEdit = FakeLineEdit
    QPlainTextEdit = FakePlainTextEdit
    QPushButton = FakePushButton
    QVBoxLayout = FakeVBoxLayout
    QHBoxLayout = FakeHBoxLayout
    QFormLayout = FakeFormLayout


def test_advanced_settings_section_exposes_browse_rules_button():
    opened: list[str] = []

    section = build_advanced_settings_section(
        FakeQtWidgets,
        UserPreferences(),
        on_open_rule_browser=lambda: opened.append("opened"),
    )
    button = _find(section, SETTINGS_BROWSE_RULES_BUTTON_OBJECT_NAME)

    assert button.text == "Browse Rules…"
    assert button.clicked.handlers
    button.clicked.handlers[0]()
    assert opened == ["opened"]


def test_advanced_settings_section_exposes_rule_paths_debug_max_issues_and_mayapy():
    section = build_advanced_settings_section(
        FakeQtWidgets,
        UserPreferences(
            extra_rule_paths=("/show/rules", "//farm/share/td"),
            debug_logging=True,
            max_issues_displayed=120,
            mayapy_path="C:/Maya2025/bin/mayapy.exe",
        ),
    )

    extra_paths = _find(section, SETTINGS_EXTRA_RULE_PATHS_INPUT_OBJECT_NAME)
    debug_toggle = _find(section, SETTINGS_DEBUG_LOGGING_TOGGLE_OBJECT_NAME)
    max_issues = _find(section, SETTINGS_MAX_ISSUES_INPUT_OBJECT_NAME)
    mayapy = _find(section, SETTINGS_MAYAPY_PATH_INPUT_OBJECT_NAME)

    assert extra_paths.toPlainText() == "/show/rules\n//farm/share/td"
    assert debug_toggle.isChecked() is True
    assert max_issues.text() == "120"
    assert mayapy.text() == "C:/Maya2025/bin/mayapy.exe"


def test_read_advanced_user_preferences_from_view_round_trips_fields():
    section = build_advanced_settings_section(
        FakeQtWidgets,
        UserPreferences(),
    )
    _find(section, SETTINGS_EXTRA_RULE_PATHS_INPUT_OBJECT_NAME).setPlainText(
        "D:/rules/custom\n\n//farm/share/td_rules"
    )
    _find(section, SETTINGS_DEBUG_LOGGING_TOGGLE_OBJECT_NAME).setChecked(True)
    _find(section, SETTINGS_MAX_ISSUES_INPUT_OBJECT_NAME).setText("42")
    _find(section, SETTINGS_MAYAPY_PATH_INPUT_OBJECT_NAME).setText("C:/mayapy.exe")

    loaded = read_advanced_user_preferences_from_view(
        section,
        FakeQtWidgets,
        base=UserPreferences(default_profile_id="artist_relaxed"),
    )

    assert loaded.default_profile_id == "artist_relaxed"
    assert loaded.extra_rule_paths == ("D:/rules/custom", "//farm/share/td_rules")
    assert loaded.debug_logging is True
    assert loaded.max_issues_displayed == 42
    assert loaded.mayapy_path == "C:/mayapy.exe"


def test_update_advanced_settings_view_refreshes_controls():
    section = build_advanced_settings_section(
        FakeQtWidgets,
        UserPreferences(debug_logging=False, max_issues_displayed=50),
    )

    update_advanced_settings_view(
        section,
        FakeQtWidgets,
        UserPreferences(
            extra_rule_paths=("/studio/rules",),
            debug_logging=True,
            max_issues_displayed=300,
            mayapy_path="D:/tools/mayapy.exe",
        ),
    )

    assert _find(section, SETTINGS_EXTRA_RULE_PATHS_INPUT_OBJECT_NAME).toPlainText() == (
        "/studio/rules"
    )
    assert _find(section, SETTINGS_DEBUG_LOGGING_TOGGLE_OBJECT_NAME).isChecked() is True
    assert _find(section, SETTINGS_MAX_ISSUES_INPUT_OBJECT_NAME).text() == "300"
    assert _find(section, SETTINGS_MAYAPY_PATH_INPUT_OBJECT_NAME).text() == "D:/tools/mayapy.exe"


def test_parse_extra_rule_paths_skips_blank_lines():
    assert parse_extra_rule_paths(" /a \n\n/b\r\n") == ("/a", "/b")


def test_parse_max_issues_displayed_clamps_and_defaults():
    assert parse_max_issues_displayed("") == DEFAULT_MAX_ISSUES_DISPLAYED
    assert parse_max_issues_displayed("not-a-number") == DEFAULT_MAX_ISSUES_DISPLAYED
    assert parse_max_issues_displayed("0") == 1
    assert parse_max_issues_displayed("99999") == 5000


def _find(widget: object, object_name: str) -> object:
    stack = [widget]
    while stack:
        current = stack.pop()
        if getattr(current, "object_name", None) == object_name:
            return current
        stack.extend(getattr(current, "children", []))
    raise AssertionError(f"Could not find object named {object_name!r}")
