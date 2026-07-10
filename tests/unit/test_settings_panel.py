from __future__ import annotations

from pathlib import Path
from typing import Any

from shader_health.studio_config import (
    ConnectorSettings,
    DeadlineConnectorSettings,
    PipelineSettings,
    StudioConfig,
    StudioEnvironmentSettings,
    TelegramConnectorSettings,
    WaiverDefaultsSettings,
)
from shader_health.ui import (
    deadline_connector_section,
    main_window,
    settings_panel,
    telegram_connector_section,
)
from shader_health.ui.advanced_settings_section import (
    SETTINGS_DEBUG_LOGGING_TOGGLE_OBJECT_NAME,
    SETTINGS_EXTRA_RULE_PATHS_INPUT_OBJECT_NAME,
    SETTINGS_MAX_ISSUES_INPUT_OBJECT_NAME,
    SETTINGS_MAYAPY_PATH_INPUT_OBJECT_NAME,
)
from shader_health.ui.basic_settings_section import (
    SETTINGS_DEFAULT_ASSET_CLASS_COMBO_OBJECT_NAME,
    SETTINGS_DEFAULT_PROFILE_COMBO_OBJECT_NAME,
    SETTINGS_DEFAULT_SCAN_SCOPE_COMBO_OBJECT_NAME,
    SETTINGS_DOCS_URL_INPUT_OBJECT_NAME,
    SETTINGS_THEME_COMBO_OBJECT_NAME,
    SETTINGS_UI_DENSITY_COMBO_OBJECT_NAME,
)
from shader_health.ui.settings_dirty_state import (
    SETTINGS_DIRTY_BANNER_OBJECT_NAME,
    SettingsDirtyState,
    studio_config_from_settings_view,
)
from shader_health.ui.settings_tabs import SETTINGS_TAB_SPECS
from shader_health.ui.studio_environment_section import (
    SETTINGS_ASSET_ROOT_INPUT_OBJECT_NAME,
    SETTINGS_CACHE_ROOT_INPUT_OBJECT_NAME,
    SETTINGS_RENDER_ROOT_INPUT_OBJECT_NAME,
    SETTINGS_STUDIO_ENVIRONMENT_LEFT_COLUMN_OBJECT_NAME,
    SETTINGS_STUDIO_ENVIRONMENT_RIGHT_COLUMN_OBJECT_NAME,
    SETTINGS_TEXTURE_ROOT_INPUT_OBJECT_NAME,
    SETTINGS_VARIABLE_ALIASES_INPUT_OBJECT_NAME,
)
from shader_health.ui.studio_policy_section import (
    SETTINGS_PINNED_WORKFLOW_PROFILES_INPUT_OBJECT_NAME,
    SETTINGS_STUDIO_NAME_INPUT_OBJECT_NAME,
    SETTINGS_WAIVER_APPROVED_BY_INPUT_OBJECT_NAME,
)
from shader_health.user_config import UserPreferences

_DEADLINE_ENABLED = deadline_connector_section.SETTINGS_DEADLINE_ENABLED_TOGGLE_OBJECT_NAME
_DEADLINE_DETAILS = deadline_connector_section.SETTINGS_DEADLINE_DETAILS_OBJECT_NAME
_DEADLINE_HOST = deadline_connector_section.SETTINGS_DEADLINE_HOST_INPUT_OBJECT_NAME
_DEADLINE_PORT = deadline_connector_section.SETTINGS_DEADLINE_PORT_INPUT_OBJECT_NAME
_DEADLINE_LEFT = deadline_connector_section.SETTINGS_DEADLINE_LEFT_COLUMN_OBJECT_NAME
_DEADLINE_RIGHT = deadline_connector_section.SETTINGS_DEADLINE_RIGHT_COLUMN_OBJECT_NAME
_DEADLINE_MAYAPY = deadline_connector_section.SETTINGS_DEADLINE_MAYAPY_INPUT_OBJECT_NAME
_TELEGRAM_ENABLED = telegram_connector_section.SETTINGS_TELEGRAM_ENABLED_TOGGLE_OBJECT_NAME
_TELEGRAM_DETAILS = telegram_connector_section.SETTINGS_TELEGRAM_DETAILS_OBJECT_NAME
_TELEGRAM_BOT_TOKEN = telegram_connector_section.SETTINGS_TELEGRAM_BOT_TOKEN_INPUT_OBJECT_NAME
_TELEGRAM_CHAT_ID = telegram_connector_section.SETTINGS_TELEGRAM_CHAT_ID_INPUT_OBJECT_NAME
_TELEGRAM_NOTIFY_PUBLISH = (
    telegram_connector_section.SETTINGS_TELEGRAM_NOTIFY_BLOCK_PUBLISH_CHECKBOX_OBJECT_NAME
)


class FakeWidget:
    def __init__(self) -> None:
        self.object_name: str | None = None
        self.children: list[Any] = []
        self.layout: Any = None
        self.visible = True
        self.maximum_width: int | None = None

    def setObjectName(self, object_name: str) -> None:
        self.object_name = object_name

    def setVisible(self, visible: bool) -> None:
        self.visible = visible

    def setMaximumWidth(self, width: int) -> None:
        self.maximum_width = width

    def setLayout(self, layout: Any) -> None:
        self.layout = layout
        for widget in getattr(layout, "widgets", []):
            if widget not in self.children:
                self.children.append(widget)


