from __future__ import annotations

from shader_health.core.manifest_gate import ManifestGatePolicy
from shader_health.studio_config import (
    PipelineSettings,
    StudioConfig,
    WaiverDefaultsSettings,
)
from shader_health.ui.studio_policy_section import (
    SETTINGS_ALLOW_CRITICAL_WAIVERS_TOGGLE_OBJECT_NAME,
    SETTINGS_EXTRA_RULES_FOLDER_INPUT_OBJECT_NAME,
    SETTINGS_MANIFEST_BLOCK_NEW_TEXTURES_TOGGLE_OBJECT_NAME,
    SETTINGS_MANIFEST_MAX_FINGERPRINT_CHANGES_INPUT_OBJECT_NAME,
    SETTINGS_MANIFEST_MAX_NEW_CHANGES_INPUT_OBJECT_NAME,
    SETTINGS_PINNED_ASSET_CLASS_PROFILES_INPUT_OBJECT_NAME,
    SETTINGS_PINNED_WORKFLOW_PROFILES_INPUT_OBJECT_NAME,
    SETTINGS_REQUIRE_TX_TOGGLE_OBJECT_NAME,
    SETTINGS_STUDIO_NAME_INPUT_OBJECT_NAME,
    SETTINGS_WAIVER_APPROVED_BY_INPUT_OBJECT_NAME,
    SETTINGS_WAIVER_EXPIRY_DAYS_INPUT_OBJECT_NAME,
    build_studio_policy_section,
    format_profile_id_list,
    parse_profile_id_list,
    read_studio_policy_from_view,
    update_studio_policy_view,
)


class FakeWidget:
    def __init__(self) -> None:
        self.object_name: str | None = None
        self.children: list[object] = []
        self.layout: object | None = None
        self.fixed_width: int | None = None

    def setObjectName(self, object_name: str) -> None:
        self.object_name = object_name

    def setFixedWidth(self, width: int) -> None:
        self.fixed_width = width

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


