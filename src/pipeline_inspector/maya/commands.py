"""Maya command entrypoints for Pipeline Inspector."""
from __future__ import annotations

import importlib
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

from pipeline_inspector.core.waivers import (
    WaiverSidecar,
    create_waiver_from_result,
    load_waiver_sidecar,
    load_waiver_sidecar_optional,
    revoke_waiver,
    write_waiver_sidecar,
)
from pipeline_inspector.maya.navigation import (
    NavigationActionResult,
    copy_path,
    open_in_hypershade,
    reveal_file,
    select_node,
)
from pipeline_inspector.maya.ui_icons import (
    ICON_CHECK_FOR_UPDATES,
    ICON_CLOSE,
    ICON_DOCUMENTATION,
    ICON_FARM_CHECK,
    ICON_MAIN,
    ICON_READINESS_CHECK,
    ICON_REPORTS,
    ICON_SETTINGS,
    ICON_VALIDATE_SCENE,
    menu_item_image_kwargs,
    shelf_button_image_kwargs,
)
from pipeline_inspector.maya.ui_launcher import (
    close_panel,
    open_documentation_action,
    show_check_for_updates_panel,
    show_farm_check_panel,
    show_panel,
    show_readiness_check_panel,
    show_reports_panel,
    show_settings_panel,
    show_validate_scene_panel,
)
from pipeline_inspector.maya.validation_pipeline import (
    DEFAULT_PROFILE_ID,
    ValidationRunResult,
    resolve_waiver_sidecar_path,
    run_validation,
    run_validation_for_user,
)
from pipeline_inspector.user_config import UserPreferences

MENU_NAME = "pipelineInspectorMenu"
MENU_LABEL = "Pipeline Inspector"
OPEN_MENU_ITEM_LABEL = "Open Pipeline Inspector"
SETTINGS_MENU_ITEM_LABEL = "Settings"
VALIDATE_SCENE_MENU_ITEM_LABEL = "Validate Scene"
REPORTS_MENU_ITEM_LABEL = "Reports"
READINESS_CHECK_MENU_ITEM_LABEL = "Readiness Check"
FARM_CHECK_MENU_ITEM_LABEL = "Farm Check"
DOCUMENTATION_MENU_ITEM_LABEL = "Documentation"
CHECK_FOR_UPDATES_MENU_ITEM_LABEL = "Check for Updates"
CLOSE_MENU_ITEM_LABEL = "Close Pipeline Inspector"
SHELF_NAME = "PipelineInspector"
OPEN_SHELF_BUTTON_NAME = "pipelineInspectorShelfButton"
SETTINGS_SHELF_BUTTON_NAME = "pipelineInspectorSettingsShelfButton"
VALIDATE_SCENE_SHELF_BUTTON_NAME = "pipelineInspectorValidateSceneShelfButton"
REPORTS_SHELF_BUTTON_NAME = "pipelineInspectorReportsShelfButton"
READINESS_CHECK_SHELF_BUTTON_NAME = "pipelineInspectorReadinessCheckShelfButton"
FARM_CHECK_SHELF_BUTTON_NAME = "pipelineInspectorFarmCheckShelfButton"
DOCUMENTATION_SHELF_BUTTON_NAME = "pipelineInspectorDocumentationShelfButton"
CHECK_FOR_UPDATES_SHELF_BUTTON_NAME = "pipelineInspectorCheckForUpdatesShelfButton"
OPEN_SHELF_BUTTON_LABEL = OPEN_MENU_ITEM_LABEL
SETTINGS_SHELF_BUTTON_LABEL = SETTINGS_MENU_ITEM_LABEL
VALIDATE_SCENE_SHELF_BUTTON_LABEL = VALIDATE_SCENE_MENU_ITEM_LABEL
REPORTS_SHELF_BUTTON_LABEL = REPORTS_MENU_ITEM_LABEL
READINESS_CHECK_SHELF_BUTTON_LABEL = READINESS_CHECK_MENU_ITEM_LABEL
FARM_CHECK_SHELF_BUTTON_LABEL = FARM_CHECK_MENU_ITEM_LABEL
DOCUMENTATION_SHELF_BUTTON_LABEL = DOCUMENTATION_MENU_ITEM_LABEL
CHECK_FOR_UPDATES_SHELF_BUTTON_LABEL = CHECK_FOR_UPDATES_MENU_ITEM_LABEL
LEGACY_SHELF_BUTTON_LABEL = "Pipeline Inspector"
LEGACY_FARM_CHECK_SHELF_BUTTON_LABEL = "Pipeline Inspector Farm Check"
OPEN_SHELF_BUTTON_ANNOTATION = "Open Maya Pipeline Inspector"
SETTINGS_SHELF_BUTTON_ANNOTATION = "Open Pipeline Inspector settings."
VALIDATE_SCENE_SHELF_BUTTON_ANNOTATION = "Run Validate Scene."
REPORTS_SHELF_BUTTON_ANNOTATION = "Open the Reports tab."
READINESS_CHECK_SHELF_BUTTON_ANNOTATION = "Open the Readiness tab."
FARM_CHECK_SHELF_BUTTON_ANNOTATION = "Open the Farm tab."
DOCUMENTATION_SHELF_BUTTON_ANNOTATION = "Open Pipeline Inspector documentation in your browser."
CHECK_FOR_UPDATES_SHELF_BUTTON_ANNOTATION = "Check for Pipeline Inspector updates."
MAYA_MAIN_WINDOW = "MayaWindow"
OPEN_UI_PYTHON_COMMAND = "from pipeline_inspector.maya.commands import show_ui\nshow_ui()"
SETTINGS_UI_PYTHON_COMMAND = (
    "from pipeline_inspector.maya.commands import show_settings_ui\nshow_settings_ui()"
)
VALIDATE_SCENE_UI_PYTHON_COMMAND = (
    "from pipeline_inspector.maya.commands import show_validate_scene_ui\n"
    "show_validate_scene_ui()"
)
REPORTS_UI_PYTHON_COMMAND = (
    "from pipeline_inspector.maya.commands import show_reports_ui\nshow_reports_ui()"
)
READINESS_CHECK_UI_PYTHON_COMMAND = (
    "from pipeline_inspector.maya.commands import show_readiness_check_ui\n"
    "show_readiness_check_ui()"
)
FARM_CHECK_UI_PYTHON_COMMAND = (
    "from pipeline_inspector.maya.commands import show_farm_check_ui\nshow_farm_check_ui()"
)
DOCUMENTATION_UI_PYTHON_COMMAND = (
    "from pipeline_inspector.maya.commands import show_documentation_ui\n"
    "show_documentation_ui()"
)
CHECK_FOR_UPDATES_UI_PYTHON_COMMAND = (
    "from pipeline_inspector.maya.commands import show_check_for_updates_ui\n"
    "show_check_for_updates_ui()"
)


