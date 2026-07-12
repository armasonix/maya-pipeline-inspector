from __future__ import annotations

from pipeline_inspector.core.manifest_gate import ManifestGatePolicy  # noqa: F401
from pipeline_inspector.studio_config import (
    ConnectorSettings,
    StudioConfig,
    TelegramConnectorSettings,
)
from pipeline_inspector.ui.telegram_connector_section import (
    SETTINGS_TELEGRAM_BOT_TOKEN_INPUT_OBJECT_NAME,
    SETTINGS_TELEGRAM_CHAT_ID_INPUT_OBJECT_NAME,
    SETTINGS_TELEGRAM_DETAILS_OBJECT_NAME,
    SETTINGS_TELEGRAM_ENABLED_TOGGLE_OBJECT_NAME,
    SETTINGS_TELEGRAM_NOTIFY_BLOCK_DEADLINE_CHECKBOX_OBJECT_NAME,
    SETTINGS_TELEGRAM_NOTIFY_BLOCK_PUBLISH_CHECKBOX_OBJECT_NAME,
    SETTINGS_TELEGRAM_SECTION_OBJECT_NAME,
    build_telegram_connector_section,
    read_telegram_connector_from_view,
    update_telegram_connector_view,
)


class FakeWidget:
    def __init__(self) -> None:
        self.object_name: str | None = None
        self.children: list[object] = []
        self.layout: object | None = None
        self.visible = True

    def setObjectName(self, object_name: str) -> None:
        self.object_name = object_name

    def setVisible(self, visible: bool) -> None:
        self.visible = visible


