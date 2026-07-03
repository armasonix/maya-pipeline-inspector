"""Maya dockable panel launcher."""
from __future__ import annotations

from typing import Any, Optional

from shader_health.ui import main_window
from shader_health.ui.fix_queue import (
    FIX_QUEUE_TABLE_OBJECT_NAME,
    FixQueueRow,
    fix_rows_from_table,
    populate_fix_queue,
    safe_fix_rows,
    selected_fix_rows,
)
from shader_health.ui.qt import load_qt_widgets

WORKSPACE_CONTROL_NAME = f"{main_window.PANEL_OBJECT_NAME}WorkspaceControl"
DEFAULT_DOCK_AREA = "right"

_PANEL: Optional[Any] = None
_SCRIPT_JOBS: list[int] = []


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
    _kill_script_jobs()
    _PANEL = None


def _create_dockable_panel() -> Any:
    _kill_script_jobs()
    qt_widgets = load_qt_widgets()
    from maya.app.general.mayaMixin import (  # type: ignore[import-not-found]
        MayaQWidgetDockableMixin,
    )

    panel_state: dict[str, Any] = {"content": None}

    def init_panel(self: Any) -> None:
        super(type(self), self).__init__()
        self.setObjectName(main_window.PANEL_OBJECT_NAME)
        self.setWindowTitle(main_window.PANEL_TITLE)

        layout = qt_widgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        content = main_window.build_main_widget(
            qt_widgets,
            export_callbacks=_export_action_callbacks(),
            validation_callbacks=_validation_action_callbacks(panel_state, qt_widgets),
            issue_details_callbacks=_issue_details_action_callbacks(panel_state, qt_widgets),
        )
        panel_state["content"] = content
        _wire_issues_table_interactions(content, qt_widgets)
        _wire_fix_queue_actions(content, qt_widgets)
        _wire_scene_change_reset(content, qt_widgets)
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


def _panel_content(panel_state: dict[str, Any]) -> Any:
    content = panel_state.get("content")
    if content is None:
        raise RuntimeError("Shader Health panel content is not initialized.")
    return content


def _validation_action_callbacks(
    panel_state: dict[str, Any],
    qt_widgets: Any,
) -> main_window.ValidationActionCallbacks:
    return main_window.ValidationActionCallbacks(
        on_validate_scene=lambda: _validate_from_ui(
            _panel_content(panel_state),
            qt_widgets,
            scan_scope="scene",
        ),
        on_validate_selection=lambda: _validate_from_ui(
            _panel_content(panel_state),
            qt_widgets,
            scan_scope="selection",
        ),
        on_profile_changed=lambda: _revalidate_with_current_scope(
            _panel_content(panel_state),
            qt_widgets,
        ),
    )


def _issue_details_action_callbacks(
    panel_state: dict[str, Any],
    qt_widgets: Any,
) -> main_window.IssueDetailsActionCallbacks:
    return main_window.IssueDetailsActionCallbacks(
        on_select_node=lambda: _run_navigation_action(
            _panel_content(panel_state),
            qt_widgets,
            "select_node",
        ),
        on_open_in_hypershade=lambda: _run_navigation_action(
            _panel_content(panel_state),
            qt_widgets,
            "open_in_hypershade",
        ),
        on_copy_path=lambda: _run_navigation_action(
            _panel_content(panel_state),
            qt_widgets,
            "copy_path",
        ),
        on_reveal_file=lambda: _run_navigation_action(
            _panel_content(panel_state),
            qt_widgets,
            "reveal_file",
        ),
        on_waive_issue=lambda: _waive_selected_issue_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
    )


def _validate_from_ui(content: Any, qt_widgets: Any, *, scan_scope: str) -> None:
    try:
        from shader_health.maya.commands import validate_scene_action, validate_selection_action

        profile_id = _selected_profile_id(content, qt_widgets)
        if scan_scope == "selection":
            result = validate_selection_action(profile_id=profile_id)
        else:
            result = validate_scene_action(profile_id=profile_id)
    except Exception as exc:  # noqa: BLE001
        message = f"Validation failed: {exc}"
        _set_label_text(content, qt_widgets, "shaderHealthInspectorDescription", message)
        print(message)
        return

    if not getattr(result, "succeeded", True):
        _reset_panel_state(content, qt_widgets, status_message=result.message)
        print(result.message)
        return

    content._shader_health_scan_scope = scan_scope
    _populate_validation_result(content, qt_widgets, result)
    print(result.message)