class FakeLabel(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.text = text
        self.word_wrap = False
        self.size_policy: tuple[Any, Any] | None = None
        self.fixed_width: int | None = None

    def setWordWrap(self, enabled: bool) -> None:
        self.word_wrap = enabled

    def setText(self, text: str) -> None:
        self.text = text

    def setStyleSheet(self, _style: str) -> None:
        return

    def setFixedWidth(self, width: int) -> None:
        self.fixed_width = width

    def setSizePolicy(self, horizontal: Any, vertical: Any) -> None:
        self.size_policy = (horizontal, vertical)


class FakeLineEdit(FakeWidget):
    Password = "password"

    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.value = text
        self.placeholder = ""
        self.fixed_width: int | None = None
        self.maximum_width: int | None = None
        self.size_policy: tuple[Any, Any] | None = None
        self.tooltip = ""
        self.echo_mode: Any | None = None

    def setText(self, text: str) -> None:
        self.value = text

    def text(self) -> str:
        return self.value

    def setPlaceholderText(self, text: str) -> None:
        self.placeholder = text

    def setToolTip(self, text: str) -> None:
        self.tooltip = text

    def setFixedWidth(self, width: int) -> None:
        self.fixed_width = width

    def setMaximumWidth(self, width: int) -> None:
        self.maximum_width = width

    def setSizePolicy(self, horizontal: Any, vertical: Any) -> None:
        self.size_policy = (horizontal, vertical)

    def setEchoMode(self, mode: Any) -> None:
        self.echo_mode = mode

    @property
    def editingFinished(self) -> FakeSignal:
        return FakeSignal()


class FakePlainTextEdit(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.value = text
        self.placeholder = ""
        self.tooltip = ""
        self.plainTextChanged = FakeSignal()

    def setPlainText(self, text: str) -> None:
        self.value = text

    def toPlainText(self) -> str:
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


class FakeCheckBox(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.text = text
        self.checked = False
        self.stateChanged = FakeSignal()

    def setText(self, text: str) -> None:
        self.text = text

    def setChecked(self, checked: bool) -> None:
        self.checked = checked

    def isChecked(self) -> bool:
        return self.checked


class FakeSignal:
    def __init__(self) -> None:
        self.handlers: list[Any] = []

    def connect(self, handler: Any) -> None:
        self.handlers.append(handler)


class FakePushButton(FakeLabel):
    def __init__(self, text: str = "") -> None:
        super().__init__(text)
        self.checkable = False
        self.checked = False
        self.style_sheet = ""
        self.tooltip = ""

    def setCheckable(self, enabled: bool) -> None:
        self.checkable = enabled

    def setChecked(self, checked: bool) -> None:
        self.checked = checked

    def isChecked(self) -> bool:
        return self.checked

    def setStyleSheet(self, style: str) -> None:
        self.style_sheet = style

    def setToolTip(self, text: str) -> None:
        self.tooltip = text

    def setFixedWidth(self, width: int) -> None:
        _ = width


class FakeVBoxLayout:
    def __init__(self, parent: Any | None = None) -> None:
        self.parent = parent
        self.widgets: list[Any] = []
        self.layouts: list[Any] = []
        self.stretches: list[int] = []
        if parent is not None:
            parent.layout = self

    def setContentsMargins(self, *_args: Any) -> None:
        return

    def setSpacing(self, _spacing: int) -> None:
        return

    def addWidget(self, widget: Any, *_args: Any) -> None:
        self.widgets.append(widget)
        self._attach_widget(widget)

    def addLayout(self, layout: Any) -> None:
        self.layouts.append(layout)
        parent_widget = self.parent
        for _label, field in getattr(layout, "rows", []):
            if parent_widget is not None and field not in parent_widget.children:
                parent_widget.children.append(field)
        for widget in getattr(layout, "widgets", []):
            self._attach_widget(widget)
        for nested in getattr(layout, "layouts", []):
            for widget in getattr(nested, "widgets", []):
                self._attach_widget(widget)

    def addStretch(self, stretch: int = 0) -> None:
        self.stretches.append(stretch)

    def _attach_widget(self, widget: Any) -> None:
        if self.parent is not None and widget not in self.parent.children:
            self.parent.children.append(widget)


class FakeHBoxLayout(FakeVBoxLayout):
    pass


class FakeFormLayout:
    def __init__(self, parent: Any | None = None) -> None:
        self.parent = parent
        self.rows: list[tuple[str, Any]] = []
        if parent is not None:
            parent.layout = self

    def setContentsMargins(self, *_args: Any) -> None:
        return

    def addRow(self, label: str, field: Any) -> None:
        self.rows.append((label, field))
        if self.parent is not None and field not in self.parent.children:
            self.parent.children.append(field)


class FakeGridLayout(FakeVBoxLayout):
    def __init__(self, parent: Any | None = None) -> None:
        super().__init__(parent)
        self.column_stretches: dict[int, int] = {}
        self.column_minimum_widths: dict[int, int] = {}

    def addWidget(self, widget: Any, row: int = 0, column: int = 0, *_args: Any) -> None:
        self._attach_widget(widget)
        _ = (row, column)

    def setHorizontalSpacing(self, _spacing: int) -> None:
        return

    def setVerticalSpacing(self, _spacing: int) -> None:
        return

    def setColumnStretch(self, column: int, stretch: int) -> None:
        self.column_stretches[column] = stretch

    def setColumnMinimumWidth(self, column: int, width: int) -> None:
        self.column_minimum_widths[column] = width


class FakeSizePolicy:
    Fixed = "fixed"
    Preferred = "preferred"


class FakeQt:
    AlignLeft = 1
    AlignRight = 2
    AlignVCenter = 4


class FakeTabWidget(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.tabs: list[tuple[str, Any]] = []

    def addTab(self, widget: Any, title: str) -> None:
        self.tabs.append((title, widget))
        self.children.append(widget)


class FakeQtWidgets:
    QWidget = FakeWidget
    QLabel = FakeLabel
    QLineEdit = FakeLineEdit
    QPlainTextEdit = FakePlainTextEdit
    QPushButton = FakePushButton
    QCheckBox = FakeCheckBox
    QComboBox = FakeComboBox
    QVBoxLayout = FakeVBoxLayout
    QHBoxLayout = FakeHBoxLayout
    QFormLayout = FakeFormLayout
    QGridLayout = FakeGridLayout
    QSizePolicy = FakeSizePolicy
    Qt = FakeQt
    QTabWidget = FakeTabWidget


def test_basic_tab_exposes_user_preference_controls():
    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        user_config=UserPreferences(
            default_profile_id="publish_strict",
            default_scan_scope="selection",
            ui_density="compact",
            theme="dark",
        ),
    )
    tabs = _find(view, settings_panel.SETTINGS_TAB_WIDGET_OBJECT_NAME)
    basic_tab = tabs.tabs[0][1]

    assert _find(basic_tab, SETTINGS_DEFAULT_PROFILE_COMBO_OBJECT_NAME).currentData() == (
        "publish_strict"
    )
    assert _find(basic_tab, SETTINGS_DEFAULT_SCAN_SCOPE_COMBO_OBJECT_NAME).currentData() == (
        "selection"
    )
    assert _find(basic_tab, SETTINGS_UI_DENSITY_COMBO_OBJECT_NAME).currentData() == "compact"
    assert _find(basic_tab, SETTINGS_THEME_COMBO_OBJECT_NAME).currentData() == "dark"


def test_advanced_tab_exposes_user_preference_controls():
    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        user_config=UserPreferences(
            extra_rule_paths=("/show/rules",),
            debug_logging=True,
            max_issues_displayed=75,
            mayapy_path="C:/mayapy.exe",
        ),
    )
    tabs = _find(view, settings_panel.SETTINGS_TAB_WIDGET_OBJECT_NAME)
    advanced_tab = tabs.tabs[1][1]

    assert _find(advanced_tab, SETTINGS_EXTRA_RULE_PATHS_INPUT_OBJECT_NAME).toPlainText() == (
        "/show/rules"
    )
    assert _find(advanced_tab, SETTINGS_DEBUG_LOGGING_TOGGLE_OBJECT_NAME).checked is True
    assert _find(advanced_tab, SETTINGS_MAX_ISSUES_INPUT_OBJECT_NAME).text() == "75"
    assert _find(advanced_tab, SETTINGS_MAYAPY_PATH_INPUT_OBJECT_NAME).text() == "C:/mayapy.exe"


def test_read_user_preferences_from_settings_view_reads_basic_tab():
    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        user_config=UserPreferences(default_profile_id="artist_relaxed"),
    )
    profile_combo = _find(view, SETTINGS_DEFAULT_PROFILE_COMBO_OBJECT_NAME)
    profile_combo.setCurrentIndex(profile_combo.findData("supervisor_full"))

    loaded = settings_panel.read_user_preferences_from_settings_view(
        view,
        FakeQtWidgets,
        base=UserPreferences(mayapy_path="C:/mayapy.exe"),
    )

    assert loaded.default_profile_id == "supervisor_full"
    assert loaded.mayapy_path == ""


def test_read_user_preferences_from_settings_view_merges_advanced_tab():
    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        user_config=UserPreferences(default_profile_id="artist_relaxed"),
    )
    _find(view, SETTINGS_EXTRA_RULE_PATHS_INPUT_OBJECT_NAME).setPlainText("/custom/rules")
    _find(view, SETTINGS_DEBUG_LOGGING_TOGGLE_OBJECT_NAME).setChecked(True)
    _find(view, SETTINGS_MAX_ISSUES_INPUT_OBJECT_NAME).setText("99")
    _find(view, SETTINGS_MAYAPY_PATH_INPUT_OBJECT_NAME).setText("D:/mayapy.exe")

    loaded = settings_panel.read_user_preferences_from_settings_view(view, FakeQtWidgets)

    assert loaded.default_profile_id == "artist_relaxed"
    assert loaded.extra_rule_paths == ("/custom/rules",)
    assert loaded.debug_logging is True
    assert loaded.max_issues_displayed == 99
    assert loaded.mayapy_path == "D:/mayapy.exe"


