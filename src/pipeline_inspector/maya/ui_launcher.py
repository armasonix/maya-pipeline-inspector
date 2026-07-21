"""Maya dockable panel launcher."""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Optional, cast

from pipeline_inspector import __version__
from pipeline_inspector.core.governance import (
    Capability,
    build_permission_resolver_from_runtime,
)
from pipeline_inspector.core.supervisor_routing import resolve_supervisor_route
from pipeline_inspector.maya.panel_session import (
    load_panel_session,
    load_runtime_configs_from_session,
    remember_panel_visible,
    remember_plugin_version,
    remember_studio_config_path,
    remember_table_column_widths,
    remember_user_config_path,
    remember_validate_splitter_sizes,
)
from pipeline_inspector.studio_config import (
    STUDIO_CONFIG_FILENAME,
    StudioConfig,
    load_studio_config,
    resolve_deadline_config,
    save_studio_config,
)
from pipeline_inspector.ui import main_window
from pipeline_inspector.ui.bug_report_section import read_bug_report_from_view
from pipeline_inspector.ui.farm_tab import (
    FARM_STATUS_LABEL_OBJECT_NAME,
    FARM_TAB_OBJECT_NAME,
    FarmTabState,
    update_farm_tab,
)
from pipeline_inspector.ui.fix_queue import (
    FIX_QUEUE_RISKY_CONFIRMATION_LABEL_OBJECT_NAME,
    FIX_QUEUE_TABLE_OBJECT_NAME,
    FixQueueActionCallbacks,
    FixQueueRow,
    blocked_selection_message,
    checked_fix_rows,
    confirm_risky_fixes,
    fix_rows_from_table,
    populate_fix_queue,
    risky_fix_rows,
    selected_fix_rows,
    update_risky_confirmation_label,
)
from pipeline_inspector.ui.governance_section import read_governance_from_view
from pipeline_inspector.ui.issues_triage import (
    apply_combo_preference,
    read_issue_filter_prefs,
    read_issue_filter_prefs_from_widgets,
)
from pipeline_inspector.ui.qt import load_qt_widgets
from pipeline_inspector.ui.readiness_tab import (
    READINESS_TAB_OBJECT_NAME,
    ReadinessTabState,
    update_readiness_tab,
)
from pipeline_inspector.ui.settings_dirty_state import (
    evaluate_settings_dirty_state_from_view,
)
from pipeline_inspector.ui.settings_panel import (
    SETTINGS_VIEW_OBJECT_NAME,
    SettingsActionCallbacks,
    read_connectors_from_settings_view,
    read_user_preferences_from_settings_view,
    update_settings_view,
)
from pipeline_inspector.ui.studio_environment_section import read_studio_environment_from_view
from pipeline_inspector.ui.studio_policy_section import read_studio_policy_from_view
from pipeline_inspector.ui.support_section import read_readiness_from_view
from pipeline_inspector.ui.user_preferences_ui import (
    apply_user_preferences_to_panel,
)
from pipeline_inspector.ui.waiver_manager import (
    WAIVER_STATUS_LABEL_OBJECT_NAME,
    WAIVER_TABLE_OBJECT_NAME,
    populate_waiver_table,
    waiver_rows_from_records,
    waiver_summary_text,
)
from pipeline_inspector.user_config import (
    UserPreferences,
    default_user_config_path,
    enrich_user_preferences,
    load_user_config,
    merge_runtime_config,
    save_user_config,
)

WORKSPACE_CONTROL_NAME = f"{main_window.PANEL_OBJECT_NAME}WorkspaceControl"
_VALIDATION_EXECUTOR = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="pipeline-inspector-validate",
)
_NOTIFY_EXECUTOR = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="pipeline-inspector-notify",
)
_VALIDATE_CYCLE_ATTR = "_pipeline_inspector_validate_cycle"
_PENDING_REVALIDATE_ATTR = "_pipeline_inspector_pending_revalidate"
OBSOLETE_WORKSPACE_CONTROL_NAMES = (
    f"{main_window.PANEL_OBJECT_NAME}DockRightWorkspaceControl",
)
DEFAULT_DOCK_AREA = "right"
WORKSPACE_RETAIN = True

VALIDATE_SPLITTER_SIZES_ATTR = "_pipeline_inspector_validate_splitter_sizes"
STUDIO_CONFIG_ATTR = "_pipeline_inspector_studio_config"
USER_CONFIG_ATTR = "_pipeline_inspector_user_config"
MERGED_RUNTIME_CONFIG_ATTR = "_pipeline_inspector_merged_runtime_config"
SAVED_STUDIO_CONFIG_ATTR = "_pipeline_inspector_saved_studio_config"
SAVED_USER_CONFIG_ATTR = "_pipeline_inspector_saved_user_config"
SESSION_RULE_OVERRIDES_ATTR = "_pipeline_inspector_session_rule_overrides"
SESSION_RULE_OVERRIDES_ATTR = "_pipeline_inspector_session_rule_overrides"

_PANEL: Optional[Any] = None
_SCRIPT_JOBS: list[int] = []


def show_panel() -> Any:
    """Open or restore the dockable Maya Pipeline Inspector panel."""

    global _PANEL
    cmds = _maya_cmds()
    _purge_obsolete_workspace_controls(cmds)

    if _workspace_control_exists(cmds):
        if _PANEL is not None:
            _configure_workspace_control_mobility(cmds)
            cmds.workspaceControl(WORKSPACE_CONTROL_NAME, edit=True, restore=True)
            raise_panel = getattr(_PANEL, "raise_", None)
            if raise_panel is not None:
                raise_panel()
            _debug_workspace_dock_log(cmds, "show_panel.restore", hypothesis_id="H12")
            remember_plugin_version(__version__)
            remember_panel_visible(True)
            return _PANEL
        cmds.deleteUI(WORKSPACE_CONTROL_NAME, control=True)

    panel = _create_dockable_panel()
    _PANEL = panel
    if _workspace_control_exists(cmds):
        cmds.deleteUI(WORKSPACE_CONTROL_NAME, control=True)
    initial_width = _preferred_docked_panel_width(panel)
    panel.show(
        dockable=True,
        area=DEFAULT_DOCK_AREA,
        floating=False,
        retain=WORKSPACE_RETAIN,
        width=initial_width,
    )
    _configure_workspace_control_mobility(cmds)
    _debug_workspace_dock_log(cmds, "show_panel.create", hypothesis_id="H12")
    remember_plugin_version(__version__)
    remember_panel_visible(True)
    return panel


def show_farm_check_panel() -> Any:
    """Open the panel on the Farm tab and run deadline_critical preflight."""

    panel = show_panel()
    content = _panel_content_from_panel(panel)
    if content is None:
        return panel
    qt_widgets = load_qt_widgets()
    _set_panel_view(content, qt_widgets, settings=False)
    _select_farm_tab(content, qt_widgets)
    _run_farm_preflight_from_ui(content, qt_widgets)
    return panel


def show_settings_panel() -> Any:
    """Open the panel on the settings view."""

    panel = show_panel()
    content = _panel_content_from_panel(panel)
    if content is None:
        return panel
    qt_widgets = load_qt_widgets()
    _set_panel_view(content, qt_widgets, settings=True)
    return panel


def show_validate_scene_panel() -> Any:
    """Open Validate and run Validate Scene."""

    panel = show_panel()
    content = _panel_content_from_panel(panel)
    if content is None:
        return panel
    qt_widgets = load_qt_widgets()
    _set_panel_view(content, qt_widgets, settings=False)
    _select_validate_tab(content, qt_widgets)
    _validate_from_ui(content, qt_widgets, scan_scope="scene")
    return panel


def show_reports_panel() -> Any:
    """Open the Reports tab."""

    panel = show_panel()
    content = _panel_content_from_panel(panel)
    if content is None:
        return panel
    qt_widgets = load_qt_widgets()
    _set_panel_view(content, qt_widgets, settings=False)
    _select_reports_tab(content, qt_widgets)
    return panel


def show_readiness_check_panel() -> Any:
    """Open the Readiness tab and run machine readiness checks."""

    panel = show_panel()
    content = _panel_content_from_panel(panel)
    if content is None:
        return panel
    qt_widgets = load_qt_widgets()
    _set_panel_view(content, qt_widgets, settings=False)
    _select_readiness_tab(content, qt_widgets)
    _run_readiness_check_from_ui(content, qt_widgets)
    return panel


def show_check_for_updates_panel() -> Any:
    """Open the panel and run Check for Updates."""

    panel = show_panel()
    content = _panel_content_from_panel(panel)
    if content is None:
        return panel
    qt_widgets = load_qt_widgets()
    _set_panel_view(content, qt_widgets, settings=False)
    _show_check_for_updates_modal_from_ui(content, qt_widgets)
    return panel


def _panel_content_from_panel(panel: Any) -> Any:
    return getattr(panel, "_pipeline_inspector_content", None)


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
    remember_panel_visible(False)


def _create_dockable_panel() -> Any:
    _kill_script_jobs()
    qt_widgets = load_qt_widgets()
    from maya.app.general.mayaMixin import (
        MayaQWidgetDockableMixin,
    )

    panel_state: dict[str, Any] = {"content": None}

    def init_panel(self: Any) -> None:
        super(type(self), self).__init__()
        self.setObjectName(main_window.PANEL_OBJECT_NAME)
        self.setWindowTitle(main_window.PANEL_TITLE)
        size_policy = qt_widgets.QSizePolicy
        self.setSizePolicy(size_policy.Preferred, size_policy.Expanding)

        layout = qt_widgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        panel_session = load_panel_session()
        studio_config, user_config = _load_runtime_configs()
        merged_runtime = merge_runtime_config(studio_config, user_config)
        content = main_window.build_main_widget(
            qt_widgets,
            export_callbacks=_export_action_callbacks(),
            fix_queue_callbacks=_fix_queue_action_callbacks(panel_state, qt_widgets),
            validation_callbacks=_validation_action_callbacks(panel_state, qt_widgets),
            issue_details_callbacks=_issue_details_action_callbacks(panel_state, qt_widgets),
            waiver_callbacks=_waiver_manager_callbacks(panel_state, qt_widgets),
            farm_callbacks=_farm_action_callbacks(panel_state, qt_widgets),
            readiness_callbacks=_readiness_action_callbacks(panel_state, qt_widgets),
            settings_callbacks=_settings_action_callbacks(panel_state, qt_widgets),
            navigation_callbacks=_panel_navigation_callbacks(panel_state, qt_widgets),
            studio_config=studio_config,
            user_config=user_config,
        )
        panel_state["content"] = content
        self._pipeline_inspector_content = content
        content._pipeline_inspector_dock = self
        if panel_session.validate_splitter_sizes:
            setattr(
                content,
                VALIDATE_SPLITTER_SIZES_ATTR,
                panel_session.validate_splitter_sizes,
            )
        setattr(content, STUDIO_CONFIG_ATTR, studio_config)
        setattr(content, USER_CONFIG_ATTR, user_config)
        setattr(content, MERGED_RUNTIME_CONFIG_ATTR, merged_runtime)
        _set_saved_settings_baselines(content, studio_config, user_config)
        if studio_config.config_path is not None:
            remember_studio_config_path(studio_config.config_path)
        if user_config.config_path is not None and Path(user_config.config_path).is_file():
            remember_user_config_path(user_config.config_path)
        _wire_issues_table_interactions(content, qt_widgets)
        _wire_waiver_manager_interactions(content, qt_widgets)
        _wire_scene_change_reset(content, qt_widgets)
        _wire_validate_shortcuts(content, qt_widgets, panel_state)
        _wire_validate_tab_focus(content, qt_widgets)
        apply_user_preferences_to_panel(content, qt_widgets, user_config)
        _restore_table_column_widths_from_session(content, qt_widgets, panel_session)
        _wire_validate_splitter_persistence(content, qt_widgets)
        _wire_table_column_persistence(content, qt_widgets)
        _sync_workspace_control_width(content)
        _set_panel_view(content, qt_widgets, settings=False)
        layout.addWidget(content)
        from pipeline_inspector.ui.theme_loader import apply_panel_theme

        apply_panel_theme(content, user_config.theme, dock=self)
        from pipeline_inspector.maya.ui_icons import apply_panel_header_icons
        from pipeline_inspector.ui.qt import load_qt_gui

        apply_panel_header_icons(content, qt_widgets, load_qt_gui())
        _schedule_on_main_thread(lambda: _refresh_waiver_manager(content, qt_widgets))
        _refresh_readiness_tab(content, qt_widgets)
        _refresh_farm_tab(content, qt_widgets, async_connection=True)
        _maybe_run_startup_update_check(content, qt_widgets, user_config)

    panel_class = type(
        "PipelineInspectorDock",
        (MayaQWidgetDockableMixin, qt_widgets.QWidget),
        {"__init__": init_panel, "__module__": __name__},
    )
    return panel_class()


def _sync_workspace_control_width(content: Any) -> None:
    """Suggest a compact dock width without locking the workspace control."""

    from pipeline_inspector.ui.ui_density_tokens import density_tokens, normalize_density

    density = str(
        getattr(content, "_pipeline_inspector_ui_density", "comfortable") or "comfortable"
    )
    tokens = density_tokens(normalize_density(density))
    if tokens.panel_max_width is None:
        return

    cmds = _maya_cmds()
    if not _workspace_control_exists(cmds):
        return
    if _workspace_control_is_floating(cmds):
        return
    try:
        cmds.workspaceControl(
            WORKSPACE_CONTROL_NAME,
            edit=True,
            resizeWidth=tokens.panel_max_width,
            widthProperty="free",
            heightProperty="free",
        )
    except (RuntimeError, TypeError, ValueError):
        return


def detach_panel() -> bool:
    """Float the panel so it can be moved independently of the Maya dock."""

    global _PANEL
    cmds = _maya_cmds()
    if _PANEL is None and not _workspace_control_exists(cmds):
        _debug_workspace_dock_log(cmds, "detach_panel.missing_panel", hypothesis_id="H13")
        return False

    _configure_workspace_control_mobility(cmds)

    set_params = getattr(_PANEL, "setDockableParameters", None) if _PANEL is not None else None
    if callable(set_params):
        with suppress(RuntimeError, TypeError, ValueError):
            set_params(dockable=True, floating=True)
        if _workspace_control_is_floating(cmds):
            _debug_workspace_dock_log(cmds, "detach_panel.mixin_float", hypothesis_id="H13")
            return True

    if _workspace_control_exists(cmds):
        with suppress(RuntimeError, TypeError, ValueError):
            cmds.workspaceControl(WORKSPACE_CONTROL_NAME, edit=True, floating=True)
        if _workspace_control_is_floating(cmds):
            _debug_workspace_dock_log(cmds, "detach_panel.workspace_float", hypothesis_id="H13")
            return True

    if _PANEL is not None:
        show_panel_widget = getattr(_PANEL, "show", None)
        if callable(show_panel_widget):
            try:
                show_panel_widget(dockable=False, floating=True)
                _debug_workspace_dock_log(
                    cmds,
                    "detach_panel.standalone_window",
                    hypothesis_id="H14",
                )
                return True
            except (RuntimeError, TypeError, ValueError):
                pass

    _debug_workspace_dock_log(cmds, "detach_panel.failed", hypothesis_id="H13")
    return False


def _sync_docked_panel_layout(cmds: Any) -> None:
    """Reapply mobility and compact width after returning to the default dock."""

    _configure_workspace_control_mobility(cmds)
    content = _panel_content_from_panel(_PANEL) if _PANEL is not None else None
    if content is not None:
        _sync_workspace_control_width(content)


def _invoke_dock_panel() -> None:
    dock_panel()


def _invoke_detach_panel() -> None:
    detach_panel()


def dock_panel() -> bool:
    """Return the panel to the default right dock."""

    global _PANEL
    cmds = _maya_cmds()
    if _PANEL is None and not _workspace_control_exists(cmds):
        _debug_workspace_dock_log(cmds, "dock_panel.missing_panel", hypothesis_id="H15")
        return False

    initial_width = _preferred_docked_panel_width(_PANEL) if _PANEL is not None else 420

    if _PANEL is not None and not _workspace_control_exists(cmds):
        show_panel_widget = getattr(_PANEL, "show", None)
        if callable(show_panel_widget):
            try:
                show_panel_widget(
                    dockable=True,
                    area=DEFAULT_DOCK_AREA,
                    floating=False,
                    retain=WORKSPACE_RETAIN,
                    width=initial_width,
                )
                _sync_docked_panel_layout(cmds)
                if _workspace_control_exists(cmds) and not _workspace_control_is_floating(cmds):
                    _debug_workspace_dock_log(cmds, "dock_panel.recreate_dock", hypothesis_id="H15")
                    return True
            except (RuntimeError, TypeError, ValueError):
                pass

    _configure_workspace_control_mobility(cmds)

    set_params = getattr(_PANEL, "setDockableParameters", None) if _PANEL is not None else None
    if callable(set_params):
        with suppress(RuntimeError, TypeError, ValueError):
            set_params(
                dockable=True,
                floating=False,
                area=DEFAULT_DOCK_AREA,
                width=initial_width,
            )
        if _workspace_control_exists(cmds) and not _workspace_control_is_floating(cmds):
            _sync_docked_panel_layout(cmds)
            _debug_workspace_dock_log(cmds, "dock_panel.mixin_dock", hypothesis_id="H15")
            return True

    if _workspace_control_exists(cmds):
        with suppress(RuntimeError, TypeError, ValueError):
            cmds.workspaceControl(
                WORKSPACE_CONTROL_NAME,
                edit=True,
                floating=False,
                dockToMainWindow=(DEFAULT_DOCK_AREA, True),
            )
        with suppress(RuntimeError, TypeError, ValueError):
            cmds.workspaceControl(WORKSPACE_CONTROL_NAME, edit=True, restore=True)
        if not _workspace_control_is_floating(cmds):
            _sync_docked_panel_layout(cmds)
            _debug_workspace_dock_log(cmds, "dock_panel.workspace_dock", hypothesis_id="H15")
            return True

    if _PANEL is not None:
        show_panel_widget = getattr(_PANEL, "show", None)
        if callable(show_panel_widget):
            try:
                show_panel_widget(
                    dockable=True,
                    area=DEFAULT_DOCK_AREA,
                    floating=False,
                    retain=WORKSPACE_RETAIN,
                    width=initial_width,
                )
                _sync_docked_panel_layout(cmds)
                if _workspace_control_exists(cmds) and not _workspace_control_is_floating(cmds):
                    _debug_workspace_dock_log(cmds, "dock_panel.show_dock", hypothesis_id="H15")
                    return True
            except (RuntimeError, TypeError, ValueError):
                pass

    _debug_workspace_dock_log(cmds, "dock_panel.failed", hypothesis_id="H15")
    return False


def _preferred_docked_panel_width(panel: Any) -> int:
    content = _panel_content_from_panel(panel)
    if content is None:
        return 420
    from pipeline_inspector.ui.ui_density_tokens import density_tokens, normalize_density

    density = str(
        getattr(content, "_pipeline_inspector_ui_density", "comfortable") or "comfortable"
    )
    tokens = density_tokens(normalize_density(density))
    if tokens.panel_max_width is not None:
        return int(tokens.panel_max_width)
    return 420


def _workspace_control_is_floating(cmds: Any) -> bool:
    if not _workspace_control_exists(cmds):
        return False
    try:
        return bool(cmds.workspaceControl(WORKSPACE_CONTROL_NAME, query=True, floating=True))
    except (RuntimeError, TypeError, ValueError):
        return False


