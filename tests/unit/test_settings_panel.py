from __future__ import annotations

from pathlib import Path
from typing import Any

from shader_health.studio_config import (
    ConnectorSettings,
    DeadlineConnectorSettings,
    PipelineSettings,
    StudioConfig,
)
from shader_health.ui import deadline_connector_section, settings_panel
from shader_health.ui.settings_tabs import SETTINGS_TAB_SPECS

_DEADLINE_ENABLED = deadline_connector_section.SETTINGS_DEADLINE_ENABLED_TOGGLE_OBJECT_NAME
_DEADLINE_DETAILS = deadline_connector_section.SETTINGS_DEADLINE_DETAILS_OBJECT_NAME
_DEADLINE_HOST = deadline_connector_section.SETTINGS_DEADLINE_HOST_INPUT_OBJECT_NAME
_DEADLINE_PORT = deadline_connector_section.SETTINGS_DEADLINE_PORT_INPUT_OBJECT_NAME
_DEADLINE_LEFT = deadline_connector_section.SETTINGS_DEADLINE_LEFT_COLUMN_OBJECT_NAME
_DEADLINE_RIGHT = deadline_connector_section.SETTINGS_DEADLINE_RIGHT_COLUMN_OBJECT_NAME
_DEADLINE_MAYAPY = deadline_connector_section.SETTINGS_DEADLINE_MAYAPY_INPUT_OBJECT_NAME


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
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.value = text
        self.placeholder = ""
        self.fixed_width: int | None = None
        self.maximum_width: int | None = None
        self.size_policy: tuple[Any, Any] | None = None

    def setText(self, text: str) -> None:
        self.value = text

    def text(self) -> str:
        return self.value

    def setPlaceholderText(self, text: str) -> None:
        self.placeholder = text

    def setFixedWidth(self, width: int) -> None:
        self.fixed_width = width

    def setMaximumWidth(self, width: int) -> None:
        self.maximum_width = width

    def setSizePolicy(self, horizontal: Any, vertical: Any) -> None:
        self.size_policy = (horizontal, vertical)

    @property
    def editingFinished(self) -> FakeSignal:
        return FakeSignal()


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
    QPushButton = FakePushButton
    QVBoxLayout = FakeVBoxLayout
    QHBoxLayout = FakeHBoxLayout
    QFormLayout = FakeFormLayout
    QGridLayout = FakeGridLayout
    QSizePolicy = FakeSizePolicy
    Qt = FakeQt
    QTabWidget = FakeTabWidget


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


def test_studio_environment_and_bug_report_tabs_show_placeholders():
    view = settings_panel.build_settings_view(FakeQtWidgets)
    tabs = _find(view, settings_panel.SETTINGS_TAB_WIDGET_OBJECT_NAME)
    studio_env_tab = tabs.tabs[4][1]
    bug_report_tab = tabs.tabs[5][1]

    studio_env_label = studio_env_tab.layout.widgets[0]
    bug_report_label = bug_report_tab.layout.widgets[0]

    assert "texture_root" in studio_env_label.text
    assert "relay URL" in bug_report_label.text


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


def test_studio_tab_clarifies_pipeline_policy_scope():
    view = settings_panel.build_settings_view(FakeQtWidgets)
    tabs = _find(view, settings_panel.SETTINGS_TAB_WIDGET_OBJECT_NAME)
    studio_tab = tabs.tabs[3][1]
    intro = studio_tab.layout.widgets[0]

    assert "pipeline policy" in intro.text.lower()
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


def test_require_tx_toggle_styles_off_state():
    toggle = settings_panel.build_require_tx_toggle(
        FakeQtWidgets,
        enabled=False,
    )

    assert toggle.text == "OFF"
    assert "#4a4a4a" in toggle.style_sheet


def _find(widget: Any, object_name: str) -> Any:
    stack = [widget]
    while stack:
        current = stack.pop()
        if getattr(current, "object_name", None) == object_name:
            return current
        stack.extend(getattr(current, "children", []))
    raise AssertionError(f"Could not find object named {object_name!r}")