def test_update_settings_view_refreshes_basic_tab_controls():
    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        user_config=UserPreferences(default_profile_id="artist_relaxed"),
    )

    settings_panel.update_settings_view(
        view,
        FakeQtWidgets,
        config=StudioConfig(),
        user_config=UserPreferences(
            default_profile_id="deadline_critical",
            default_scan_scope="selection",
            ui_density="compact",
            theme="dark",
        ),
    )

    assert _find(view, SETTINGS_DEFAULT_PROFILE_COMBO_OBJECT_NAME).currentData() == (
        "deadline_critical"
    )
    assert _find(view, SETTINGS_DEFAULT_SCAN_SCOPE_COMBO_OBJECT_NAME).currentData() == (
        "selection"
    )
    assert _find(view, SETTINGS_THEME_COMBO_OBJECT_NAME).currentData() == "dark"


def test_update_settings_view_refreshes_advanced_tab_controls():
    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        user_config=UserPreferences(debug_logging=False),
    )

    settings_panel.update_settings_view(
        view,
        FakeQtWidgets,
        config=StudioConfig(),
        user_config=UserPreferences(
            extra_rule_paths=("//farm/rules",),
            debug_logging=True,
            max_issues_displayed=200,
            mayapy_path="C:/Maya/bin/mayapy.exe",
        ),
    )

    assert _find(view, SETTINGS_EXTRA_RULE_PATHS_INPUT_OBJECT_NAME).toPlainText() == "//farm/rules"
    assert _find(view, SETTINGS_DEBUG_LOGGING_TOGGLE_OBJECT_NAME).checked is True
    assert _find(view, SETTINGS_MAX_ISSUES_INPUT_OBJECT_NAME).text() == "200"
    assert _find(view, SETTINGS_MAYAPY_PATH_INPUT_OBJECT_NAME).text() == "C:/Maya/bin/mayapy.exe"


