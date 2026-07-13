from __future__ import annotations

from pipeline_inspector.ui.basic_settings_section import (
    SETTINGS_DEFAULT_ASSET_CLASS_COMBO_OBJECT_NAME,
    SETTINGS_DEFAULT_PROFILE_COMBO_OBJECT_NAME,
    SETTINGS_DEFAULT_SCAN_SCOPE_COMBO_OBJECT_NAME,
    SETTINGS_DOCS_URL_INPUT_OBJECT_NAME,
    SETTINGS_THEME_COMBO_OBJECT_NAME,
    SETTINGS_UI_DENSITY_COMBO_OBJECT_NAME,
    build_basic_settings_section,
    read_basic_user_preferences_from_view,
    update_basic_settings_view,
)
from pipeline_inspector.user_config import DEFAULT_USER_DOCS_URL, UserPreferences


class FakeWidget:
    def __init__(self) -> None:
        self.object_name: str | None = None
        self.children: list[object] = []
        self.layout: object | None = None

    def setObjectName(self, object_name: str) -> None:
        self.object_name = object_name


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
        self.tooltip = ""
        self.editingFinished = FakeSignal()

    def setText(self, text: str) -> None:
        self.value = text

    def text(self) -> str:
        return self.value

    def setPlaceholderText(self, text: str) -> None:
        self.placeholder = text

    def setToolTip(self, text: str) -> None:
        self.tooltip = text