class FakeLabel(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.text = text
        self.word_wrap = False
        self.fixed_width: int | None = None

    def setWordWrap(self, enabled: bool) -> None:
        self.word_wrap = enabled

    def setText(self, text: str) -> None:
        self.text = text

    def setStyleSheet(self, _style: str) -> None:
        return

    def setFixedWidth(self, width: int) -> None:
        self.fixed_width = width


class FakeLineEdit(FakeWidget):
    Password = "password"

    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.value = text
        self.placeholder = ""
        self.fixed_width: int | None = None
        self.echo_mode: object | None = None
        self.editingFinished = _FakeSignal()

    def setText(self, text: str) -> None:
        self.value = text

    def text(self) -> str:
        return self.value

    def setPlaceholderText(self, text: str) -> None:
        self.placeholder = text

    def setFixedWidth(self, width: int) -> None:
        self.fixed_width = width

    def setEchoMode(self, mode: object) -> None:
        self.echo_mode = mode


class FakeCheckBox(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.text = text
        self.checked = False
        self.stateChanged = _FakeSignal()

    def setText(self, text: str) -> None:
        self.text = text

    def setChecked(self, checked: bool) -> None:
        self.checked = checked

    def isChecked(self) -> bool:
        return self.checked


class FakePushButton(FakeLabel):
    def __init__(self, text: str = "") -> None:
        super().__init__(text)
        self.checkable = False
        self.checked = False
        self.style_sheet = ""
        self.clicked = _FakeSignal()

    def setCheckable(self, enabled: bool) -> None:
        self.checkable = enabled

    def setChecked(self, checked: bool) -> None:
        self.checked = checked

    def isChecked(self) -> bool:
        return self.checked

    def setStyleSheet(self, style: str) -> None:
        self.style_sheet = style


class _FakeSignal:
    def __init__(self) -> None:
        self.handlers: list[object] = []

    def connect(self, handler: object) -> None:
        self.handlers.append(handler)


class FakeHBoxLayout:
    def __init__(self, parent: FakeWidget | None = None) -> None:
        self.parent = parent
        self.widgets: list[object] = []
        self.layouts: list[object] = []
        self.stretches: list[int] = []
        if parent is not None:
            parent.layout = self

    def setContentsMargins(self, *_args: int) -> None:
        return

    def setSpacing(self, _spacing: int) -> None:
        return

    def addWidget(self, widget: object, *_args: object) -> None:
        self.widgets.append(widget)
        if (
            self.parent is not None
            and isinstance(widget, FakeWidget)
            and widget not in self.parent.children
        ):
            self.parent.children.append(widget)

    def addLayout(self, layout: object) -> None:
        self.layouts.append(layout)

    def addStretch(self, stretch: int = 0) -> None:
        self.stretches.append(stretch)


class FakeVBoxLayout:
    def __init__(self, parent: FakeWidget | None = None) -> None:
        self.parent = parent
        self.widgets: list[object] = []
        self.layouts: list[object] = []
        if parent is not None:
            parent.layout = self

    def setContentsMargins(self, *_args: int) -> None:
        return

    def setSpacing(self, _spacing: int) -> None:
        return

    def addWidget(self, widget: object) -> None:
        self.widgets.append(widget)
        self._attach_widget(widget)

    def addLayout(self, layout: object) -> None:
        self.layouts.append(layout)
        for widget in getattr(layout, "widgets", []):
            self._attach_widget(widget)

    def addStretch(self, _stretch: int = 0) -> None:
        return

    def _attach_widget(self, widget: object) -> None:
        if (
            self.parent is not None
            and isinstance(widget, FakeWidget)
            and widget not in self.parent.children
        ):
            self.parent.children.append(widget)


class FakeSizePolicy:
    Fixed = "fixed"


class FakeQt:
    AlignLeft = "align_left"


class FakeQtWidgets:
    QWidget = FakeWidget
    QLabel = FakeLabel
    QLineEdit = FakeLineEdit
    QCheckBox = FakeCheckBox
    QPushButton = FakePushButton
    QHBoxLayout = FakeHBoxLayout
    QVBoxLayout = FakeVBoxLayout
    QSizePolicy = FakeSizePolicy
    Qt = FakeQt


def _find(root: FakeWidget, object_name: str) -> FakeWidget:
    stack = [root]
    while stack:
        current = stack.pop()
        if getattr(current, "object_name", None) == object_name:
            return current
        stack.extend(getattr(current, "children", []))
    raise AssertionError(f"Could not find object named {object_name!r}")


def test_build_telegram_connector_section_exposes_toggle_and_collapsed_details():
    section = build_telegram_connector_section(
        FakeQtWidgets,
        StudioConfig(
            connectors=ConnectorSettings(
                telegram=TelegramConnectorSettings(enabled=False),
            )
        ),
    )

    assert section.object_name == SETTINGS_TELEGRAM_SECTION_OBJECT_NAME
    toggle = _find(section, SETTINGS_TELEGRAM_ENABLED_TOGGLE_OBJECT_NAME)
    details = _find(section, SETTINGS_TELEGRAM_DETAILS_OBJECT_NAME)
    assert toggle.checked is False
    assert details.visible is False


def test_build_telegram_connector_section_masks_bot_token_and_shows_notify_checkboxes():
    section = build_telegram_connector_section(
        FakeQtWidgets,
        StudioConfig(
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

    details = _find(section, SETTINGS_TELEGRAM_DETAILS_OBJECT_NAME)
    token = _find(section, SETTINGS_TELEGRAM_BOT_TOKEN_INPUT_OBJECT_NAME)
    chat_id = _find(section, SETTINGS_TELEGRAM_CHAT_ID_INPUT_OBJECT_NAME)
    publish = _find(section, SETTINGS_TELEGRAM_NOTIFY_BLOCK_PUBLISH_CHECKBOX_OBJECT_NAME)
    deadline = _find(section, SETTINGS_TELEGRAM_NOTIFY_BLOCK_DEADLINE_CHECKBOX_OBJECT_NAME)

    assert details.visible is True
    assert token.value == "secret-token"
    assert token.echo_mode == FakeLineEdit.Password
    assert chat_id.value == "-10042"
    assert publish.checked is True
    assert deadline.checked is False


def test_read_telegram_connector_from_view_round_trips_settings():
    section = build_telegram_connector_section(
        FakeQtWidgets,
        StudioConfig(
            connectors=ConnectorSettings(
                telegram=TelegramConnectorSettings(enabled=True),
            )
        ),
    )
    toggle = _find(section, SETTINGS_TELEGRAM_ENABLED_TOGGLE_OBJECT_NAME)
    token = _find(section, SETTINGS_TELEGRAM_BOT_TOKEN_INPUT_OBJECT_NAME)
    chat_id = _find(section, SETTINGS_TELEGRAM_CHAT_ID_INPUT_OBJECT_NAME)
    publish = _find(section, SETTINGS_TELEGRAM_NOTIFY_BLOCK_PUBLISH_CHECKBOX_OBJECT_NAME)
    deadline = _find(section, SETTINGS_TELEGRAM_NOTIFY_BLOCK_DEADLINE_CHECKBOX_OBJECT_NAME)

    toggle.setChecked(True)
    token.setText("123:abc")
    chat_id.setText("-10099")
    publish.setChecked(True)
    deadline.setChecked(True)

    loaded = read_telegram_connector_from_view(section, FakeQtWidgets)

    assert loaded == TelegramConnectorSettings(
        enabled=True,
        bot_token="123:abc",
        chat_id="-10099",
        notify_on=("block_publish", "block_deadline"),
    )


def test_update_telegram_connector_view_refreshes_fields():
    section = build_telegram_connector_section(
        FakeQtWidgets,
        StudioConfig(
            connectors=ConnectorSettings(
                telegram=TelegramConnectorSettings(enabled=False),
            )
        ),
    )

    update_telegram_connector_view(
        section,
        FakeQtWidgets,
        TelegramConnectorSettings(
            enabled=True,
            bot_token="rotated-token",
            chat_id="42",
            notify_on=("block_deadline",),
        ),
    )

    details = _find(section, SETTINGS_TELEGRAM_DETAILS_OBJECT_NAME)
    token = _find(section, SETTINGS_TELEGRAM_BOT_TOKEN_INPUT_OBJECT_NAME)
    chat_id = _find(section, SETTINGS_TELEGRAM_CHAT_ID_INPUT_OBJECT_NAME)
    publish = _find(section, SETTINGS_TELEGRAM_NOTIFY_BLOCK_PUBLISH_CHECKBOX_OBJECT_NAME)
    deadline = _find(section, SETTINGS_TELEGRAM_NOTIFY_BLOCK_DEADLINE_CHECKBOX_OBJECT_NAME)

    assert details.visible is True
    assert token.value == "rotated-token"
    assert chat_id.value == "42"
    assert publish.checked is False
    assert deadline.checked is True