def test_read_user_preferences_from_settings_view_round_trips_all_basic_fields():
    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        user_config=UserPreferences(default_profile_id="artist_relaxed"),
    )
    expected = UserPreferences(
        default_profile_id="supervisor_full",
        default_asset_class_id="asset_class_background",
        default_scan_scope="selection",
        ui_density="compact",
        theme="dark",
        docs_url="https://example.test/docs",
    )
    _set_basic_tab_values(view, expected)

    loaded = settings_panel.read_user_preferences_from_settings_view(
        view,
        FakeQtWidgets,
        base=UserPreferences(docs_url=expected.docs_url),
    )

    assert loaded.default_profile_id == expected.default_profile_id
    assert loaded.default_asset_class_id == expected.default_asset_class_id
    assert loaded.default_scan_scope == expected.default_scan_scope
    assert loaded.ui_density == expected.ui_density
    assert loaded.theme == expected.theme
    assert loaded.docs_url == expected.docs_url


def test_read_user_preferences_from_settings_view_round_trips_all_advanced_fields():
    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        user_config=UserPreferences(default_profile_id="artist_relaxed", debug_logging=False),
    )
    expected = UserPreferences(
        extra_rule_paths=("/studio/rules", "//farm/share/td"),
        debug_logging=True,
        max_issues_displayed=180,
        mayapy_path="C:/Program Files/Autodesk/Maya2025/bin/mayapy.exe",
    )
    _set_advanced_tab_values(view, expected)

    loaded = settings_panel.read_user_preferences_from_settings_view(
        view,
        FakeQtWidgets,
        base=UserPreferences(default_profile_id="artist_relaxed"),
    )

    assert loaded.default_profile_id == "artist_relaxed"
    assert loaded.extra_rule_paths == expected.extra_rule_paths
    assert loaded.debug_logging is expected.debug_logging
    assert loaded.max_issues_displayed == expected.max_issues_displayed
    assert loaded.mayapy_path == expected.mayapy_path


def test_settings_panel_round_trips_basic_and_advanced_through_read_and_update():
    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        user_config=UserPreferences(
            default_profile_id="artist_relaxed",
            debug_logging=False,
            max_issues_displayed=500,
        ),
    )
    expected = UserPreferences(
        default_profile_id="deadline_critical",
        default_asset_class_id="asset_class_prop",
        default_scan_scope="selection",
        ui_density="compact",
        theme="dark",
        extra_rule_paths=("D:/show/rules",),
        debug_logging=True,
        max_issues_displayed=64,
        mayapy_path="D:/tools/mayapy.exe",
        docs_url="https://example.test/docs",
    )
    _set_basic_tab_values(view, expected)
    _set_advanced_tab_values(view, expected)

    loaded = settings_panel.read_user_preferences_from_settings_view(
        view,
        FakeQtWidgets,
        base=UserPreferences(docs_url=expected.docs_url),
    )

    assert loaded.default_profile_id == expected.default_profile_id
    assert loaded.default_asset_class_id == expected.default_asset_class_id
    assert loaded.default_scan_scope == expected.default_scan_scope
    assert loaded.ui_density == expected.ui_density
    assert loaded.theme == expected.theme
    assert loaded.extra_rule_paths == expected.extra_rule_paths
    assert loaded.debug_logging is expected.debug_logging
    assert loaded.max_issues_displayed == expected.max_issues_displayed
    assert loaded.mayapy_path == expected.mayapy_path
    assert loaded.docs_url == expected.docs_url

    settings_panel.update_settings_view(
        view,
        FakeQtWidgets,
        config=StudioConfig(),
        user_config=loaded,
    )

    _assert_basic_tab_values(view, expected)
    _assert_advanced_tab_values(view, expected)


def test_settings_view_includes_category_tabs_and_studio_pipeline_toggle():
    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        config=StudioConfig(pipeline=PipelineSettings(require_tx_derivatives=True)),
    )
    tabs = _find(view, settings_panel.SETTINGS_TAB_WIDGET_OBJECT_NAME)

    assert [title for title, _tab in tabs.tabs] == [
        "Basic",
        "Advanced",
        "Connectors",
        "Studio",
        "Studio Environment",
        "Bug Report",
    ]
    toggle = _find(view, settings_panel.SETTINGS_REQUIRE_TX_TOGGLE_OBJECT_NAME)
    assert toggle.checked is True
    assert toggle.text == "ON"
    assert "#2ecc71" in toggle.style_sheet