def _configure_workspace_control_mobility(cmds: Any) -> None:
    """Allow undocking to a floating window while keeping the default right dock."""

    if not _workspace_control_exists(cmds):
        return
    try:
        cmds.workspaceControl(
            WORKSPACE_CONTROL_NAME,
            edit=True,
            retain=WORKSPACE_RETAIN,
            widthProperty="free",
            heightProperty="free",
            minimumWidth=1,
            minimumHeight=1,
            maximumWidth=5000,
            maximumHeight=5000,
            actLikeMayaUIElement=True,
        )
    except TypeError:
        try:
            cmds.workspaceControl(
                WORKSPACE_CONTROL_NAME,
                edit=True,
                retain=WORKSPACE_RETAIN,
            )
        except (RuntimeError, TypeError, ValueError):
            return
    except (RuntimeError, ValueError):
        return


def _debug_workspace_dock_log(cmds: Any, location: str, *, hypothesis_id: str) -> None:
    # #region agent log
    from pipeline_inspector.util.debug_log import debug_log_enabled, write_debug_log

    if not debug_log_enabled():
        return

    data: dict[str, str] = {"location": location}
    for key, flag in (
        ("floating", "floating"),
        ("width_property", "widthProperty"),
        ("height_property", "heightProperty"),
        ("width", "width"),
        ("minimum_width", "minimumWidth"),
        ("maximum_width", "maximumWidth"),
    ):
        try:
            value = cmds.workspaceControl(WORKSPACE_CONTROL_NAME, query=True, **{flag: True})
        except (RuntimeError, TypeError, ValueError):
            value = ""
        data[key] = str(value)
    write_debug_log(
        f"ui_launcher.{location}",
        "Workspace control dock state",
        data,
        hypothesis_id=hypothesis_id,
    )
    # #endregion


def _panel_navigation_callbacks(
    panel_state: dict[str, Any],
    qt_widgets: Any,
) -> main_window.PanelNavigationCallbacks:
    return main_window.PanelNavigationCallbacks(
        on_open_settings=lambda: _set_panel_view(
            _panel_content(panel_state),
            qt_widgets,
            settings=True,
        ),
        on_open_documentation=lambda: _open_documentation_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_check_for_updates=lambda: _show_check_for_updates_modal_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_detach_panel=_invoke_detach_panel,
        on_dock_panel=_invoke_dock_panel,
        on_report_bug=lambda: _report_bug_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
    )


def _show_check_for_updates_modal_from_ui(content: Any, qt_widgets: Any) -> None:
    from pipeline_inspector.ui.settings_widgets import try_reactivate_modal_dialog
    from pipeline_inspector.ui.update_progress_dialog import UPDATE_PROGRESS_DIALOG_OBJECT_NAME

    if try_reactivate_modal_dialog(UPDATE_PROGRESS_DIALOG_OBJECT_NAME):
        return

    def _open_update_wizard() -> None:
        from pipeline_inspector import __version__
        from pipeline_inspector.studio_config import StudioConfig
        from pipeline_inspector.ui.update_modal import show_update_modal_shell
        from pipeline_inspector.ui.update_wizard import (
            format_update_wizard_user_message,
            run_update_check_only,
        )

        try:
            studio_config = getattr(content, "_pipeline_inspector_studio_config", None)
            if studio_config is not None and not isinstance(studio_config, StudioConfig):
                studio_config = None

            maya_parent = _maya_main_window_widget(qt_widgets)
            check_result = run_update_check_only(
                installed_version=__version__,
                studio_config=studio_config,
            )
            message = format_update_wizard_user_message(
                check_result,
                installed_version=__version__,
            )
            _set_label_text(
                content,
                qt_widgets,
                main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
                message.replace("\n", " "),
            )

            if check_result.up_to_date:
                _show_information_dialog(
                    qt_widgets,
                    "Check for Updates",
                    message,
                    singleton_key="pipelineInspectorCheckForUpdates",
                )
                return

            if check_result.skipped_reason == "disabled" or check_result.error_message:
                _show_information_dialog(
                    qt_widgets,
                    "Check for Updates",
                    message,
                    singleton_key="pipelineInspectorCheckForUpdates",
                )
                return

            if not check_result.update_available:
                _show_information_dialog(
                    qt_widgets,
                    "Check for Updates",
                    message,
                    singleton_key="pipelineInspectorCheckForUpdates",
                )
                return

            session = show_update_modal_shell(
                qt_widgets,
                parent=maya_parent,
                installed_version=__version__,
                studio_config=studio_config,
            )
            final_message = format_update_wizard_user_message(
                session.result,
                installed_version=__version__,
            )
            _set_label_text(
                content,
                qt_widgets,
                main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
                final_message.replace("\n", " "),
            )
        except Exception as exc:
            _show_information_dialog(
                qt_widgets,
                "Check for Updates",
                f"Update check failed: {exc}",
                singleton_key="pipelineInspectorCheckForUpdates",
            )
            raise

    timer_cls = getattr(qt_widgets, "QTimer", None)
    single_shot = getattr(timer_cls, "singleShot", None) if timer_cls is not None else None
    if single_shot is not None:
        single_shot(0, _open_update_wizard)
        return
    _open_update_wizard()


def _maybe_run_startup_update_check(
    content: Any,
    qt_widgets: Any,
    user_config: UserPreferences,
) -> None:
    """Run a deferred check-only update query when the user pref requests it."""

    if not user_config.updates.check_on_startup:
        return

    timer_cls = getattr(qt_widgets, "QTimer", None)
    single_shot = getattr(timer_cls, "singleShot", None) if timer_cls is not None else None
    if single_shot is None:
        _run_startup_update_check(content, qt_widgets)
        return

    single_shot(0, lambda: _run_startup_update_check(content, qt_widgets))


def _run_startup_update_check(content: Any, qt_widgets: Any) -> None:
    from pipeline_inspector import __version__
    from pipeline_inspector.studio_config import StudioConfig
    from pipeline_inspector.ui.update_wizard import (
        format_update_wizard_user_message,
        run_update_check_only,
    )

    studio_config = getattr(content, STUDIO_CONFIG_ATTR, None)
    if studio_config is not None and not isinstance(studio_config, StudioConfig):
        studio_config = None

    try:
        result = run_update_check_only(
            installed_version=__version__,
            studio_config=studio_config,
        )
    except Exception:
        return

    if result.up_to_date or result.skipped_reason == "disabled":
        return
    if not result.update_available and not result.error_message:
        return

    message = format_update_wizard_user_message(
        result,
        installed_version=__version__,
    )
    _set_label_text(
        content,
        qt_widgets,
        main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
        message.replace("\n", " "),
    )


def _maya_main_window_widget(qt_widgets: Any) -> Any | None:
    try:
        import shiboken2  # type: ignore[import-not-found]
        from maya import OpenMayaUI as omui

        main_window_ptr = omui.MQtUtil.mainWindow()
        if main_window_ptr is None:
            return None
        widget_cls = getattr(qt_widgets, "QWidget", None)
        if widget_cls is None:
            return None
        return shiboken2.wrapInstance(int(main_window_ptr), widget_cls)
    except Exception:
        return None


def _report_bug_from_ui(content: Any, qt_widgets: Any) -> None:
    from pipeline_inspector.ui.bug_report_dialog import BUG_REPORT_DIALOG_OBJECT_NAME
    from pipeline_inspector.ui.settings_widgets import try_reactivate_modal_dialog

    if try_reactivate_modal_dialog(BUG_REPORT_DIALOG_OBJECT_NAME):
        return

    from pipeline_inspector import __version__
    from pipeline_inspector.integrations.bug_report import (
        build_bug_report_payload,
        maybe_submit_bug_report,
    )
    from pipeline_inspector.ui.bug_report_dialog import (
        BugReportFormValues,
        show_bug_report_dialog,
    )

    def submit_form(values: BugReportFormValues):
        validation_result = getattr(content, "_pipeline_inspector_last_validation_result", None)
        scene_path = getattr(content, "_pipeline_inspector_scene_path", "") or _current_scene_path()
        profile_id = getattr(content, "_pipeline_inspector_profile_id", "")
        maya_version = _resolve_maya_version_for_bug_report(content)

        health_score = None
        validation_summary = ""
        if validation_result is not None:
            health = getattr(validation_result, "health_score", None)
            if health is not None:
                health_score = int(getattr(health, "score", 0) or 0)
            results = getattr(validation_result, "results", ()) or ()
            failed_count = sum(1 for item in results if getattr(item, "status", "") == "failed")
            if health_score is not None:
                validation_summary = f"Health {health_score}/100; {failed_count} failed issue(s)."
            message = str(getattr(validation_result, "message", "") or "").strip()
            if message:
                validation_summary = message if not validation_summary else (
                    f"{validation_summary} {message}"
                )

        payload = build_bug_report_payload(
            title=values.title,
            description=values.description,
            steps_to_reproduce=values.steps_to_reproduce,
            plugin_version=__version__,
            scene_path=scene_path,
            maya_version=maya_version,
            profile_id=profile_id,
            validation_summary=validation_summary,
            health_score=health_score,
        )
        screenshot_jpeg = None
        if values.attach_screenshot:
            if values.screenshot_path:
                from pipeline_inspector.integrations.bug_report.screenshot import (
                    read_image_file_as_jpeg,
                )

                screenshot_jpeg = read_image_file_as_jpeg(
                    values.screenshot_path,
                    qt_widgets=qt_widgets,
                )
            else:
                from pipeline_inspector.maya.bug_report_screenshot import (
                    capture_maya_main_window_jpeg,
                )

                screenshot_jpeg = capture_maya_main_window_jpeg(qt_widgets=qt_widgets)
        return maybe_submit_bug_report(
            _studio_config_for_content(content),
            payload,
            screenshot_jpeg=screenshot_jpeg,
        )

    show_bug_report_dialog(
        qt_widgets,
        parent=_maya_main_window_widget(qt_widgets),
        on_submit=submit_form,
    )


def _resolve_maya_version_for_bug_report(content: Any) -> str:
    snapshot = getattr(content, "_pipeline_inspector_snapshot", None)
    if snapshot is not None:
        version = str(getattr(snapshot, "maya_version", "") or "").strip()
        if version:
            return version
    try:
        cmds = _maya_cmds()
        version = str(cmds.about(version=True) or "").strip()
        if version:
            return version
    except RuntimeError:
        return ""
    return ""


def open_documentation_action() -> bool:
    """Open documentation from menu, shelf, or scripts without showing the panel."""

    from pipeline_inspector.ui.documentation_actions import open_documentation_url
    from pipeline_inspector.user_config import UserPreferences

    return open_documentation_url(UserPreferences.default().docs_url)


def _open_documentation_from_ui(content: Any, qt_widgets: Any) -> None:
    from pipeline_inspector.ui.documentation_actions import open_documentation_url

    user_config = _user_config_for_content(content)
    opened = open_documentation_url(user_config.docs_url)
    if opened:
        return
    _set_label_text(
        content,
        qt_widgets,
        main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
        "Could not open documentation URL. Check Settings в†’ Basic в†’ Documentation URL.",
    )


def _settings_action_callbacks(
    panel_state: dict[str, Any],
    qt_widgets: Any,
) -> SettingsActionCallbacks:
    def content_fn() -> Any:
        return _panel_content(panel_state)

    def sync_connectors() -> None:
        _sync_connectors_from_ui(content_fn(), qt_widgets)

    return SettingsActionCallbacks(
        on_back=lambda: _set_panel_view(_panel_content(panel_state), qt_widgets, settings=False),
        on_require_tx_changed=lambda enabled: _set_require_tx_derivatives(
            _panel_content(panel_state),
            qt_widgets,
            enabled,
        ),
        on_deadline_enabled_changed=lambda enabled: _set_deadline_connector_enabled(
            _panel_content(panel_state),
            qt_widgets,
            enabled,
        ),
        on_deadline_settings_changed=sync_connectors,
        on_telegram_enabled_changed=lambda _enabled: sync_connectors(),
        on_telegram_settings_changed=sync_connectors,
        on_discord_enabled_changed=lambda _enabled: sync_connectors(),
        on_discord_settings_changed=sync_connectors,
        on_slack_enabled_changed=lambda _enabled: sync_connectors(),
        on_slack_settings_changed=sync_connectors,
        on_ftrack_enabled_changed=lambda _enabled: sync_connectors(),
        on_ftrack_settings_changed=sync_connectors,
        on_shotgrid_enabled_changed=lambda _enabled: sync_connectors(),
        on_shotgrid_settings_changed=sync_connectors,
        on_cerebro_enabled_changed=lambda _enabled: sync_connectors(),
        on_cerebro_settings_changed=sync_connectors,
        on_render_settings_changed=lambda: _sync_render_settings_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_apply_render_preset=lambda quality: _apply_render_preset_from_ui(
            _panel_content(panel_state),
            qt_widgets,
            quality,
        ),
        on_studio_environment_changed=lambda: _sync_studio_environment_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_studio_policy_changed=lambda: _sync_studio_policy_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_governance_changed=lambda: _sync_governance_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_readiness_settings_changed=lambda: _sync_readiness_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_bug_report_settings_changed=lambda: _sync_bug_report_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_bug_report_enabled_changed=lambda enabled: _set_bug_report_enabled(
            _panel_content(panel_state),
            qt_widgets,
            enabled,
        ),
        on_save_studio_settings=lambda: _save_studio_settings_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_load_studio_settings=lambda: _load_studio_settings_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_save_user_preferences=lambda: _save_user_preferences_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_load_user_preferences=lambda: _load_user_preferences_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_user_preferences_changed=lambda: _sync_user_preferences_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_theme_changed=lambda: _apply_theme_preview_from_settings_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_open_rule_editor=lambda: _open_rule_editor_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_open_new_rule_wizard=lambda: _open_new_rule_wizard_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
    )


def _load_runtime_configs() -> tuple[StudioConfig, UserPreferences]:
    """Load studio and user config files for panel startup."""

    return load_runtime_configs_from_session()


def _studio_config_for_content(content: Any) -> StudioConfig:
    config = getattr(content, STUDIO_CONFIG_ATTR, None)
    if isinstance(config, StudioConfig):
        return config
    return StudioConfig.default()


def _user_config_for_content(content: Any) -> UserPreferences:
    config = getattr(content, USER_CONFIG_ATTR, None)
    if isinstance(config, UserPreferences):
        return config
    return UserPreferences.default()


def _permission_resolver_for_content(content: Any):
    return build_permission_resolver_from_runtime(
        studio=_studio_config_for_content(content),
        user=_user_config_for_content(content),
    )


def _guard_panel_capability(
    content: Any,
    qt_widgets: Any,
    capability: Capability,
    *,
    title: str = "Permission denied",
    status_object_name: str = main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
) -> bool:
    decision = _permission_resolver_for_content(content).require(capability)
    if decision.allowed:
        return True
    _show_information_dialog(qt_widgets, title, decision.reason)
    _set_label_text(content, qt_widgets, status_object_name, decision.reason)
    return False


def _session_rule_overrides_for_content(content: Any) -> dict[str, Any]:
    overrides = getattr(content, SESSION_RULE_OVERRIDES_ATTR, None)
    if isinstance(overrides, dict):
        return overrides
    return {}


def _set_session_rule_overrides(content: Any, overrides: dict[str, Any]) -> None:
    setattr(content, SESSION_RULE_OVERRIDES_ATTR, dict(overrides))


def _open_rule_editor_from_ui(content: Any, qt_widgets: Any) -> None:
    from pipeline_inspector.core.rule_browser import load_packaged_rules_catalog
    from pipeline_inspector.runtime_preferences import user_extra_rule_paths
    from pipeline_inspector.ui.rule_editor_dialog import (
        RULE_EDITOR_DIALOG_OBJECT_NAME,
        show_rule_editor_dialog,
    )
    from pipeline_inspector.ui.settings_widgets import try_reactivate_modal_dialog

    if content is None:
        return
    if try_reactivate_modal_dialog(RULE_EDITOR_DIALOG_OBJECT_NAME):
        return

    try:
        user_config = _user_config_for_content(content)
        catalog = load_packaged_rules_catalog(
            extra_rule_paths=user_extra_rule_paths(user_config),
        )
        show_rule_editor_dialog(
            qt_widgets,
            catalog=catalog,
            session_overrides=_session_rule_overrides_for_content(content),
            on_save=lambda overrides: _set_session_rule_overrides(content, overrides),
        )
    except Exception as exc:
        _show_information_dialog(qt_widgets, "Rule Editor", f"Could not open Rule Editor: {exc}")
        raise


_open_rule_browser_from_ui = _open_rule_editor_from_ui


def _studio_extra_rules_folder_for_content(content: Any) -> str:
    studio_config = _studio_config_for_content(content)
    return studio_config.pipeline.extra_rules_folder.strip()


def _open_new_rule_wizard_from_ui(content: Any, qt_widgets: Any) -> None:
    from pipeline_inspector.core.rule_wizard import known_rule_ids_for_authoring
    from pipeline_inspector.runtime_preferences import user_extra_rule_paths
    from pipeline_inspector.ui.new_rule_wizard_dialog import (
        NEW_RULE_WIZARD_DIALOG_OBJECT_NAME,
        show_new_rule_wizard_dialog,
    )
    from pipeline_inspector.ui.settings_widgets import try_reactivate_modal_dialog

    if content is None:
        return
    if try_reactivate_modal_dialog(NEW_RULE_WIZARD_DIALOG_OBJECT_NAME):
        return

    try:
        user_config = _user_config_for_content(content)
        extra_paths = user_extra_rule_paths(user_config)
        studio_folder = _studio_extra_rules_folder_for_content(content)
        default_output = ""
        if studio_folder:
            default_output = str(Path(studio_folder) / "custom_rule.json")
        elif extra_paths:
            default_output = str(extra_paths[0] / "custom_rule.json")
        show_new_rule_wizard_dialog(
            qt_widgets,
            known_rule_ids=known_rule_ids_for_authoring(extra_rule_paths=extra_paths),
            default_output_path=default_output,
            studio_extra_rules_folder=studio_folder,
        )
    except Exception as exc:
        _show_information_dialog(qt_widgets, "New Rule Wizard", f"Could not open New Rule: {exc}")
        raise


def _create_rule_draft_from_issue_ui(content: Any, qt_widgets: Any) -> None:
    from pipeline_inspector.core.rule_wizard import (
        IncidentRuleExportContext,
        build_draft_prefill_from_issue,
        incident_rule_sidecar_path,
        known_rule_ids_for_authoring,
    )
    from pipeline_inspector.runtime_preferences import user_extra_rule_paths
    from pipeline_inspector.ui.new_rule_wizard_dialog import show_new_rule_wizard_dialog

    if content is None:
        return

    issue = _selected_issue(content)
    if issue is None:
        _set_label_text(
            content,
            qt_widgets,
            main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
            "Select a failed issue before creating a rule draft.",
        )
        return

    rules = getattr(content, "_pipeline_inspector_rules", ())
    rules_by_id = {rule.id: rule for rule in rules}
    source_rule_id = str(getattr(issue, "rule_id", "") or "")
    source_rule = rules_by_id.get(source_rule_id)
    prefill = build_draft_prefill_from_issue(issue, source_rule)

    user_config = _user_config_for_content(content)
    extra_paths = user_extra_rule_paths(user_config)
    studio_folder = _studio_extra_rules_folder_for_content(content)
    default_output = ""
    if studio_folder:
        default_output = str(
            incident_rule_sidecar_path(Path(studio_folder), prefill.draft_input.rule_id)
        )
    elif extra_paths:
        default_output = str(extra_paths[0] / f"{prefill.draft_input.rule_id}.json")
    show_new_rule_wizard_dialog(
        qt_widgets,
        parent=content,
        known_rule_ids=known_rule_ids_for_authoring(extra_rule_paths=extra_paths),
        default_output_path=default_output,
        prefill=prefill,
        studio_extra_rules_folder=studio_folder,
        export_context=IncidentRuleExportContext(
            source_rule_id=source_rule_id,
            scene_path=str(getattr(content, "_pipeline_inspector_scene_path", "") or ""),
        ),
    )