def show_ui() -> Any:
    """Open the dockable Maya Pipeline Inspector panel from script/menu/shelf."""

    return show_panel()


def show_farm_check_ui() -> Any:
    """Open the Farm tab and run deadline_critical preflight from menu/shelf."""

    return show_farm_check_panel()


def show_settings_ui() -> Any:
    """Open Pipeline Inspector settings from menu/shelf."""

    return show_settings_panel()


def show_validate_scene_ui() -> Any:
    """Open Validate and run Validate Scene from menu/shelf."""

    return show_validate_scene_panel()


def show_reports_ui() -> Any:
    """Open the Reports tab from menu/shelf."""

    return show_reports_panel()


def show_readiness_check_ui() -> Any:
    """Open the Readiness tab from menu/shelf."""

    return show_readiness_check_panel()


def show_check_for_updates_ui() -> Any:
    """Open Check for Updates from menu/shelf."""

    return show_check_for_updates_panel()


def show_documentation_ui() -> bool:
    """Open documentation from menu/shelf."""

    return open_documentation_action()


def close_ui(*, delete: bool = True) -> None:
    """Close the dockable Maya Pipeline Inspector panel."""

    close_panel(delete=delete)


def validate_scene_action(
    *,
    profile_id: str = DEFAULT_PROFILE_ID,
    asset_class_id: str = "",
    studio_config: Optional[Any] = None,
    extra_rule_paths: tuple[Path, ...] = (),
    user_config: Optional[UserPreferences] = None,
    session_rule_overrides: Optional[dict[str, Any]] = None,
) -> Any:
    """Validate the current Maya scene and return a UI-friendly result object."""

    return _validate(
        scan_scope="scene",
        profile_id=profile_id,
        asset_class_id=asset_class_id,
        studio_config=studio_config,
        extra_rule_paths=extra_rule_paths,
        user_config=user_config,
        session_rule_overrides=session_rule_overrides,
    )


def validate_selection_action(
    *,
    profile_id: str = DEFAULT_PROFILE_ID,
    asset_class_id: str = "",
    studio_config: Optional[Any] = None,
    extra_rule_paths: tuple[Path, ...] = (),
    user_config: Optional[UserPreferences] = None,
    session_rule_overrides: Optional[dict[str, Any]] = None,
) -> Any:
    """Validate the current Maya selection and return a UI-friendly result object."""

    return _validate(
        scan_scope="selection",
        profile_id=profile_id,
        asset_class_id=asset_class_id,
        studio_config=studio_config,
        extra_rule_paths=extra_rule_paths,
        user_config=user_config,
        session_rule_overrides=session_rule_overrides,
    )