def test_settings_tabs_use_stable_object_names():
    view = settings_panel.build_settings_view(FakeQtWidgets)
    tabs = _find(view, settings_panel.SETTINGS_TAB_WIDGET_OBJECT_NAME)

    assert [tab.object_name for _title, tab in tabs.tabs] == [
        spec.object_name for spec in SETTINGS_TAB_SPECS
    ]


def test_bug_report_tab_shows_placeholder():
    view = settings_panel.build_settings_view(FakeQtWidgets)
    tabs = _find(view, settings_panel.SETTINGS_TAB_WIDGET_OBJECT_NAME)
    bug_report_tab = tabs.tabs[5][1]
    bug_report_label = bug_report_tab.layout.widgets[0]

    assert "relay URL" in bug_report_label.text


def test_studio_environment_tab_exposes_network_path_controls():
    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        config=StudioConfig(
            studio_environment=StudioEnvironmentSettings(
                texture_root="\\\\farm\\textures",
                asset_root="\\\\farm\\assets",
                cache_root="\\\\farm\\cache",
                render_root="\\\\farm\\render",
                variable_aliases={"STUDIO_TEXTURE_ROOT": "\\\\farm\\textures"},
            )
        ),
    )
    texture = _find(view, SETTINGS_TEXTURE_ROOT_INPUT_OBJECT_NAME)
    aliases = _find(view, SETTINGS_VARIABLE_ALIASES_INPUT_OBJECT_NAME)

    assert texture.text() == "\\\\farm\\textures"
    assert aliases.toPlainText() == "STUDIO_TEXTURE_ROOT=\\\\farm\\textures"


def test_studio_environment_tab_uses_parallel_root_columns():
    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        config=StudioConfig(
            studio_environment=StudioEnvironmentSettings(
                texture_root="\\\\farm\\textures",
            )
        ),
    )
    left_column = _find(view, SETTINGS_STUDIO_ENVIRONMENT_LEFT_COLUMN_OBJECT_NAME)
    right_column = _find(view, SETTINGS_STUDIO_ENVIRONMENT_RIGHT_COLUMN_OBJECT_NAME)
    texture = _find(view, SETTINGS_TEXTURE_ROOT_INPUT_OBJECT_NAME)
    asset = _find(view, SETTINGS_ASSET_ROOT_INPUT_OBJECT_NAME)
    cache = _find(view, SETTINGS_CACHE_ROOT_INPUT_OBJECT_NAME)
    render = _find(view, SETTINGS_RENDER_ROOT_INPUT_OBJECT_NAME)

    assert texture in left_column.children
    assert cache in left_column.children
    assert asset in right_column.children
    assert render in right_column.children


def test_studio_config_from_settings_view_reads_studio_environment_fields():
    view = settings_panel.build_settings_view(FakeQtWidgets)
    _find(view, SETTINGS_TEXTURE_ROOT_INPUT_OBJECT_NAME).setText("\\\\farm\\textures")
    _find(view, SETTINGS_ASSET_ROOT_INPUT_OBJECT_NAME).setText("\\\\farm\\assets")
    _find(view, SETTINGS_CACHE_ROOT_INPUT_OBJECT_NAME).setText("\\\\farm\\cache")
    _find(view, SETTINGS_RENDER_ROOT_INPUT_OBJECT_NAME).setText("\\\\farm\\render")
    _find(view, SETTINGS_VARIABLE_ALIASES_INPUT_OBJECT_NAME).setPlainText(
        "STUDIO_TEXTURE_ROOT=\\\\farm\\textures"
    )

    studio = studio_config_from_settings_view(
        view,
        FakeQtWidgets,
        base=StudioConfig(),
    )

    assert studio.studio_environment.texture_root == "\\\\farm\\textures"
    assert studio.studio_environment.asset_root == "\\\\farm\\assets"
    assert studio.studio_environment.cache_root == "\\\\farm\\cache"
    assert studio.studio_environment.render_root == "\\\\farm\\render"
    assert studio.studio_environment.variable_aliases["STUDIO_TEXTURE_ROOT"] == (
        "\\\\farm\\textures"
    )


def test_update_settings_view_refreshes_studio_environment_fields():
    view = settings_panel.build_settings_view(FakeQtWidgets)
    settings_panel.update_settings_view(
        view,
        FakeQtWidgets,
        config=StudioConfig(
            studio_environment=StudioEnvironmentSettings(
                texture_root="\\\\farm\\textures",
                variable_aliases={"CUSTOM_ROOT": "\\\\farm\\custom"},
            )
        ),
    )

    assert _find(view, SETTINGS_TEXTURE_ROOT_INPUT_OBJECT_NAME).text() == "\\\\farm\\textures"
    assert _find(view, SETTINGS_VARIABLE_ALIASES_INPUT_OBJECT_NAME).toPlainText() == (
        "CUSTOM_ROOT=\\\\farm\\custom"
    )


def test_settings_view_exposes_split_save_and_load_actions():
    view = settings_panel.build_settings_view(FakeQtWidgets)

    assert _find(view, settings_panel.SETTINGS_SAVE_STUDIO_BUTTON_OBJECT_NAME).text == (
        "Save Studio Config"
    )
    assert _find(view, settings_panel.SETTINGS_LOAD_STUDIO_BUTTON_OBJECT_NAME).text == (
        "Load Studio Config"
    )
    assert _find(view, settings_panel.SETTINGS_SAVE_USER_BUTTON_OBJECT_NAME).text == (
        "Save User Preferences"
    )
    assert _find(view, settings_panel.SETTINGS_LOAD_USER_BUTTON_OBJECT_NAME).text == (
        "Load User Preferences"
    )


