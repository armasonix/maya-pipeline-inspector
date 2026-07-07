from __future__ import annotations

from typing import Any

from shader_health.ui.fix_queue import (
    FIX_QUEUE_TABLE_OBJECT_NAME,
    FixQueueRow,
    allows_batch_risky_confirmation,
    confirm_risky_fixes,
    risky_confirmation_text,
    risky_fix_rows,
    update_risky_confirmation_label,
)


def _high_risk_row(
    *,
    selected: bool = True,
    target_node: str = "file1",
    fix_id: str = "",
) -> FixQueueRow:
    resolved_fix_id = fix_id or f"common.displacement.amount.max:{target_node}:disable_feature"
    return FixQueueRow(
        selected=selected,
        title="Disable displacement",
        risk="high",
        target_node=target_node,
        target_attr="displacement",
        before_value="True",
        after_value="False",
        fix_id=resolved_fix_id,
        requires_confirmation=True,
    )


def _supervisor_row() -> FixQueueRow:
    return FixQueueRow(
        selected=True,
        title="Supervisor relink",
        risk="medium",
        target_node="file2",
        target_attr="fileTextureName",
        before_value="v001",
        after_value="v003",
        requires_confirmation=True,
    )


class FakeStandardButton:
    Yes = 1
    No = 0


class FakeMessageBox:
    StandardButton = FakeStandardButton
    Yes = 1
    No = 0
    calls: list[tuple[str, str]] = []
    responses: list[int] = []

    @classmethod
    def warning(cls, _parent, title: str, message: str, *_args, **_kwargs) -> int:
        cls.calls.append((title, message))
        if cls.responses:
            return cls.responses.pop(0)
        return cls.No

    @classmethod
    def reset(cls) -> None:
        cls.calls.clear()
        cls.responses.clear()


class FakeQtWidgets:
    QMessageBox = FakeMessageBox


class FakeLabel:
    def __init__(self) -> None:
        self.text = ""

    def setText(self, value: str) -> None:
        self.text = value


def test_allows_batch_risky_confirmation_only_for_supervisor_full():
    assert allows_batch_risky_confirmation("supervisor_full") is True
    assert allows_batch_risky_confirmation("artist_relaxed") is False
    assert allows_batch_risky_confirmation("publish_strict") is False


def test_risky_confirmation_text_counts_pending_and_selected():
    rows = (
        _high_risk_row(selected=False),
        FixQueueRow(
            selected=True,
            title="Low",
            risk="low",
            target_node="file3",
            target_attr="colorSpace",
            before_value="sRGB",
            after_value="Raw",
        ),
    )

    assert risky_confirmation_text(rows) == "Risky fixes require confirmation: 1 pending."
    assert (
        risky_confirmation_text(rows, selected_rows=rows)
        == "Risky fixes require confirmation: 1 pending, 1 selected."
    )


def test_update_risky_confirmation_label_refreshes_helper_text():
    label = FakeLabel()
    rows = (_high_risk_row(selected=True),)

    update_risky_confirmation_label(label, rows, selected_rows=rows)

    assert label.text == "Risky fixes require confirmation: 1 pending, 1 selected."


def test_confirm_risky_fixes_returns_true_when_no_risky_rows():
    FakeMessageBox.reset()

    assert confirm_risky_fixes(FakeQtWidgets, ()) is True
    assert FakeMessageBox.calls == []


def test_confirm_risky_fixes_cancel_returns_false_without_extra_dialogs():
    FakeMessageBox.reset()
    FakeMessageBox.responses = [FakeMessageBox.No]

    confirmed = confirm_risky_fixes(
        FakeQtWidgets,
        (_high_risk_row(),),
        profile_id="artist_relaxed",
    )

    assert confirmed is False
    assert len(FakeMessageBox.calls) == 1
    assert FakeMessageBox.calls[0][0] == "Confirm Risky Fix"
    assert "risk=high" in FakeMessageBox.calls[0][1]
    assert "file1.displacement: True -> False" in FakeMessageBox.calls[0][1]