def waive_issue_action(result: Any, *, reason: str, approved_by: str = "artist") -> Any:
    """Persist a waiver for a failed validation result and return the sidecar path."""

    if getattr(result, "status", "") != "failed":
        raise ValueError("Only failed issues can be waived.")
    snapshot_path = getattr(result, "_scene_path", None) or _current_scene_path()
    sidecar_path = resolve_waiver_sidecar_path(snapshot_path)
    if sidecar_path is None:
        raise ValueError("Save the scene before creating a waiver sidecar.")

    sidecar = (
        load_waiver_sidecar(sidecar_path)
        if sidecar_path.is_file()
        else WaiverSidecar()
    )
    now = datetime.now(timezone.utc)
    waiver = create_waiver_from_result(
        result,
        reason=reason,
        approved_by=approved_by,
        created_at_utc=now.isoformat().replace("+00:00", "Z"),
        expires_at_utc=(now + timedelta(days=30)).isoformat().replace("+00:00", "Z"),
    )
    updated = WaiverSidecar(waivers=(*sidecar.waivers, waiver))
    write_waiver_sidecar(sidecar_path, updated)
    return SimpleNamespace(
        action="waive_issue",
        succeeded=True,
        path=str(sidecar_path),
        message=f"Waiver saved to {sidecar_path.name}.",
    )


def list_waivers_action(scene_path: Optional[str] = None) -> Any:
    """Load waivers from the scene sidecar for UI display."""

    snapshot_path = scene_path or _current_scene_path()
    sidecar_path = resolve_waiver_sidecar_path(snapshot_path)
    if sidecar_path is None:
        return SimpleNamespace(
            action="list_waivers",
            succeeded=True,
            path="",
            waivers=(),
            message="Save the scene to locate the waiver sidecar.",
        )

    sidecar = load_waiver_sidecar_optional(sidecar_path)
    return SimpleNamespace(
        action="list_waivers",
        succeeded=True,
        path=str(sidecar_path),
        waivers=tuple(sidecar.waivers),
        message=f"Loaded {len(sidecar.waivers)} waiver(s) from {sidecar_path.name}.",
    )


def revoke_waiver_action(waiver_id: str, scene_path: Optional[str] = None) -> Any:
    """Remove one waiver from the scene sidecar."""

    snapshot_path = scene_path or _current_scene_path()
    sidecar_path = resolve_waiver_sidecar_path(snapshot_path)
    if sidecar_path is None:
        raise ValueError("Save the scene before revoking a waiver.")

    sidecar = load_waiver_sidecar_optional(sidecar_path)
    updated = revoke_waiver(sidecar, waiver_id)
    write_waiver_sidecar(sidecar_path, updated)
    return SimpleNamespace(
        action="revoke_waiver",
        succeeded=True,
        path=str(sidecar_path),
        message=f"Revoked waiver {waiver_id!r} in {sidecar_path.name}.",
    )


def select_node_action(
    node_name: str,
    *,
    target_id: str = "",
    material_name: Optional[str] = None,
    snapshot: Optional[Any] = None,
) -> NavigationActionResult:
    """Select a Maya node or USD prim from a UI action."""

    from pipeline_inspector.maya.usd_navigation import (
        is_usd_prim_target,
        resolve_usd_prim_path,
        select_usd_prim,
    )

    maya_cmds = _maya_cmds()
    maya_target = _resolve_maya_target_name(node_name, target_id)
    should_try_usd = is_usd_prim_target(target_id=target_id, node_name=node_name) or _looks_like_usd_prim_issue(
        target_id=target_id,
        node_name=node_name,
        snapshot=snapshot,
    )
    if should_try_usd:
        prim_path = resolve_usd_prim_path(
            target_id=target_id,
            node_name=node_name,
            material_name=material_name or "",
            snapshot=snapshot,
            cmds=maya_cmds,
        )
        if prim_path:
            return select_usd_prim(prim_path, cmds=maya_cmds)

    if maya_target and maya_cmds.objExists(maya_target):
        return select_node(maya_target)

    return select_node(maya_target or _maya_node_name(node_name))


def open_in_hypershade_action(
    node_name: str,
    *,
    material_name: Optional[str] = None,
    target_id: str = "",
    snapshot: Optional[Any] = None,
) -> NavigationActionResult:
    """Open Hypershade or the USD shader editor for an issue target."""

    from pipeline_inspector.maya.usd_navigation import (
        is_usd_prim_target,
        open_usd_shader_view,
        resolve_usd_prim_path,
    )

    maya_cmds = _maya_cmds()
    should_try_usd = is_usd_prim_target(target_id=target_id, node_name=node_name) or _looks_like_usd_prim_issue(
        target_id=target_id,
        node_name=node_name,
        snapshot=snapshot,
    )
    if should_try_usd:
        prim_path = resolve_usd_prim_path(
            target_id=target_id,
            node_name=node_name,
            material_name=material_name or "",
            snapshot=snapshot,
            cmds=maya_cmds,
        )
        if prim_path:
            return open_usd_shader_view(prim_path, cmds=maya_cmds)

    maya_target = _resolve_maya_target_name(node_name, target_id)
    candidates: list[str] = []
    if material_name:
        candidates.append(_maya_node_name(material_name))
    if maya_target:
        candidates.append(maya_target)
    elif node_name:
        candidates.append(_maya_node_name(node_name))
    target = next((name for name in candidates if maya_cmds.objExists(name)), None)
    if target is None:
        label = material_name or node_name or "node"
        return NavigationActionResult(
            action="open_in_hypershade",
            target=str(label),
            succeeded=False,
            message="Material or node does not exist.",
        )
    return open_in_hypershade(target)


