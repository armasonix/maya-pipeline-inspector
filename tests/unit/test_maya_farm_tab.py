from __future__ import annotations

from typing import Any

from tests.unit.test_maya_summary_header import (
    FakePushButton,
    FakeQtWidgets,
    _find,
)

from shader_health.ui import farm_tab, main_window


class FakeSignal:
    def __init__(self) -> None:
        self._callbacks: list[Any] = []

    def connect(self, callback: Any) -> None:
        self._callbacks.append(callback)

    def emit(self, *args: object, **kwargs: object) -> None:
        for callback in self._callbacks:
            callback(*args, **kwargs)


class FakeFarmPushButton(FakePushButton):
    def __init__(self, text: str = "") -> None:
        super().__init__(text)
        self.clicked = FakeSignal()


class FakeFarmQtWidgets(FakeQtWidgets):
    QPushButton = FakeFarmPushButton


def test_build_main_widget_includes_farm_tab():
    widget = main_window.build_main_widget(FakeQtWidgets)
    tabs = _find(widget, main_window.TAB_WIDGET_OBJECT_NAME)
    assert tabs is not None
    assert tabs.tabs[-1][0] == "Farm"
    assert tabs.tabs[-1][1].object_name == farm_tab.FARM_TAB_OBJECT_NAME


def test_build_farm_tab_exposes_status_and_actions():
    clicked: list[str] = []

    callbacks = farm_tab.FarmActionCallbacks(
        on_refresh_connection=lambda: clicked.append("refresh"),
        on_run_farm_preflight=lambda: clicked.append("preflight"),
        on_submit_to_farm=lambda: clicked.append("submit"),
    )
    tab = farm_tab.build_farm_tab(FakeFarmQtWidgets, callbacks=callbacks)
    assert _find(tab, farm_tab.FARM_CONNECTION_LABEL_OBJECT_NAME) is not None
    assert _find(tab, farm_tab.FARM_CONNECTION_STATUS_LABEL_OBJECT_NAME).text == "Status:"
    assert _find(tab, farm_tab.FARM_CONNECTION_LAMP_OBJECT_NAME) is not None
    assert _find(tab, farm_tab.FARM_ELIGIBILITY_LABEL_OBJECT_NAME) is not None
    assert _find(tab, farm_tab.FARM_LAST_REPORT_LABEL_OBJECT_NAME) is not None
    assert _find(tab, farm_tab.FARM_LAST_JOB_LABEL_OBJECT_NAME) is not None

    _find(tab, farm_tab.FARM_REFRESH_CONNECTION_BUTTON_OBJECT_NAME).clicked.emit()
    _find(tab, farm_tab.FARM_RUN_PREFLIGHT_BUTTON_OBJECT_NAME).clicked.emit()
    _find(tab, farm_tab.FARM_SUBMIT_BUTTON_OBJECT_NAME).clicked.emit()
    assert clicked == ["refresh", "preflight", "submit"]


def test_connection_status_group_keeps_lamp_left_of_stretch():
    tab = farm_tab.build_farm_tab(FakeQtWidgets)
    status_caption = _find(tab, farm_tab.FARM_CONNECTION_STATUS_LABEL_OBJECT_NAME)
    lamp = _find(tab, farm_tab.FARM_CONNECTION_LAMP_OBJECT_NAME)
    status_value = _find(tab, farm_tab.FARM_CONNECTION_STATUS_VALUE_LABEL_OBJECT_NAME)
    stack = [tab]
    status_group = None
    while stack:
        current = stack.pop()
        if (
            status_caption in current.children
            and lamp in current.children
            and status_value in current.children
        ):
            status_group = current
            break
        stack.extend(current.children)
    assert status_group is not None
    assert status_group.layout is not None
    assert status_group.layout.stretches == [1]
    layout_widgets = status_group.layout.widgets
    assert layout_widgets.index(status_caption) < layout_widgets.index(lamp)
    assert layout_widgets.index(lamp) < layout_widgets.index(status_value)


def test_farm_action_buttons_share_one_row():
    tab = farm_tab.build_farm_tab(FakeQtWidgets)
    button_names = {
        farm_tab.FARM_REFRESH_CONNECTION_BUTTON_OBJECT_NAME,
        farm_tab.FARM_RUN_PREFLIGHT_BUTTON_OBJECT_NAME,
        farm_tab.FARM_SUBMIT_BUTTON_OBJECT_NAME,
    }
    stack = [tab]
    button_row = None
    while stack:
        current = stack.pop()
        child_names = {getattr(child, "object_name", None) for child in current.children}
        if button_names.issubset(child_names):
            button_row = current
            break
        stack.extend(current.children)
    assert button_row is not None
    row_button_names = [
        child.object_name
        for child in button_row.children
        if getattr(child, "object_name", None) in button_names
    ]
    assert row_button_names == [
        farm_tab.FARM_REFRESH_CONNECTION_BUTTON_OBJECT_NAME,
        farm_tab.FARM_RUN_PREFLIGHT_BUTTON_OBJECT_NAME,
        farm_tab.FARM_SUBMIT_BUTTON_OBJECT_NAME,
    ]


def test_build_farm_tab_shows_green_lamp_when_connected():
    tab = farm_tab.build_farm_tab(
        FakeQtWidgets,
        state=farm_tab.FarmTabState(
            connection_reachable=True,
            connection_status="connected",
        ),
    )
    lamp = _find(tab, farm_tab.FARM_CONNECTION_LAMP_OBJECT_NAME)
    assert "#2ecc71" in lamp.style_sheet
    assert _find(tab, farm_tab.FARM_CONNECTION_STATUS_VALUE_LABEL_OBJECT_NAME).text == "Online"


def test_update_farm_tab_refreshes_labels():
    tab = farm_tab.build_farm_tab(
        FakeQtWidgets,
        state=farm_tab.FarmTabState(
            api_url="http://farm:8081",
            connection_reachable=True,
            connection_status="connected",
            eligibility_decision="allow",
            eligibility_allowed=True,
            last_report_path="D:/show/report.json",
            last_job_id="job-42",
            status_message="Ready",
        ),
    )
    farm_tab.update_farm_tab(
        tab,
        FakeQtWidgets,
        farm_tab.FarmTabState(
            connection_reachable=False,
            connection_status="unreachable",
            eligibility_decision="block",
            last_job_id="job-99",
            status_message="Blocked",
        ),
    )
    assert "unreachable" in _find(tab, farm_tab.FARM_CONNECTION_LABEL_OBJECT_NAME).text
    assert "block" in _find(tab, farm_tab.FARM_ELIGIBILITY_LABEL_OBJECT_NAME).text
    assert "job-99" in _find(tab, farm_tab.FARM_LAST_JOB_LABEL_OBJECT_NAME).text
    assert _find(tab, farm_tab.FARM_STATUS_LABEL_OBJECT_NAME).text == "Blocked"
    lamp = _find(tab, farm_tab.FARM_CONNECTION_LAMP_OBJECT_NAME)
    assert "#e74c3c" in lamp.style_sheet
    status_value_label = _find(tab, farm_tab.FARM_CONNECTION_STATUS_VALUE_LABEL_OBJECT_NAME)
    assert status_value_label.text == "Offline"