class FakeComboBox(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[tuple[str, str]] = []
        self.current_index = 0
        self.tooltip = ""
        self.currentIndexChanged = FakeSignal()

    def addItem(self, text: str, user_data: str = "") -> None:
        self.items.append((text, user_data or text))

    def setCurrentIndex(self, index: int) -> None:
        self.current_index = index

    def setCurrentText(self, text: str) -> None:
        for index, (label, _data) in enumerate(self.items):
            if label == text:
                self.current_index = index
                return

    def currentText(self) -> str:
        if not self.items:
            return ""
        return self.items[self.current_index][0]

    def currentData(self):
        if not self.items:
            return None
        return self.items[self.current_index][1]

    def findData(self, data: str) -> int:
        for index, (_label, item_data) in enumerate(self.items):
            if item_data == data:
                return index
        return -1

    def setToolTip(self, text: str) -> None:
        self.tooltip = text


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

    def addStretch(self, stretch: int = 0) -> None:
        self.stretches.append(stretch)


class FakeFormLayout:
    def __init__(self) -> None:
        self.rows: list[tuple[str, object]] = []

    def setContentsMargins(self, *_args: object) -> None:
        return

    def addRow(self, label: str, field: object) -> None:
        self.rows.append((label, field))


class FakeTabWidget(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.tabs: list[object] = []

    def widget(self, index: int):
        return self.tabs[index]


class FakeQtWidgets:
    QWidget = FakeWidget
    QLabel = FakeLabel
    QLineEdit = FakeLineEdit
    QComboBox = FakeComboBox
    QVBoxLayout = FakeVBoxLayout
    QFormLayout = FakeFormLayout
    QTabWidget = FakeTabWidget


def test_basic_settings_section_exposes_profile_asset_scan_scope_and_density_controls():
    section = build_basic_settings_section(
        FakeQtWidgets,
        UserPreferences(
            default_profile_id="publish_strict",
            default_asset_class_id="asset_class_hero",
            default_scan_scope="selection",
            ui_density="compact",
            theme="dark",
        ),
    )

    profile_combo = _find(section, SETTINGS_DEFAULT_PROFILE_COMBO_OBJECT_NAME)
    asset_class_combo = _find(section, SETTINGS_DEFAULT_ASSET_CLASS_COMBO_OBJECT_NAME)
    scan_scope_combo = _find(section, SETTINGS_DEFAULT_SCAN_SCOPE_COMBO_OBJECT_NAME)
    density_combo = _find(section, SETTINGS_UI_DENSITY_COMBO_OBJECT_NAME)
    theme_combo = _find(section, SETTINGS_THEME_COMBO_OBJECT_NAME)

    assert profile_combo.currentData() == "publish_strict"
    assert asset_class_combo.currentData() == "asset_class_hero"
    assert scan_scope_combo.currentData() == "selection"
    assert density_combo.currentData() == "compact"
    assert theme_combo.currentData() == "dark"
    docs_input = _find(section, SETTINGS_DOCS_URL_INPUT_OBJECT_NAME)
    assert docs_input.value == DEFAULT_USER_DOCS_URL
    assert docs_input.placeholder == DEFAULT_USER_DOCS_URL


def test_read_basic_user_preferences_from_view_round_trips_combo_values():
    section = build_basic_settings_section(
        FakeQtWidgets,
        UserPreferences(default_profile_id="artist_relaxed"),
    )
    _find(section, SETTINGS_DEFAULT_PROFILE_COMBO_OBJECT_NAME).setCurrentIndex(
        _find(section, SETTINGS_DEFAULT_PROFILE_COMBO_OBJECT_NAME).findData("deadline_critical")
    )
    _find(section, SETTINGS_DEFAULT_ASSET_CLASS_COMBO_OBJECT_NAME).setCurrentIndex(
        _find(section, SETTINGS_DEFAULT_ASSET_CLASS_COMBO_OBJECT_NAME).findData("asset_class_prop")
    )
    _find(section, SETTINGS_DEFAULT_SCAN_SCOPE_COMBO_OBJECT_NAME).setCurrentIndex(1)
    _find(section, SETTINGS_UI_DENSITY_COMBO_OBJECT_NAME).setCurrentIndex(1)
    _find(section, SETTINGS_THEME_COMBO_OBJECT_NAME).setCurrentIndex(1)
    _find(section, SETTINGS_DOCS_URL_INPUT_OBJECT_NAME).setText("https://example.test/docs")

    loaded = read_basic_user_preferences_from_view(
        section,
        FakeQtWidgets,
        base=UserPreferences(),
    )

    assert loaded.default_profile_id == "deadline_critical"
    assert loaded.default_asset_class_id == "asset_class_prop"
    assert loaded.default_scan_scope == "selection"
    assert loaded.ui_density == "compact"
    assert loaded.theme == "dark"
    assert loaded.docs_url == "https://example.test/docs"


def test_update_basic_settings_view_refreshes_controls():
    section = build_basic_settings_section(
        FakeQtWidgets,
        UserPreferences(default_profile_id="artist_relaxed"),
    )

    update_basic_settings_view(
        section,
        FakeQtWidgets,
        UserPreferences(
            default_profile_id="supervisor_full",
            default_asset_class_id="asset_class_background",
            default_scan_scope="selection",
            ui_density="compact",
            theme="dark",
            docs_url="https://studio.test/wiki",
        ),
    )

    assert _find(section, SETTINGS_DEFAULT_PROFILE_COMBO_OBJECT_NAME).currentData() == (
        "supervisor_full"
    )
    assert _find(section, SETTINGS_DEFAULT_ASSET_CLASS_COMBO_OBJECT_NAME).currentData() == (
        "asset_class_background"
    )
    assert _find(section, SETTINGS_DEFAULT_SCAN_SCOPE_COMBO_OBJECT_NAME).currentData() == (
        "selection"
    )
    assert _find(section, SETTINGS_UI_DENSITY_COMBO_OBJECT_NAME).currentData() == "compact"
    assert _find(section, SETTINGS_THEME_COMBO_OBJECT_NAME).currentData() == "dark"
    assert _find(section, SETTINGS_DOCS_URL_INPUT_OBJECT_NAME).value == (
        "https://studio.test/wiki"
    )


def _find(widget: object, object_name: str) -> object:
    stack = [widget]
    while stack:
        current = stack.pop()
        if getattr(current, "object_name", None) == object_name:
            return current
        stack.extend(getattr(current, "children", []))
    raise AssertionError(f"Could not find object named {object_name!r}")