def _revalidate_with_current_scope(content: Any, qt_widgets: Any) -> None:
    scan_scope = getattr(content, "_shader_health_scan_scope", "scene")
    if getattr(content, "_shader_health_failed_results", ()):
        _validate_from_ui(content, qt_widgets, scan_scope=scan_scope)


def _selected_profile_id(content: Any, qt_widgets: Any) -> str:
    profile_dropdown = _find_child(
        content,
        qt_widgets.QComboBox,
        main_window.PROFILE_DROPDOWN_OBJECT_NAME,
    )
    if profile_dropdown is None:
        return "artist_relaxed"
    current_text = getattr(profile_dropdown, "currentText", lambda: "artist_relaxed")()
    return str(current_text or "artist_relaxed")


def _selected_issue(content: Any) -> Any:
    return getattr(content, "_shader_health_selected_issue", None)


def _run_navigation_action(content: Any, qt_widgets: Any, action: str) -> None:
    from shader_health.maya import commands

    issue = _selected_issue(content)
    if issue is None:
        return
    try:
        if action == "select_node":
            result = commands.select_node_action(str(issue.node or ""))
        elif action == "open_in_hypershade":
            result = commands.open_in_hypershade_action(
                str(issue.node or ""),
                material_name=str(getattr(issue, "material", "") or "") or None,
            )
        elif action == "copy_path":
            result = commands.copy_path_action(_issue_path(issue))
        elif action == "reveal_file":
            result = commands.reveal_file_action(_issue_path(issue))
        else:
            return
    except Exception as exc:  # noqa: BLE001
        _set_label_text(content, qt_widgets, "shaderHealthInspectorDescription", str(exc))
        return
    _set_label_text(content, qt_widgets, "shaderHealthInspectorDescription", result.message)


def _issue_path(issue: Any) -> str:
    evidence = getattr(issue, "evidence", {}) or {}
    for key in ("resolved_path", "raw_path", "path"):
        value = evidence.get(key)
        if value:
            return str(value)
    current_value = getattr(issue, "current_value", "")
    if isinstance(current_value, str) and ("/" in current_value or "\\" in current_value):
        return current_value
    raise ValueError("Selected issue does not expose a filesystem path.")


def _waive_selected_issue_from_ui(content: Any, qt_widgets: Any) -> None:
    from shader_health.maya import commands

    issue = _selected_issue(content)
    if issue is None:
        return
    try:
        result = commands.waive_issue_action(
            issue,
            reason="Approved from Maya Shader Health Inspector UI.",
        )
    except Exception as exc:  # noqa: BLE001
        _set_label_text(content, qt_widgets, "shaderHealthInspectorDescription", str(exc))
        return
    _set_label_text(content, qt_widgets, "shaderHealthInspectorDescription", result.message)
    _revalidate_with_current_scope(content, qt_widgets)


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
        _store_validation_state(content, failed_results, rows, result)

    _update_severity_filter_options(content, qt_widgets, rows)
    _update_owner_filter_options(content, qt_widgets, rows)
    _refresh_issues_table_view(content, qt_widgets)

    display_results = getattr(
        content,
        "_shader_health_display_failed_results",
        failed_results,
    )
    _populate_first_issue_details(content, qt_widgets, display_results)


def _update_severity_filter_options(
    content: Any,
    qt_widgets: Any,
    rows: tuple[main_window.IssueTableRow, ...],
) -> None:
    severity_filter = _find_child(
        content,
        qt_widgets.QComboBox,
        main_window.ISSUES_SEVERITY_FILTER_OBJECT_NAME,
    )
    if severity_filter is None:
        return

    block_signals = getattr(severity_filter, "blockSignals", None)
    if block_signals is not None:
        block_signals(True)
    try:
        options = list(main_window.severity_filter_options(rows))
        clear = getattr(severity_filter, "clear", None)
        if clear is not None:
            clear()
        add_items = getattr(severity_filter, "addItems", None)
        if add_items is not None:
            add_items(options)
        set_current = getattr(severity_filter, "setCurrentText", None)
        if set_current is not None and options:
            set_current(options[0])
    finally:
        if block_signals is not None:
            block_signals(False)


