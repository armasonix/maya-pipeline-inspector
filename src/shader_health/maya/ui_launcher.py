"""Maya dockable panel launcher."""
from __future__ import annotations

from typing import Any, Optional

from shader_health.ui import main_window
from shader_health.ui.qt import load_qt_widgets

WORKSPACE_CONTROL_NAME = f"{main_window.PANEL_OBJECT_NAME}WorkspaceControl"
DEFAULT_DOCK_AREA = "right"

_PANEL: Optional[Any] = None


def show_panel() -> Any:
    """Open or restore the dockable Maya Shader Health Inspector panel."""

    global _PANEL
    cmds = _maya_cmds()

    if _workspace_control_exists(cmds):
        if _PANEL is not None:
            cmds.workspaceControl(WORKSPACE_CONTROL_NAME, edit=True, restore=True)
            _PANEL.show()
            return _PANEL
        cmds.deleteUI(WORKSPACE_CONTROL_NAME, control=True)

    panel = _create_dockable_panel()
    _PANEL = panel
    panel.show(
        dockable=True,
        area=DEFAULT_DOCK_AREA,
        floating=False,
        retain=False,
    )
    return panel


def close_panel(*, delete: bool = True) -> None:
    """Close the dockable panel and optionally delete its Maya workspaceControl."""

    global _PANEL
    cmds = _maya_cmds()

    if _workspace_control_exists(cmds):
        if delete:
            cmds.deleteUI(WORKSPACE_CONTROL_NAME, control=True)
        else:
            cmds.workspaceControl(WORKSPACE_CONTROL_NAME, edit=True, close=True)

    if _PANEL is not None:
        _PANEL.close()
    _PANEL = None


def _create_dockable_panel() -> Any:
    qt_widgets = load_qt_widgets()
    from maya.app.general.mayaMixin import (  # type: ignore[import-not-found]
        MayaQWidgetDockableMixin,
    )

    def init_panel(self: Any) -> None:
        super(type(self), self).__init__()
        self.setObjectName(main_window.PANEL_OBJECT_NAME)
        self.setWindowTitle(main_window.PANEL_TITLE)

        layout = qt_widgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        content = main_window.build_main_widget(
            qt_widgets,
            export_callbacks=_export_action_callbacks(),
        )
        _wire_validate_scene(content, qt_widgets)
        layout.addWidget(content)

    panel_class = type(
        "ShaderHealthInspectorDock",
        (MayaQWidgetDockableMixin, qt_widgets.QWidget),
        {"__init__": init_panel, "__module__": __name__},
    )
    return panel_class()


def _export_action_callbacks() -> main_window.ExportActionCallbacks:
    return main_window.ExportActionCallbacks(
        on_export_json=_export_json_from_ui,
        on_export_html=_export_html_from_ui,
        on_export_manifest=_export_manifest_from_ui,
    )


def _export_json_from_ui() -> None:
    from shader_health.maya.commands import export_json_report_action

    _print_export_result(export_json_report_action())


def _export_html_from_ui() -> None:
    from shader_health.maya.commands import export_html_report_action

    _print_export_result(export_html_report_action())


def _export_manifest_from_ui() -> None:
    from shader_health.maya.commands import export_shader_manifest_action

    _print_export_result(export_shader_manifest_action())


def _wire_validate_scene(content: Any, qt_widgets: Any) -> None:
    button = _find_child(
        content,
        qt_widgets.QPushButton,
        "shaderHealthInspectorValidateSceneButton",
    )
    if button is None:
        return
    button.setEnabled(True)
    button.setToolTip("Scan and validate the current Maya scene.")
    clicked = getattr(button, "clicked", None)
    connect = getattr(clicked, "connect", None)
    if connect is not None:
        connect(lambda *_: _validate_scene_from_ui(content, qt_widgets))


def _validate_scene_from_ui(content: Any, qt_widgets: Any) -> None:
    try:
        from shader_health.maya.commands import validate_scene_action

        result = validate_scene_action()
    except Exception as exc:  # noqa: BLE001
        message = f"Validation failed: {exc}"
        _set_label_text(
            content,
            qt_widgets,
            "shaderHealthInspectorDescription",
            message,
        )
        print(message)
        return

    _populate_validation_result(content, qt_widgets, result)
    print(result.message)