def _resolve_maya_target_name(node_name: str, target_id: str) -> str:
    if str(target_id).startswith("node:"):
        return str(target_id).removeprefix("node:")
    if str(node_name).startswith("node:"):
        return str(node_name).removeprefix("node:")
    if node_name:
        return _maya_node_name(node_name)
    return ""


def _looks_like_usd_prim_issue(
    *,
    target_id: str = "",
    node_name: str = "",
    snapshot: Optional[Any],
) -> bool:
    from pipeline_inspector.maya.usd_navigation import is_usd_prim_target

    if is_usd_prim_target(target_id=target_id, node_name=node_name):
        return True
    if snapshot is None:
        return False
    nodes = getattr(snapshot, "nodes", ()) or ()
    if not any(str(node.id).startswith("prim:") for node in nodes):
        return False
    for node in nodes:
        if not str(node.id).startswith("prim:"):
            continue
        if node.name == node_name or node.full_name == node_name:
            return True
    return False


def open_attribute_editor_action(node_name: str) -> NavigationActionResult:
    """Deprecated alias kept for older callers."""

    return open_in_hypershade_action(node_name)


def copy_path_action(path: str) -> NavigationActionResult:
    """Copy a path from a UI action."""

    return copy_path(path)


def reveal_file_action(path: str) -> NavigationActionResult:
    """Reveal a file from a UI action where the host OS supports it."""

    return reveal_file(path)


def export_json_report_action(path: Optional[str] = None) -> Any:
    """Export a JSON report artifact from the current Maya scene."""

    return _export_json_report(path)


def export_html_report_action(path: Optional[str] = None) -> Any:
    """Export an HTML report artifact from the current Maya scene."""

    return _export_html_report(path)


def export_shader_manifest_action(path: Optional[str] = None) -> Any:
    """Export a shader manifest artifact from the current Maya scene."""

    return _export_shader_manifest(path)


def export_fix_plan_action(path: Optional[str] = None) -> Any:
    """Export a fix plan artifact from the current Maya scene."""

    return _export_fix_plan(path)


def export_manifest_diff_action(
    baseline_manifest_path: Optional[str] = None,
    *,
    json_path: Optional[str] = None,
    html_path: Optional[str] = None,
    prefer_approved_sidecar: bool = False,
) -> Any:
    """Export manifest diff artifacts against a user-selected baseline manifest."""

    return _export_manifest_diff_with_snapshot(
        None,
        baseline_manifest_path=baseline_manifest_path,
        json_path=json_path,
        html_path=html_path,
        prefer_approved_sidecar=prefer_approved_sidecar,
    )


def install_menu(parent: Optional[str] = None) -> str:
    """Install standalone Maya menu entries for Pipeline Inspector actions."""

    cmds = _maya_cmds()
    menu_parent = parent or MAYA_MAIN_WINDOW
    if cmds.menu(MENU_NAME, query=True, exists=True):
        cmds.deleteUI(MENU_NAME, menu=True)
    menu_name = cmds.menu(MENU_NAME, label=MENU_LABEL, parent=menu_parent, tearOff=True)
    _install_standalone_menu_item(
        cmds,
        menu_name,
        label=OPEN_MENU_ITEM_LABEL,
        command=lambda *_: show_ui(),
        icon_id=ICON_MAIN,
    )
    _install_standalone_menu_item(
        cmds,
        menu_name,
        label=SETTINGS_MENU_ITEM_LABEL,
        command=lambda *_: show_settings_ui(),
        icon_id=ICON_SETTINGS,
    )
    _install_standalone_menu_item(
        cmds,
        menu_name,
        label=VALIDATE_SCENE_MENU_ITEM_LABEL,
        command=lambda *_: show_validate_scene_ui(),
        icon_id=ICON_VALIDATE_SCENE,
    )
    _install_standalone_menu_item(
        cmds,
        menu_name,
        label=REPORTS_MENU_ITEM_LABEL,
        command=lambda *_: show_reports_ui(),
        icon_id=ICON_REPORTS,
    )
    _install_standalone_menu_item(
        cmds,
        menu_name,
        label=READINESS_CHECK_MENU_ITEM_LABEL,
        command=lambda *_: show_readiness_check_ui(),
        icon_id=ICON_READINESS_CHECK,
    )
    _install_standalone_menu_item(
        cmds,
        menu_name,
        label=FARM_CHECK_MENU_ITEM_LABEL,
        command=lambda *_: show_farm_check_ui(),
        icon_id=ICON_FARM_CHECK,
    )
    _install_standalone_menu_item(
        cmds,
        menu_name,
        label=DOCUMENTATION_MENU_ITEM_LABEL,
        command=lambda *_: show_documentation_ui(),
        icon_id=ICON_DOCUMENTATION,
    )
    _install_standalone_menu_item(
        cmds,
        menu_name,
        label=CHECK_FOR_UPDATES_MENU_ITEM_LABEL,
        command=lambda *_: show_check_for_updates_ui(),
        icon_id=ICON_CHECK_FOR_UPDATES,
    )
    cmds.menuItem(divider=True, parent=menu_name)
    _install_standalone_menu_item(
        cmds,
        menu_name,
        label=CLOSE_MENU_ITEM_LABEL,
        command=lambda *_: close_ui(),
        icon_id=ICON_CLOSE,
    )
    return str(menu_name)