def _update_owner_filter_options(
    content: Any,
    qt_widgets: Any,
    rows: tuple[main_window.IssueTableRow, ...],
) -> None:
    owner_filter = _find_child(
        content,
        qt_widgets.QComboBox,
        main_window.ISSUES_OWNER_FILTER_OBJECT_NAME,
    )
    if owner_filter is None:
        return

    block_signals = getattr(owner_filter, "blockSignals", None)
    if block_signals is not None:
        block_signals(True)
    try:
        options = list(main_window.owner_filter_options(rows))
        clear = getattr(owner_filter, "clear", None)
        if clear is not None:
            clear()
        add_items = getattr(owner_filter, "addItems", None)
        if add_items is not None:
            add_items(options)
        set_current = getattr(owner_filter, "setCurrentText", None)
        if set_current is not None and options:
            set_current(options[0])
    finally:
        if block_signals is not None:
            block_signals(False)


def _store_validation_state(
    content: Any,
    failed_results: tuple[Any, ...],
    rows: tuple[main_window.IssueTableRow, ...],
    result: Any,
) -> None:
    content._shader_health_failed_results = failed_results
    content._shader_health_issue_rows = rows
    content._shader_health_fix_plan = getattr(result, "fix_plan", None)
    _populate_fix_queue(content, result)


def _populate_fix_queue(content: Any, result: Any) -> None:
    fix_plan = getattr(result, "fix_plan", None)
    actions = getattr(fix_plan, "actions", ())
    fix_rows = tuple(
        FixQueueRow(
            selected=False,
            title=action.title,
            risk=action.risk,
            target_node=action.target_node,
            target_attr=str(action.target_attr or ""),
            before_value=str(action.before_value),
            after_value=str(action.after_value),
            blocked=action.blocked,
            requires_confirmation=action.risk == "high" or action.requires_supervisor,
        )
        for action in actions
    )
    content._shader_health_fix_rows = fix_rows
    qt_widgets = load_qt_widgets()
    table = _find_child(content, qt_widgets.QTableWidget, FIX_QUEUE_TABLE_OBJECT_NAME)
    if table is not None:
        populate_fix_queue(qt_widgets, table, fix_rows)


def _wire_issues_table_interactions(content: Any, qt_widgets: Any) -> None:
    table = _find_child(content, qt_widgets.QTableWidget, main_window.ISSUES_TABLE_OBJECT_NAME)
    severity_filter = _find_child(
        content,
        qt_widgets.QComboBox,
        main_window.ISSUES_SEVERITY_FILTER_OBJECT_NAME,
    )
    sort_dropdown = _find_child(
        content,
        qt_widgets.QComboBox,
        main_window.ISSUES_SORT_DROPDOWN_OBJECT_NAME,
    )
    owner_filter = _find_child(
        content,
        qt_widgets.QComboBox,
        main_window.ISSUES_OWNER_FILTER_OBJECT_NAME,
    )
    view_filter = _find_child(
        content,
        qt_widgets.QComboBox,
        main_window.ISSUES_VIEW_FILTER_OBJECT_NAME,
    )
    if table is not None:
        selection_model = getattr(table, "selectionModel", lambda: None)()
        selection_changed = getattr(selection_model, "selectionChanged", None)
        connect = getattr(selection_changed, "connect", None)
        if connect is not None:
            connect(lambda *_: _on_issue_row_selected(content, qt_widgets))
    if severity_filter is not None:
        current_text_changed = getattr(severity_filter, "currentTextChanged", None)
        connect = getattr(current_text_changed, "connect", None)
        if connect is not None:
            connect(lambda *_: _refresh_issues_table_view(content, qt_widgets))
    if sort_dropdown is not None:
        current_text_changed = getattr(sort_dropdown, "currentTextChanged", None)
        connect = getattr(current_text_changed, "connect", None)
        if connect is not None:
            connect(lambda *_: _refresh_issues_table_view(content, qt_widgets))
    if owner_filter is not None:
        current_text_changed = getattr(owner_filter, "currentTextChanged", None)
        connect = getattr(current_text_changed, "connect", None)
        if connect is not None:
            connect(lambda *_: _refresh_issues_table_view(content, qt_widgets))
    if view_filter is not None:
        current_text_changed = getattr(view_filter, "currentTextChanged", None)
        connect = getattr(current_text_changed, "connect", None)
        if connect is not None:
            connect(lambda *_: _refresh_issues_table_view(content, qt_widgets))