def _deadline_config_for_content(content: Any) -> Any:
    return resolve_deadline_config(_studio_config_for_content(content))


def _disabled_farm_tab_state() -> FarmTabState:
    return FarmTabState(
        integration_enabled=False,
        connection_status="disabled",
        connection_reachable=False,
        status_message=(
            "Remote farm connector is disabled. Enable Thinkbox Deadline under "
            "Settings в†’ Connectors в†’ Remote Farm."
        ),
    )


def _set_saved_settings_baselines(
    content: Any,
    studio_config: StudioConfig,
    user_config: UserPreferences,
) -> None:
    setattr(content, SAVED_STUDIO_CONFIG_ATTR, studio_config)
    setattr(content, SAVED_USER_CONFIG_ATTR, user_config.normalized())


def _saved_studio_config_for_content(content: Any) -> StudioConfig:
    config = getattr(content, SAVED_STUDIO_CONFIG_ATTR, None)
    if isinstance(config, StudioConfig):
        return config
    return _studio_config_for_content(content)


def _saved_user_config_for_content(content: Any) -> UserPreferences:
    config = getattr(content, SAVED_USER_CONFIG_ATTR, None)
    if isinstance(config, UserPreferences):
        return config
    return _user_config_for_content(content).normalized()


def _settings_dirty_state(content: Any, settings_view: Any, qt_widgets: Any):
    return evaluate_settings_dirty_state_from_view(
        settings_view,
        qt_widgets,
        current_studio=_studio_config_for_content(content),
        saved_studio=_saved_studio_config_for_content(content),
        current_user=_user_config_for_content(content).normalized(),
        saved_user=_saved_user_config_for_content(content),
    )


def _set_studio_config(content: Any, qt_widgets: Any, config: StudioConfig) -> None:
    setattr(content, STUDIO_CONFIG_ATTR, config)
    setattr(
        content,
        MERGED_RUNTIME_CONFIG_ATTR,
        merge_runtime_config(config, _user_config_for_content(content)),
    )
    from pipeline_inspector.util.paths import sync_studio_environment_to_os

    sync_studio_environment_to_os(config.studio_environment)
    _refresh_settings_view(content, qt_widgets)


def _set_user_config(content: Any, qt_widgets: Any, config: UserPreferences) -> None:
    setattr(content, USER_CONFIG_ATTR, config)
    setattr(
        content,
        MERGED_RUNTIME_CONFIG_ATTR,
        merge_runtime_config(_studio_config_for_content(content), config),
    )
    content._pipeline_inspector_settings_programmatic = True
    try:
        apply_user_preferences_to_panel(content, qt_widgets, config)
    finally:
        content._pipeline_inspector_settings_programmatic = False
    _sync_workspace_control_width(content)
    _refresh_settings_view(content, qt_widgets)


def _apply_theme_preview_from_settings_ui(content: Any, qt_widgets: Any) -> None:
    """Apply UI theme immediately without the settings refresh reentrancy guard."""

    from pipeline_inspector.ui.basic_settings_section import (
        _THEME_OPTIONS,
        SETTINGS_THEME_COMBO_OBJECT_NAME,
        _combo_data,
    )
    from pipeline_inspector.ui.settings_panel import SETTINGS_VIEW_OBJECT_NAME
    from pipeline_inspector.ui.theme_loader import apply_panel_theme, normalize_theme

    settings_view = _find_child(content, qt_widgets.QWidget, SETTINGS_VIEW_OBJECT_NAME)
    theme_combo = (
        _find_child(settings_view, qt_widgets.QComboBox, SETTINGS_THEME_COMBO_OBJECT_NAME)
        if settings_view is not None
        else None
    )
    theme = normalize_theme(_combo_data(theme_combo, options=_THEME_OPTIONS) or "classic")
    if settings_view is None or theme_combo is None:
        return
    apply_panel_theme(
        content,
        theme,
        dock=getattr(content, "_pipeline_inspector_dock", None),
    )
    current = _user_config_for_content(content)
    setattr(content, USER_CONFIG_ATTR, current.with_updates(theme=theme))


def _sync_user_preferences_from_ui(content: Any, qt_widgets: Any) -> None:
    if getattr(content, "_pipeline_inspector_settings_programmatic", False):
        return
    settings_view = _find_child(content, qt_widgets.QWidget, SETTINGS_VIEW_OBJECT_NAME)
    if settings_view is None:
        return
    updated = read_user_preferences_from_settings_view(
        settings_view,
        qt_widgets,
        base=_user_config_for_content(content),
    )
    setattr(content, USER_CONFIG_ATTR, updated)
    apply_user_preferences_to_panel(content, qt_widgets, updated)
    _refresh_settings_view(content, qt_widgets)


def _apply_user_preferences_to_panel(
    content: Any,
    qt_widgets: Any,
    user_config: UserPreferences,
) -> None:
    apply_user_preferences_to_panel(content, qt_widgets, user_config)
    _restore_table_column_widths_from_session(
        content,
        qt_widgets,
        load_panel_session(),
    )
    _wire_table_column_persistence(content, qt_widgets)


def _refresh_settings_view(content: Any, qt_widgets: Any, *, status_message: str = "") -> None:
    if getattr(content, "_pipeline_inspector_settings_programmatic", False):
        return
    settings_view = _find_child(content, qt_widgets.QWidget, SETTINGS_VIEW_OBJECT_NAME)
    if settings_view is None:
        return
    studio_config = _studio_config_for_content(content)
    user_config = _user_config_for_content(content)
    content._pipeline_inspector_settings_programmatic = True
    try:
        update_settings_view(
            settings_view,
            qt_widgets,
            config=studio_config,
            user_config=user_config,
            status_message=status_message,
            dirty_state=_settings_dirty_state(content, settings_view, qt_widgets),
        )
    finally:
        content._pipeline_inspector_settings_programmatic = False
    dirty_state = _settings_dirty_state(content, settings_view, qt_widgets)
    main_window.update_panel_header_unsaved_indicator(
        content,
        qt_widgets,
        dirty=dirty_state.any_dirty,
    )


def _set_panel_view(content: Any, qt_widgets: Any, *, settings: bool) -> None:
    stack = _find_child(
        content,
        qt_widgets.QStackedWidget,
        main_window.PANEL_BODY_STACK_OBJECT_NAME,
    )
    if stack is None:
        return
    set_current = getattr(stack, "setCurrentIndex", None)
    if set_current is not None:
        set_current(main_window.SETTINGS_VIEW_INDEX if settings else 0)
    if settings:
        _refresh_settings_view(content, qt_widgets)
        _prepare_settings_interactive_state(content, qt_widgets)


def _prepare_settings_interactive_state(content: Any, qt_widgets: Any) -> None:
    from pipeline_inspector.ui.settings_panel import (
        SETTINGS_VIEW_OBJECT_NAME,
        prepare_settings_interactive_state,
    )

    settings_view = _find_child(content, qt_widgets.QWidget, SETTINGS_VIEW_OBJECT_NAME)
    if settings_view is None:
        return
    prepare_settings_interactive_state(
        settings_view,
        qt_widgets,
        _user_config_for_content(content),
        on_preferences_changed=lambda: _sync_user_preferences_from_ui(content, qt_widgets),
        on_theme_changed=lambda: _apply_theme_preview_from_settings_ui(content, qt_widgets),
    )


def _set_require_tx_derivatives(content: Any, qt_widgets: Any, enabled: bool) -> None:
    current = _studio_config_for_content(content)
    updated = current.with_updates(
        pipeline=replace(current.pipeline, require_tx_derivatives=enabled),
    )
    _set_studio_config(content, qt_widgets, updated)
    _set_settings_status(
        content,
        qt_widgets,
        (
            "Pipeline updated: .tx derivative checks are "
            f"{'enabled' if enabled else 'disabled'} for this session."
        ),
    )


def _sync_studio_policy_from_ui(content: Any, qt_widgets: Any) -> None:
    current = _studio_config_for_content(content)
    settings_view = _find_child(content, qt_widgets.QWidget, SETTINGS_VIEW_OBJECT_NAME)
    if settings_view is None:
        return
    updated = read_studio_policy_from_view(settings_view, qt_widgets, base=current)
    _set_studio_config(content, qt_widgets, updated)


def _sync_governance_from_ui(content: Any, qt_widgets: Any) -> None:
    current = _studio_config_for_content(content)
    settings_view = _find_child(content, qt_widgets.QWidget, SETTINGS_VIEW_OBJECT_NAME)
    if settings_view is None:
        return
    governance = read_governance_from_view(settings_view, qt_widgets, base=current)
    _set_studio_config(content, qt_widgets, current.with_updates(governance=governance))


def _sync_readiness_from_ui(content: Any, qt_widgets: Any) -> None:
    current = _studio_config_for_content(content)
    settings_view = _find_child(content, qt_widgets.QWidget, SETTINGS_VIEW_OBJECT_NAME)
    if settings_view is None:
        return
    readiness = read_readiness_from_view(
        settings_view,
        qt_widgets,
        base=current.readiness,
    )
    updated = current.with_updates(readiness=readiness)
    setattr(content, STUDIO_CONFIG_ATTR, updated)
    setattr(
        content,
        MERGED_RUNTIME_CONFIG_ATTR,
        merge_runtime_config(updated, _user_config_for_content(content)),
    )
    _refresh_readiness_tab(content, qt_widgets)
    dirty_state = _settings_dirty_state(content, settings_view, qt_widgets)
    from pipeline_inspector.ui.settings_dirty_state import dirty_indicator_text
    from pipeline_inspector.ui.settings_panel import SETTINGS_DIRTY_BANNER_OBJECT_NAME

    dirty_banner = _find_child(
        settings_view,
        qt_widgets.QLabel,
        SETTINGS_DIRTY_BANNER_OBJECT_NAME,
    )
    if dirty_banner is not None:
        banner_text = dirty_indicator_text(dirty_state)
        dirty_banner.setText(banner_text)
        set_visible = getattr(dirty_banner, "setVisible", None)
        if set_visible is not None:
            set_visible(bool(banner_text))
    main_window.update_panel_header_unsaved_indicator(
        content,
        qt_widgets,
        dirty=dirty_state.any_dirty,
    )


def _sync_bug_report_from_ui(content: Any, qt_widgets: Any) -> None:
    current = _studio_config_for_content(content)
    settings_view = _find_child(content, qt_widgets.QWidget, SETTINGS_VIEW_OBJECT_NAME)
    if settings_view is None:
        return
    updated = read_bug_report_from_view(settings_view, qt_widgets, base=current)
    _set_studio_config(content, qt_widgets, updated)


def _set_bug_report_enabled(content: Any, qt_widgets: Any, enabled: bool) -> None:
    _sync_bug_report_from_ui(content, qt_widgets)
    _set_settings_status(
        content,
        qt_widgets,
        f"Bug Report relay {'enabled' if enabled else 'disabled'} for this session.",
    )


def _sync_studio_environment_from_ui(content: Any, qt_widgets: Any) -> None:
    current = _studio_config_for_content(content)
    settings_view = _find_child(content, qt_widgets.QWidget, SETTINGS_VIEW_OBJECT_NAME)
    if settings_view is None:
        return
    studio_environment = read_studio_environment_from_view(
        settings_view,
        qt_widgets,
        base=current.studio_environment,
    )
    updated = current.with_updates(studio_environment=studio_environment)
    _set_studio_config(content, qt_widgets, updated)


def _ftrack_connection_status_message(studio_config: StudioConfig) -> str:
    ftrack = studio_config.connectors.ftrack
    if not ftrack.enabled:
        return ""
    if not (
        ftrack.api_url.strip()
        and ftrack.api_user.strip()
        and ftrack.api_key.strip()
    ):
        return "Ftrack: enter API URL, user, and key to test the connection."
    from pipeline_inspector.integrations.ftrack.verify import verify_ftrack_connection

    result = verify_ftrack_connection(studio_config)
    return f"Ftrack: {result.message}"


def _cerebro_connection_status_message(studio_config: StudioConfig) -> str:
    cerebro = studio_config.connectors.cerebro
    if not cerebro.enabled:
        return ""
    if not (
        cerebro.server_url.strip()
        and cerebro.api_user.strip()
        and cerebro.api_password.strip()
    ):
        return "Cerebro: enter Database host, API user, and access token to test the connection."
    from pipeline_inspector.integrations.cerebro.verify import verify_cerebro_connection

    result = verify_cerebro_connection(studio_config)
    return f"Cerebro: {result.message}"


def _verify_connectors_if_enabled(content: Any, qt_widgets: Any) -> None:
    studio_config = _studio_config_for_content(content)
    messages = [
        message
        for message in (
            _ftrack_connection_status_message(studio_config),
            _cerebro_connection_status_message(studio_config),
        )
        if message
    ]
    if not messages:
        return
    _set_settings_status(content, qt_widgets, " ".join(messages))


def _verify_ftrack_connector_if_enabled(content: Any, qt_widgets: Any) -> None:
    _verify_connectors_if_enabled(content, qt_widgets)


def _sync_render_settings_from_ui(content: Any, qt_widgets: Any) -> None:
    """Read render preset fields from Settings and update in-session studio config."""

    current = _studio_config_for_content(content)
    settings_view = _find_child(content, qt_widgets.QWidget, SETTINGS_VIEW_OBJECT_NAME)
    if settings_view is None:
        return

    from pipeline_inspector.ui.render_settings_section import read_render_settings_from_view

    render = read_render_settings_from_view(
        settings_view,
        qt_widgets,
        base=current.render,
    )
    updated = current.with_updates(render=render)
    setattr(content, STUDIO_CONFIG_ATTR, updated)
    _refresh_settings_view(content, qt_widgets)


def _apply_render_preset_from_ui(content: Any, qt_widgets: Any, quality: str) -> None:
    """Apply Draft/Production render preset values to the open Maya scene."""

    _sync_render_settings_from_ui(content, qt_widgets)
    from pipeline_inspector.maya.render_preset_actions import apply_studio_render_quality_to_scene

    config = _studio_config_for_content(content)
    try:
        result = apply_studio_render_quality_to_scene(config.render, quality)
    except Exception as exc:  # noqa: BLE001
        _set_settings_status(content, qt_widgets, f"Apply render preset failed: {exc}")
        return
    _set_settings_status(content, qt_widgets, result.message)
    print(result.message)


def _sync_farm_quality_from_ui(content: Any, qt_widgets: Any) -> None:
    """Read Draft/Production checkboxes from the Farm tab into studio config."""

    from dataclasses import replace

    from pipeline_inspector.ui.farm_tab import read_farm_submit_qualities_from_view

    farm_tab = _farm_tab_widget(content, qt_widgets)
    if farm_tab is None:
        return
    allow_draft, allow_production = read_farm_submit_qualities_from_view(
        farm_tab,
        qt_widgets,
    )
    # region agent log
    from pipeline_inspector.util.debug_log import write_debug_log

    write_debug_log(
        "ui_launcher.py:_sync_farm_quality_from_ui",
        "farm quality synced",
        {
            "allow_draft": allow_draft,
            "allow_production": allow_production,
        },
        hypothesis_id="farm-exclusive-quality",
        run_id="post-fix",
    )
    # endregion
    current = _studio_config_for_content(content)
    deadline = replace(
        current.connectors.deadline,
        allow_draft_submit=allow_draft,
        allow_production_submit=allow_production,
    )
    updated = current.with_updates(connectors=replace(current.connectors, deadline=deadline))
    setattr(content, STUDIO_CONFIG_ATTR, updated)
    _refresh_settings_view(content, qt_widgets)


def _sync_connectors_from_ui(content: Any, qt_widgets: Any) -> None:
    """Read all connector sections from Settings and update in-session studio config."""

    current = _studio_config_for_content(content)
    settings_view = _find_child(content, qt_widgets.QWidget, SETTINGS_VIEW_OBJECT_NAME)
    if settings_view is None:
        return
    connectors = read_connectors_from_settings_view(
        settings_view,
        qt_widgets,
        base=current.connectors,
    )
    updated = current.with_updates(connectors=connectors)
    setattr(content, STUDIO_CONFIG_ATTR, updated)
    _refresh_farm_tab(content, qt_widgets)
    _refresh_settings_view(content, qt_widgets)
    _verify_ftrack_connector_if_enabled(content, qt_widgets)


def _sync_deadline_connector_from_ui(content: Any, qt_widgets: Any) -> None:
    _sync_connectors_from_ui(content, qt_widgets)


def _set_deadline_connector_enabled(content: Any, qt_widgets: Any, enabled: bool) -> None:
    _sync_deadline_connector_from_ui(content, qt_widgets)
    _set_settings_status(
        content,
        qt_widgets,
        (
            "Thinkbox Deadline connector "
            f"{'enabled' if enabled else 'disabled'} for this session."
        ),
    )


def _commit_saved_settings_baselines(content: Any) -> None:
    _set_saved_settings_baselines(
        content,
        _studio_config_for_content(content),
        _user_config_for_content(content),
    )


def _save_studio_settings_from_ui(content: Any, qt_widgets: Any) -> None:
    if not _guard_panel_capability(
        content,
        qt_widgets,
        "edit_studio_settings",
        title="Save Studio Config",
    ):
        return
    if not _guard_panel_capability(
        content,
        qt_widgets,
        "edit_connectors",
        title="Save Studio Config",
    ):
        return
    _sync_deadline_connector_from_ui(content, qt_widgets)
    _sync_render_settings_from_ui(content, qt_widgets)
    _sync_farm_quality_from_ui(content, qt_widgets)
    _sync_studio_environment_from_ui(content, qt_widgets)
    _sync_studio_policy_from_ui(content, qt_widgets)
    _sync_governance_from_ui(content, qt_widgets)
    _sync_bug_report_from_ui(content, qt_widgets)
    config = _studio_config_for_content(content)
    path = _pick_settings_save_path(qt_widgets, config.config_path)
    if path is None:
        return
    try:
        saved_path = save_studio_config(path, config.with_updates(config_path=path))
    except OSError as exc:
        _set_settings_status(content, qt_widgets, f"Save failed: {exc}")
        return
    _set_studio_config(content, qt_widgets, config.with_updates(config_path=saved_path))
    remember_studio_config_path(saved_path)
    _commit_saved_settings_baselines(content)
    ftrack_note = _ftrack_connection_status_message(config.with_updates(config_path=saved_path))
    _set_settings_status(
        content,
        qt_widgets,
        (
            f"Studio settings saved to {saved_path}. "
            "Point other machines at this file via Load Studio Config or "
            "PIPELINE_INSPECTOR_STUDIO_CONFIG."
            f"{ftrack_note}"
        ),
    )