def uninstall_menu() -> None:
    """Remove the Maya menu entry if it exists."""

    cmds = _maya_cmds()
    if cmds.menu(MENU_NAME, query=True, exists=True):
        cmds.deleteUI(MENU_NAME, menu=True)


def install_shelf(parent: Optional[str] = None) -> str:
    """Install or refresh the Pipeline Inspector shelf tab and buttons."""

    cmds = _maya_cmds()
    shelf_parent = parent or _maya_shelf_top_level()

    if not cmds.shelfLayout(SHELF_NAME, query=True, exists=True):
        cmds.shelfLayout(SHELF_NAME, parent=shelf_parent)

    _remove_legacy_shelf_buttons(cmds)
    for entry in _standalone_shelf_entries():
        _ensure_shelf_button(cmds, **entry)
    return SHELF_NAME


def uninstall_shelf() -> None:
    """Remove Pipeline Inspector shelf buttons, including legacy unnamed duplicates."""

    cmds = _maya_cmds()
    if not cmds.shelfLayout(SHELF_NAME, query=True, exists=True):
        return
    labels = tuple(entry["label"] for entry in _standalone_shelf_entries())
    labels += (LEGACY_SHELF_BUTTON_LABEL, LEGACY_FARM_CHECK_SHELF_BUTTON_LABEL)
    for label in labels:
        for child in _shelf_layout_children(cmds, SHELF_NAME):
            if not cmds.shelfButton(child, query=True, exists=True):
                continue
            if _shelf_button_label(cmds, child) != label:
                continue
            cmds.deleteUI(child, control=True)


def uninstall_ui() -> None:
    """Remove Pipeline Inspector UI entrypoints for the current session."""

    close_ui(delete=True)
    uninstall_shelf()
    uninstall_menu()


_UI_INSTALLED = False


def install_ui() -> None:
    """Install or refresh Maya UI entrypoints for the current session."""

    install_menu()
    install_shelf()
    global _UI_INSTALLED
    _UI_INSTALLED = True


def reset_ui_install_state() -> None:
    """Reset the install guard. Intended for tests and plugin unload."""

    global _UI_INSTALLED
    _UI_INSTALLED = False


def _validate(
    *,
    scan_scope: str,
    profile_id: str,
    asset_class_id: str = "",
    studio_config: Optional[Any] = None,
    extra_rule_paths: tuple[Path, ...] = (),
    user_config: Optional[UserPreferences] = None,
    session_rule_overrides: Optional[dict[str, Any]] = None,
) -> Any:
    from pipeline_inspector.maya.scanner import scan_scene, scan_selection, selection_node_names

    if scan_scope == "selection":
        selected = selection_node_names()
        if not selected:
            return _validation_error(
                "Nothing selected. Select geometry or shader nodes before validating.",
                action="validate_selection",
                scan_scope=scan_scope,
                profile_id=profile_id,
            )
        raw_snapshot = scan_selection()
        if not raw_snapshot.shading_engines:
            return _validation_error(
                "Selection has no assigned shader networks to validate.",
                action="validate_selection",
                scan_scope=scan_scope,
                profile_id=profile_id,
            )
    else:
        raw_snapshot = scan_scene()
    if user_config is not None:
        run = run_validation_for_user(
            raw_snapshot,
            user_config=user_config,
            scan_scope=scan_scope,
            profile_id=profile_id or None,
            asset_class_id=asset_class_id or None,
            studio_config=studio_config,
            session_rule_overrides=session_rule_overrides,
        )
    else:
        run = run_validation(
            raw_snapshot,
            profile_id=profile_id,
            asset_class_id=asset_class_id or None,
            scan_scope=scan_scope,
            studio_config=studio_config,
            extra_rule_paths=extra_rule_paths,
            session_rule_overrides=session_rule_overrides,
        )
    # #region agent log
    _debug_health_log_command(
        "commands._validate",
        "Maya validation finished",
        {
            "scan_scope": scan_scope,
            "snapshot_renderer": getattr(run.snapshot, "renderer", ""),
            "usd_metadata": getattr(run.snapshot, "usd_stage_metadata", None) is not None,
            "prim_nodes": sum(
                1 for node in getattr(run.snapshot, "nodes", []) if str(node.id).startswith("prim:")
            ),
            "failed_count": sum(1 for item in run.results if item.status == "failed"),
            "failed_rules": "|".join(
                sorted({item.rule_id for item in run.results if item.status == "failed"})[:12]
            ),
            "fix_unblocked": sum(
                1 for action in (run.fix_plan.actions if run.fix_plan else ()) if not action.blocked
            ),
        },
        hypothesis_id="H1",
    )
    # #endregion
    return _validation_result(run, action=f"validate_{scan_scope}")