def _wire_fix_queue_actions(content: Any, qt_widgets: Any) -> None:
    table = _find_child(content, qt_widgets.QTableWidget, FIX_QUEUE_TABLE_OBJECT_NAME)
    apply_selected = _find_child(
        content,
        qt_widgets.QPushButton,
        "shaderHealthInspectorApplySelectedFixesButton",
    )
    apply_safe = _find_child(
        content,
        qt_widgets.QPushButton,
        "shaderHealthInspectorApplySafeFixesButton",
    )
    if table is not None:
        cell_clicked = getattr(table, "cellClicked", None)
        connect = getattr(cell_clicked, "connect", None)
        if connect is not None:
            connect(
                lambda row, column: _on_fix_queue_cell_clicked(
                    content,
                    qt_widgets,
                    int(row),
                    int(column),
                ),
            )
    if apply_selected is not None:
        clicked = getattr(apply_selected, "clicked", None)
        connect = getattr(clicked, "connect", None)
        if connect is not None:
            connect(lambda *_: _apply_selected_fixes_from_ui(content, qt_widgets))
    if apply_safe is not None:
        clicked = getattr(apply_safe, "clicked", None)
        connect = getattr(clicked, "connect", None)
        if connect is not None:
            connect(lambda *_: _apply_safe_fixes_from_ui(content, qt_widgets))


def _on_fix_queue_cell_clicked(
    content: Any,
    qt_widgets: Any,
    row: int,
    column: int,
) -> None:
    if column != 0:
        return
    from shader_health.ui.fix_queue import toggle_selected_table_item

    table = _find_child(content, qt_widgets.QTableWidget, FIX_QUEUE_TABLE_OBJECT_NAME)
    stored_rows = getattr(content, "_shader_health_fix_rows", ())
    if table is None or not stored_rows or row < 0 or row >= len(stored_rows):
        return
    item = table.item(row, 0)
    if item is None:
        return
    toggle_selected_table_item(item)
    _sync_fix_queue_selection(content, qt_widgets)


def _sync_fix_queue_selection(content: Any, qt_widgets: Any) -> None:
    table = _find_child(content, qt_widgets.QTableWidget, FIX_QUEUE_TABLE_OBJECT_NAME)
    stored_rows = getattr(content, "_shader_health_fix_rows", ())
    if table is None or not stored_rows:
        return
    content._shader_health_fix_rows = fix_rows_from_table(table, stored_rows)


def _apply_selected_fixes_from_ui(content: Any, qt_widgets: Any) -> None:
    from shader_health.maya.fix_applier import apply_fix_actions

    fix_plan = getattr(content, "_shader_health_fix_plan", None)
    table = _find_child(content, qt_widgets.QTableWidget, FIX_QUEUE_TABLE_OBJECT_NAME)
    stored_rows = getattr(content, "_shader_health_fix_rows", ())
    if fix_plan is None or not stored_rows or table is None:
        return
    fix_rows = fix_rows_from_table(table, stored_rows)
    content._shader_health_fix_rows = fix_rows
    selected = selected_fix_rows(fix_rows)
    if not selected:
        _set_label_text(
            content,
            qt_widgets,
            "shaderHealthInspectorDescription",
            "No fixes selected. Check rows in the Safe Auto-Fix Queue first.",
        )
        return
    selected_ids = {
        (row.target_node, row.target_attr, row.before_value, row.after_value)
        for row in selected
    }
    actions = tuple(
        action
        for action in fix_plan.actions
        if (
            action.target_node,
            str(action.target_attr or ""),
            str(action.before_value),
            str(action.after_value),
        )
        in selected_ids
    )
    report = apply_fix_actions(actions)
    _set_label_text(
        content,
        qt_widgets,
        "shaderHealthInspectorDescription",
        f"Applied {report.applied_count} selected fix(es).",
    )
    _revalidate_with_current_scope(content, qt_widgets)


