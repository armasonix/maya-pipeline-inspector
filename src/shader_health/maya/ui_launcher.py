"""Maya dockable panel launcher."""
from __future__ import annotations

from typing import Any, Optional

from shader_health.maya.export_actions import (
    ExportActionResult,
    export_html_report,
    export_json_report,
    export_shader_manifest,
)
from shader_health.ui.main_window import (
    ExportActionCallbacks,
    PANEL_OBJECT_NAME,
    PANEL_TITLE,
    build_main_widget,
)
from shader_health.ui.qt import load_qt_widgets

WORKSPACE_CONTROL_NAME = f"{PANEL_OBJECT_NAME}WorkspaceControl"
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
        self.setObjectName(PANEL_OBJECT_NAME)
        self.setWindowTitle(PANEL_TITLE)

        layout = qt_widgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            build_main_widget(
                qt_widgets,
                export_callbacks=_export_action_callbacks(),
            )
        )

    panel_class = type(
        "ShaderHealthInspectorDock",
        (MayaQWidgetDockableMixin, qt_widgets.QWidget),
        {"__init__": init_panel, "__module__": __name__},
    )
    return panel_class()


def _export_action_callbacks() -> ExportActionCallbacks:
    return ExportActionCallbacks(
        on_export_json=_export_json_from_ui,
        on_export_html=_export_html_from_ui,
        on_export_manifest=_export_manifest_from_ui,
    )


def _export_json_from_ui() -> None:
    _print_export_result(export_json_report())


def _export_html_from_ui() -> None:
    _print_export_result(export_html_report())


def _export_manifest_from_ui() -> None:
    _print_export_result(export_shader_manifest())


def _print_export_result(result: ExportActionResult) -> None:
    print(f"{result.message} {result.path}")


def _workspace_control_exists(cmds: Any) -> bool:
    return bool(cmds.workspaceControl(WORKSPACE_CONTROL_NAME, query=True, exists=True))


def _maya_cmds() -> Any:
    try:
        from maya import cmds  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("Maya UI can only be launched inside Autodesk Maya.") from exc
    return cmds