def _validation_error(
    message: str,
    *,
    action: str,
    scan_scope: str,
    profile_id: str = "",
) -> Any:
    return SimpleNamespace(
        action=action,
        succeeded=False,
        snapshot=None,
        results=(),
        rules=(),
        fix_plan=None,
        summary=None,
        health_score=SimpleNamespace(
            score=100,
            critical=0,
            error=0,
            warning=0,
            info=0,
            block_publish=False,
            block_deadline=False,
        ),
        message=message,
        profile_id=profile_id,
        scan_scope=scan_scope,
    )


def _validation_result(run: ValidationRunResult, *, action: str) -> Any:
    return SimpleNamespace(
        action=action,
        succeeded=True,
        snapshot=run.snapshot,
        results=run.results,
        rules=run.rules,
        fix_plan=run.fix_plan,
        summary=run.summary,
        health_score=run.health_score,
        message=run.message,
        profile_id=run.profile_id,
        asset_class_id=getattr(run, "asset_class_id", ""),
        scan_scope=run.scan_scope,
    )


def _export_json_report(path: Optional[str]) -> Any:
    from pipeline_inspector.reports import write_json_report

    validation = _validate(scan_scope="scene", profile_id=DEFAULT_PROFILE_ID)
    output_path = _runtime_output_path(path, validation.snapshot.scene_path, "report", "json")
    write_json_report(output_path, validation.snapshot, validation.results)
    return _runtime_result("export_json_report", output_path, "JSON report exported.")


def _export_html_report(path: Optional[str]) -> Any:
    from pipeline_inspector.reports.html_report import write_html_report

    validation = _validate(scan_scope="scene", profile_id=DEFAULT_PROFILE_ID)
    export_health = validation.health_score.score
    # region agent log
    _debug_health_log_command(
        "commands.py:_export_html_report",
        "revalidated export health score",
        {
            "path": "revalidate",
            "export_health": export_health,
            "profile_id": DEFAULT_PROFILE_ID,
            "scan_scope": "scene",
            "failed_count": sum(1 for item in validation.results if item.status == "failed"),
        },
        hypothesis_id="H1",
    )
    # endregion
    output_path = _runtime_output_path(path, validation.snapshot.scene_path, "report", "html")
    write_html_report(output_path, validation.snapshot, validation.results)
    return _runtime_result("export_html_report", output_path, "HTML report exported.")


def _export_shader_manifest(path: Optional[str]) -> Any:
    from pipeline_inspector.maya import export_actions

    validation = _validate(scan_scope="scene", profile_id=DEFAULT_PROFILE_ID)
    output_path = _runtime_output_path(path, validation.snapshot.scene_path, "manifest", "json")
    health_score = getattr(getattr(validation, "health_score", None), "score", None)
    result = export_actions.export_shader_manifest(
        output_path,
        snapshot=validation.snapshot,
        results=validation.results,
        health_score=health_score,
    )
    return _runtime_result(
        "export_shader_manifest",
        Path(result.path),
        result.message,
        succeeded=result.succeeded,
    )


def _export_fix_plan(path: Optional[str]) -> Any:
    from pipeline_inspector.maya import export_actions

    validation = _validate(scan_scope="scene", profile_id=DEFAULT_PROFILE_ID)
    output_path = _runtime_output_path(path, validation.snapshot.scene_path, "fix_plan", "json")
    result = export_actions.export_fix_plan(
        output_path,
        fix_plan=validation.fix_plan,
        snapshot=validation.snapshot,
        profile_id=validation.profile_id,
    )
    return _runtime_result(result.action, Path(result.path), result.message)