class FakeLineEdit(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.value = text
        self.placeholder = ""
        self.tooltip = ""
        self.editingFinished = _FakeSignal()

    def setText(self, text: str) -> None:
        self.value = text

    def text(self) -> str:
        return self.value

    def setPlaceholderText(self, text: str) -> None:
        self.placeholder = text

    def setToolTip(self, text: str) -> None:
        self.tooltip = text


class FakePlainTextEdit(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.value = text
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


class FakePushButton(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.text = text
        self.checked = False
        self.checkable = False
        self.style_sheet = ""
        self.clicked = _FakeSignal()

    def setText(self, text: str) -> None:
        self.text = text

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


class FakeFormLayout:
    def __init__(self) -> None:
        self.rows: list[tuple[str, object]] = []

    def setContentsMargins(self, *_args: int) -> None:
        return

    def addRow(self, label: str, field: object) -> None:
        self.rows.append((label, field))


class FakeGridLayout:
    def __init__(self, parent: FakeWidget | None = None) -> None:
        self.parent = parent
        self.widgets: list[object] = []
        if parent is not None:
            parent.layout = self
            if parent not in self.widgets:
                pass

    def setContentsMargins(self, *_args: object) -> None:
        return

    def setHorizontalSpacing(self, _spacing: int) -> None:
        return

    def setVerticalSpacing(self, _spacing: int) -> None:
        return

    def setColumnStretch(self, _column: int, _stretch: int) -> None:
        return

    def addWidget(self, widget: object, _row: int, _column: int, *_args: object) -> None:
        self.widgets.append(widget)
        if self.parent is not None and widget not in self.parent.children:
            self.parent.children.append(widget)


class FakeQt:
    AlignLeft = 1
    AlignVCenter = 2


class FakeHBoxLayout:
    def __init__(self, parent: FakeWidget | None = None) -> None:
        self.parent = parent
        self.widgets: list[object] = []
        if parent is not None:
            parent.layout = self

    def setContentsMargins(self, *_args: object) -> None:
        return

    def setSpacing(self, _spacing: int) -> None:
        return

    def addWidget(self, widget: object, *_args: object) -> None:
        self.widgets.append(widget)

    def addSpacing(self, _spacing: int) -> None:
        return

    def addStretch(self, _stretch: int = 0) -> None:
        return


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
        for _label, field in getattr(layout, "rows", []):
            self._attach_widget(field)
            if hasattr(field, "children"):
                for child in field.children:
                    self._attach_widget(child)
            if hasattr(field, "layout") and hasattr(field.layout, "widgets"):
                for child in field.layout.widgets:
                    self._attach_widget(child)

    def _attach_widget(self, widget: object) -> None:
        if (
            self.parent is not None
            and isinstance(widget, FakeWidget)
            and widget not in self.parent.children
        ):
            self.parent.children.append(widget)


class FakeQtWidgets:
    QWidget = FakeWidget
    QLabel = FakeLabel
    QLineEdit = FakeLineEdit
    QPlainTextEdit = FakePlainTextEdit
    QPushButton = FakePushButton
    QFormLayout = FakeFormLayout
    QHBoxLayout = FakeHBoxLayout
    QVBoxLayout = FakeVBoxLayout
    QGridLayout = FakeGridLayout
    Qt = FakeQt


def _find(root: FakeWidget, object_name: str) -> FakeWidget:
    stack = [root]
    while stack:
        current = stack.pop()
        if getattr(current, "object_name", None) == object_name:
            return current
        stack.extend(getattr(current, "children", []))
    raise AssertionError(f"Widget not found: {object_name}")


def test_parse_and_format_profile_id_list_round_trip():
    profile_ids = ("artist_relaxed", "publish_strict")

    assert parse_profile_id_list(format_profile_id_list(profile_ids)) == profile_ids


def test_build_studio_policy_section_populates_policy_fields():
    config = StudioConfig(
        studio_name="Demo Studio",
        pipeline=PipelineSettings(
            require_tx_derivatives=False,
            waiver_defaults=WaiverDefaultsSettings(
                default_approved_by="pipeline_td",
                default_expiry_days=14,
                allow_critical_waivers=True,
            ),
            manifest_gate_defaults=ManifestGatePolicy(
                max_new_changes=1,
                max_fingerprint_changes=2,
                block_on_new_textures=False,
            ),
            pinned_workflow_profile_ids=("artist_relaxed",),
            pinned_asset_class_profile_ids=("asset_class_hero",),
            extra_rules_folder="//studio/share/extra_rules",
        ),
    )
    section = build_studio_policy_section(FakeQtWidgets, config)

    assert _find(section, SETTINGS_STUDIO_NAME_INPUT_OBJECT_NAME).value == "Demo Studio"
    assert _find(section, SETTINGS_EXTRA_RULES_FOLDER_INPUT_OBJECT_NAME).value == (
        "//studio/share/extra_rules"
    )
    assert _find(section, SETTINGS_REQUIRE_TX_TOGGLE_OBJECT_NAME).checked is False
    assert _find(section, SETTINGS_WAIVER_APPROVED_BY_INPUT_OBJECT_NAME).value == "pipeline_td"
    assert _find(section, SETTINGS_PINNED_WORKFLOW_PROFILES_INPUT_OBJECT_NAME).value == (
        "artist_relaxed"
    )


def test_read_studio_policy_from_view_reads_policy_fields():
    config = StudioConfig()
    section = build_studio_policy_section(FakeQtWidgets, config)
    _find(section, SETTINGS_STUDIO_NAME_INPUT_OBJECT_NAME).setText("Network Studio")
    _find(section, SETTINGS_WAIVER_APPROVED_BY_INPUT_OBJECT_NAME).setText("lead_td")
    _find(section, SETTINGS_WAIVER_EXPIRY_DAYS_INPUT_OBJECT_NAME).setText("21")
    _find(section, SETTINGS_ALLOW_CRITICAL_WAIVERS_TOGGLE_OBJECT_NAME).setChecked(True)
    _find(section, SETTINGS_MANIFEST_MAX_NEW_CHANGES_INPUT_OBJECT_NAME).setText("3")
    _find(section, SETTINGS_MANIFEST_MAX_FINGERPRINT_CHANGES_INPUT_OBJECT_NAME).setText("4")
    _find(section, SETTINGS_MANIFEST_BLOCK_NEW_TEXTURES_TOGGLE_OBJECT_NAME).setChecked(False)
    _find(section, SETTINGS_PINNED_WORKFLOW_PROFILES_INPUT_OBJECT_NAME).setPlainText(
        "publish_strict"
    )
    _find(section, SETTINGS_PINNED_ASSET_CLASS_PROFILES_INPUT_OBJECT_NAME).setPlainText(
        "asset_class_prop"
    )
    _find(section, SETTINGS_EXTRA_RULES_FOLDER_INPUT_OBJECT_NAME).setText(
        "D:/studio/extra_rules"
    )

    studio = read_studio_policy_from_view(section, FakeQtWidgets, base=config)

    assert studio.studio_name == "Network Studio"
    assert studio.pipeline.waiver_defaults.default_approved_by == "lead_td"
    assert studio.pipeline.waiver_defaults.default_expiry_days == 21
    assert studio.pipeline.waiver_defaults.allow_critical_waivers is True
    assert studio.pipeline.manifest_gate_defaults.max_new_changes == 3
    assert studio.pipeline.manifest_gate_defaults.max_fingerprint_changes == 4
    assert studio.pipeline.manifest_gate_defaults.block_on_new_textures is False
    assert studio.pipeline.pinned_workflow_profile_ids == ("publish_strict",)
    assert studio.pipeline.pinned_asset_class_profile_ids == ("asset_class_prop",)
    assert studio.pipeline.extra_rules_folder == "D:/studio/extra_rules"
    assert studio.pipeline.extra_rules_folder == "D:/studio/extra_rules"


def test_update_studio_policy_view_refreshes_policy_fields():
    config = StudioConfig()
    section = build_studio_policy_section(FakeQtWidgets, config)
    updated = StudioConfig(
        studio_name="Refreshed Studio",
        pipeline=PipelineSettings(
            require_tx_derivatives=True,
            waiver_defaults=WaiverDefaultsSettings(default_approved_by="shader_td"),
            pinned_workflow_profile_ids=("deadline_critical",),
        ),
    )

    update_studio_policy_view(section, FakeQtWidgets, updated)

    assert _find(section, SETTINGS_STUDIO_NAME_INPUT_OBJECT_NAME).value == "Refreshed Studio"
    assert _find(section, SETTINGS_REQUIRE_TX_TOGGLE_OBJECT_NAME).checked is True
    assert _find(section, SETTINGS_WAIVER_APPROVED_BY_INPUT_OBJECT_NAME).value == "shader_td"
    assert _find(section, SETTINGS_PINNED_WORKFLOW_PROFILES_INPUT_OBJECT_NAME).value == (
        "deadline_critical"
    )