def _populate_validation_result(content: Any, qt_widgets: Any, result: Any) -> None:
    health = result.health_score
    _set_label_text(
        content,
        qt_widgets,
        main_window.HEALTH_SCORE_LABEL_OBJECT_NAME,
        f"Health: {health.score} / 100",
    )
    _set_label_text(
        content,
        qt_widgets,
        main_window.SEVERITY_COUNTS_LABEL_OBJECT_NAME,
        (
            f"Critical: {health.critical}   "
            f"Error: {health.error}   "
            f"Warning: {health.warning}   "
            f"Info: {health.info}"
        ),
    )
    _set_label_text(
        content,
        qt_widgets,
        main_window.BLOCK_STATUS_LABEL_OBJECT_NAME,
        (
            f"Publish Block: {_yes_no(health.block_publish)}   "
            f"Deadline Block: {_yes_no(health.block_deadline)}"
        ),
    )
    _set_label_text(content, qt_widgets, "shaderHealthInspectorDescription", result.message)

    failed_results = tuple(item for item in result.results if item.status == "failed")
    rows = tuple(_issue_row_from_result(item) for item in failed_results)
    table = _find_child(content, qt_widgets.QTableWidget, main_window.ISSUES_TABLE_OBJECT_NAME)
    if table is not None:
        table.setSortingEnabled(False)
        main_window.populate_issues_table(qt_widgets, table, rows)
        table.setSortingEnabled(True)

    _populate_first_issue_details(content, qt_widgets, failed_results)


def _issue_row_from_result(result: Any) -> main_window.IssueTableRow:
    return main_window.IssueTableRow(
        severity=str(result.severity),
        material=str(result.material or ""),
        node=str(result.node or ""),
        issue=str(result.message or result.title),
        owner=str(result.owner),
        rule=str(result.rule_id),
    )


def _populate_first_issue_details(
    content: Any,
    qt_widgets: Any,
    failed_results: tuple[Any, ...],
) -> None:
    if not failed_results:
        state = main_window.IssueDetailsState(
            message="No failed issues found",
            why="The current scene passed the active validation rules.",
            current_value="N/A",
            expected_value="N/A",
            graph_trace="N/A",
            fix_available=False,
            fix_description="No safe fix selected.",
        )
    else:
        first = failed_results[0]
        state = main_window.IssueDetailsState(
            message=str(first.message),
            why=str(first.why),
            current_value=str(first.current_value),
            expected_value=str(first.expected_value),
            graph_trace=" -> ".join(str(item) for item in first.graph_trace) or "N/A",
            fix_available=bool(first.auto_fix_available),
            fix_description=str(first.fix_id or "No safe fix selected."),
        )

    _set_label_text(
        content,
        qt_widgets,
        main_window.DETAILS_MESSAGE_LABEL_OBJECT_NAME,
        f"Message: {state.message}",
    )
    _set_label_text(
        content,
        qt_widgets,
        main_window.DETAILS_WHY_LABEL_OBJECT_NAME,
        f"Why: {state.why}",
    )
    _set_label_text(
        content,
        qt_widgets,
        main_window.DETAILS_VALUES_LABEL_OBJECT_NAME,
        f"Current: {state.current_value}   Expected: {state.expected_value}",
    )
    _set_label_text(
        content,
        qt_widgets,
        main_window.DETAILS_GRAPH_TRACE_LABEL_OBJECT_NAME,
        f"Graph Trace: {state.graph_trace}",
    )
    _set_label_text(
        content,
        qt_widgets,
        main_window.DETAILS_FIX_LABEL_OBJECT_NAME,
        f"Fix Available: {_yes_no(state.fix_available)}   {state.fix_description}",
    )


def _find_child(content: Any, widget_type: Any, object_name: str) -> Any:
    finder = getattr(content, "findChild", None)
    if finder is None:
        return None
    return finder(widget_type, object_name)


def _set_label_text(content: Any, qt_widgets: Any, object_name: str, text: str) -> None:
    label = _find_child(content, qt_widgets.QLabel, object_name)
    if label is not None:
        label.setText(text)


def _yes_no(value: bool) -> str:
    return "YES" if value else "NO"


def _print_export_result(result: Any) -> None:
    print(f"{result.message} {result.path}")


def _workspace_control_exists(cmds: Any) -> bool:
    return bool(cmds.workspaceControl(WORKSPACE_CONTROL_NAME, query=True, exists=True))


def _maya_cmds() -> Any:
    try:
        from maya import cmds  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("Maya UI can only be launched inside Autodesk Maya.") from exc
    return cmds