def _export_manifest_diff_with_snapshot(
    snapshot: Any,
    *,
    baseline_manifest_path: Optional[str] = None,
    json_path: Optional[str] = None,
    html_path: Optional[str] = None,
    prefer_approved_sidecar: bool = False,
) -> Any:
    from pipeline_inspector.maya import export_actions

    baseline_path = baseline_manifest_path
    if baseline_path is None and prefer_approved_sidecar:
        baseline_path = _approved_manifest_sidecar_path(snapshot)
    if baseline_path is None:
        baseline_path = _pick_baseline_manifest_json()
    if not baseline_path:
        return SimpleNamespace(
            action="export_manifest_diff",
            path="",
            succeeded=False,
            message="Manifest diff export cancelled.",
        )

    if snapshot is not None:
        result = export_actions.export_manifest_diff(
            baseline_path,
            json_path=json_path,
            html_path=html_path,
            snapshot=snapshot,
        )
    else:
        validation = _validate(scan_scope="scene", profile_id=DEFAULT_PROFILE_ID)
        result = export_actions.export_manifest_diff(
            baseline_path,
            json_path=json_path,
            html_path=html_path,
            snapshot=validation.snapshot,
        )
    return _runtime_result(
        result.action,
        Path(result.path) if result.path else Path("."),
        result.message,
        succeeded=result.succeeded,
    )


def _pick_baseline_manifest_json() -> Optional[str]:
    cmds = _maya_cmds()
    selected = cmds.fileDialog2(
        fileMode=1,
        caption="Select Baseline Shader Manifest",
        fileFilter="JSON Manifest (*.json)",
        okCaption="Select",
    )
    if not selected:
        return None
    return str(selected[0])


def _approved_manifest_sidecar_path(snapshot: Any = None) -> Optional[str]:
    scene_path = ""
    if snapshot is not None:
        scene_path_value = getattr(snapshot, "scene_path", None)
        if scene_path_value:
            scene_path = str(scene_path_value)
    if not scene_path:
        scene_path = _current_scene_path()
    if not scene_path:
        return None
    from pipeline_inspector.reports.scene_output_paths import resolve_existing_scene_export_path

    sidecar = resolve_existing_scene_export_path(scene_path, suffix="manifest", extension="json")
    if sidecar is not None:
        return str(sidecar)
    return None


def _runtime_output_path(
    path: Optional[str],
    scene_path: str,
    suffix: str,
    extension: str,
) -> Path:
    if path:
        return Path(path)
    from pipeline_inspector.reports.scene_output_paths import default_scene_export_path

    return default_scene_export_path(scene_path or None, suffix=suffix, extension=extension)


def _write_json(path: Path, payload: Any) -> None:
    _write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _runtime_result(action: str, path: Path, message: str, *, succeeded: bool = True) -> Any:
    return SimpleNamespace(
        action=action,
        path=str(path),
        succeeded=succeeded,
        message=message,
    )


def _current_scene_path() -> str:
    cmds = _maya_cmds()
    return str(cmds.file(query=True, sceneName=True) or "")


def _maya_node_name(node_id: Optional[str]) -> str:
    if not node_id:
        raise ValueError("node_name must not be empty.")
    text = str(node_id)
    if text.startswith("node:"):
        return text.split(":", 1)[1]
    return text


def _shelf_layout_children(cmds: Any, shelf_name: str) -> tuple[str, ...]:
    if not cmds.shelfLayout(shelf_name, query=True, exists=True):
        return ()
    children = cmds.shelfLayout(shelf_name, query=True, childArray=True)
    if not children:
        return ()
    if isinstance(children, str):
        return (children,)
    return tuple(str(child) for child in children)


def _shelf_button_label(cmds: Any, button_name: str) -> str:
    try:
        return str(cmds.shelfButton(button_name, query=True, label=True) or "")
    except Exception:
        return ""


def _remove_extra_shelf_buttons(
    cmds: Any,
    *,
    shelf_name: str,
    label: str,
    keep_name: str,
) -> None:
    for child in _shelf_layout_children(cmds, shelf_name):
        if child == keep_name:
            continue
        if not cmds.shelfButton(child, query=True, exists=True):
            continue
        if _shelf_button_label(cmds, child) != label:
            continue
        cmds.deleteUI(child, control=True)


def _install_standalone_menu_item(
    cmds: Any,
    menu_name: str,
    *,
    label: str,
    command: Any,
    icon_id: str,
) -> None:
    fields = {
        "label": label,
        "parent": menu_name,
        "command": command,
        **menu_item_image_kwargs(icon_id),
    }
    cmds.menuItem(**fields)