def test_settings_view_shows_studio_and_user_config_paths():
    from shader_health.user_config import UserPreferences

    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        config=StudioConfig(config_path=Path("C:/studio/shader_health_studio.json")),
        user_config=UserPreferences(config_path=Path("C:/Users/me/.shader_health/user.json")),
    )

    studio_label = _find(view, settings_panel.SETTINGS_STUDIO_CONFIG_PATH_LABEL_OBJECT_NAME)
    user_label = _find(view, settings_panel.SETTINGS_USER_CONFIG_PATH_LABEL_OBJECT_NAME)

    assert "shader_health_studio.json" in studio_label.text
    assert "user.json" in user_label.text


def test_studio_tab_exposes_policy_fields():
    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        config=StudioConfig(
            studio_name="Demo Studio",
            pipeline=PipelineSettings(
                waiver_defaults=WaiverDefaultsSettings(default_approved_by="pipeline_td"),
                pinned_workflow_profile_ids=("artist_relaxed",),
            ),
        ),
    )
    assert _find(view, SETTINGS_STUDIO_NAME_INPUT_OBJECT_NAME).text() == "Demo Studio"
    assert _find(view, SETTINGS_WAIVER_APPROVED_BY_INPUT_OBJECT_NAME).text() == "pipeline_td"
    assert _find(view, SETTINGS_PINNED_WORKFLOW_PROFILES_INPUT_OBJECT_NAME).toPlainText() == (
        "artist_relaxed"
    )


def test_studio_config_from_settings_view_reads_studio_policy_fields():
    view = settings_panel.build_settings_view(FakeQtWidgets)
    _find(view, SETTINGS_STUDIO_NAME_INPUT_OBJECT_NAME).setText("Network Studio")
    _find(view, SETTINGS_WAIVER_APPROVED_BY_INPUT_OBJECT_NAME).setText("lead_td")
    _find(view, SETTINGS_PINNED_WORKFLOW_PROFILES_INPUT_OBJECT_NAME).setPlainText(
        "publish_strict"
    )

    studio = studio_config_from_settings_view(
        view,
        FakeQtWidgets,
        base=StudioConfig(),
    )

    assert studio.studio_name == "Network Studio"
    assert studio.pipeline.waiver_defaults.default_approved_by == "lead_td"
    assert studio.pipeline.pinned_workflow_profile_ids == ("publish_strict",)


def test_studio_tab_clarifies_pipeline_policy_scope():
    view = settings_panel.build_settings_view(FakeQtWidgets)
    tabs = _find(view, settings_panel.SETTINGS_TAB_WIDGET_OBJECT_NAME)
    studio_tab = tabs.tabs[3][1]
    policy_section = studio_tab.layout.widgets[0]
    intro = policy_section.layout.widgets[0]

    assert "shader_health_studio.json" in intro.text
    assert "Studio Environment" in intro.text


def test_connectors_tab_includes_deadline_remote_farm_toggle_and_collapsed_details():
    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        config=StudioConfig(
            connectors=ConnectorSettings(
                deadline=DeadlineConnectorSettings(enabled=False),
            )
        ),
    )
    connectors_tab = _find(view, settings_panel.SETTINGS_TAB_WIDGET_OBJECT_NAME).tabs[2][1]
    toggle = _find(connectors_tab, _DEADLINE_ENABLED)
    details = _find(connectors_tab, _DEADLINE_DETAILS)

    assert toggle.checked is False
    assert details.visible is False


def test_connectors_tab_shows_deadline_details_when_remote_farm_enabled():
    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        config=StudioConfig(
            connectors=ConnectorSettings(
                deadline=DeadlineConnectorSettings(
                    enabled=True,
                    web_service_host="10.0.0.5",
                    web_service_port=8081,
                    repo_root="\\\\farm\\repo",
                )
            )
        ),
    )
    connectors_tab = _find(view, settings_panel.SETTINGS_TAB_WIDGET_OBJECT_NAME).tabs[2][1]
    details = _find(connectors_tab, _DEADLINE_DETAILS)
    host = _find(connectors_tab, _DEADLINE_HOST)

    assert details.visible is True
    assert host.text() == "10.0.0.5"


def test_read_connectors_from_settings_view_reads_deadline_fields():
    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        config=StudioConfig(
            connectors=ConnectorSettings(
                deadline=DeadlineConnectorSettings(enabled=True),
            )
        ),
    )
    host = _find(view, _DEADLINE_HOST)
    host.setText("farm-host")
    port = _find(view, _DEADLINE_PORT)
    port.setText("9090")

    connectors = settings_panel.read_connectors_from_settings_view(view, FakeQtWidgets)

    assert connectors.deadline.enabled is True
    assert connectors.deadline.web_service_host == "farm-host"
    assert connectors.deadline.web_service_port == 9090


