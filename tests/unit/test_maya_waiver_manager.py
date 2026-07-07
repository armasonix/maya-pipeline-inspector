from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from shader_health.core.waivers import create_waiver_from_result
from shader_health.maya import commands
from shader_health.ui import waiver_manager


class FakeSignal:
    def __init__(self) -> None:
        self.callback: Optional[Any] = None

    def connect(self, callback: Any) -> None:
        self.callback = callback

    def emit(self) -> None:
        assert self.callback is not None
        self.callback()


class FakeWidget:
    def __init__(self) -> None:
        self.object_name: Optional[str] = None
        self.children: list[Any] = []

    def setObjectName(self, object_name: str) -> None:
        self.object_name = object_name


class FakeLabel(FakeWidget):
    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.text = text
        self.word_wrap = False

    def setWordWrap(self, enabled: bool) -> None:
        self.word_wrap = enabled


class FakePushButton(FakeLabel):
    def __init__(self, text: str = "") -> None:
        super().__init__(text)
        self.clicked = FakeSignal()
        self.tooltip = ""

    def setToolTip(self, text: str) -> None:
        self.tooltip = text


class FakeTableWidgetItem:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeTableWidget(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.column_count = 0
        self.row_count = 0
        self.headers: list[str] = []
        self.sorting_enabled = False
        self.items: dict[tuple[int, int], FakeTableWidgetItem] = {}
        self.current_row = -1
        self.selection_model = FakeSelectionModel()

    def setColumnCount(self, count: int) -> None:
        self.column_count = count

    def setRowCount(self, count: int) -> None:
        self.row_count = count

    def setHorizontalHeaderLabels(self, headers: list[str]) -> None:
        self.headers = headers

    def setSortingEnabled(self, enabled: bool) -> None:
        self.sorting_enabled = enabled

    def setItem(self, row: int, column: int, item: FakeTableWidgetItem) -> None:
        self.items[(row, column)] = item

    def currentRow(self) -> int:
        return self.current_row

    def selectionModel(self) -> FakeSelectionModel:
        return self.selection_model


class FakeSelectionModel:
    def __init__(self) -> None:
        self.selectionChanged = FakeSignal()


class FakeVBoxLayout:
    def __init__(self, parent: FakeWidget) -> None:
        self.parent = parent

    def setContentsMargins(self, left: int, top: int, right: int, bottom: int) -> None:
        _ = (left, top, right, bottom)

    def setSpacing(self, spacing: int) -> None:
        _ = spacing

    def addWidget(self, widget: Any, stretch: Optional[int] = None) -> None:
        self.parent.children.append(widget)
        _ = stretch


class FakeHBoxLayout(FakeVBoxLayout):
    pass


class FakeQtWidgets:
    QWidget = FakeWidget
    QLabel = FakeLabel
    QPushButton = FakePushButton
    QTableWidget = FakeTableWidget
    QTableWidgetItem = FakeTableWidgetItem
    QVBoxLayout = FakeVBoxLayout
    QHBoxLayout = FakeHBoxLayout


def _failed_result():
    from shader_health.core import RuleResult

    return RuleResult(
        rule_id="common.texture.colorspace.data_raw",
        severity="critical",
        status="failed",
        title="Data textures must use Raw color space",
        message="Data texture uses color space.",
        why="Data textures must not be color transformed.",
        owner="shader_td",
        target_kind="node",
        target_id="node:file1",
        node="file1",
        plug="colorSpace",
        current_value="ACEScg",
        expected_value="Raw",
        block_publish=True,
        block_deadline=True,
        auto_fix_available=True,
        fix_id="set_attr",
    )


def test_waiver_rows_from_records_marks_expired_entries():
    active = create_waiver_from_result(
        _failed_result(),
        reason="Approved.",
        approved_by="lead",
        created_at_utc="2026-07-02T08:00:00Z",
        expires_at_utc="2026-08-02T08:00:00Z",
    )
    expired = create_waiver_from_result(
        _failed_result(),
        reason="Old approval.",
        approved_by="supervisor",
        created_at_utc="2026-06-01T08:00:00Z",
        expires_at_utc="2026-06-15T08:00:00Z",
    )

    rows = waiver_manager.waiver_rows_from_records(
        (active, expired),
        now_utc="2026-07-03T08:00:00Z",
    )

    assert rows[0].status == "active"
    assert rows[1].status == "expired"
    assert "expired" in waiver_manager.waiver_summary_text(rows)


def test_populate_waiver_table_writes_status_and_rule_columns():
    rows = (
        waiver_manager.WaiverTableRow(
            waiver_id="waiver:test",
            status="expired",
            rule_id="common.texture.missing",
            target="node:file1",
            approved_by="lead",
            expires_at_utc="2026-06-15T08:00:00Z",
        ),
    )
    table = FakeTableWidget()

    waiver_manager.populate_waiver_table(FakeQtWidgets, table, rows)

    assert table.row_count == 1
    assert table.items[(0, 0)].text == "expired (ignored)"
    assert table.items[(0, 1)].text == "common.texture.missing"


def test_waiver_manager_callbacks_fire_refresh_revoke_and_make_waive(
    tmp_path: Path,
    monkeypatch: Any,
):
    calls: list[str] = []
    callbacks = waiver_manager.WaiverManagerCallbacks(
        on_refresh=lambda: calls.append("refresh"),
        on_revoke_selected=lambda: calls.append("revoke"),
        on_make_waive=lambda: calls.append("make_waive"),
    )

    widget = waiver_manager.build_waiver_manager(FakeQtWidgets, callbacks=callbacks)

    _find(widget, waiver_manager.WAIVER_MAKE_WAIVE_BUTTON_OBJECT_NAME).clicked.emit()
    _find(widget, waiver_manager.WAIVER_REFRESH_BUTTON_OBJECT_NAME).clicked.emit()
    _find(widget, waiver_manager.WAIVER_REVOKE_BUTTON_OBJECT_NAME).clicked.emit()

    assert calls == ["make_waive", "refresh", "revoke"]


def test_revoke_waiver_action_updates_sidecar(tmp_path: Path, monkeypatch: Any):
    scene_path = tmp_path / "hero.ma"
    scene_path.write_text("//Maya ASCII", encoding="utf-8")
    sidecar_path = tmp_path / "hero.shader_health_waivers.json"
    waiver = create_waiver_from_result(
        _failed_result(),
        reason="Approved.",
        approved_by="lead",
        created_at_utc="2026-07-02T08:00:00Z",
        expires_at_utc="2026-08-02T08:00:00Z",
    )
    from shader_health.core.waivers import (
        WaiverSidecar,
        load_waiver_sidecar_optional,
        write_waiver_sidecar,
    )

    write_waiver_sidecar(sidecar_path, WaiverSidecar((waiver,)))
    monkeypatch.setattr(commands, "_current_scene_path", lambda: str(scene_path))

    result = commands.revoke_waiver_action(waiver.id)

    assert result.succeeded is True
    loaded = load_waiver_sidecar_optional(sidecar_path)
    assert loaded.waivers == ()


def _find(widget: Any, object_name: str) -> Any:
    stack = [widget]
    while stack:
        current = stack.pop()
        if getattr(current, "object_name", None) == object_name:
            return current
        stack.extend(getattr(current, "children", []))
    raise AssertionError(f"Could not find object named {object_name!r}")