def _standalone_shelf_entries() -> tuple[dict[str, Any], ...]:
    return (
        {
            "name": OPEN_SHELF_BUTTON_NAME,
            "parent": SHELF_NAME,
            "label": OPEN_SHELF_BUTTON_LABEL,
            "annotation": OPEN_SHELF_BUTTON_ANNOTATION,
            "command": OPEN_UI_PYTHON_COMMAND,
            "icon_id": ICON_MAIN,
        },
        {
            "name": SETTINGS_SHELF_BUTTON_NAME,
            "parent": SHELF_NAME,
            "label": SETTINGS_SHELF_BUTTON_LABEL,
            "annotation": SETTINGS_SHELF_BUTTON_ANNOTATION,
            "command": SETTINGS_UI_PYTHON_COMMAND,
            "icon_id": ICON_SETTINGS,
        },
        {
            "name": VALIDATE_SCENE_SHELF_BUTTON_NAME,
            "parent": SHELF_NAME,
            "label": VALIDATE_SCENE_SHELF_BUTTON_LABEL,
            "annotation": VALIDATE_SCENE_SHELF_BUTTON_ANNOTATION,
            "command": VALIDATE_SCENE_UI_PYTHON_COMMAND,
            "icon_id": ICON_VALIDATE_SCENE,
        },
        {
            "name": REPORTS_SHELF_BUTTON_NAME,
            "parent": SHELF_NAME,
            "label": REPORTS_SHELF_BUTTON_LABEL,
            "annotation": REPORTS_SHELF_BUTTON_ANNOTATION,
            "command": REPORTS_UI_PYTHON_COMMAND,
            "icon_id": ICON_REPORTS,
        },
        {
            "name": READINESS_CHECK_SHELF_BUTTON_NAME,
            "parent": SHELF_NAME,
            "label": READINESS_CHECK_SHELF_BUTTON_LABEL,
            "annotation": READINESS_CHECK_SHELF_BUTTON_ANNOTATION,
            "command": READINESS_CHECK_UI_PYTHON_COMMAND,
            "icon_id": ICON_READINESS_CHECK,
        },
        {
            "name": FARM_CHECK_SHELF_BUTTON_NAME,
            "parent": SHELF_NAME,
            "label": FARM_CHECK_SHELF_BUTTON_LABEL,
            "annotation": FARM_CHECK_SHELF_BUTTON_ANNOTATION,
            "command": FARM_CHECK_UI_PYTHON_COMMAND,
            "icon_id": ICON_FARM_CHECK,
        },
        {
            "name": DOCUMENTATION_SHELF_BUTTON_NAME,
            "parent": SHELF_NAME,
            "label": DOCUMENTATION_SHELF_BUTTON_LABEL,
            "annotation": DOCUMENTATION_SHELF_BUTTON_ANNOTATION,
            "command": DOCUMENTATION_UI_PYTHON_COMMAND,
            "icon_id": ICON_DOCUMENTATION,
        },
        {
            "name": CHECK_FOR_UPDATES_SHELF_BUTTON_NAME,
            "parent": SHELF_NAME,
            "label": CHECK_FOR_UPDATES_SHELF_BUTTON_LABEL,
            "annotation": CHECK_FOR_UPDATES_SHELF_BUTTON_ANNOTATION,
            "command": CHECK_FOR_UPDATES_UI_PYTHON_COMMAND,
            "icon_id": ICON_CHECK_FOR_UPDATES,
        },
    )


def _remove_legacy_shelf_buttons(cmds: Any) -> None:
    for child in _shelf_layout_children(cmds, SHELF_NAME):
        if not cmds.shelfButton(child, query=True, exists=True):
            continue
        label = _shelf_button_label(cmds, child)
        if label == LEGACY_FARM_CHECK_SHELF_BUTTON_LABEL:
            cmds.deleteUI(child, control=True)
            continue
        if label == LEGACY_SHELF_BUTTON_LABEL and child != OPEN_SHELF_BUTTON_NAME:
            cmds.deleteUI(child, control=True)


def _ensure_shelf_button(
    cmds: Any,
    *,
    name: str,
    parent: str,
    label: str,
    annotation: str,
    command: str,
    icon_id: str,
) -> None:
    _remove_extra_shelf_buttons(cmds, shelf_name=parent, label=label, keep_name=name)
    button_fields = {
        "label": label,
        "annotation": annotation,
        "sourceType": "python",
        "command": command,
        **shelf_button_image_kwargs(icon_id),
    }
    if cmds.shelfButton(name, query=True, exists=True):
        cmds.shelfButton(name, edit=True, **button_fields)
        return
    cmds.shelfButton(name, parent=parent, **button_fields)


def _maya_shelf_top_level() -> str:
    mel = _maya_mel()
    shelf_top_level = mel.eval("$tmp=$gShelfTopLevel")
    return str(shelf_top_level)


def _maya_cmds() -> Any:
    try:
        return importlib.import_module("maya.cmds")
    except ImportError as exc:
        raise RuntimeError("Maya commands are available only inside Autodesk Maya.") from exc


def _maya_mel() -> Any:
    try:
        return importlib.import_module("maya.mel")
    except ImportError as exc:
        raise RuntimeError("Maya MEL is available only inside Autodesk Maya.") from exc


def _debug_health_log_command(
    location: str,
    message: str,
    data: dict[str, object],
    *,
    hypothesis_id: str,
) -> None:
    try:
        log_path = Path(__file__).resolve().parents[3] / "debug-618f4f.log"
        payload = {
            "sessionId": "618f4f",
            "timestamp": int(time.time() * 1000),
            "location": location,
            "message": message,
            "data": {key: str(value) for key, value in data.items()},
            "hypothesisId": hypothesis_id,
        }
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
    except OSError:
        return