def test_connectors_tab_uses_parallel_deadline_columns():
    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        config=StudioConfig(
            connectors=ConnectorSettings(
                deadline=DeadlineConnectorSettings(enabled=True),
            )
        ),
    )
    details_row = _find(view, _DEADLINE_DETAILS)
    left_column = _find(view, _DEADLINE_LEFT)
    right_column = _find(view, _DEADLINE_RIGHT)
    host = _find(view, _DEADLINE_HOST)
    port = _find(view, _DEADLINE_PORT)
    mayapy = _find(view, _DEADLINE_MAYAPY)
    host_label = next(
        child
        for child in left_column.children
        if getattr(child, "text", None) == "Host"
    )

    assert details_row.visible is True
    assert host in left_column.children
    assert mayapy in right_column.children
    assert host.fixed_width == deadline_connector_section._DEADLINE_FIELD_HOST_WIDTH
    assert port.fixed_width == deadline_connector_section._DEADLINE_FIELD_PORT_WIDTH
    assert host_label.fixed_width == deadline_connector_section._DEADLINE_LABEL_WIDTH


def test_connectors_tab_includes_telegram_toggle_and_collapsed_details():
    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        config=StudioConfig(
            connectors=ConnectorSettings(
                telegram=TelegramConnectorSettings(enabled=False),
            )
        ),
    )
    connectors_tab = _find(view, settings_panel.SETTINGS_TAB_WIDGET_OBJECT_NAME).tabs[2][1]
    toggle = _find(connectors_tab, _TELEGRAM_ENABLED)
    details = _find(connectors_tab, _TELEGRAM_DETAILS)

    assert toggle.checked is False
    assert details.visible is False


def test_connectors_tab_shows_telegram_details_when_notifications_enabled():
    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        config=StudioConfig(
            connectors=ConnectorSettings(
                telegram=TelegramConnectorSettings(
                    enabled=True,
                    bot_token="secret-token",
                    chat_id="-10042",
                    notify_on=("block_publish",),
                )
            )
        ),
    )
    connectors_tab = _find(view, settings_panel.SETTINGS_TAB_WIDGET_OBJECT_NAME).tabs[2][1]
    details = _find(connectors_tab, _TELEGRAM_DETAILS)
    token = _find(connectors_tab, _TELEGRAM_BOT_TOKEN)
    publish = _find(connectors_tab, _TELEGRAM_NOTIFY_PUBLISH)

    assert details.visible is True
    assert token.value == "secret-token"
    assert token.echo_mode == FakeLineEdit.Password
    assert publish.checked is True


def test_read_connectors_from_settings_view_reads_telegram_fields():
    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        config=StudioConfig(
            connectors=ConnectorSettings(
                telegram=TelegramConnectorSettings(enabled=True),
            )
        ),
    )
    token = _find(view, _TELEGRAM_BOT_TOKEN)
    token.setText("123:abc")
    chat_id = _find(view, _TELEGRAM_CHAT_ID)
    chat_id.setText("-10099")
    publish = _find(view, _TELEGRAM_NOTIFY_PUBLISH)
    publish.setChecked(True)

    connectors = settings_panel.read_connectors_from_settings_view(view, FakeQtWidgets)

    assert connectors.telegram.enabled is True
    assert connectors.telegram.bot_token == "123:abc"
    assert connectors.telegram.chat_id == "-10099"
    assert connectors.telegram.notify_on == ("block_publish",)


def test_require_tx_toggle_styles_off_state():
    toggle = settings_panel.build_require_tx_toggle(
        FakeQtWidgets,
        enabled=False,
    )

    assert toggle.text == "OFF"
    assert "#4a4a4a" in toggle.style_sheet


def test_update_settings_view_shows_dirty_banner_for_unsaved_user_preferences():
    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        user_config=UserPreferences(default_profile_id="artist_relaxed"),
    )

    settings_panel.update_settings_view(
        view,
        FakeQtWidgets,
        config=StudioConfig(),
        user_config=UserPreferences(default_profile_id="artist_relaxed"),
        dirty_state=SettingsDirtyState(user_dirty=True),
    )

    dirty_banner = _find(view, SETTINGS_DIRTY_BANNER_OBJECT_NAME)
    status_label = _find(view, settings_panel.SETTINGS_STATUS_LABEL_OBJECT_NAME)

    assert dirty_banner.visible is True
    assert dirty_banner.text == "Unsaved changes: user preferences."
    assert "Save studio policy" in status_label.text


def test_update_settings_view_hides_dirty_banner_after_save_message():
    view = settings_panel.build_settings_view(FakeQtWidgets)

    settings_panel.update_settings_view(
        view,
        FakeQtWidgets,
        config=StudioConfig(),
        user_config=UserPreferences(),
        dirty_state=SettingsDirtyState(),
        status_message="User preferences saved to C:/Users/me/.shader_health/user.json.",
    )

    dirty_banner = _find(view, SETTINGS_DIRTY_BANNER_OBJECT_NAME)
    status_label = _find(view, settings_panel.SETTINGS_STATUS_LABEL_OBJECT_NAME)

    assert dirty_banner.visible is False
    assert "saved to" in status_label.text


def test_build_main_widget_applies_user_defaults_to_validate_tab():
    from tests.unit.test_maya_summary_header import FakeQtWidgets as MainWindowFakeQtWidgets

    widget = main_window.build_main_widget(
        MainWindowFakeQtWidgets,
        user_config=UserPreferences(
            default_profile_id="deadline_critical",
            default_asset_class_id="asset_class_hero",
            default_scan_scope="selection",
            theme="dark",
        ),
    )

    profile_dropdown = _find(widget, main_window.PROFILE_DROPDOWN_OBJECT_NAME)
    asset_class_dropdown = _find(widget, main_window.ASSET_CLASS_DROPDOWN_OBJECT_NAME)

    assert profile_dropdown.currentData() == "deadline_critical"
    assert asset_class_dropdown.currentData() == "asset_class_hero"
    assert widget._shader_health_scan_scope == "selection"
    assert widget._shader_health_theme == "dark"