def test_confirm_risky_fixes_per_fix_requires_all_confirmations():
    FakeMessageBox.reset()
    FakeMessageBox.responses = [FakeMessageBox.Yes, FakeMessageBox.No]

    confirmed = confirm_risky_fixes(
        FakeQtWidgets,
        (_high_risk_row(target_node="file1"), _high_risk_row(target_node="file2")),
        profile_id="publish_strict",
    )

    assert confirmed is False
    assert len(FakeMessageBox.calls) == 2
    assert all(title == "Confirm Risky Fix" for title, _ in FakeMessageBox.calls)


def test_confirm_risky_fixes_supervisor_full_uses_single_batch_dialog():
    FakeMessageBox.reset()
    FakeMessageBox.responses = [FakeMessageBox.Yes]

    confirmed = confirm_risky_fixes(
        FakeQtWidgets,
        (_high_risk_row(target_node="file1"), _high_risk_row(target_node="file2")),
        profile_id="supervisor_full",
    )

    assert confirmed is True
    assert len(FakeMessageBox.calls) == 1
    title, message = FakeMessageBox.calls[0]
    assert title == "Confirm Risky Fixes"
    assert "Apply 2 high-risk fix(es)?" in message
    assert "file1.displacement" in message
    assert "file2.displacement" in message


def test_risky_fix_summary_includes_supervisor_flag_for_non_high_risk():
    FakeMessageBox.reset()
    FakeMessageBox.responses = [FakeMessageBox.Yes]

    confirm_risky_fixes(FakeQtWidgets, (_supervisor_row(),), profile_id="artist_relaxed")

    _, message = FakeMessageBox.calls[0]
    assert "risk=medium, supervisor" in message


def test_risky_fix_rows_includes_requires_confirmation_medium_risk():
    rows = (_supervisor_row(),)

    assert len(risky_fix_rows(rows)) == 1


def test_apply_selected_fixes_cancel_skips_apply(monkeypatch):
    from types import SimpleNamespace

    from shader_health.maya import ui_launcher
    from shader_health.ui.fix_queue import FIX_QUEUE_TABLE_OBJECT_NAME

    apply_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def fake_apply(*args, **kwargs):
        apply_calls.append((args, kwargs))
        return SimpleNamespace(applied_count=1)

    monkeypatch.setattr(
        "shader_health.maya.fix_applier.apply_fix_actions",
        fake_apply,
    )
    monkeypatch.setattr(ui_launcher, "confirm_risky_fixes", lambda *_a, **_k: False)

    class FakeItem:
        def text(self) -> str:
            return "YES"

    class FakeTable:
        def item(self, _row: int, _column: int):
            return FakeItem()

    class FakeLabel:
        def __init__(self) -> None:
            self.text = ""

        def setText(self, value: str) -> None:
            self.text = value

    description_label = FakeLabel()
    content = SimpleNamespace(
        _shader_health_fix_plan=SimpleNamespace(
            actions=(
                SimpleNamespace(
                    fix_id="common.displacement.amount.max:file1:disable_feature",
                    target_node="file1",
                    target_attr="displacement",
                    before_value=True,
                    after_value=False,
                ),
            )
        ),
        _shader_health_fix_rows=(
            _high_risk_row(),
        ),
        _shader_health_profile_id="artist_relaxed",
    )

    def fake_find_child(_content, _widget_type, object_name: str):
        if object_name == FIX_QUEUE_TABLE_OBJECT_NAME:
            return FakeTable()
        if object_name == "shaderHealthInspectorDescription":
            return description_label
        return None

    monkeypatch.setattr(ui_launcher, "_find_child", fake_find_child)
    monkeypatch.setattr(ui_launcher, "_persist_fix_apply_audit", lambda *_a: None)
    monkeypatch.setattr(ui_launcher, "_revalidate_with_current_scope", lambda *_a: None)

    class FakeQtWidgets:
        QWidget = object
        QTableWidget = object
        QLabel = object

    ui_launcher._apply_selected_fixes_from_ui(content, FakeQtWidgets())

    assert apply_calls == []
    assert description_label.text == "High-risk fixes were not applied."
