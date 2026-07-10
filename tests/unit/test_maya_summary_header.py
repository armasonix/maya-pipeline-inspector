from __future__ import annotations

from typing import Any, Optional

from shader_health.ui import main_window


class FakeWidget:
    def __init__(self) -> None:
        self.object_name: Optional[str] = None
        self.children: list[Any] = []
        self.layout: Optional[FakeVBoxLayout] = None
        self.size_policy: Optional[tuple[Any, Any]] = None
        self.visible = True
        self.style_sheet = ""

    def setObjectName(self, object_name: str) -> None:
        self.object_name = object_name

    def setStyleSheet(self, style: str) -> None:
        self.style_sheet = style

    def setSizePolicy(self, horizontal: Any, vertical: Any) -> None:
        self.size_policy = (horizontal, vertical)

    def setVisible(self, visible: bool) -> None:
        self.visible = visible

    def setLayout(self, layout: Any) -> None:
        self.layout = layout
        for widget in getattr(layout, "widgets", []):
            if widget not in self.children:
                self.children.append(widget)


class FakePlainTextEdit(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.value = text
        self.plainTextChanged = FakeSignal()

    def setPlainText(self, text: str) -> None:
        self.value = text

    def toPlainText(self) -> str:
        return self.value

    def setPlaceholderText(self, text: str) -> None:
        _ = text

    def setToolTip(self, text: str) -> None:
        _ = text


class FakeLineEdit(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.value = text

    def setText(self, text: str) -> None:
        self.value = text

    def text(self) -> str:
        return self.value

    def setPlaceholderText(self, text: str) -> None:
        _ = text

    def setToolTip(self, text: str) -> None:
        _ = text

    @property
    def editingFinished(self) -> FakeSignal:
        return FakeSignal()


class FakeSignal:
    def __init__(self) -> None:
        self.handlers: list[Any] = []

    def connect(self, handler: Any) -> None:
        self.handlers.append(handler)

    def emit(self, *_args: Any) -> None:
        for handler in self.handlers:
            handler()


class FakeLabel(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.text = text
        self.word_wrap = False
        self.style_sheet = ""
        self.fixed_size: Optional[tuple[int, int]] = None
        self.text_format: Optional[Any] = None

    def setWordWrap(self, enabled: bool) -> None:
        self.word_wrap = enabled

    def setText(self, text: str) -> None:
        self.text = text

    def setTextFormat(self, text_format: Any) -> None:
        self.text_format = text_format

    def setStyleSheet(self, style: str) -> None:
        self.style_sheet = style

    def setFixedSize(self, width: int, height: int) -> None:
        self.fixed_size = (width, height)


class FakeQFrame(FakeWidget):
    HLine = "hline"
    Sunken = "sunken"

    def __init__(self) -> None:
        super().__init__()
        self.frame_shape: Optional[Any] = None
        self.frame_shadow: Optional[Any] = None
        self.fixed_height: Optional[int] = None

    def setFrameShape(self, shape: Any) -> None:
        self.frame_shape = shape

    def setFrameShadow(self, shadow: Any) -> None:
        self.frame_shadow = shadow

    def setFixedHeight(self, height: int) -> None:
        self.fixed_height = height


class FakeComboBox(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[tuple[str, str]] = []
        self.current_index = 0
        self.tooltip = ""

    def addItem(self, text: str, user_data: str = "") -> None:
        self.items.append((text, user_data or text))

    def addItems(self, items: list[str]) -> None:
        for item in items:
            self.addItem(item)

    def setCurrentText(self, text: str) -> None:
        for index, (label, _data) in enumerate(self.items):
            if label == text:
                self.current_index = index
                return

    def setCurrentIndex(self, index: int) -> None:
        self.current_index = index

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


class FakePushButton(FakeLabel):
    def __init__(self, text: str = "") -> None:
        super().__init__(text)
        self.enabled = True
        self.tooltip = ""
        self.checkable = False
        self.checked = False
        self.style_sheet = ""
        self.fixed_width: int | None = None
        self.clicked = FakeSignal()

    def setEnabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def setToolTip(self, text: str) -> None:
        self.tooltip = text

    def setCheckable(self, enabled: bool) -> None:
        self.checkable = enabled

    def setChecked(self, checked: bool) -> None:
        self.checked = checked

    def isChecked(self) -> bool:
        return self.checked

    def setStyleSheet(self, style: str) -> None:
        self.style_sheet = style

    def setFixedWidth(self, width: int) -> None:
        self.fixed_width = width


class FakeCheckBox(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.checked = False

    def setChecked(self, checked: bool) -> None:
        self.checked = checked

    def setToolTip(self, _text: str) -> None:
        return


class FakeTableWidget(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.column_count = 0
        self.row_count = 0
        self.headers: list[str] = []
        self.sorting_enabled = False

    def setColumnCount(self, count: int) -> None:
        self.column_count = count

    def setRowCount(self, count: int) -> None:
        self.row_count = count

    def setHorizontalHeaderLabels(self, headers: list[str]) -> None:
        self.headers = headers

    def setSortingEnabled(self, enabled: bool) -> None:
        self.sorting_enabled = enabled


class FakeTableWidgetItem:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeVBoxLayout:
    def __init__(self, parent: FakeWidget | None = None) -> None:
        self.parent = parent
        self.margins: Optional[tuple[int, int, int, int]] = None
        self.spacing: Optional[int] = None
        self.widgets: list[Any] = []
        self.layouts: list[Any] = []
        self.stretches: list[int] = []
        if parent is not None:
            parent.layout = self

    def setContentsMargins(self, left: int, top: int, right: int, bottom: int) -> None:
        self.margins = (left, top, right, bottom)

    def setSpacing(self, spacing: int) -> None:
        self.spacing = spacing

    def addWidget(self, widget: Any, stretch: Optional[int] = None) -> None:
        self.widgets.append(widget)
        self._attach_widget(widget)
        _ = stretch

    def addLayout(self, layout: Any) -> None:
        self.layouts.append(layout)
        for widget in getattr(layout, "widgets", []):
            self._attach_widget(widget)
        for nested in getattr(layout, "layouts", []):
            for widget in getattr(nested, "widgets", []):
                self._attach_widget(widget)

    def addStretch(self, stretch: int) -> None:
        self.stretches.append(stretch)

    def _attach_widget(self, widget: Any) -> None:
        if self.parent is not None and widget not in self.parent.children:
            self.parent.children.append(widget)


class FakeHBoxLayout(FakeVBoxLayout):
    pass


class FakeGridLayout(FakeVBoxLayout):
    def addWidget(self, widget: Any, row: int = 0, column: int = 0, *_args: Any) -> None:
        self._attach_widget(widget)
        _ = (row, column)


class FakeFormLayout:
    def __init__(self, parent: FakeWidget | None = None) -> None:
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


class FakeTabWidget(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.tabs: list[tuple[str, FakeWidget]] = []

    def addTab(self, widget: FakeWidget, title: str) -> None:
        self.tabs.append((title, widget))
        self.children.append(widget)


class FakeStackedWidget(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.pages: list[Any] = []
        self.current_index = 0

    def addWidget(self, widget: Any) -> None:
        self.pages.append(widget)
        self.children.append(widget)

    def setCurrentIndex(self, index: int) -> None:
        self.current_index = index


class FakeSplitter(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.widgets: list[Any] = []
        self.stretch_factors: list[tuple[int, int]] = []
        self.orientation: Any = None
        self.children_collapsible: Optional[bool] = None
        self.collapsible: dict[int, bool] = {}

    def setOrientation(self, orientation: Any) -> None:
        self.orientation = orientation

    def addWidget(self, widget: Any) -> None:
        self.widgets.append(widget)
        self.children.append(widget)

    def setStretchFactor(self, index: int, stretch: int) -> None:
        self.stretch_factors.append((index, stretch))

    def setChildrenCollapsible(self, enabled: bool) -> None:
        self.children_collapsible = enabled

    def setCollapsible(self, index: int, enabled: bool) -> None:
        self.collapsible[index] = enabled


class FakeQt:
    Horizontal = "horizontal"
    RichText = "rich_text"
    ScrollBarAlwaysOff = "scroll_bar_always_off"


class FakeSizePolicy:
    Preferred = "preferred"
    Fixed = "fixed"
    Maximum = "maximum"
    Expanding = "expanding"
    Minimum = "minimum"


class FakeQScrollArea(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.widget_resizable = False
        self.scroll_widget: Any = None
        self.horizontal_scroll_policy: Any = None
        self.size_policy: Optional[tuple[Any, Any]] = None

    def setWidgetResizable(self, enabled: bool) -> None:
        self.widget_resizable = enabled

    def setHorizontalScrollBarPolicy(self, policy: Any) -> None:
        self.horizontal_scroll_policy = policy

    def setWidget(self, widget: Any) -> None:
        self.scroll_widget = widget
        self.children.append(widget)

    def setSizePolicy(self, horizontal: Any, vertical: Any) -> None:
        self.size_policy = (horizontal, vertical)


class FakeProgressBar(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.visible = True
        self.maximum = 1
        self.minimum = 0
        self.text_visible = True
        self.fixed_height: Optional[int] = None
        self.maximum_width: Optional[int] = None

    def setTextVisible(self, visible: bool) -> None:
        self.text_visible = visible

    def setMaximum(self, value: int) -> None:
        self.maximum = value

    def setMinimum(self, value: int) -> None:
        self.minimum = value

    def setFixedHeight(self, height: int) -> None:
        self.fixed_height = height

    def setMaximumWidth(self, width: int) -> None:
        self.maximum_width = width

    def setVisible(self, visible: bool) -> None:
        self.visible = visible


class FakeQtWidgets:
    QWidget = FakeWidget
    QLabel = FakeLabel
    QLineEdit = FakeLineEdit
    QPlainTextEdit = FakePlainTextEdit
    QFrame = FakeQFrame
    QScrollArea = FakeQScrollArea
    QProgressBar = FakeProgressBar
    QComboBox = FakeComboBox
    QPushButton = FakePushButton
    QCheckBox = FakeCheckBox
    QTableWidget = FakeTableWidget
    QTableWidgetItem = FakeTableWidgetItem
    QVBoxLayout = FakeVBoxLayout
    QHBoxLayout = FakeHBoxLayout
    QGridLayout = FakeGridLayout
    QFormLayout = FakeFormLayout
    QTabWidget = FakeTabWidget
    QStackedWidget = FakeStackedWidget
    QSplitter = FakeSplitter
    QSizePolicy = FakeSizePolicy
    Qt = FakeQt


def test_summary_header_defaults_show_score_counts_blocks_and_profile_dropdown():
    header = main_window.build_summary_header(FakeQtWidgets)

    assert _find(header, main_window.HEALTH_SCORE_LABEL_OBJECT_NAME).text == "Health: 100 / 100"
    assert (
        _find(header, main_window.CRITICAL_COUNT_LABEL_OBJECT_NAME).text
        == 'Critical: <span style="color:#e74c3c;">0</span>'
    )
    assert (
        _find(header, main_window.ERROR_COUNT_LABEL_OBJECT_NAME).text
        == 'Error: <span style="color:#e67e22;">0</span>'
    )
    assert (
        _find(header, main_window.WARNING_COUNT_LABEL_OBJECT_NAME).text
        == 'Warning: <span style="color:#f1c40f;">0</span>'
    )
    assert (
        _find(header, main_window.INFO_COUNT_LABEL_OBJECT_NAME).text
        == 'Info: <span style="color:#22d3ee;">0</span>'
    )
    assert _find(header, main_window.PUBLISH_BLOCK_LABEL_OBJECT_NAME).text == "Publish Block: NO"
    assert _find(header, main_window.DEADLINE_BLOCK_LABEL_OBJECT_NAME).text == "Deadline Block: NO"
    assert _find(header, main_window.PUBLISH_BLOCK_LAMP_OBJECT_NAME) is not None
    assert _find(header, main_window.DEADLINE_BLOCK_LAMP_OBJECT_NAME) is not None
    assert _find(header, main_window.SCENE_NAME_LABEL_OBJECT_NAME).text == "Scene: (unsaved)"
    assert _find(header, main_window.LAST_VALIDATED_LABEL_OBJECT_NAME).text == "Last validated: —"
    assert _find(header, main_window.SCAN_SCOPE_LABEL_OBJECT_NAME).text == "Scope: —"
    profile_dropdown = _find(header, main_window.PROFILE_DROPDOWN_OBJECT_NAME)
    asset_class_dropdown = _find(header, main_window.ASSET_CLASS_DROPDOWN_OBJECT_NAME)
    workflow_ids = [option.profile_id for option in main_window.DEFAULT_WORKFLOW_PROFILE_OPTIONS]
    assert [item[1] for item in profile_dropdown.items] == workflow_ids
    assert profile_dropdown.currentText() == "Artist Relaxed"
    assert asset_class_dropdown.currentText() == main_window.ASSET_CLASS_NONE_LABEL


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
        _find(header, main_window.CRITICAL_COUNT_LABEL_OBJECT_NAME).text
        == 'Critical: <span style="color:#e74c3c;">2</span>'
    )
    assert (
        _find(header, main_window.ERROR_COUNT_LABEL_OBJECT_NAME).text
        == 'Error: <span style="color:#e67e22;">4</span>'
    )
    assert (
        _find(header, main_window.WARNING_COUNT_LABEL_OBJECT_NAME).text
        == 'Warning: <span style="color:#f1c40f;">7</span>'
    )
    assert (
        _find(header, main_window.INFO_COUNT_LABEL_OBJECT_NAME).text
        == 'Info: <span style="color:#22d3ee;">11</span>'
    )
    assert _find(header, main_window.PUBLISH_BLOCK_LABEL_OBJECT_NAME).text == "Publish Block: YES"
    assert _find(header, main_window.DEADLINE_BLOCK_LABEL_OBJECT_NAME).text == "Deadline Block: YES"
    profile_dropdown = _find(header, main_window.PROFILE_DROPDOWN_OBJECT_NAME)
    assert profile_dropdown.currentData() == "deadline_critical"


def test_summary_header_accepts_custom_profile_options():
    from shader_health.maya.validation_pipeline import ProfileOption

    state = main_window.SummaryHeaderState(profile_id="publish_strict")

    header = main_window.build_summary_header(
        FakeQtWidgets,
        state=state,
        workflow_options=(
            ProfileOption("artist_relaxed", "Artist Relaxed"),
            ProfileOption("publish_strict", "Publish Strict"),
        ),
    )

    profile_dropdown = _find(header, main_window.PROFILE_DROPDOWN_OBJECT_NAME)
    assert [item[1] for item in profile_dropdown.items] == ["artist_relaxed", "publish_strict"]
    assert profile_dropdown.currentData() == "publish_strict"


def test_main_widget_contains_tabbed_shell():
    widget = main_window.build_main_widget(FakeQtWidgets)

    _find(widget, main_window.PANEL_HEADER_OBJECT_NAME)
    _find(widget, main_window.SETTINGS_GEAR_BUTTON_OBJECT_NAME)
    _find(widget, main_window.DOCUMENTATION_BUTTON_OBJECT_NAME)
    _find(widget, main_window.CHECK_FOR_UPDATES_BUTTON_OBJECT_NAME)
    stack = _find(widget, main_window.PANEL_BODY_STACK_OBJECT_NAME)
    assert len(stack.pages) == 2
    tabs = _find(widget, main_window.TAB_WIDGET_OBJECT_NAME)
    assert tabs.object_name == main_window.TAB_WIDGET_OBJECT_NAME
    assert [title for title, _tab in tabs.tabs] == [
        "Validate",
        "Waivers",
        "Fixes",
        "Reports",
        "Farm",
    ]


def test_validate_tab_uses_sticky_chrome_action_bar_and_splitter():
    widget = main_window.build_main_widget(FakeQtWidgets)
    validate_tab = _find(widget, main_window.TAB_WIDGET_OBJECT_NAME).tabs[0][1]

    _find(validate_tab, main_window.VALIDATE_STICKY_CHROME_OBJECT_NAME)
    _find(validate_tab, main_window.VALIDATE_ACTION_BAR_OBJECT_NAME)
    _find(validate_tab, main_window.VALIDATE_PRIMARY_ACTIONS_OBJECT_NAME)
    _find(validate_tab, main_window.VALIDATE_PIPELINE_ACTIONS_OBJECT_NAME)
    _find(validate_tab, main_window.VALIDATE_STATUS_ROW_OBJECT_NAME)
    progress = _find(validate_tab, main_window.VALIDATE_PROGRESS_BAR_OBJECT_NAME)
    assert progress.visible is False
    splitter = _find(validate_tab, main_window.VALIDATE_ISSUES_SPLITTER_OBJECT_NAME)
    assert len(splitter.widgets) == 2
    assert splitter.stretch_factors == [(0, 3), (1, 2)]
    assert splitter.children_collapsible is False
    assert splitter.collapsible == {0: False, 1: False}


def test_validation_action_bar_groups_primary_pipeline_and_triage_buttons():
    callbacks = main_window.ValidationActionCallbacks()
    issue_callbacks = main_window.IssueDetailsActionCallbacks()
    action_bar = main_window.build_validation_actions(
        FakeQtWidgets,
        callbacks=callbacks,
        issue_details_callbacks=issue_callbacks,
    )

    primary = _find(action_bar, main_window.VALIDATE_PRIMARY_ACTIONS_OBJECT_NAME)
    pipeline = _find(action_bar, main_window.VALIDATE_PIPELINE_ACTIONS_OBJECT_NAME)
    triage = _find(action_bar, main_window.VALIDATE_TRIAGE_ACTIONS_OBJECT_NAME)
    assert _find(primary, main_window.VALIDATE_SCENE_BUTTON_OBJECT_NAME) is not None
    assert _find(primary, main_window.VALIDATE_SELECTION_BUTTON_OBJECT_NAME) is not None
    assert _find(pipeline, main_window.VALIDATE_PUBLISH_PREFLIGHT_BUTTON_OBJECT_NAME) is not None
    assert _find(pipeline, main_window.VALIDATE_MANIFEST_GATE_BUTTON_OBJECT_NAME) is not None
    assert _find(triage, main_window.SELECT_NODE_BUTTON_OBJECT_NAME) is not None
    assert _find(triage, main_window.OPEN_ATTR_EDITOR_BUTTON_OBJECT_NAME) is not None
    assert _find(triage, main_window.COPY_PATH_BUTTON_OBJECT_NAME) is not None
    assert _find(triage, main_window.REVEAL_FILE_BUTTON_OBJECT_NAME) is not None


def test_format_last_validated_display_parses_utc_timestamp():
    text = main_window.format_last_validated_display("2026-07-02T12:30:00Z")
    assert text.startswith("Last validated: 2026-07-02")


def test_build_reports_status_text_includes_validation_metadata():
    text = main_window.build_reports_status_text(
        scene_path="D:/show/char.ma",
        scanned_at_utc="2026-07-02T12:30:00Z",
        scan_scope="scene",
    )
    assert "Scene: char.ma" in text
    assert "Last validated:" in text
    assert "Scope: scene" in text


def test_update_severity_count_indicators_sets_colored_summary_labels():
    widget = main_window.build_summary_header(FakeQtWidgets)
    main_window.update_severity_count_indicators(
        widget,
        FakeQtWidgets,
        critical_count=12,
        error_count=23,
        warning_count=5,
        info_count=1,
    )

    assert (
        _find(widget, main_window.CRITICAL_COUNT_LABEL_OBJECT_NAME).text
        == 'Critical: <span style="color:#e74c3c;">12</span>'
    )
    assert (
        _find(widget, main_window.ERROR_COUNT_LABEL_OBJECT_NAME).text
        == 'Error: <span style="color:#e67e22;">23</span>'
    )
    assert (
        _find(widget, main_window.WARNING_COUNT_LABEL_OBJECT_NAME).text
        == 'Warning: <span style="color:#f1c40f;">5</span>'
    )
    assert (
        _find(widget, main_window.INFO_COUNT_LABEL_OBJECT_NAME).text
        == 'Info: <span style="color:#22d3ee;">1</span>'
    )


def test_panel_header_includes_version_settings_gear_documentation_and_updates_buttons():
    opened: list[str] = []

    header = main_window.build_panel_header(
        FakeQtWidgets,
        version="0.3.0",
        navigation_callbacks=main_window.PanelNavigationCallbacks(
            on_open_documentation=lambda: opened.append("docs"),
            on_check_for_updates=lambda: opened.append("updates"),
        ),
    )
    title = _find(header, main_window.PANEL_HEADER_TITLE_OBJECT_NAME)
    gear = _find(header, main_window.SETTINGS_GEAR_BUTTON_OBJECT_NAME)
    docs = _find(header, main_window.DOCUMENTATION_BUTTON_OBJECT_NAME)
    updates = _find(header, main_window.CHECK_FOR_UPDATES_BUTTON_OBJECT_NAME)

    assert "Maya Shader Health Inspector" in title.text
    assert "v0.3.0" in title.text
    assert gear.tooltip == "Open settings"
    assert docs.text == "Documentation"
    assert docs.tooltip == "Open shader health documentation in your browser."
    assert updates.text == "Check for Updates"
    assert updates.tooltip == "Open the update wizard shell and preview staged progress steps."
    docs.clicked.emit()
    updates.clicked.emit()
    assert opened == ["docs", "updates"]


def _find(widget: Any, object_name: str) -> Any:
    stack = [widget]
    while stack:
        current = stack.pop()
        if getattr(current, "object_name", None) == object_name:
            return current
        stack.extend(getattr(current, "children", []))
    raise AssertionError(f"Could not find object named {object_name!r}")
