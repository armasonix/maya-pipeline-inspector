from __future__ import annotations

from pipeline_inspector.studio_config import StudioConfig, StudioEnvironmentSettings
from pipeline_inspector.ui.studio_environment_section import (
    SETTINGS_ASSET_ROOT_INPUT_OBJECT_NAME,
    SETTINGS_CACHE_ROOT_INPUT_OBJECT_NAME,
    SETTINGS_RENDER_ROOT_INPUT_OBJECT_NAME,
    SETTINGS_TEXTURE_ROOT_INPUT_OBJECT_NAME,
    SETTINGS_VARIABLE_ALIASES_INPUT_OBJECT_NAME,
    build_studio_environment_section,
    format_variable_aliases,
    parse_variable_aliases,
    read_studio_environment_from_view,
    update_studio_environment_view,
)


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
        self.fixed_width: int | None = None
        self.size_policy: tuple[object, object] | None = None

    def setWordWrap(self, enabled: bool) -> None:
        self.word_wrap = enabled

    def setText(self, text: str) -> None:
        self.text = text

    def setFixedWidth(self, width: int) -> None:
        self.fixed_width = width

    def setSizePolicy(self, horizontal: object, vertical: object) -> None:
        self.size_policy = (horizontal, vertical)


class FakeLineEdit(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.value = text
        self.placeholder = ""
        self.fixed_width: int | None = None
        self.size_policy: tuple[object, object] | None = None
        self.editingFinished = _FakeSignal()

    def setText(self, text: str) -> None:
        self.value = text

    def text(self) -> str:
        return self.value

    def setPlaceholderText(self, text: str) -> None:
        self.placeholder = text

    def setFixedWidth(self, width: int) -> None:
        self.fixed_width = width

    def setSizePolicy(self, horizontal: object, vertical: object) -> None:
        self.size_policy = (horizontal, vertical)


class FakePlainTextEdit(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.value = ""
        self.placeholder = ""
        self.tooltip = ""
        self.plainTextChanged = _FakeSignal()

    def setPlainText(self, text: str) -> None:
        self.value = text

    def toPlainText(self) -> str:
        return self.value

    def setPlaceholderText(self, text: str) -> None:
        self.placeholder = text

    def setToolTip(self, text: str) -> None:
        self.tooltip = text


class _FakeSignal:
    def __init__(self) -> None:
        self.handlers: list[object] = []

    def connect(self, handler: object) -> None:
        self.handlers.append(handler)


class FakeHBoxLayout:
    def __init__(self) -> None:
        self.widgets: list[object] = []
        self.layouts: list[object] = []
        self.spacing: int | None = None
        self.margins: tuple[int, int, int, int] | None = None

    def setContentsMargins(self, *margins: int) -> None:
        self.margins = margins

    def setSpacing(self, spacing: int) -> None:
        self.spacing = spacing

    def addWidget(self, widget: object) -> None:
        self.widgets.append(widget)

    def addLayout(self, layout: object) -> None:
        self.layouts.append(layout)


class FakeVBoxLayout:
    def __init__(self, parent: FakeWidget | None = None) -> None:
        self.parent = parent
        self.widgets: list[object] = []
        self.layouts: list[object] = []
        self.spacing: int | None = None
        self.margins: tuple[int, int, int, int] | None = None
        if parent is not None:
            parent.layout = self

    def setContentsMargins(self, *margins: int) -> None:
        self.margins = margins

    def setSpacing(self, spacing: int) -> None:
        self.spacing = spacing

    def addWidget(self, widget: object) -> None:
        self.widgets.append(widget)
        self._attach_widget(widget)

    def addLayout(self, layout: object) -> None:
        self.layouts.append(layout)
        for widget in getattr(layout, "widgets", []):
            self._attach_widget(widget)
        for nested in getattr(layout, "layouts", []):
            for widget in getattr(nested, "widgets", []):
                self._attach_widget(widget)

    def addStretch(self, _stretch: int = 0) -> None:
        return

    def _attach_widget(self, widget: object) -> None:
        if self.parent is not None and isinstance(widget, FakeWidget):
            if widget not in self.parent.children:
                self.parent.children.append(widget)
            for child in widget.children:
                if isinstance(child, FakeWidget) and child not in self.parent.children:
                    self.parent.children.append(child)


class FakeGridLayout(FakeVBoxLayout):
    def __init__(self, parent: FakeWidget | None = None) -> None:
        super().__init__(parent)
        self.column_stretch: dict[int, int] = {}
        self.column_minimum_width: dict[int, int] = {}

    def setHorizontalSpacing(self, spacing: int) -> None:
        self.horizontal_spacing = spacing

    def setVerticalSpacing(self, spacing: int) -> None:
        self.vertical_spacing = spacing

    def setColumnStretch(self, column: int, stretch: int) -> None:
        self.column_stretch[column] = stretch

    def setColumnMinimumWidth(self, column: int, width: int) -> None:
        self.column_minimum_width[column] = width

    def addWidget(self, widget: object, row: int = 0, column: int = 0, *_args: object) -> None:
        self.widgets.append((widget, row, column))
        self._attach_widget(widget)


class FakeQtWidgets:
    QWidget = FakeWidget
    QLabel = FakeLabel
    QLineEdit = FakeLineEdit
    QPlainTextEdit = FakePlainTextEdit
    QHBoxLayout = FakeHBoxLayout
    QVBoxLayout = FakeVBoxLayout
    QGridLayout = FakeGridLayout


def _find(root: FakeWidget, object_name: str) -> FakeWidget:
    stack = [root]
    while stack:
        current = stack.pop()
        if getattr(current, "object_name", None) == object_name:
            return current
        stack.extend(getattr(current, "children", []))
    raise AssertionError(f"Widget not found: {object_name}")


def test_parse_and_format_variable_aliases_round_trip():
    aliases = {
        "STUDIO_TEXTURE_ROOT": "\\\\farm\\textures",
        "CUSTOM_ROOT": "\\\\farm\\custom",
    }

    assert parse_variable_aliases(format_variable_aliases(aliases)) == aliases


def test_parse_variable_aliases_skips_invalid_lines():
    text = "\n".join(
        [
            "STUDIO_TEXTURE_ROOT=\\\\farm\\textures",
            "invalid-line",
            "  ",
            "CUSTOM_ROOT=\\\\farm\\custom",
        ]
    )

    assert parse_variable_aliases(text) == {
        "STUDIO_TEXTURE_ROOT": "\\\\farm\\textures",
        "CUSTOM_ROOT": "\\\\farm\\custom",
    }


def test_build_studio_environment_section_populates_root_fields():
    config = StudioConfig(
        studio_environment=StudioEnvironmentSettings(
            texture_root="\\\\farm\\textures",
            asset_root="\\\\farm\\assets",
            cache_root="\\\\farm\\cache",
            render_root="\\\\farm\\render",
            variable_aliases={"STUDIO_TEXTURE_ROOT": "\\\\farm\\textures"},
        )
    )
    section = build_studio_environment_section(FakeQtWidgets, config)
    texture = _find(section, SETTINGS_TEXTURE_ROOT_INPUT_OBJECT_NAME)
    aliases = _find(section, SETTINGS_VARIABLE_ALIASES_INPUT_OBJECT_NAME)

    assert texture.value == "\\\\farm\\textures"
    assert aliases.value == "STUDIO_TEXTURE_ROOT=\\\\farm\\textures"


def test_read_studio_environment_from_view_reads_roots_and_aliases():
    config = StudioConfig()
    section = build_studio_environment_section(FakeQtWidgets, config)
    _find(section, SETTINGS_TEXTURE_ROOT_INPUT_OBJECT_NAME).setText("\\\\farm\\textures")
    _find(section, SETTINGS_ASSET_ROOT_INPUT_OBJECT_NAME).setText("\\\\farm\\assets")
    _find(section, SETTINGS_CACHE_ROOT_INPUT_OBJECT_NAME).setText("\\\\farm\\cache")
    _find(section, SETTINGS_RENDER_ROOT_INPUT_OBJECT_NAME).setText("\\\\farm\\render")
    _find(section, SETTINGS_VARIABLE_ALIASES_INPUT_OBJECT_NAME).setPlainText(
        "STUDIO_TEXTURE_ROOT=\\\\farm\\textures"
    )

    environment = read_studio_environment_from_view(section, FakeQtWidgets)

    assert environment.texture_root == "\\\\farm\\textures"
    assert environment.asset_root == "\\\\farm\\assets"
    assert environment.cache_root == "\\\\farm\\cache"
    assert environment.render_root == "\\\\farm\\render"
    assert environment.variable_aliases["STUDIO_TEXTURE_ROOT"] == "\\\\farm\\textures"


def test_update_studio_environment_view_refreshes_controls():
    config = StudioConfig()
    section = build_studio_environment_section(FakeQtWidgets, config)
    updated = StudioEnvironmentSettings(
        texture_root="\\\\farm\\textures",
        asset_root="\\\\farm\\assets",
        cache_root="\\\\farm\\cache",
        render_root="\\\\farm\\render",
        variable_aliases={"CUSTOM_ROOT": "\\\\farm\\custom"},
    )

    update_studio_environment_view(section, FakeQtWidgets, updated)

    assert _find(section, SETTINGS_TEXTURE_ROOT_INPUT_OBJECT_NAME).value == "\\\\farm\\textures"
    assert _find(section, SETTINGS_VARIABLE_ALIASES_INPUT_OBJECT_NAME).value == (
        "CUSTOM_ROOT=\\\\farm\\custom"
    )