def _apply_safe_fixes_from_ui(content: Any, qt_widgets: Any) -> None:
    from shader_health.maya.fix_applier import apply_fix_actions

    fix_plan = getattr(content, "_shader_health_fix_plan", None)
    table = _find_child(content, qt_widgets.QTableWidget, FIX_QUEUE_TABLE_OBJECT_NAME)
    stored_rows = getattr(content, "_shader_health_fix_rows", ())
    if fix_plan is None or not stored_rows or table is None:
        return
    fix_rows = fix_rows_from_table(table, stored_rows)
    content._shader_health_fix_rows = fix_rows
    safe_ids = {
        (row.target_node, row.target_attr, row.before_value, row.after_value)
        for row in safe_fix_rows(fix_rows)
    }
    actions = tuple(
        action
        for action in fix_plan.actions
        if (
            action.target_node,
            str(action.target_attr or ""),
            str(action.before_value),
            str(action.after_value),
        )
        in safe_ids
    )
    report = apply_fix_actions(actions)
    _set_label_text(
        content,
        qt_widgets,
        "shaderHealthInspectorDescription",
        f"Applied {report.applied_count} safe fix(es).",
    )
    _revalidate_with_current_scope(content, qt_widgets)


def _on_issue_row_selected(content: Any, qt_widgets: Any) -> None:
    table = _find_child(content, qt_widgets.QTableWidget, main_window.ISSUES_TABLE_OBJECT_NAME)
    display_results = getattr(
        content,
        "_shader_health_display_failed_results",
        getattr(content, "_shader_health_failed_results", ()),
    )
    if table is None or not display_results:
        return
    selected_rows = sorted(
        {int(index.row()) for index in getattr(table, "selectedIndexes", lambda: [])()}
    )
    if not selected_rows:
        return
    selected_index = selected_rows[0]
    if selected_index < 0 or selected_index >= len(display_results):
        return
    selected = display_results[selected_index]
    content._shader_health_selected_issue = selected
    _populate_issue_details(content, qt_widgets, selected)


def _refresh_issues_table_view(content: Any, qt_widgets: Any) -> None:
    rows = getattr(content, "_shader_health_issue_rows", ())
    failed_results = getattr(content, "_shader_health_failed_results", ())
    if not rows or not failed_results:
        return

    severity_filter = _find_child(
        content,
        qt_widgets.QComboBox,
        main_window.ISSUES_SEVERITY_FILTER_OBJECT_NAME,
    )
    sort_dropdown = _find_child(
        content,
        qt_widgets.QComboBox,
        main_window.ISSUES_SORT_DROPDOWN_OBJECT_NAME,
    )
    owner_filter = _find_child(
        content,
        qt_widgets.QComboBox,
        main_window.ISSUES_OWNER_FILTER_OBJECT_NAME,
    )
    view_filter = _find_child(
        content,
        qt_widgets.QComboBox,
        main_window.ISSUES_VIEW_FILTER_OBJECT_NAME,
    )
    default_filter = main_window.ALL_SEVERITIES_LABEL
    filter_label = getattr(
        severity_filter,
        "currentText",
        lambda: default_filter,
    )()
    owner_label = getattr(
        owner_filter,
        "currentText",
        lambda: main_window.ALL_OWNERS_LABEL,
    )()
    view_label = getattr(
        view_filter,
        "currentText",
        lambda: main_window.ALL_ISSUES_LABEL,
    )()
    sort_key = getattr(sort_dropdown, "currentText", lambda: "severity")()

    pairs = list(zip(rows, failed_results))
    if filter_label and filter_label != main_window.ALL_SEVERITIES_LABEL:
        normalized = filter_label.casefold()
        pairs = [
            (row, result)
            for row, result in pairs
            if row.severity.casefold() == normalized
        ]
    if owner_label and owner_label != main_window.ALL_OWNERS_LABEL:
        normalized_owner = owner_label.casefold()
        pairs = [
            (row, result)
            for row, result in pairs
            if row.owner.casefold() == normalized_owner
        ]
    if view_label == main_window.BLOCKING_ONLY_LABEL:
        pairs = [
            (row, result)
            for row, result in pairs
            if getattr(result, "block_publish", False) or getattr(result, "block_deadline", False)
        ]
    elif view_label == main_window.AUTO_FIXABLE_LABEL:
        pairs = [
            (row, result)
            for row, result in pairs
            if getattr(result, "auto_fix_available", False)
        ]
    pairs.sort(key=lambda pair: main_window._issue_sort_value(pair[0], str(sort_key)))
    display_rows = tuple(row for row, _ in pairs)
    display_results = tuple(result for _, result in pairs)

    table = _find_child(content, qt_widgets.QTableWidget, main_window.ISSUES_TABLE_OBJECT_NAME)
    if table is None:
        return
    table.setSortingEnabled(False)
    main_window.populate_issues_table(qt_widgets, table, display_rows)
    table.setSortingEnabled(True)
    content._shader_health_display_failed_results = display_results