def test_apply_user_preferences_to_panel_sets_validate_dropdowns_and_scan_scope():
    from tests.unit.test_maya_summary_header import FakeQtWidgets as MainWindowFakeQtWidgets

    from shader_health.ui import main_window
    from shader_health.ui.user_preferences_ui import apply_user_preferences_to_panel

    widget = main_window.build_main_widget(
        MainWindowFakeQtWidgets,
        user_config=UserPreferences(default_profile_id="artist_relaxed"),
    )

    apply_user_preferences_to_panel(
        widget,
        MainWindowFakeQtWidgets,
        UserPreferences(
            default_profile_id="deadline_critical",
            default_asset_class_id="asset_class_hero",
            default_scan_scope="selection",
            ui_density="compact",
        ),
    )

    profile_dropdown = _find(widget, main_window.PROFILE_DROPDOWN_OBJECT_NAME)
    asset_class_dropdown = _find(widget, main_window.ASSET_CLASS_DROPDOWN_OBJECT_NAME)

    assert profile_dropdown.currentData() == "deadline_critical"
    assert asset_class_dropdown.currentData() == "asset_class_hero"
    assert widget._shader_health_scan_scope == "selection"
    assert widget._shader_health_ui_density == "compact"


def _set_combo_data(view: Any, object_name: str, data: str) -> None:
    combo = _find(view, object_name)
    combo.setCurrentIndex(combo.findData(data))


def _set_basic_tab_values(view: Any, user_config: UserPreferences) -> None:
    _set_combo_data(
        view,
        SETTINGS_DEFAULT_PROFILE_COMBO_OBJECT_NAME,
        user_config.default_profile_id,
    )
    _set_combo_data(
        view,
        SETTINGS_DEFAULT_ASSET_CLASS_COMBO_OBJECT_NAME,
        user_config.default_asset_class_id,
    )
    _set_combo_data(
        view,
        SETTINGS_DEFAULT_SCAN_SCOPE_COMBO_OBJECT_NAME,
        user_config.default_scan_scope,
    )
    _set_combo_data(view, SETTINGS_UI_DENSITY_COMBO_OBJECT_NAME, user_config.ui_density)
    _set_combo_data(view, SETTINGS_THEME_COMBO_OBJECT_NAME, user_config.theme)
    _find(view, SETTINGS_DOCS_URL_INPUT_OBJECT_NAME).setText(user_config.docs_url)


def _assert_basic_tab_values(view: Any, user_config: UserPreferences) -> None:
    assert _find(view, SETTINGS_DEFAULT_PROFILE_COMBO_OBJECT_NAME).currentData() == (
        user_config.default_profile_id
    )
    assert _find(view, SETTINGS_DEFAULT_ASSET_CLASS_COMBO_OBJECT_NAME).currentData() == (
        user_config.default_asset_class_id
    )
    assert _find(view, SETTINGS_DEFAULT_SCAN_SCOPE_COMBO_OBJECT_NAME).currentData() == (
        user_config.default_scan_scope
    )
    assert (
        _find(view, SETTINGS_UI_DENSITY_COMBO_OBJECT_NAME).currentData()
        == user_config.ui_density
    )
    assert _find(view, SETTINGS_THEME_COMBO_OBJECT_NAME).currentData() == user_config.theme
    assert _find(view, SETTINGS_DOCS_URL_INPUT_OBJECT_NAME).text() == user_config.docs_url


def _set_advanced_tab_values(view: Any, user_config: UserPreferences) -> None:
    _find(view, SETTINGS_EXTRA_RULE_PATHS_INPUT_OBJECT_NAME).setPlainText(
        "\n".join(user_config.extra_rule_paths)
    )
    _find(view, SETTINGS_DEBUG_LOGGING_TOGGLE_OBJECT_NAME).setChecked(user_config.debug_logging)
    _find(view, SETTINGS_MAX_ISSUES_INPUT_OBJECT_NAME).setText(
        str(user_config.max_issues_displayed)
    )
    _find(view, SETTINGS_MAYAPY_PATH_INPUT_OBJECT_NAME).setText(user_config.mayapy_path)


def _assert_advanced_tab_values(view: Any, user_config: UserPreferences) -> None:
    assert _find(view, SETTINGS_EXTRA_RULE_PATHS_INPUT_OBJECT_NAME).toPlainText() == (
        "\n".join(user_config.extra_rule_paths)
    )
    assert (
        _find(view, SETTINGS_DEBUG_LOGGING_TOGGLE_OBJECT_NAME).checked
        is user_config.debug_logging
    )
    assert _find(view, SETTINGS_MAX_ISSUES_INPUT_OBJECT_NAME).text() == str(
        user_config.max_issues_displayed
    )
    assert _find(view, SETTINGS_MAYAPY_PATH_INPUT_OBJECT_NAME).text() == user_config.mayapy_path


def _find(widget: Any, object_name: str) -> Any:
    stack = [widget]
    while stack:
        current = stack.pop()
        if getattr(current, "object_name", None) == object_name:
            return current
        stack.extend(getattr(current, "children", []))
    raise AssertionError(f"Could not find object named {object_name!r}")