def _save_user_preferences_from_ui(content: Any, qt_widgets: Any) -> None:
    _sync_user_preferences_from_ui(content, qt_widgets)
    config = _user_config_for_content(content)
    if config.extra_rule_paths and not _permission_resolver_for_content(content).allows(
        "manage_rules"
    ):
        _guard_panel_capability(
            content,
            qt_widgets,
            "manage_rules",
            title="Save User Preferences",
        )
        return
    path = config.config_path or default_user_config_path()
    try:
        saved_path = save_user_config(path, config.with_updates(config_path=path))
    except OSError as exc:
        _set_settings_status(content, qt_widgets, f"User save failed: {exc}")
        return
    _set_user_config(content, qt_widgets, config.with_updates(config_path=saved_path))
    remember_user_config_path(saved_path)
    _commit_saved_settings_baselines(content)
    _set_settings_status(
        content,
        qt_widgets,
        f"User preferences saved to {saved_path}.",
    )


def _load_user_preferences_from_ui(content: Any, qt_widgets: Any) -> None:
    path = _pick_user_config_load_path(qt_widgets)
    if path is None:
        return
    try:
        loaded = load_user_config(path)
    except (OSError, ValueError) as exc:
        _set_settings_status(content, qt_widgets, f"User load failed: {exc}")
        return
    remember_user_config_path(path)
    _set_user_config(content, qt_widgets, enrich_user_preferences(loaded))
    _commit_saved_settings_baselines(content)
    _set_settings_status(
        content,
        qt_widgets,
        f"Loaded user preferences from {path}.",
    )


def _load_studio_settings_from_ui(content: Any, qt_widgets: Any) -> None:
    path = _pick_settings_load_path(qt_widgets)
    if path is None:
        return
    try:
        loaded = load_studio_config(path)
    except (OSError, ValueError) as exc:
        _set_settings_status(content, qt_widgets, f"Load failed: {exc}")
        return
    loaded = loaded.with_updates(config_path=path.resolve())
    remember_studio_config_path(path.resolve())
    _set_studio_config(content, qt_widgets, loaded)
    _refresh_farm_tab(content, qt_widgets)
    _commit_saved_settings_baselines(content)
    _set_settings_status(
        content,
        qt_widgets,
        f"Loaded studio settings from {path}. Validation now follows this config.",
    )


def _set_settings_status(content: Any, qt_widgets: Any, message: str) -> None:
    _refresh_settings_view(content, qt_widgets, status_message=message)


def _pick_settings_save_path(qt_widgets: Any, current_path: Path | None) -> Path | None:
    file_dialog = getattr(qt_widgets, "QFileDialog", None)
    if file_dialog is None:
        return current_path or _default_studio_config_path()
    get_save = getattr(file_dialog, "getSaveFileName", None)
    if get_save is None:
        return current_path or _default_studio_config_path()
    default_dir = str(current_path.parent if current_path else _default_studio_config_path().parent)
    default_name = current_path.name if current_path else STUDIO_CONFIG_FILENAME
    selected, _filter = get_save(
        None,
        "Save Studio Settings",
        str(Path(default_dir) / default_name),
        "Pipeline Inspector Studio (*.json);;All Files (*)",
    )
    if not selected:
        return None
    path = Path(selected)
    if path.suffix.lower() != ".json":
        path = path.with_suffix(".json")
    return path


def _pick_settings_load_path(qt_widgets: Any) -> Path | None:
    file_dialog = getattr(qt_widgets, "QFileDialog", None)
    if file_dialog is None:
        discovered = StudioConfig.default().config_path
        return discovered
    get_open = getattr(file_dialog, "getOpenFileName", None)
    if get_open is None:
        return StudioConfig.default().config_path
    env_path = os.environ.get("PIPELINE_INSPECTOR_STUDIO_CONFIG", "").strip()
    start_dir = env_path or str(_default_studio_config_path().parent)
    selected, _filter = get_open(
        None,
        "Load Studio Settings",
        start_dir,
        "Pipeline Inspector Studio (*.json);;All Files (*)",
    )
    if not selected:
        return None
    return Path(selected)


def _pick_user_config_load_path(qt_widgets: Any) -> Path | None:
    file_dialog = getattr(qt_widgets, "QFileDialog", None)
    default_path = default_user_config_path()
    if file_dialog is None:
        return default_path if default_path.is_file() else None
    get_open = getattr(file_dialog, "getOpenFileName", None)
    if get_open is None:
        return default_path if default_path.is_file() else None
    selected, _filter = get_open(
        None,
        "Load User Preferences",
        str(default_path),
        "Pipeline Inspector User (*.json);;All Files (*)",
    )
    if not selected:
        return None
    return Path(selected)


def _default_studio_config_path() -> Path:
    return Path.home() / ".pipeline_inspector" / STUDIO_CONFIG_FILENAME


def _waiver_manager_callbacks(
    panel_state: dict[str, Any],
    qt_widgets: Any,
) -> Any:
    from pipeline_inspector.ui.waiver_manager import WaiverManagerCallbacks

    return WaiverManagerCallbacks(
        on_refresh=lambda: _refresh_waiver_manager(_panel_content(panel_state), qt_widgets),
        on_make_waive=lambda: _waive_selected_issue_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_report_supervisor=lambda: _report_supervisor_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_revoke_selected=lambda: _revoke_selected_waiver_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_waiver_selected=lambda: _on_waiver_row_selected(
            _panel_content(panel_state),
            qt_widgets,
        ),
    )


def _fix_queue_action_callbacks(
    panel_state: dict[str, Any],
    qt_widgets: Any,
) -> FixQueueActionCallbacks:
    return FixQueueActionCallbacks(
        on_apply_selected=lambda: _apply_selected_fixes_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_apply_safe=lambda: _apply_safe_fixes_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_export_fix_plan=_export_fix_plan_from_ui,
    )


def _export_action_callbacks() -> main_window.ExportActionCallbacks:
    return main_window.ExportActionCallbacks(
        on_export_json=_export_json_from_ui,
        on_export_html=_export_html_from_ui,
        on_export_manifest=_export_manifest_from_ui,
        on_export_manifest_diff=_export_manifest_diff_from_ui,
        on_compare_approved_manifest=_compare_approved_manifest_from_ui,
        on_compare_after_fixes=_compare_after_fixes_from_ui,
        on_send_to_tracker=_send_to_tracker_from_ui,
        on_export_farm_html=_export_farm_html_from_ui,
    )


def _panel_content_attr(content: Any | None, attr: str, default: Any = None) -> Any:
    if content is None:
        return default
    return getattr(content, attr, default)


def _export_json_from_ui() -> None:
    content = _active_panel_content()
    snapshot = _panel_content_attr(content, "_pipeline_inspector_snapshot")
    results = _panel_content_attr(content, "_pipeline_inspector_results")
    if snapshot is not None and results is not None:
        from pipeline_inspector.maya import export_actions

        fix_audit = getattr(content, "_pipeline_inspector_last_fix_audit", None)
        _print_export_result(
            export_actions.export_json_report(
                snapshot=snapshot,
                results=results,
                fix_audit=fix_audit,
            )
        )
        return

    from pipeline_inspector.maya.commands import export_json_report_action

    _print_export_result(export_json_report_action())


def _export_html_from_ui() -> None:
    content = _active_panel_content()
    snapshot = _panel_content_attr(content, "_pipeline_inspector_snapshot")
    results = _panel_content_attr(content, "_pipeline_inspector_results")
    if snapshot is not None and results is not None:
        from pipeline_inspector.core.scoring import compute_health_score
        from pipeline_inspector.maya import export_actions

        cached_health = compute_health_score(results).score
        # region agent log
        _debug_health_log(
            "ui_launcher.py:_export_html_from_ui",
            "export html from cached validation state",
            {
                "path": "cached",
                "cached_health": cached_health,
                "profile_id": _panel_content_attr(content, "_pipeline_inspector_profile_id", ""),
                "scan_scope": _panel_content_attr(content, "_pipeline_inspector_scan_scope", ""),
                "failed_count": sum(1 for item in results if item.status == "failed"),
            },
            hypothesis_id="H1",
        )
        # endregion
        _print_export_result(
            export_actions.export_html_report(
                snapshot=snapshot,
                results=results,
            )
        )
        return

    # region agent log
    _debug_health_log(
        "ui_launcher.py:_export_html_from_ui",
        "export html falling back to revalidation",
        {"path": "revalidate"},
        hypothesis_id="H1",
    )
    # endregion
    from pipeline_inspector.maya.commands import export_html_report_action

    _print_export_result(export_html_report_action())


def _export_farm_html_from_ui() -> None:
    from pipeline_inspector.maya import farm_actions

    scene_path = ""
    content = _active_panel_content()
    if content is not None:
        scene_path = str(getattr(content, "_pipeline_inspector_scene_path", "") or "")
    if not scene_path:
        try:
            import maya.cmds as cmds

            scene_path = str(cmds.file(query=True, sceneName=True) or "")
        except ImportError:
            scene_path = ""
    _print_export_result(
        farm_actions.export_farm_html_report(scene_path=scene_path or None)
    )


def _export_manifest_from_ui() -> None:
    content = _active_panel_content()
    snapshot = _panel_content_attr(content, "_pipeline_inspector_snapshot")
    results = _panel_content_attr(content, "_pipeline_inspector_results")
    if snapshot is not None:
        from pipeline_inspector.core.scoring import compute_health_score
        from pipeline_inspector.maya import export_actions

        health_score = compute_health_score(results or ()).score if results is not None else None
        result = export_actions.export_shader_manifest(
            snapshot=snapshot,
            results=results or (),
            health_score=health_score,
        )
        _print_export_result(result)
        return

    from pipeline_inspector.maya.commands import export_shader_manifest_action

    _print_export_result(export_shader_manifest_action())


def _compare_after_fixes_from_ui() -> None:
    qt_widgets = load_qt_widgets()
    _show_information_dialog(
        qt_widgets,
        "Compare After Fixes",
        (
            "This compares Material Passport snapshots (textures, paths, graph fingerprints), "
            "not validation fixes like colorSpace.\n\n"
            "Workflow:\n"
            "1. Export Shader Manifest when the scene is approved (baseline sidecar).\n"
            "2. Apply fixes or edit shading.\n"
            "3. Press Compare After Fixes to revalidate and diff vs the baseline.\n\n"
            "Changes to colorSpace alone may not appear in the manifest diff."
        ),
    )
    content = _active_panel_content()
    if content is not None:
        _revalidate_with_current_scope(content, qt_widgets)
    _compare_approved_manifest_from_ui()


def _export_manifest_diff_from_ui() -> None:
    content = _active_panel_content()
    snapshot = _panel_content_attr(content, "_pipeline_inspector_snapshot")
    from pipeline_inspector.maya.commands import _export_manifest_diff_with_snapshot

    _print_export_result(_export_manifest_diff_with_snapshot(snapshot))


def _compare_approved_manifest_from_ui() -> None:
    content = _active_panel_content()
    snapshot = _panel_content_attr(content, "_pipeline_inspector_snapshot")
    from pipeline_inspector.maya.commands import _export_manifest_diff_with_snapshot

    _print_export_result(
        _export_manifest_diff_with_snapshot(
            snapshot,
            prefer_approved_sidecar=True,
        )
    )


def _export_fix_plan_from_ui() -> None:
    content = _active_panel_content()
    fix_plan = _panel_content_attr(content, "_pipeline_inspector_fix_plan")
    snapshot = _panel_content_attr(content, "_pipeline_inspector_snapshot")
    profile_id = _panel_content_attr(content, "_pipeline_inspector_profile_id", "")
    if fix_plan is not None and snapshot is not None:
        from pipeline_inspector.maya import export_actions

        _print_export_result(
            export_actions.export_fix_plan(
                fix_plan=fix_plan,
                snapshot=snapshot,
                profile_id=profile_id,
            )
        )
        return

    from pipeline_inspector.maya.commands import export_fix_plan_action

    _print_export_result(export_fix_plan_action())


def _studio_config_for_send_to_tracker(content: Any, qt_widgets: Any) -> StudioConfig:
    """Read connector settings for publish without refreshing the whole Settings UI."""

    current = _studio_config_for_content(content)
    settings_view = _find_child(content, qt_widgets.QWidget, SETTINGS_VIEW_OBJECT_NAME)
    if settings_view is None:
        return current
    connectors = read_connectors_from_settings_view(
        settings_view,
        qt_widgets,
        base=current.connectors,
    )
    return current.with_updates(connectors=connectors)


def _set_send_to_tracker_button_enabled(
    content: Any,
    qt_widgets: Any,
    *,
    enabled: bool,
) -> None:
    button = _find_child(
        content,
        qt_widgets.QPushButton,
        main_window.EXPORT_SEND_TO_TRACKER_BUTTON_OBJECT_NAME,
    )
    set_enabled = getattr(button, "setEnabled", None)
    if set_enabled is not None:
        set_enabled(enabled)


def _schedule_on_main_thread(
    callback: Callable[[], None],
    qt_widgets: Any | None = None,
) -> None:
    import threading

    if threading.current_thread() is not threading.main_thread():
        # #region agent log
        _debug_validate_cycle_log(
            "ui_launcher._schedule_on_main_thread",
            "defer via executeDeferred from worker thread",
            {"thread": threading.current_thread().name},
            hypothesis_id="H-LOOP1",
        )
        # #endregion
        try:
            import maya.utils

            maya.utils.executeDeferred(callback)
        except ImportError:
            callback()
        return

    from pipeline_inspector.ui.qt import qt_single_shot_callback

    single_shot = qt_single_shot_callback(qt_widgets)
    if single_shot is not None:
        single_shot(0, callback)
        return
    try:
        import maya.utils

        maya.utils.executeDeferred(callback)
    except ImportError:
        callback()


def _send_to_tracker_from_ui() -> None:
    content = _active_panel_content()
    if content is None:
        return

    validation_result = getattr(content, "_pipeline_inspector_last_validation_result", None)
    if validation_result is None:
        qt_widgets = load_qt_widgets()
        message = "Send to Tracker skipped вЂ” run Validate Scene first."
        print(message)
        _set_reports_status_label(content, qt_widgets, message)
        return

    qt_widgets = load_qt_widgets()
    studio_config = _studio_config_for_send_to_tracker(content, qt_widgets)
    scanned_at_utc = getattr(content, "_pipeline_inspector_last_validated_at", "")
    scene_path = getattr(content, "_pipeline_inspector_scene_path", "")
    scan_scope = getattr(content, "_pipeline_inspector_scan_scope", "")

    from pipeline_inspector.integrations.trackers.publish_dispatcher import (
        format_tracker_publish_status,
        preload_tracker_publish_modules,
        publish_validation_to_first_tracker,
    )

    preload_tracker_publish_modules(studio_config)
    _set_send_to_tracker_button_enabled(content, qt_widgets, enabled=False)
    _set_reports_status_label(
        content,
        qt_widgets,
        main_window.build_reports_status_text(
            scene_path=scene_path,
            scanned_at_utc=scanned_at_utc,
            scan_scope=scan_scope,
            export_message="Publishing validation summary to tracker...",
        ),
    )

    def _run_publish_on_main_thread() -> None:
        try:
            outcome = publish_validation_to_first_tracker(studio_config, validation_result)
            message = format_tracker_publish_status(outcome)
        except Exception as exc:
            message = f"Send to Tracker failed: {exc}"
            print(message)
            import traceback

            traceback.print_exc()
        print(message)

        finish_widgets = load_qt_widgets()
        _set_send_to_tracker_button_enabled(content, finish_widgets, enabled=True)
        _set_reports_status_label(
            content,
            finish_widgets,
            main_window.build_reports_status_text(
                scene_path=scene_path,
                scanned_at_utc=scanned_at_utc,
                scan_scope=scan_scope,
                export_message=message,
            ),
        )

    _schedule_on_main_thread(_run_publish_on_main_thread)


def _panel_content(panel_state: dict[str, Any]) -> Any:
    content = panel_state.get("content")
    if content is None:
        raise RuntimeError("Pipeline Inspector panel content is not initialized.")
    return content