def _populate_issue_details(content: Any, qt_widgets: Any, issue: Any) -> None:
    state = main_window.IssueDetailsState(
        message=str(issue.message),
        why=str(issue.why),
        current_value=str(issue.current_value),
        expected_value=str(issue.expected_value),
        graph_trace=" -> ".join(str(item) for item in issue.graph_trace) or "N/A",
        fix_available=bool(issue.auto_fix_available),
        fix_description=str(issue.fix_id or "No safe fix selected."),
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
        return

    _populate_issue_details(content, qt_widgets, failed_results[0])
    content._shader_health_selected_issue = failed_results[0]


def _wire_scene_change_reset(content: Any, qt_widgets: Any) -> None:
    global _SCRIPT_JOBS
    cmds = _maya_cmds()
    for event in ("SceneOpened", "NewSceneOpened"):
        job_id = cmds.scriptJob(
            event=[event, lambda c=content, q=qt_widgets: _reset_panel_state(c, q)],
        )
        _SCRIPT_JOBS.append(int(job_id))


def _kill_script_jobs() -> None:
    global _SCRIPT_JOBS
    if not _SCRIPT_JOBS:
        return
    try:
        cmds = _maya_cmds()
    except RuntimeError:
        _SCRIPT_JOBS = []
        return
    for job_id in _SCRIPT_JOBS:
        try:
            cmds.scriptJob(kill=job_id, force=True)
        except Exception:  # noqa: BLE001
            continue
    _SCRIPT_JOBS = []


def _reset_panel_state(
    content: Any,
    qt_widgets: Any,
    *,
    status_message: str = "Ready to validate the current scene or selection.",
) -> None:
    content._shader_health_failed_results = ()
    content._shader_health_display_failed_results = ()
    content._shader_health_issue_rows = ()
    content._shader_health_fix_plan = None
    content._shader_health_fix_rows = ()
    content._shader_health_selected_issue = None
    content._shader_health_scan_scope = "scene"

    _set_label_text(
        content,
        qt_widgets,
        main_window.HEALTH_SCORE_LABEL_OBJECT_NAME,
        "Health: 100 / 100",
    )
    _set_label_text(
        content,
        qt_widgets,
        main_window.SEVERITY_COUNTS_LABEL_OBJECT_NAME,
        "Critical: 0   Error: 0   Warning: 0   Info: 0",
    )
    _set_label_text(
        content,
        qt_widgets,
        main_window.BLOCK_STATUS_LABEL_OBJECT_NAME,
        "Publish Block: NO   Deadline Block: NO",
    )
    _set_label_text(content, qt_widgets, "shaderHealthInspectorDescription", status_message)

    issues_table = _find_child(
        content,
        qt_widgets.QTableWidget,
        main_window.ISSUES_TABLE_OBJECT_NAME,
    )
    if issues_table is not None:
        issues_table.setSortingEnabled(False)
        issues_table.setRowCount(0)
        issues_table.setSortingEnabled(True)

    fix_table = _find_child(content, qt_widgets.QTableWidget, FIX_QUEUE_TABLE_OBJECT_NAME)
    if fix_table is not None:
        populate_fix_queue(qt_widgets, fix_table, ())

    _populate_first_issue_details(content, qt_widgets, ())


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