def _active_panel_content() -> Any | None:
    if _PANEL is None:
        return None
    return getattr(_PANEL, "_pipeline_inspector_content", None)


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
        on_publish_preflight=lambda: _publish_preflight_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_manifest_gate=lambda: _manifest_gate_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_profile_changed=lambda: _revalidate_with_current_scope(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_asset_class_changed=lambda: _revalidate_with_current_scope(
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
        on_create_rule_draft=lambda: _create_rule_draft_from_issue_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
    )


def _farm_action_callbacks(
    panel_state: dict[str, Any],
    qt_widgets: Any,
) -> Any:
    from pipeline_inspector.ui.farm_tab import FarmActionCallbacks

    return FarmActionCallbacks(
        on_refresh_connection=lambda: _refresh_farm_connection_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_run_farm_preflight=lambda: _run_farm_preflight_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_submit_to_farm=lambda: _submit_farm_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_farm_quality_changed=lambda: _sync_farm_quality_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
    )


def _readiness_action_callbacks(
    panel_state: dict[str, Any],
    qt_widgets: Any,
) -> Any:
    from pipeline_inspector.ui.readiness_tab import ReadinessActionCallbacks

    return ReadinessActionCallbacks(
        on_run_readiness_check=lambda: _run_readiness_check_from_ui(
            _panel_content(panel_state),
            qt_widgets,
        ),
        on_send_report_to_sysadmin=lambda: _send_readiness_report_from_ui(
            _panel_content(panel_state),
            qt_widgets,
            recipient="sysadmin",
        ),
        on_send_report_to_support=lambda: _send_readiness_report_from_ui(
            _panel_content(panel_state),
            qt_widgets,
            recipient="support",
        ),
    )


def _validate_from_ui(content: Any, qt_widgets: Any, *, scan_scope: str) -> None:
    _schedule_ui_validation(content, qt_widgets, scan_scope=scan_scope)


def _publish_preflight_from_ui(content: Any, qt_widgets: Any) -> None:
    _schedule_ui_validation(
        content,
        qt_widgets,
        scan_scope="scene",
        profile_id="publish_strict",
        post_validate=_finish_publish_preflight,
    )


def _schedule_ui_validation(
    content: Any,
    qt_widgets: Any,
    *,
    scan_scope: str,
    profile_id: Optional[str] = None,
    post_validate: Optional[Any] = None,
) -> None:
    if getattr(content, "_pipeline_inspector_validate_running", False):
        # #region agent log
        _debug_validate_cycle_log(
            "ui_launcher._schedule_ui_validation",
            "validate skipped because another run is active",
            {
                "scan_scope": scan_scope,
                "cycle": str(getattr(content, _VALIDATE_CYCLE_ATTR, 0)),
            },
            hypothesis_id="H-LOOP1",
        )
        # #endregion
        return

    cycle = _next_validate_cycle(content)
    content._pipeline_inspector_validate_running = True
    # #region agent log
    _debug_validate_cycle_log(
        "ui_launcher._schedule_ui_validation",
        "validate scheduled",
        {
            "scan_scope": scan_scope,
            "cycle": str(cycle),
            "profile_id": profile_id or "",
        },
        hypothesis_id="H-LOOP1",
    )
    # #endregion
    busy_message = (
        "Validating selection..."
        if scan_scope == "selection"
        else "Validating scene..."
    )
    _set_validate_busy_state(content, qt_widgets, busy=True, status_message=busy_message)

    def _job() -> None:
        async_pending = False
        try:
            async_pending = _run_validation_job(
                content,
                qt_widgets,
                scan_scope=scan_scope,
                profile_id=profile_id,
                post_validate=post_validate,
            )
        except Exception as exc:  # noqa: BLE001
            message = f"Validation failed: {exc}"
            _set_label_text(
                content,
                qt_widgets,
                main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
                message,
            )
            print(message)
        finally:
            if not async_pending:
                _finish_validate_running(
                    content,
                    qt_widgets,
                    reason="sync_validation_job",
                )

    from pipeline_inspector.ui.qt import qt_single_shot_callback

    single_shot = qt_single_shot_callback(qt_widgets)
    if single_shot is not None:
        single_shot(0, _job)
    else:
        _schedule_on_main_thread(_job, qt_widgets)


def _run_validation_job(
    content: Any,
    qt_widgets: Any,
    *,
    scan_scope: str,
    profile_id: Optional[str] = None,
    post_validate: Optional[Any] = None,
) -> bool:
    """Run validation. Returns True when async work is still pending."""

    # #region agent log
    _debug_validate_job_log(
        "ui_launcher._run_validation_job",
        "Validation job started",
        {"scan_scope": scan_scope, "profile_id": profile_id or ""},
        hypothesis_id="H34",
    )
    # #endregion
    from pipeline_inspector.maya.commands import (
        capture_validation_snapshot,
        execute_validation_on_snapshot,
    )

    selected_profile = profile_id or _selected_workflow_profile_id(content, qt_widgets)
    asset_class_id = _selected_asset_class_id(content, qt_widgets)
    studio_config = _studio_config_for_content(content)
    user_config = _user_config_for_content(content)
    session_rule_overrides = _session_rule_overrides_for_content(content)
    validation_kwargs = {
        "scan_scope": scan_scope,
        "profile_id": selected_profile,
        "asset_class_id": asset_class_id,
        "studio_config": studio_config,
        "user_config": user_config,
        "session_rule_overrides": session_rule_overrides,
    }

    try:
        captured = capture_validation_snapshot(
            scan_scope=scan_scope,
            profile_id=selected_profile,
        )
    except Exception as exc:  # noqa: BLE001
        # #region agent log
        _debug_validate_job_log(
            "ui_launcher._run_validation_job",
            "Validation scan failed",
            {"scan_scope": scan_scope, "error": str(exc)},
            hypothesis_id="H34",
        )
        # #endregion
        message = f"Validation failed: {exc}"
        _set_label_text(content, qt_widgets, main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME, message)
        print(message)
        return False

    if not getattr(captured, "succeeded", False):
        _apply_validation_job_result(
            content,
            qt_widgets,
            captured,
            scan_scope=scan_scope,
            post_validate=post_validate,
        )
        return False

    future = _VALIDATION_EXECUTOR.submit(
        execute_validation_on_snapshot,
        captured.snapshot,
        **cast(Any, validation_kwargs),
    )
    # #region agent log
    _debug_validate_cycle_log(
        "ui_launcher._run_validation_job",
        "async validation submitted",
        {
            "scan_scope": scan_scope,
            "cycle": str(getattr(content, _VALIDATE_CYCLE_ATTR, 0)),
        },
        hypothesis_id="H-LOOP4",
    )
    # #endregion

    def _dispatch_result(done_future: Any) -> None:
        # #region agent log
        _debug_validate_cycle_log(
            "ui_launcher._run_validation_job",
            "async validation worker finished",
            {
                "scan_scope": scan_scope,
                "cycle": str(getattr(content, _VALIDATE_CYCLE_ATTR, 0)),
            },
            hypothesis_id="H-LOOP4",
        )
        # #endregion

        def _on_main_thread() -> None:
            # #region agent log
            _debug_validate_cycle_log(
                "ui_launcher._run_validation_job",
                "async validation main thread callback started",
                {
                    "scan_scope": scan_scope,
                    "cycle": str(getattr(content, _VALIDATE_CYCLE_ATTR, 0)),
                },
                hypothesis_id="H-LOOP1",
            )
            # #endregion
            try:
                result = done_future.result()
                _apply_validation_job_result(
                    content,
                    qt_widgets,
                    result,
                    scan_scope=scan_scope,
                    post_validate=post_validate,
                )
            except Exception as exc:  # noqa: BLE001
                # #region agent log
                _debug_validate_job_log(
                    "ui_launcher._run_validation_job",
                    "Validation job failed",
                    {"scan_scope": scan_scope, "error": str(exc)},
                    hypothesis_id="H34",
                )
                # #endregion
                message = f"Validation failed: {exc}"
                _set_label_text(
                    content,
                    qt_widgets,
                    main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
                    message,
                )
                print(message)
            finally:
                _finish_validate_running(
                    content,
                    qt_widgets,
                    reason="async_validation_callback",
                )

        _schedule_on_main_thread(_on_main_thread, qt_widgets)

    future.add_done_callback(_dispatch_result)
    return True


def _apply_validation_job_result(
    content: Any,
    qt_widgets: Any,
    result: Any,
    *,
    scan_scope: str,
    post_validate: Optional[Any] = None,
) -> None:
    # #region agent log
    _debug_validate_job_log(
        "ui_launcher._run_validation_job",
        "Validation job finished",
        {
            "scan_scope": scan_scope,
            "succeeded": str(getattr(result, "succeeded", True)),
            "failed_count": str(
                sum(
                    1
                    for item in getattr(result, "results", ()) or ()
                    if getattr(item, "status", "") == "failed"
                )
            ),
        },
        hypothesis_id="H34",
    )
    # #endregion

    if not getattr(result, "succeeded", True):
        _reset_panel_state(content, qt_widgets, status_message=result.message)
        print(result.message)
        return

    content._pipeline_inspector_scan_scope = scan_scope
    # #region agent log
    _debug_validate_job_log(
        "ui_launcher._run_validation_job",
        "phase populate_ui_start",
        {"scan_scope": scan_scope},
        hypothesis_id="H-HANG5",
    )
    # #endregion
    _populate_validation_result(content, qt_widgets, result)
    # #region agent log
    _debug_validate_job_log(
        "ui_launcher._run_validation_job",
        "phase populate_ui_done",
        {"scan_scope": scan_scope},
        hypothesis_id="H-HANG5",
    )
    # #endregion
    _update_validation_chrome_labels(content, qt_widgets, result)
    _maybe_notify_validation(content, qt_widgets, result)
    if post_validate is not None:
        post_validate(content, qt_widgets, result)
    else:
        print(result.message)


def _maybe_notify_validation(content: Any, qt_widgets: Any, result: Any) -> None:
    """Send configured validation notifications without blocking the Maya UI."""

    def _dispatch_notifications() -> None:
        try:
            from pipeline_inspector.integrations.notify.dispatcher import (
                dispatch_validation_notifications,
                report_validation_notification_outcomes,
            )

            studio_config = _studio_config_for_content(content)
            dispatch_result = dispatch_validation_notifications(
                studio_config,
                result,
                force_notify=False,
            )
            report_validation_notification_outcomes(dispatch_result)

            def _on_main_thread() -> None:
                _append_validation_notification_status(content, qt_widgets, dispatch_result)

            _schedule_on_main_thread(_on_main_thread, qt_widgets)
        except Exception as exc:  # noqa: BLE001
            print(f"Validation notification dispatch failed: {exc}")

    _NOTIFY_EXECUTOR.submit(_dispatch_notifications)


def _report_supervisor_from_ui(content: Any, qt_widgets: Any) -> None:
    """Send the latest validation summary to the configured supervisor route."""

    result = getattr(content, "_pipeline_inspector_last_validation_result", None)
    if result is None:
        _set_label_text(
            content,
            qt_widgets,
            main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
            "Report Supervisor: run Validate first.",
        )
        return

    try:
        from pipeline_inspector.integrations.notify.dispatcher import (
            dispatch_validation_notifications,
            report_validation_notification_outcomes,
        )

        studio_config = _studio_config_for_content(content)
        resolver = _permission_resolver_for_content(content)
        supervisor_route = resolve_supervisor_route(
            studio_config.governance,
            resolver.effective_role,
        )
        if supervisor_route is None:
            _set_label_text(
                content,
                qt_widgets,
                main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
                "Report Supervisor: no route configured for your pipeline role.",
            )
            return

        from pipeline_inspector.integrations.trackers.display_name import (
            format_reporter_line,
            resolve_tracker_display_name,
        )

        reporter_line = format_reporter_line(
            display_name=resolve_tracker_display_name(
                studio_config,
                user=_user_config_for_content(content),
            ),
            pipeline_role=resolver.effective_role,
        )

        dispatch_result = dispatch_validation_notifications(
            studio_config,
            result,
            supervisor_route=supervisor_route,
            force_notify=True,
            reporter_line=reporter_line,
        )
        report_validation_notification_outcomes(dispatch_result)
        _append_validation_notification_status(
            content,
            qt_widgets,
            dispatch_result,
            prefix="Report Supervisor:",
        )
    except Exception as exc:  # noqa: BLE001
        message = f"Report Supervisor failed: {exc}"
        _set_label_text(content, qt_widgets, main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME, message)
        print(message)


def _append_validation_notification_status(
    content: Any,
    qt_widgets: Any,
    dispatch_result: Any,
    *,
    prefix: str = "",
) -> None:
    """Mirror connector notification outcomes on the Validate status label."""

    from pipeline_inspector.integrations.notify.dispatcher import (
        ValidationNotificationDispatchResult,
    )

    if not isinstance(dispatch_result, ValidationNotificationDispatchResult):
        return

    lines: list[str] = []
    for outcome in dispatch_result.outcomes:
        display_name = outcome.connector_id.title()
        if outcome.sent:
            lines.append(f"{display_name}: notification sent.")
        elif outcome.error_message:
            lines.append(f"{display_name}: notification failed ({outcome.error_message}).")
        elif outcome.skipped_reason:
            lines.append(f"{display_name}: notification skipped ({outcome.skipped_reason}).")
    if not lines:
        return
    status_label = _find_child(
        content,
        qt_widgets.QLabel,
        main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
    )
    if status_label is None:
        return
    text_fn = getattr(status_label, "text", None)
    set_text = getattr(status_label, "setText", None)
    if text_fn is None or set_text is None:
        return
    current = str(text_fn()).strip()
    suffix = " ".join(lines)
    message = f"{current} {suffix}".strip() if current else suffix
    if prefix:
        message = f"{prefix} {message}".strip()
    set_text(message)


def _finish_publish_preflight(content: Any, qt_widgets: Any, result: Any) -> None:
    summary = getattr(result, "summary", None)
    block_publish = bool(getattr(summary, "block_publish", False)) if summary else False
    block_deadline = bool(getattr(summary, "block_deadline", False)) if summary else False
    health = getattr(result, "health_score", None)
    score = getattr(health, "score", None)
    score_text = f"{score}/100" if score is not None else "N/A"
    message = (
        f"Publish preflight (publish_strict) complete. Health {score_text}. "
        f"Publish Block: {_yes_no(block_publish)}. Deadline Block: {_yes_no(block_deadline)}."
    )
    _set_label_text(content, qt_widgets, main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME, message)
    print(message)


def _set_validate_busy_state(
    content: Any,
    qt_widgets: Any,
    *,
    busy: bool,
    status_message: str = "",
) -> None:
    progress = _find_child(
        content,
        qt_widgets.QProgressBar,
        main_window.VALIDATE_PROGRESS_BAR_OBJECT_NAME,
    )
    if progress is not None:
        set_visible = getattr(progress, "setVisible", None)
        if set_visible is not None:
            set_visible(busy)

    if status_message:
        _set_label_text(
            content,
            qt_widgets,
            main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
            status_message,
        )

    for object_name in (
        main_window.VALIDATE_SCENE_BUTTON_OBJECT_NAME,
        main_window.VALIDATE_SELECTION_BUTTON_OBJECT_NAME,
        main_window.VALIDATE_PUBLISH_PREFLIGHT_BUTTON_OBJECT_NAME,
    ):
        button = _find_child(content, qt_widgets.QPushButton, object_name)
        if button is not None:
            set_enabled = getattr(button, "setEnabled", None)
            if set_enabled is not None:
                set_enabled(not busy)

    app_class = getattr(qt_widgets, "QApplication", None)
    if app_class is None:
        return
    instance = getattr(app_class, "instance", lambda: None)()
    if instance is None:
        return
    set_override = getattr(instance, "setOverrideCursor", None)
    restore_override = getattr(instance, "restoreOverrideCursor", None)
    qt_module = getattr(qt_widgets, "Qt", None)
    wait_cursor = getattr(qt_module, "WaitCursor", None) if qt_module is not None else None
    if busy and set_override is not None and wait_cursor is not None:
        set_override(wait_cursor)
    elif not busy and restore_override is not None:
        restore_override()


def _refresh_farm_connection_from_ui(content: Any, qt_widgets: Any) -> None:
    from pipeline_inspector.maya.farm_actions import check_deadline_connection

    config = _deadline_config_for_content(content)
    if config is None:
        _apply_farm_tab_state(content, qt_widgets, _disabled_farm_tab_state())
        return
    tab_state = check_deadline_connection(config)
    _apply_farm_tab_state(content, qt_widgets, tab_state)


def _run_farm_preflight_from_ui(content: Any, qt_widgets: Any) -> None:
    from pipeline_inspector.maya.commands import validate_scene_action
    from pipeline_inspector.maya.farm_actions import (
        collect_farm_scene_state,
        run_farm_preflight_action,
    )

    if content is None:
        _show_information_dialog(
            qt_widgets,
            "Farm Preflight",
            "Open the Pipeline Inspector panel first.",
        )
        return

    if _deadline_config_for_content(content) is None:
        _apply_farm_tab_state(content, qt_widgets, _disabled_farm_tab_state())
        _show_information_dialog(
            qt_widgets,
            "Farm Preflight",
            _disabled_farm_tab_state().status_message,
        )
        return

    try:
        asset_class_id = _selected_asset_class_id(content, qt_widgets)
        validation = validate_scene_action(
            profile_id="deadline_critical",
            asset_class_id=asset_class_id,
            studio_config=_studio_config_for_content(content),
        )
    except Exception as exc:  # noqa: BLE001
        message = f"Farm preflight failed: {exc}"
        _set_farm_status(content, qt_widgets, message)
        print(message)
        return

    if not getattr(validation, "succeeded", True):
        _set_farm_status(content, qt_widgets, validation.message)
        print(validation.message)
        return

    content._pipeline_inspector_scan_scope = "scene"
    _populate_validation_result(content, qt_widgets, validation)
    _update_validation_chrome_labels(content, qt_widgets, validation)
    _maybe_notify_validation(content, qt_widgets, validation)
    connection_state = getattr(content, "_pipeline_inspector_farm_tab_state", None)
    result = run_farm_preflight_action(
        summary=getattr(validation, "summary", None),
        scene_state=collect_farm_scene_state(),
        config=_deadline_config_for_content(content),
        connection_state=connection_state,
        last_job_id=getattr(content, "_pipeline_inspector_farm_last_job_id", ""),
    )
    _apply_farm_tab_state(content, qt_widgets, result.tab_state)
    _show_information_dialog(qt_widgets, "Farm Preflight", result.message)
    print(result.message)


def _submit_farm_from_ui(content: Any, qt_widgets: Any) -> None:
    from pipeline_inspector.maya.farm_actions import (
        collect_farm_scene_state,
        farm_validation_result_from_summary,
        submit_farm_validation_action,
    )

    if content is None:
        _show_information_dialog(
            qt_widgets,
            "Submit to Farm",
            "Open the Pipeline Inspector panel first.",
        )
        return

    if _deadline_config_for_content(content) is None:
        _apply_farm_tab_state(content, qt_widgets, _disabled_farm_tab_state())
        _show_information_dialog(
            qt_widgets,
            "Submit to Farm",
            _disabled_farm_tab_state().status_message,
        )
        return

    if not _guard_panel_capability(
        content,
        qt_widgets,
        "submit_farm",
        title="Submit to Farm",
    ):
        return

    scene_path = getattr(content, "_pipeline_inspector_scene_path", "") or _current_scene_path()
    summary = getattr(content, "_pipeline_inspector_summary", None)
    validation_result = (
        farm_validation_result_from_summary(summary) if summary is not None else None
    )
    connection_state = getattr(content, "_pipeline_inspector_farm_tab_state", None)
    result = submit_farm_validation_action(
        scene_path=scene_path,
        scene_state=collect_farm_scene_state(),
        validation_result=validation_result,
        config=_deadline_config_for_content(content),
        connection_state=connection_state,
    )
    _apply_farm_tab_state(content, qt_widgets, result.tab_state)
    title = "Submit to Farm" if result.succeeded else "Farm Submit Blocked"
    _show_information_dialog(qt_widgets, title, result.message)
    print(result.message)
    if result.succeeded and result.job_id:
        from pipeline_inspector.maya.farm_job_monitor import start_farm_job_notification_poll

        start_farm_job_notification_poll(
            config=_deadline_config_for_content(content),
            studio_config=_studio_config_for_content(content),
            job_id=result.job_id,
            job_name=Path(scene_path).name if scene_path else "",
        )


def _refresh_farm_tab(
    content: Any,
    qt_widgets: Any,
    *,
    async_connection: bool = False,
) -> None:
    from pipeline_inspector.maya.farm_actions import check_deadline_connection

    if content is None:
        return
    config = _deadline_config_for_content(content)
    if config is None:
        _apply_farm_tab_state(content, qt_widgets, _disabled_farm_tab_state())
        return
    if not async_connection:
        _apply_farm_tab_state(content, qt_widgets, check_deadline_connection(config))
        return

    pending = FarmTabState(
        integration_enabled=True,
        api_url=config.api_url,
        connection_status="checking",
        connection_reachable=False,
        status_message="Checking Deadline connection...",
        allow_draft_submit=_studio_config_for_content(content).connectors.deadline.allow_draft_submit,
        allow_production_submit=_studio_config_for_content(content).connectors.deadline.allow_production_submit,
    )
    _apply_farm_tab_state(content, qt_widgets, pending)

    future = _VALIDATION_EXECUTOR.submit(check_deadline_connection, config)

    def _dispatch_result(done_future: Any) -> None:
        def _on_main_thread() -> None:
            try:
                tab_state = done_future.result()
            except Exception as exc:  # noqa: BLE001
                tab_state = FarmTabState(
                    api_url=config.api_url,
                    connection_status=f"error: {exc}",
                    connection_reachable=False,
                    status_message="Deadline connection check failed.",
                )
            _apply_farm_tab_state(content, qt_widgets, tab_state)

        _schedule_on_main_thread(_on_main_thread)

    future.add_done_callback(_dispatch_result)


def _apply_farm_tab_state(content: Any, qt_widgets: Any, tab_state: FarmTabState) -> None:
    if content is not None:
        from dataclasses import replace

        deadline = _studio_config_for_content(content).connectors.deadline
        tab_state = replace(
            tab_state,
            allow_draft_submit=deadline.allow_draft_submit,
            allow_production_submit=deadline.allow_production_submit,
        )
        content._pipeline_inspector_farm_tab_state = tab_state
        content._pipeline_inspector_farm_last_job_id = tab_state.last_job_id
    farm_tab = _farm_tab_widget(content, qt_widgets)
    if farm_tab is not None:
        update_farm_tab(farm_tab, qt_widgets, tab_state)


def _set_farm_status(content: Any, qt_widgets: Any, message: str) -> None:
    stored = getattr(content, "_pipeline_inspector_farm_tab_state", None)
    if isinstance(stored, FarmTabState):
        _apply_farm_tab_state(
            content,
            qt_widgets,
            FarmTabState(
                integration_enabled=stored.integration_enabled,
                api_url=stored.api_url,
                connection_status=stored.connection_status,
                connection_reachable=stored.connection_reachable,
                scene_saved=stored.scene_saved,
                renderer_plugin_loaded=stored.renderer_plugin_loaded,
                eligibility_decision=stored.eligibility_decision,
                eligibility_allowed=stored.eligibility_allowed,
                last_report_path=stored.last_report_path,
        last_job_id=stored.last_job_id,
        status_message=message,
        allow_draft_submit=stored.allow_draft_submit,
        allow_production_submit=stored.allow_production_submit,
    ),
        )
        return
    _set_label_text(content, qt_widgets, FARM_STATUS_LABEL_OBJECT_NAME, message)


def _farm_tab_widget(content: Any, qt_widgets: Any) -> Any:
    tabs = _find_child(content, qt_widgets.QTabWidget, main_window.TAB_WIDGET_OBJECT_NAME)
    if tabs is None:
        return None
    count = getattr(tabs, "count", lambda: 0)()
    for index in range(count):
        widget = getattr(tabs, "widget", lambda _index: None)(index)
        object_name = getattr(widget, "objectName", lambda: "")()
        if not object_name:
            object_name = getattr(widget, "object_name", "")
        if widget is not None and object_name == FARM_TAB_OBJECT_NAME:
            return widget
    return _find_child(content, qt_widgets.QWidget, FARM_TAB_OBJECT_NAME)


def _select_tab_by_object_name(content: Any, qt_widgets: Any, object_name: str) -> bool:
    tabs = _find_child(content, qt_widgets.QTabWidget, main_window.TAB_WIDGET_OBJECT_NAME)
    if tabs is None:
        return False
    count = getattr(tabs, "count", lambda: 0)()
    for index in range(count):
        widget = getattr(tabs, "widget", lambda _index: None)(index)
        widget_name = getattr(widget, "objectName", lambda: "")()
        if not widget_name:
            widget_name = getattr(widget, "object_name", "")
        if widget is not None and widget_name == object_name:
            set_current = getattr(tabs, "setCurrentIndex", None)
            if set_current is not None:
                set_current(index)
            return True
    return False


def _select_validate_tab(content: Any, qt_widgets: Any) -> None:
    _select_tab_by_object_name(content, qt_widgets, main_window.VALIDATE_TAB_OBJECT_NAME)


def _select_reports_tab(content: Any, qt_widgets: Any) -> None:
    _select_tab_by_object_name(content, qt_widgets, main_window.REPORTS_TAB_OBJECT_NAME)


def _select_farm_tab(content: Any, qt_widgets: Any) -> None:
    _select_tab_by_object_name(content, qt_widgets, FARM_TAB_OBJECT_NAME)


def _select_readiness_tab(content: Any, qt_widgets: Any) -> None:
    _select_tab_by_object_name(content, qt_widgets, READINESS_TAB_OBJECT_NAME)


def _refresh_readiness_tab(content: Any, qt_widgets: Any) -> None:
    from pipeline_inspector.maya.readiness_actions import initial_readiness_tab_state

    stored_state = getattr(content, "_pipeline_inspector_readiness_tab_state", None)
    if stored_state is not None:
        config = _studio_config_for_content(content)
        tab_state = replace(
            stored_state,
            checks_configured=initial_readiness_tab_state(config).checks_configured,
            can_send_report=initial_readiness_tab_state(config).can_send_report,
        )
    else:
        tab_state = initial_readiness_tab_state(_studio_config_for_content(content))
    _apply_readiness_tab_state(content, qt_widgets, tab_state)


def _run_readiness_check_from_ui(content: Any, qt_widgets: Any) -> None:
    from pipeline_inspector.maya.readiness_actions import (
        collect_maya_readiness_probes,
        run_readiness_check_action,
    )

    config = _studio_config_for_content(content)
    probes = collect_maya_readiness_probes()
    content._pipeline_inspector_readiness_probes = probes
    result = run_readiness_check_action(config, probes=probes)
    content._pipeline_inspector_readiness_report = result.report
    content._pipeline_inspector_readiness_tab_state = result.tab_state
    _apply_readiness_tab_state(content, qt_widgets, result.tab_state)


def _send_readiness_report_from_ui(
    content: Any,
    qt_widgets: Any,
    *,
    recipient: str,
) -> None:
    from pipeline_inspector.maya.readiness_actions import send_readiness_report_action

    config = _studio_config_for_content(content)
    report = getattr(content, "_pipeline_inspector_readiness_report", None)
    if report is None:
        _set_readiness_status(content, qt_widgets, "Run Machine Readiness before sending a report.")
        return
    result = send_readiness_report_action(
        config,
        report,
        recipient=recipient,
    )
    content._pipeline_inspector_readiness_tab_state = result.tab_state
    _apply_readiness_tab_state(content, qt_widgets, result.tab_state)


def _apply_readiness_tab_state(
    content: Any,
    qt_widgets: Any,
    tab_state: ReadinessTabState,
) -> None:
    readiness_tab = _readiness_tab_widget(content, qt_widgets)
    if readiness_tab is not None:
        update_readiness_tab(readiness_tab, qt_widgets, tab_state)


def _set_readiness_status(content: Any, qt_widgets: Any, message: str) -> None:
    stored_state = getattr(content, "_pipeline_inspector_readiness_tab_state", None)
    if stored_state is not None:
        tab_state = replace(stored_state, status_message=message)
    else:
        from pipeline_inspector.maya.readiness_actions import initial_readiness_tab_state

        tab_state = replace(
            initial_readiness_tab_state(_studio_config_for_content(content)),
            status_message=message,
        )
    content._pipeline_inspector_readiness_tab_state = tab_state
    _apply_readiness_tab_state(content, qt_widgets, tab_state)


def _readiness_tab_widget(content: Any, qt_widgets: Any) -> Any:
    tabs = _find_child(content, qt_widgets.QTabWidget, main_window.TAB_WIDGET_OBJECT_NAME)
    if tabs is None:
        return None
    count = getattr(tabs, "count", lambda: 0)()
    for index in range(count):
        widget = getattr(tabs, "widget", lambda _index: None)(index)
        object_name = getattr(widget, "objectName", lambda: "")()
        if not object_name:
            object_name = getattr(widget, "object_name", "")
        if widget is not None and object_name == READINESS_TAB_OBJECT_NAME:
            return widget
    return _find_child(content, qt_widgets.QWidget, READINESS_TAB_OBJECT_NAME)


def _current_scene_path() -> str:
    return str(_maya_cmds().file(query=True, sceneName=True) or "")


def _manifest_gate_from_ui(content: Any, qt_widgets: Any) -> None:
    if content is None:
        _show_information_dialog(
            qt_widgets,
            "Manifest Gate",
            "Open the Pipeline Inspector panel and validate the scene first.",
        )
        return
    snapshot = getattr(content, "_pipeline_inspector_snapshot", None)
    if snapshot is None:
        _validate_from_ui(content, qt_widgets, scan_scope="scene")
        snapshot = getattr(content, "_pipeline_inspector_snapshot", None)
    if snapshot is None:
        _show_information_dialog(
            qt_widgets,
            "Manifest Gate",
            "Validate the scene first, then export an approved manifest sidecar "
            "before running gate.",
        )
        return

    from pipeline_inspector.core.manifest_gate import evaluate_manifest_gate
    from pipeline_inspector.maya.commands import _approved_manifest_sidecar_path
    from pipeline_inspector.maya.validation_pipeline import compose_profiles
    from pipeline_inspector.reports.manifest import build_shader_manifest
    from pipeline_inspector.reports.manifest_diff_cli import load_manifest_json

    baseline_path = _approved_manifest_sidecar_path(snapshot)
    if not baseline_path:
        _show_information_dialog(
            qt_widgets,
            "Manifest Gate",
            "No approved manifest sidecar found. Use Reports в†’ Export Shader Manifest first.",
        )
        return

    profile_id = _selected_workflow_profile_id(content, qt_widgets)
    asset_class_id = _selected_asset_class_id(content, qt_widgets)
    profile = compose_profiles(profile_id, asset_class_id or None)
    old_manifest = load_manifest_json(Path(baseline_path))
    new_manifest = build_shader_manifest(snapshot)
    gate_result = evaluate_manifest_gate(
        old_manifest,
        new_manifest,
        policy=profile.manifest_diff_policy,
    )
    summary = gate_result.diff_summary
    reasons = gate_result.reasons
    if gate_result.blocked:
        message = "Manifest gate BLOCKED.\n\n" + "\n".join(f"- {reason}" for reason in reasons)
    else:
        message = (
            "Manifest gate PASSED.\n\n"
            f"New: {summary.get('new', 0)}, Changed: {summary.get('changed', 0)}, "
            f"Fingerprint changes: {summary.get('fingerprint_changes', 0)}."
        )
    _set_label_text(
        content,
        qt_widgets,
        main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
        message.replace("\n", " "),
    )
    _show_information_dialog(qt_widgets, "Manifest Gate", message)
    print(message)


def _show_information_dialog(
    qt_widgets: Any,
    title: str,
    message: str,
    *,
    singleton_key: str | None = None,
) -> None:
    from pipeline_inspector.ui.settings_widgets import show_maya_information_dialog

    show_maya_information_dialog(
        qt_widgets,
        title,
        message,
        singleton_key=singleton_key,
    )


def _revalidate_with_current_scope(content: Any, qt_widgets: Any) -> None:
    scan_scope = getattr(content, "_pipeline_inspector_scan_scope", "scene")
    failed_results = getattr(content, "_pipeline_inspector_failed_results", ())
    if not failed_results:
        return
    if getattr(content, "_pipeline_inspector_validate_running", False):
        content._pipeline_inspector_pending_revalidate = True
        # #region agent log
        _debug_validate_cycle_log(
            "ui_launcher._revalidate_with_current_scope",
            "revalidate queued while validate running",
            {
                "scan_scope": scan_scope,
                "failed_count": str(len(failed_results)),
                "cycle": str(getattr(content, _VALIDATE_CYCLE_ATTR, 0)),
            },
            hypothesis_id="H-LOOP2",
        )
        # #endregion
        return
    # #region agent log
    _debug_validate_cycle_log(
        "ui_launcher._revalidate_with_current_scope",
        "revalidate starting",
        {
            "scan_scope": scan_scope,
            "failed_count": str(len(failed_results)),
            "cycle": str(getattr(content, _VALIDATE_CYCLE_ATTR, 0)),
        },
        hypothesis_id="H-LOOP3",
    )
    # #endregion
    _validate_from_ui(content, qt_widgets, scan_scope=scan_scope)


def _next_validate_cycle(content: Any) -> int:
    cycle = int(getattr(content, _VALIDATE_CYCLE_ATTR, 0) or 0) + 1
    content._pipeline_inspector_validate_cycle = cycle
    return cycle


def _finish_validate_running(
    content: Any,
    qt_widgets: Any,
    *,
    reason: str,
) -> None:
    # #region agent log
    _debug_validate_cycle_log(
        "ui_launcher._finish_validate_running",
        "validate running cleared",
        {
            "reason": reason,
            "cycle": str(getattr(content, _VALIDATE_CYCLE_ATTR, 0)),
            "pending_revalidate": str(getattr(content, _PENDING_REVALIDATE_ATTR, False)),
        },
        hypothesis_id="H-LOOP1",
    )
    # #endregion
    content._pipeline_inspector_validate_running = False
    _set_validate_busy_state(content, qt_widgets, busy=False)
    if not getattr(content, _PENDING_REVALIDATE_ATTR, False):
        return
    content._pipeline_inspector_pending_revalidate = False
    # #region agent log
    _debug_validate_cycle_log(
        "ui_launcher._finish_validate_running",
        "flushing pending revalidate",
        {"cycle": str(getattr(content, _VALIDATE_CYCLE_ATTR, 0))},
        hypothesis_id="H-LOOP2",
    )
    # #endregion
    _revalidate_with_current_scope(content, qt_widgets)


def _selected_workflow_profile_id(content: Any, qt_widgets: Any) -> str:
    profile_dropdown = _find_child(
        content,
        qt_widgets.QComboBox,
        main_window.PROFILE_DROPDOWN_OBJECT_NAME,
    )
    if profile_dropdown is None:
        return "artist_relaxed"
    profile_id = main_window.combo_profile_id(profile_dropdown)
    return profile_id or "artist_relaxed"


def _selected_asset_class_id(content: Any, qt_widgets: Any) -> str:
    asset_class_dropdown = _find_child(
        content,
        qt_widgets.QComboBox,
        main_window.ASSET_CLASS_DROPDOWN_OBJECT_NAME,
    )
    if asset_class_dropdown is None:
        return ""
    return main_window.combo_profile_id(asset_class_dropdown)


def _selected_issue(content: Any) -> Any:
    return getattr(content, "_pipeline_inspector_selected_issue", None)


def _run_navigation_action(content: Any, qt_widgets: Any, action: str) -> None:
    from pipeline_inspector.maya import commands

    issue = _selected_issue(content)
    if issue is None:
        _set_label_text(
            content,
            qt_widgets,
            main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
            "Make Waive: select an issue in the table first.",
        )
        return
    snapshot = getattr(content, "_pipeline_inspector_snapshot", None)
    target_id = str(getattr(issue, "target_id", "") or "")
    node_name = str(getattr(issue, "node", "") or "")
    material_name = str(getattr(issue, "material", "") or "") or None
    # #region agent log
    _debug_nav_log_ui(
        "ui_launcher._run_navigation_action",
        "Navigation requested",
        {
            "action": action,
            "target_id": target_id,
            "node_name": node_name,
            "material_name": material_name or "",
            "has_snapshot": snapshot is not None,
            "prim_nodes": sum(
                1
                for node in getattr(snapshot, "nodes", ()) or ()
                if str(getattr(node, "id", "")).startswith("prim:")
            )
            if snapshot is not None
            else 0,
        },
        hypothesis_id="H6",
    )
    # #endregion
    try:
        if action == "select_node":
            result = commands.select_node_action(
                node_name,
                target_id=target_id,
                material_name=material_name,
                snapshot=snapshot,
            )
        elif action == "open_in_hypershade":
            result = commands.open_in_hypershade_action(
                node_name,
                material_name=material_name,
                target_id=target_id,
                snapshot=snapshot,
            )
        elif action == "copy_path":
            result = commands.copy_path_action(_issue_path(issue))
        elif action == "reveal_file":
            result = commands.reveal_file_action(_issue_path(issue))
        else:
            return
    except Exception as exc:  # noqa: BLE001
        _set_label_text(
            content,
            qt_widgets,
            main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
            str(exc),
        )
        return
    _set_label_text(
        content,
        qt_widgets,
        main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
        result.message,
    )
    # #region agent log
    _debug_nav_log_ui(
        "ui_launcher._run_navigation_action",
        "Navigation result",
        {
            "action": action,
            "succeeded": result.succeeded,
            "message": result.message,
            "target": result.target,
        },
        hypothesis_id="H6",
    )
    # #endregion


def _debug_nav_log_ui(
    location: str,
    message: str,
    data: dict[str, object],
    *,
    hypothesis_id: str,
) -> None:
    _debug_health_log(location, message, data, hypothesis_id=hypothesis_id)


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
    from pipeline_inspector.maya import commands

    issue = _selected_issue(content)
    if issue is None:
        _set_label_text(
            content,
            qt_widgets,
            main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
            "Make Waive: select an issue in the table first.",
        )
        return
    try:
        result = commands.waive_issue_action(
            issue,
            reason="Approved from Maya Pipeline Inspector UI.",
        )
    except Exception as exc:  # noqa: BLE001
        _set_label_text(
            content,
            qt_widgets,
            main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
            str(exc),
        )
        return
    _set_label_text(
        content,
        qt_widgets,
        main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
        result.message,
    )
    _revalidate_with_current_scope(content, qt_widgets)


def _refresh_waiver_manager(content: Any, qt_widgets: Any) -> None:
    from pipeline_inspector.maya import commands

    try:
        listing = commands.list_waivers_action(
            getattr(content, "_pipeline_inspector_scene_path", None),
        )
    except Exception as exc:  # noqa: BLE001
        _set_label_text(
            content,
            qt_widgets,
            WAIVER_STATUS_LABEL_OBJECT_NAME,
            f"Could not load waivers: {exc}",
        )
        return

    waivers = getattr(listing, "waivers", ())
    rows = waiver_rows_from_records(waivers)
    table = _find_child(content, qt_widgets.QTableWidget, WAIVER_TABLE_OBJECT_NAME)
    if table is not None:
        table.setSortingEnabled(False)
        populate_waiver_table(qt_widgets, table, rows)
        table.setSortingEnabled(True)

    content._pipeline_inspector_waiver_rows = rows
    content._pipeline_inspector_waivers = tuple(waivers)
    content._pipeline_inspector_waiver_sidecar_path = getattr(listing, "path", "")
    _set_label_text(
        content,
        qt_widgets,
        WAIVER_STATUS_LABEL_OBJECT_NAME,
        waiver_summary_text(rows, sidecar_path=getattr(listing, "path", "")),
    )
    _on_waiver_row_selected(content, qt_widgets)


def _revoke_selected_waiver_from_ui(content: Any, qt_widgets: Any) -> None:
    from pipeline_inspector.maya import commands

    waiver_id = getattr(content, "_pipeline_inspector_selected_waiver_id", "")
    if not waiver_id:
        _set_label_text(
            content,
            qt_widgets,
            WAIVER_STATUS_LABEL_OBJECT_NAME,
            "Select a waiver row before revoking.",
        )
        return
    try:
        result = commands.revoke_waiver_action(
            waiver_id,
            getattr(content, "_pipeline_inspector_scene_path", None),
        )
    except Exception as exc:  # noqa: BLE001
        _set_label_text(content, qt_widgets, WAIVER_STATUS_LABEL_OBJECT_NAME, str(exc))
        return
    _set_label_text(content, qt_widgets, WAIVER_STATUS_LABEL_OBJECT_NAME, result.message)
    _refresh_waiver_manager(content, qt_widgets)
    _revalidate_with_current_scope(content, qt_widgets)


def _on_waiver_row_selected(content: Any, qt_widgets: Any) -> None:
    table = _find_child(content, qt_widgets.QTableWidget, WAIVER_TABLE_OBJECT_NAME)
    rows = getattr(content, "_pipeline_inspector_waiver_rows", ())
    if table is None or not rows:
        content._pipeline_inspector_selected_waiver_id = ""
        return

    current_row = getattr(table, "currentRow", lambda: -1)()
    if current_row is None or int(current_row) < 0 or int(current_row) >= len(rows):
        content._pipeline_inspector_selected_waiver_id = ""
        return

    content._pipeline_inspector_selected_waiver_id = rows[int(current_row)].waiver_id


def _resolution_probe_hint(snapshot: Any, asset_class_id: str) -> str:
    from pipeline_inspector.maya.validation_pipeline import ASSET_CLASS_NONE_ID

    if not asset_class_id or asset_class_id == ASSET_CLASS_NONE_ID:
        return ""
    unprobed: list[str] = []
    for dep in getattr(snapshot, "file_dependencies", ()) or ():
        if not getattr(dep, "exists", False):
            continue
        if getattr(dep, "max_dimension", None) is not None:
            continue
        label = dep.raw_path or dep.resolved_path or dep.node_id
        unprobed.append(label)
    if not unprobed:
        return ""
    sample = ", ".join(unprobed[:2])
    suffix = f" (+{len(unprobed) - 2} more)" if len(unprobed) > 2 else ""
    return (
        f" Resolution skipped for {len(unprobed)} texture(s) вЂ” format not probed or unreadable:"
        f" {sample}{suffix}."
    )


def _populate_validation_result(content: Any, qt_widgets: Any, result: Any) -> None:
    health = result.health_score
    # region agent log
    _debug_health_log(
        "ui_launcher.py:_populate_validation_result",
        "gui validation health score",
        {
            "gui_health": health.score,
            "profile_id": getattr(result, "profile_id", ""),
            "scan_scope": getattr(result, "scan_scope", ""),
            "failed_count": sum(
                1 for item in getattr(result, "results", ()) if item.status == "failed"
            ),
        },
        hypothesis_id="H1",
    )
    # endregion
    _set_label_text(
        content,
        qt_widgets,
        main_window.HEALTH_SCORE_LABEL_OBJECT_NAME,
        f"Health: {health.score} / 100",
    )
    main_window.update_severity_count_indicators(
        content,
        qt_widgets,
        critical_count=int(health.critical),
        error_count=int(health.error),
        warning_count=int(health.warning),
        info_count=int(health.info),
    )
    failed_results = tuple(item for item in result.results if item.status == "failed")
    deadline_blockers = sum(1 for item in failed_results if getattr(item, "block_deadline", False))
    publish_blockers = sum(1 for item in failed_results if getattr(item, "block_publish", False))
    main_window.update_block_status_indicators(
        content,
        qt_widgets,
        block_publish=bool(health.block_publish),
        block_deadline=bool(health.block_deadline),
        publish_blocker_count=publish_blockers,
        deadline_blocker_count=deadline_blockers,
    )
    description = result.message
    snapshot = (
        getattr(result, "snapshot", None)
        or getattr(content, "_pipeline_inspector_snapshot", None)
    )
    asset_class_id = _selected_asset_class_id(content, qt_widgets)
    if snapshot is not None:
        description += _resolution_probe_hint(snapshot, asset_class_id)
    _set_label_text(content, qt_widgets, main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME, description)

    rows = tuple(_issue_row_from_result(item) for item in failed_results)
    table = _find_child(content, qt_widgets.QTableWidget, main_window.ISSUES_TABLE_OBJECT_NAME)
    if table is not None:
        table.setSortingEnabled(False)
        main_window.populate_issues_table(qt_widgets, table, rows)
        table.setSortingEnabled(True)
        _store_validation_state(content, failed_results, rows, result)

    _update_severity_filter_options(content, qt_widgets, rows)
    _update_owner_filter_options(content, qt_widgets, rows)
    _restore_issue_filter_controls(content, qt_widgets)
    _refresh_issues_table_view(content, qt_widgets)

    display_results = getattr(
        content,
        "_pipeline_inspector_display_failed_results",
        failed_results,
    )
    _populate_first_issue_details(content, qt_widgets, display_results)
    _refresh_waiver_manager(content, qt_widgets)


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
        prefs = read_issue_filter_prefs(content)
        options = list(main_window.severity_filter_options(rows))
        clear = getattr(severity_filter, "clear", None)
        if clear is not None:
            clear()
        add_items = getattr(severity_filter, "addItems", None)
        if add_items is not None:
            add_items(options)
        apply_combo_preference(
            severity_filter,
            options,
            prefs.severity,
            fallback=main_window.ALL_SEVERITIES_LABEL,
        )
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
        prefs = read_issue_filter_prefs(content)
        options = list(main_window.owner_filter_options(rows))
        clear = getattr(owner_filter, "clear", None)
        if clear is not None:
            clear()
        add_items = getattr(owner_filter, "addItems", None)
        if add_items is not None:
            add_items(options)
        apply_combo_preference(
            owner_filter,
            options,
            prefs.owner,
            fallback=main_window.ALL_OWNERS_LABEL,
        )
    finally:
        if block_signals is not None:
            block_signals(False)


def _store_validation_state(
    content: Any,
    failed_results: tuple[Any, ...],
    rows: tuple[main_window.IssueTableRow, ...],
    result: Any,
) -> None:
    content._pipeline_inspector_failed_results = failed_results
    content._pipeline_inspector_issue_rows = rows
    content._pipeline_inspector_fix_plan = getattr(result, "fix_plan", None)
    content._pipeline_inspector_snapshot = getattr(result, "snapshot", None)
    content._pipeline_inspector_results = getattr(result, "results", ())
    content._pipeline_inspector_rules = tuple(getattr(result, "rules", ()) or ())
    content._pipeline_inspector_profile_id = getattr(result, "profile_id", "")
    content._pipeline_inspector_asset_class_id = getattr(result, "asset_class_id", "")
    content._pipeline_inspector_summary = getattr(result, "summary", None)
    snapshot = getattr(result, "snapshot", None)
    content._pipeline_inspector_scene_path = getattr(snapshot, "scene_path", "") if snapshot else ""
    _populate_fix_queue(content, result)


def _populate_fix_queue(content: Any, result: Any) -> None:
    fix_plan = getattr(result, "fix_plan", None)
    actions = getattr(fix_plan, "actions", ())
    # #region agent log
    _debug_fix_queue_log(
        "ui_launcher._populate_fix_queue",
        "Fix queue populated",
        {
            "action_count": len(actions),
            "usd_actions": sum(
                1 for action in actions if str(action.target_id).startswith("prim:")
            ),
            "scene_usd_actions": sum(
                1
                for action in actions
                if action.fix_type in {
                    "set_default_prim",
                    "set_attr",
                    "normalize_path",
                    "relink_path",
                }
                and action.target_kind in {"scene", "graph"}
            ),
            "unblocked": sum(1 for action in actions if not action.blocked),
            "fix_types": "|".join(sorted({action.fix_type for action in actions})),
            "texture_rename_blocked": sum(
                1
                for action in actions
                if action.fix_type == "rename_texture_file" and action.blocked
            ),
            "texture_rename_unblocked": sum(
                1
                for action in actions
                if action.fix_type == "rename_texture_file" and not action.blocked
            ),
            "texture_rename_block_reasons": "|".join(
                sorted(
                    {
                        reason
                        for action in actions
                        if action.fix_type == "rename_texture_file" and action.blocked
                        for reason in action.block_reasons
                    }
                )
            ),
        },
        hypothesis_id="H4",
    )
    # #endregion
    fix_rows = tuple(
        FixQueueRow(
            selected=False,
            title=action.title,
            risk=action.risk,
            target_node=action.target_node,
            target_attr=str(action.target_attr or ""),
            before_value=str(action.before_value),
            after_value=str(action.after_value),
            fix_id=action.fix_id,
            blocked=action.blocked,
            requires_confirmation=action.risk == "high" or action.requires_supervisor,
        )
        for action in actions
    )
    content._pipeline_inspector_fix_rows = fix_rows
    qt_widgets = load_qt_widgets()
    table = _find_child(content, qt_widgets.QTableWidget, FIX_QUEUE_TABLE_OBJECT_NAME)
    if table is not None:
        populate_fix_queue(
            qt_widgets,
            table,
            fix_rows,
            on_selection_changed=lambda: _sync_fix_queue_selection(content, qt_widgets),
        )
    _refresh_fix_queue_confirmation_label(content, qt_widgets, fix_rows)


def _refresh_fix_queue_confirmation_label(
    content: Any,
    qt_widgets: Any,
    rows: tuple[FixQueueRow, ...],
    *,
    selected_rows: Optional[tuple[FixQueueRow, ...]] = None,
) -> None:
    label = _find_child(
        content,
        qt_widgets.QLabel,
        FIX_QUEUE_RISKY_CONFIRMATION_LABEL_OBJECT_NAME,
    )
    if label is not None:
        update_risky_confirmation_label(label, rows, selected_rows=selected_rows)


def _restore_issue_filter_controls(content: Any, qt_widgets: Any) -> None:
    prefs = read_issue_filter_prefs(content)
    view_filter = _find_child(
        content,
        qt_widgets.QComboBox,
        main_window.ISSUES_VIEW_FILTER_OBJECT_NAME,
    )
    sort_dropdown = _find_child(
        content,
        qt_widgets.QComboBox,
        main_window.ISSUES_SORT_DROPDOWN_OBJECT_NAME,
    )
    apply_combo_preference(
        view_filter,
        (
            main_window.ALL_ISSUES_LABEL,
            main_window.BLOCKING_ONLY_LABEL,
            main_window.AUTO_FIXABLE_LABEL,
        ),
        prefs.view,
        fallback=main_window.ALL_ISSUES_LABEL,
    )
    apply_combo_preference(
        sort_dropdown,
        main_window.ISSUES_SORT_KEYS,
        prefs.sort,
        fallback="severity",
    )


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
        item_double_clicked = getattr(table, "itemDoubleClicked", None)
        double_connect = getattr(item_double_clicked, "connect", None)
        if double_connect is not None:
            double_connect(
                lambda item: _on_issue_row_double_clicked(
                    content,
                    qt_widgets,
                    int(getattr(item, "row", lambda: -1)()),
                )
            )
    if severity_filter is not None:
        current_text_changed = getattr(severity_filter, "currentTextChanged", None)
        connect = getattr(current_text_changed, "connect", None)
        if connect is not None:
            connect(lambda *_: _on_issue_filters_changed(content, qt_widgets))
    if sort_dropdown is not None:
        current_text_changed = getattr(sort_dropdown, "currentTextChanged", None)
        connect = getattr(current_text_changed, "connect", None)
        if connect is not None:
            connect(lambda *_: _on_issue_filters_changed(content, qt_widgets))
    if owner_filter is not None:
        current_text_changed = getattr(owner_filter, "currentTextChanged", None)
        connect = getattr(current_text_changed, "connect", None)
        if connect is not None:
            connect(lambda *_: _on_issue_filters_changed(content, qt_widgets))
    if view_filter is not None:
        current_text_changed = getattr(view_filter, "currentTextChanged", None)
        connect = getattr(current_text_changed, "connect", None)
        if connect is not None:
            connect(lambda *_: _on_issue_filters_changed(content, qt_widgets))


def _layout_persistence_enabled(content: Any) -> bool:
    density = str(
        getattr(content, "_pipeline_inspector_ui_density", "comfortable") or "comfortable"
    )
    return density != "compact"


def _tracked_table_object_names() -> tuple[str, ...]:
    from pipeline_inspector.ui.fix_queue import FIX_QUEUE_TABLE_OBJECT_NAME
    from pipeline_inspector.ui.readiness_tab import READINESS_RESULTS_TABLE_OBJECT_NAME
    from pipeline_inspector.ui.waiver_manager import WAIVER_TABLE_OBJECT_NAME

    return (
        main_window.ISSUES_TABLE_OBJECT_NAME,
        FIX_QUEUE_TABLE_OBJECT_NAME,
        WAIVER_TABLE_OBJECT_NAME,
        READINESS_RESULTS_TABLE_OBJECT_NAME,
    )


def _restore_table_column_widths_from_session(
    content: Any,
    qt_widgets: Any,
    panel_session: Any,
) -> None:
    if not _layout_persistence_enabled(content):
        return

    from pipeline_inspector.ui.table_column_persistence import apply_table_column_widths

    widths_by_table = getattr(panel_session, "table_column_widths", {}) or {}
    for table_key in _tracked_table_object_names():
        widths = widths_by_table.get(table_key)
        if not widths:
            continue
        table = _find_child(content, qt_widgets.QTableWidget, table_key)
        if table is None:
            continue
        apply_table_column_widths(table, qt_widgets, widths)


def _wire_table_column_persistence(content: Any, qt_widgets: Any) -> None:
    from pipeline_inspector.ui.table_column_persistence import wire_table_column_persistence

    enabled = _layout_persistence_enabled(content)

    def _persist_widths(table_key: str, widths: tuple[int, ...]) -> None:
        remember_table_column_widths(table_key, widths)

    for table_key in _tracked_table_object_names():
        table = _find_child(content, qt_widgets.QTableWidget, table_key)
        if table is None:
            continue
        wire_table_column_persistence(
            table,
            qt_widgets,
            table_key=table_key,
            on_widths_changed=_persist_widths,
            enabled=enabled,
        )


def _wire_validate_splitter_persistence(content: Any, qt_widgets: Any) -> None:
    splitter = _find_child(
        content,
        qt_widgets.QWidget,
        main_window.VALIDATE_ISSUES_SPLITTER_OBJECT_NAME,
    )
    if splitter is None:
        return

    density = str(
        getattr(content, "_pipeline_inspector_ui_density", "comfortable") or "comfortable"
    )
    set_sizes = getattr(splitter, "setSizes", None)
    saved_sizes = getattr(content, VALIDATE_SPLITTER_SIZES_ATTR, None)
    if density != "compact" and set_sizes is not None and saved_sizes:
        set_sizes([int(size) for size in saved_sizes])

    def _persist_splitter_sizes(*_args: Any) -> None:
        if str(getattr(content, "_pipeline_inspector_ui_density", "comfortable")) == "compact":
            return
        sizes_fn = getattr(splitter, "sizes", None)
        if sizes_fn is None:
            return
        sizes = tuple(int(size) for size in sizes_fn())
        if len(sizes) >= 2 and sizes[1] >= main_window.DETAILS_PANEL_MIN_WIDTH:
            setattr(content, VALIDATE_SPLITTER_SIZES_ATTR, sizes)
            remember_validate_splitter_sizes(sizes)

    splitter_moved = getattr(splitter, "splitterMoved", None)
    connect = getattr(splitter_moved, "connect", None)
    if connect is not None:
        connect(_persist_splitter_sizes)


def _wire_validate_tab_focus(content: Any, qt_widgets: Any) -> None:
    tab_widget = _find_child(content, qt_widgets.QTabWidget, main_window.TAB_WIDGET_OBJECT_NAME)
    if tab_widget is None:
        return
    current_changed = getattr(tab_widget, "currentChanged", None)
    connect = getattr(current_changed, "connect", None)
    if connect is not None:
        connect(lambda index: _on_validate_tab_focused(content, qt_widgets, int(index)))


def _on_validate_tab_focused(content: Any, qt_widgets: Any, tab_index: int) -> None:
    if tab_index != 0:
        return
    if not getattr(content, "_pipeline_inspector_issue_rows", ()):
        return
    _restore_issue_filter_controls(content, qt_widgets)
    _refresh_issues_table_view(content, qt_widgets)


def _on_issue_filters_changed(content: Any, qt_widgets: Any) -> None:
    read_issue_filter_prefs_from_widgets(content, qt_widgets, find_child=_find_child)
    _refresh_issues_table_view(content, qt_widgets)


def _on_issue_row_double_clicked(content: Any, qt_widgets: Any, row_index: int) -> None:
    display_results = getattr(
        content,
        "_pipeline_inspector_display_failed_results",
        getattr(content, "_pipeline_inspector_failed_results", ()),
    )
    if row_index < 0 or row_index >= len(display_results):
        return
    issue = display_results[row_index]
    content._pipeline_inspector_selected_issue = issue
    _populate_issue_details(content, qt_widgets, issue)
    _run_navigation_action(content, qt_widgets, "select_node")


def _wire_waiver_manager_interactions(content: Any, qt_widgets: Any) -> None:
    table = _find_child(content, qt_widgets.QTableWidget, WAIVER_TABLE_OBJECT_NAME)
    if table is not None:
        selection_model = getattr(table, "selectionModel", lambda: None)()
        selection_changed = getattr(selection_model, "selectionChanged", None)
        connect = getattr(selection_changed, "connect", None)
        if connect is not None:
            connect(lambda *_: _on_waiver_row_selected(content, qt_widgets))


def _fix_queue_table(content: Any, qt_widgets: Any) -> Any:
    return _find_child(content, qt_widgets.QTableWidget, FIX_QUEUE_TABLE_OBJECT_NAME)


def _sync_fix_queue_selection(content: Any, qt_widgets: Any) -> None:
    table = _fix_queue_table(content, qt_widgets)
    stored_rows = getattr(content, "_pipeline_inspector_fix_rows", ())
    if table is None or not stored_rows:
        return
    fix_rows = fix_rows_from_table(table, stored_rows)
    content._pipeline_inspector_fix_rows = fix_rows
    selected = selected_fix_rows(fix_rows)
    _refresh_fix_queue_confirmation_label(
        content,
        qt_widgets,
        fix_rows,
        selected_rows=selected,
    )


def _apply_selected_fixes_from_ui(content: Any, qt_widgets: Any) -> None:
    from pipeline_inspector.maya.fix_router import apply_fix_actions

    fix_plan = getattr(content, "_pipeline_inspector_fix_plan", None)
    table = _fix_queue_table(content, qt_widgets)
    stored_rows = getattr(content, "_pipeline_inspector_fix_rows", ())
    if fix_plan is None or not stored_rows or table is None:
        return
    fix_rows = fix_rows_from_table(table, stored_rows)
    content._pipeline_inspector_fix_rows = fix_rows
    checked = checked_fix_rows(fix_rows)
    selected = selected_fix_rows(fix_rows)
    if not checked:
        _set_label_text(
            content,
            qt_widgets,
            main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
            "No fixes selected. Check rows in the Select column on the Fixes tab first.",
        )
        return
    blocked_message = blocked_selection_message(fix_rows)
    if not selected:
        _set_label_text(
            content,
            qt_widgets,
            main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
            blocked_message
            or "Selected fixes are blocked and were not applied.",
        )
        return
    selected_ids = {row.fix_id for row in selected if row.fix_id}
    actions = tuple(
        action
        for action in fix_plan.actions
        if action.fix_id in selected_ids
    )
    if not actions:
        _set_label_text(
            content,
            qt_widgets,
            main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
            "No matching fix actions found for the selected queue rows.",
        )
        return
    if risky_fix_rows(selected):
        if not _guard_panel_capability(content, qt_widgets, "apply_risky_fixes"):
            return
        profile_id = getattr(content, "_pipeline_inspector_profile_id", "") or ""
        if not confirm_risky_fixes(qt_widgets, selected, profile_id=profile_id):
            _set_label_text(
                content,
                qt_widgets,
                main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
                "High-risk fixes were not applied.",
            )
            return
    allow_high_risk = bool(risky_fix_rows(selected))
    report = apply_fix_actions(
        actions,
        allow_high_risk=allow_high_risk,
        allow_referenced=True,
        allow_locked=True,
        studio_environment=_studio_environment_from_content(content),
    )
    _persist_fix_apply_audit(content, report)
    _set_label_text(
        content,
        qt_widgets,
        main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
        _format_fix_apply_message(report, selected_count=len(selected)),
    )
    # #region agent log
    _debug_validate_cycle_log(
        "ui_launcher._apply_selected_fixes_from_ui",
        "fix apply finished, triggering revalidate",
        {
            "selected_count": str(len(selected)),
            "cycle": str(getattr(content, _VALIDATE_CYCLE_ATTR, 0)),
            "validate_running": str(
                getattr(content, "_pipeline_inspector_validate_running", False)
            ),
        },
        hypothesis_id="H-LOOP3",
    )
    # #endregion
    _revalidate_with_current_scope(content, qt_widgets)


def _apply_safe_fixes_from_ui(content: Any, qt_widgets: Any) -> None:
    from pipeline_inspector.core.fix_plan import NAMING_FIX_TYPE, TEXTURE_FILE_FIX_TYPE
    from pipeline_inspector.maya.fix_router import apply_fix_actions
    from pipeline_inspector.ui.fix_queue import HIGH_RISK, MEDIUM_RISK

    fix_plan = getattr(content, "_pipeline_inspector_fix_plan", None)
    if fix_plan is None:
        return

    usd_medium_safe_fix_types = frozenset({"normalize_path", "relink_path"})

    def _include_apply_safe_action(action: Any) -> bool:
        if action.requires_supervisor:
            return False
        if action.risk == HIGH_RISK:
            return False
        if action.risk == MEDIUM_RISK:
            if action.fix_type == TEXTURE_FILE_FIX_TYPE or (
                action.fix_type in usd_medium_safe_fix_types
                and (
                    str(action.target_id).startswith("prim:")
                    or action.target_kind == "file_dependency"
                )
            ):
                pass
            else:
                return False
        if action.blocked:
            return bool(
                action.fix_type == NAMING_FIX_TYPE
                and (action.referenced or action.requires_reference_edit)
            )
        return True

    actions = tuple(
        action
        for action in fix_plan.actions
        if _include_apply_safe_action(action)
    )
    if not actions:
        _set_label_text(
            content,
            qt_widgets,
            main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
            "No safe fixes available. Referenced, locked, medium/high-risk, "
            "or unplannable fixes are skipped.",
        )
        return
    report = apply_fix_actions(
        actions,
        allow_referenced=True,
        allow_locked=True,
        studio_environment=_studio_environment_from_content(content),
    )
    _persist_fix_apply_audit(content, report)
    _set_label_text(
        content,
        qt_widgets,
        main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
        _format_fix_apply_message(report, selected_count=len(actions)),
    )
    # #region agent log
    _debug_validate_cycle_log(
        "ui_launcher._apply_safe_fixes_from_ui",
        "fix apply finished, triggering revalidate",
        {
            "action_count": str(len(actions)),
            "cycle": str(getattr(content, _VALIDATE_CYCLE_ATTR, 0)),
            "validate_running": str(
                getattr(content, "_pipeline_inspector_validate_running", False)
            ),
        },
        hypothesis_id="H-LOOP3",
    )
    # #endregion
    _revalidate_with_current_scope(content, qt_widgets)


def _persist_fix_apply_audit(content: Any, report: Any) -> None:
    from pipeline_inspector.maya.validation_pipeline import persist_fix_apply_audit

    snapshot = getattr(content, "_pipeline_inspector_snapshot", None)
    scene_path = getattr(snapshot, "scene_path", "") if snapshot is not None else ""
    profile_id = getattr(content, "_pipeline_inspector_profile_id", "")
    _, session_dict = persist_fix_apply_audit(
        report,
        scene_path=scene_path,
        profile_id=profile_id,
    )
    content._pipeline_inspector_last_fix_audit = session_dict


def _on_issue_row_selected(content: Any, qt_widgets: Any) -> None:
    table = _find_child(content, qt_widgets.QTableWidget, main_window.ISSUES_TABLE_OBJECT_NAME)
    display_results = getattr(
        content,
        "_pipeline_inspector_display_failed_results",
        getattr(content, "_pipeline_inspector_failed_results", ()),
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
    content._pipeline_inspector_selected_issue = selected
    _populate_issue_details(content, qt_widgets, selected)


def _refresh_issues_table_view(content: Any, qt_widgets: Any) -> None:
    rows = getattr(content, "_pipeline_inspector_issue_rows", ())
    failed_results = getattr(content, "_pipeline_inspector_failed_results", ())
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
    from pipeline_inspector.user_config import DEFAULT_MAX_ISSUES_DISPLAYED

    max_issues = int(
        getattr(content, "_pipeline_inspector_max_issues_displayed", DEFAULT_MAX_ISSUES_DISPLAYED)
    )
    pairs = pairs[: max(max_issues, 1)]
    display_rows = tuple(row for row, _ in pairs)
    display_results = tuple(result for _, result in pairs)

    table = _find_child(content, qt_widgets.QTableWidget, main_window.ISSUES_TABLE_OBJECT_NAME)
    if table is None:
        return
    table.setSortingEnabled(False)
    main_window.populate_issues_table(qt_widgets, table, display_rows)
    table.setSortingEnabled(True)
    content._pipeline_inspector_display_failed_results = display_results


def _populate_issue_details(content: Any, qt_widgets: Any, issue: Any) -> None:
    fix_action = _fix_action_for_issue(content, issue)
    state = main_window.IssueDetailsState(
        message=str(issue.message),
        why=str(issue.why),
        current_value=str(issue.current_value),
        expected_value=str(issue.expected_value),
        graph_trace=" -> ".join(str(item) for item in issue.graph_trace) or "N/A",
        reference_safety=_reference_safety_text(content, issue, fix_action),
        fix_available=bool(issue.auto_fix_available),
        fix_description=_fix_description_text(issue, fix_action),
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
        main_window.DETAILS_REFERENCE_LABEL_OBJECT_NAME,
        state.reference_safety,
    )
    _set_label_text(
        content,
        qt_widgets,
        main_window.DETAILS_FIX_LABEL_OBJECT_NAME,
        f"Fix Available: {_yes_no(state.fix_available)}   {state.fix_description}",
    )


def _fix_action_for_issue(content: Any, issue: Any) -> Any:
    fix_plan = getattr(content, "_pipeline_inspector_fix_plan", None)
    if fix_plan is None:
        return None
    issue_node = str(getattr(issue, "node", "") or "")
    for action in getattr(fix_plan, "actions", ()):
        if getattr(action, "rule_id", "") != getattr(issue, "rule_id", ""):
            continue
        target_node = str(getattr(action, "target_node", "") or "")
        if issue_node and target_node and issue_node in {target_node, target_node.split("|")[-1]}:
            return action
        if issue_node and issue_node == target_node:
            return action
    for action in getattr(fix_plan, "actions", ()):
        if getattr(action, "rule_id", "") == getattr(issue, "rule_id", ""):
            return action
    return None


def _node_snapshot_for_issue(content: Any, issue: Any) -> Any:
    snapshot = getattr(content, "_pipeline_inspector_snapshot", None)
    if snapshot is None:
        return None
    issue_node = str(getattr(issue, "node", "") or "")
    target_id = str(getattr(issue, "target_id", "") or "")
    for node in getattr(snapshot, "nodes", ()):
        candidates = {
            str(getattr(node, "id", "") or ""),
            str(getattr(node, "name", "") or ""),
            str(getattr(node, "full_name", "") or ""),
        }
        if issue_node in candidates or target_id in candidates:
            return node
    return None


def _reference_safety_text(content: Any, issue: Any, fix_action: Any) -> str:
    referenced = bool(getattr(fix_action, "referenced", False))
    locked = bool(getattr(fix_action, "locked", False))
    reference_path = getattr(fix_action, "reference_path", None)
    blocked = bool(getattr(fix_action, "blocked", False))
    block_reasons = list(getattr(fix_action, "block_reasons", ()) or ())

    node = _node_snapshot_for_issue(content, issue)
    if node is not None:
        referenced = referenced or bool(getattr(node, "referenced", False))
        locked = locked or bool(getattr(node, "locked", False))
        reference_path = reference_path or getattr(node, "reference_path", None)

    if referenced:
        path_label = str(reference_path or "unknown reference")
        requires_edit = bool(getattr(fix_action, "requires_reference_edit", False))
        if requires_edit and not locked:
            return (
                "Reference safety: referenced node "
                f"({path_label}). Fixes apply here as reference edits."
            )
        blocked_here = blocked or "target_locked" in block_reasons
        suffix = " Fix blocked in this scene." if blocked_here else ""
        return f"Reference safety: referenced node ({path_label}).{suffix}"
    if locked:
        blocked_here = blocked or "target_locked" in block_reasons
        suffix = " Fix blocked in this scene." if blocked_here else ""
        return f"Reference safety: locked node.{suffix}"
    return "Reference safety: local node вЂ” safe fixes may apply when not blocked by risk policy."


def _fix_description_text(issue: Any, fix_action: Any) -> str:
    if fix_action is None:
        return str(getattr(issue, "fix_id", None) or "No safe fix selected.")
    parts = [
        str(getattr(fix_action, "fix_type", "") or getattr(issue, "fix_id", "")),
        f"risk={getattr(fix_action, 'risk', '')}",
    ]
    if getattr(fix_action, "blocked", False):
        reasons = ", ".join(getattr(fix_action, "block_reasons", ()) or ())
        parts.append(f"blocked ({reasons or 'policy'})")
    return " ".join(part for part in parts if part)


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
            reference_safety="Reference safety: N/A",
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
            main_window.DETAILS_REFERENCE_LABEL_OBJECT_NAME,
            state.reference_safety,
        )
        _set_label_text(
            content,
            qt_widgets,
            main_window.DETAILS_FIX_LABEL_OBJECT_NAME,
            f"Fix Available: {_yes_no(state.fix_available)}   {state.fix_description}",
        )
        return

    _populate_issue_details(content, qt_widgets, failed_results[0])
    content._pipeline_inspector_selected_issue = failed_results[0]


def _wire_validate_shortcuts(content: Any, qt_widgets: Any, panel_state: dict[str, Any]) -> None:
    shortcut_class = getattr(qt_widgets, "QShortcut", None)
    key_sequence = getattr(qt_widgets, "QKeySequence", None)
    if shortcut_class is None or key_sequence is None:
        return
    shortcut = shortcut_class(key_sequence("F5"), content)
    activated = getattr(shortcut, "activated", None)
    connect = getattr(activated, "connect", None)
    if connect is None:
        return
    connect(
        lambda: _validate_from_ui(
            _panel_content(panel_state),
            qt_widgets,
            scan_scope="scene",
        )
    )


def _update_validation_chrome_labels(content: Any, qt_widgets: Any, result: Any) -> None:
    snapshot = getattr(result, "snapshot", None)
    scene_path = getattr(snapshot, "scene_path", "") if snapshot else ""
    scanned_at_utc = getattr(snapshot, "scanned_at_utc", "") if snapshot else ""
    scan_scope = getattr(content, "_pipeline_inspector_scan_scope", "scene")
    profile_id = getattr(result, "profile_id", "") or _selected_workflow_profile_id(
        content,
        qt_widgets,
    )
    asset_class_id = getattr(result, "asset_class_id", "") or _selected_asset_class_id(
        content,
        qt_widgets,
    )

    content._pipeline_inspector_last_validated_at = scanned_at_utc
    content._pipeline_inspector_scene_path = scene_path
    content._pipeline_inspector_last_validation_result = result

    _set_label_text(
        content,
        qt_widgets,
        main_window.SCENE_NAME_LABEL_OBJECT_NAME,
        main_window.format_scene_display_name(scene_path),
    )
    _set_label_text(
        content,
        qt_widgets,
        main_window.PROFILE_CHIP_LABEL_OBJECT_NAME,
        main_window.format_profile_chip_text(
            main_window.profile_display_name(profile_id),
            profile_id,
        ),
    )
    _set_label_text(
        content,
        qt_widgets,
        main_window.ASSET_CLASS_CHIP_LABEL_OBJECT_NAME,
        main_window.format_asset_class_chip_text(
            main_window.asset_class_display_name(asset_class_id),
        ),
    )
    _set_label_text(
        content,
        qt_widgets,
        main_window.LAST_VALIDATED_LABEL_OBJECT_NAME,
        main_window.format_last_validated_display(scanned_at_utc),
    )
    _set_label_text(
        content,
        qt_widgets,
        main_window.SCAN_SCOPE_LABEL_OBJECT_NAME,
        main_window.format_scan_scope_display(scan_scope),
    )
    _set_reports_status_label(
        content,
        qt_widgets,
        main_window.build_reports_status_text(
            scene_path=scene_path,
            scanned_at_utc=scanned_at_utc,
            scan_scope=scan_scope,
        ),
    )


def _set_reports_status_label(content: Any, qt_widgets: Any, message: str) -> None:
    _set_label_text(content, qt_widgets, main_window.REPORTS_STATUS_LABEL_OBJECT_NAME, message)


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
    content._pipeline_inspector_failed_results = ()
    content._pipeline_inspector_display_failed_results = ()
    content._pipeline_inspector_issue_rows = ()
    content._pipeline_inspector_fix_plan = None
    content._pipeline_inspector_fix_rows = ()
    content._pipeline_inspector_selected_issue = None
    content._pipeline_inspector_scan_scope = "scene"
    content._pipeline_inspector_snapshot = None
    content._pipeline_inspector_results = ()
    content._pipeline_inspector_profile_id = ""
    content._pipeline_inspector_asset_class_id = ""
    content._pipeline_inspector_last_validated_at = ""
    content._pipeline_inspector_last_validation_result = None
    content._pipeline_inspector_last_fix_audit = None

    _set_label_text(
        content,
        qt_widgets,
        main_window.HEALTH_SCORE_LABEL_OBJECT_NAME,
        "Health: 100 / 100",
    )
    main_window.update_severity_count_indicators(
        content,
        qt_widgets,
        critical_count=0,
        error_count=0,
        warning_count=0,
        info_count=0,
    )
    main_window.update_block_status_indicators(
        content,
        qt_widgets,
        block_publish=False,
        block_deadline=False,
    )
    _set_label_text(
        content,
        qt_widgets,
        main_window.SCENE_NAME_LABEL_OBJECT_NAME,
        main_window.format_scene_display_name(""),
    )
    _set_label_text(
        content,
        qt_widgets,
        main_window.PROFILE_CHIP_LABEL_OBJECT_NAME,
        main_window.format_profile_chip_text("Artist Relaxed", "artist_relaxed"),
    )
    _set_label_text(
        content,
        qt_widgets,
        main_window.ASSET_CLASS_CHIP_LABEL_OBJECT_NAME,
        main_window.format_asset_class_chip_text(main_window.ASSET_CLASS_NONE_LABEL),
    )
    _set_label_text(
        content,
        qt_widgets,
        main_window.LAST_VALIDATED_LABEL_OBJECT_NAME,
        main_window.format_last_validated_display(""),
    )
    _set_label_text(
        content,
        qt_widgets,
        main_window.SCAN_SCOPE_LABEL_OBJECT_NAME,
        main_window.format_scan_scope_display(""),
    )
    _set_label_text(
        content,
        qt_widgets,
        main_window.VALIDATE_STATUS_LABEL_OBJECT_NAME,
        status_message,
    )
    _set_reports_status_label(
        content,
        qt_widgets,
        main_window.build_reports_status_text(),
    )

    issues_table = _find_child(
        content,
        qt_widgets.QTableWidget,
        main_window.ISSUES_TABLE_OBJECT_NAME,
    )
    if issues_table is not None:
        issues_table.setSortingEnabled(False)
        issues_table.setRowCount(0)
        issues_table.setSortingEnabled(True)

    fix_table = _fix_queue_table(content, qt_widgets)
    if fix_table is not None:
        populate_fix_queue(qt_widgets, fix_table, ())

    _populate_first_issue_details(content, qt_widgets, ())


def _find_child(content: Any, widget_type: Any, object_name: str) -> Any:
    from pipeline_inspector.ui.settings_widgets import find_child

    return find_child(content, widget_type, object_name)


def _set_label_text(content: Any, qt_widgets: Any, object_name: str, text: str) -> None:
    label = _find_child(content, qt_widgets.QLabel, object_name)
    if label is not None:
        label.setText(text)


def _format_fix_apply_message(report: Any, *, selected_count: int) -> str:
    applied = int(getattr(report, "applied_count", 0) or 0)
    blocked = int(getattr(report, "blocked_count", 0) or 0)
    failed = int(getattr(report, "failed_count", 0) or 0)
    message = f"Applied {applied} of {selected_count} selected fix(es)."
    if blocked:
        message += f" {blocked} blocked at apply time."
    if failed:
        message += f" {failed} failed."
    if applied == 0 and blocked == 0 and failed == 0:
        message = "No fixes were applied."
    return message


def _yes_no(value: bool) -> str:
    return "YES" if value else "NO"


def _studio_environment_from_content(content: Any) -> Any:
    user_config = getattr(content, "_pipeline_inspector_user_config", None)
    studio_config = getattr(user_config, "studio_config", None) if user_config else None
    if studio_config is None:
        return None
    from pipeline_inspector.maya.validation_pipeline import _studio_environment_for_validation

    return _studio_environment_for_validation(studio_config)


def _debug_fix_queue_log(
    location: str,
    message: str,
    data: dict[str, object],
    *,
    hypothesis_id: str,
) -> None:
    _debug_health_log(location, message, data, hypothesis_id=hypothesis_id)


def _debug_validate_job_log(
    location: str,
    message: str,
    data: dict[str, object],
    *,
    hypothesis_id: str,
) -> None:
    _debug_health_log(location, message, data, hypothesis_id=hypothesis_id)


def _debug_validate_cycle_log(
    location: str,
    message: str,
    data: dict[str, object],
    *,
    hypothesis_id: str,
) -> None:
    from pipeline_inspector.util.debug_log import write_agent_cycle_log

    write_agent_cycle_log(location, message, dict(data), hypothesis_id=hypothesis_id)


def _debug_health_log(
    location: str,
    message: str,
    data: dict[str, object],
    *,
    hypothesis_id: str,
) -> None:
    from pipeline_inspector.util.debug_log import write_debug_log

    write_debug_log(location, message, data, hypothesis_id=hypothesis_id)


def _print_export_result(result: Any) -> None:
    print(f"{result.message} {result.path}")
    content = _active_panel_content()
    if content is None:
        return
    path = str(getattr(result, "path", "") or "").strip()
    if not path:
        return
    qt_widgets = load_qt_widgets()
    scanned_at_utc = getattr(content, "_pipeline_inspector_last_validated_at", "")
    scene_path = getattr(content, "_pipeline_inspector_scene_path", "")
    scan_scope = getattr(content, "_pipeline_inspector_scan_scope", "")
    _set_reports_status_label(
        content,
        qt_widgets,
        main_window.build_reports_status_text(
            scene_path=scene_path,
            scanned_at_utc=scanned_at_utc,
            scan_scope=scan_scope,
            export_message=f"Exported: {path}",
        ),
    )


def _purge_obsolete_workspace_controls(cmds: Any) -> None:
    for name in OBSOLETE_WORKSPACE_CONTROL_NAMES:
        _purge_named_workspace_control(cmds, name)


def _purge_named_workspace_control(cmds: Any, name: str) -> None:
    if not _workspace_control_exists(cmds, name):
        _remove_workspace_control_state(cmds, name)
        return
    with suppress(Exception):
        cmds.workspaceControl(name, edit=True, visible=False)
    with suppress(Exception):
        cmds.workspaceControl(name, edit=True, close=True)
    with suppress(Exception):
        cmds.deleteUI(name, control=True)
    _remove_workspace_control_state(cmds, name)


def _remove_workspace_control_state(cmds: Any, name: str) -> None:
    with suppress(Exception):
        if cmds.workspaceControlState(name, query=True, exists=True):
            cmds.workspaceControlState(name, remove=True)


def _workspace_control_exists(cmds: Any, name: str | None = None) -> bool:
    control_name = name or WORKSPACE_CONTROL_NAME
    return bool(cmds.workspaceControl(control_name, query=True, exists=True))


def _maya_cmds() -> Any:
    try:
        from maya import cmds
    except ImportError as exc:
        raise RuntimeError("Maya UI can only be launched inside Autodesk Maya.") from exc
    return cmds
