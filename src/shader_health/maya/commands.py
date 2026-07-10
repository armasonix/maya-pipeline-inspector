"""Maya command entrypoints for Shader Health Inspector."""
from __future__ import annotations

import importlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

from shader_health.core.waivers import (
    WaiverSidecar,
    create_waiver_from_result,
    load_waiver_sidecar,
    load_waiver_sidecar_optional,
    revoke_waiver,
    write_waiver_sidecar,
)
from shader_health.maya.navigation import (
    NavigationActionResult,
    copy_path,
    open_in_hypershade,
    reveal_file,
    select_node,
)
from shader_health.maya.ui_launcher import close_panel, show_farm_check_panel, show_panel
from shader_health.maya.validation_pipeline import (
    DEFAULT_PROFILE_ID,
    ValidationRunResult,
    run_validation,
    run_validation_for_user,
    waiver_sidecar_path_for_scene,
)
from shader_health.user_config import UserPreferences

MENU_NAME = "shaderHealthInspectorMenu"
MENU_LABEL = "Shader Health"
OPEN_MENU_ITEM_LABEL = "Open Shader Health Inspector"
FARM_CHECK_MENU_ITEM_LABEL = "Shader Health Farm Check"
CLOSE_MENU_ITEM_LABEL = "Close Shader Health Inspector"
SHELF_NAME = "ShaderHealth"
SHELF_BUTTON_NAME = "shaderHealthInspectorShelfButton"
FARM_CHECK_SHELF_BUTTON_NAME = "shaderHealthInspectorFarmCheckShelfButton"
SHELF_BUTTON_LABEL = "Shader Health"
FARM_CHECK_SHELF_BUTTON_LABEL = "Shader Health Farm Check"
SHELF_BUTTON_ANNOTATION = "Open Maya Shader Health Inspector"
FARM_CHECK_SHELF_BUTTON_ANNOTATION = (
    "Open the Farm tab and run deadline_critical preflight."
)
MAYA_MAIN_WINDOW = "MayaWindow"
OPEN_UI_PYTHON_COMMAND = "from shader_health.maya.commands import show_ui\nshow_ui()"
FARM_CHECK_UI_PYTHON_COMMAND = (
    "from shader_health.maya.commands import show_farm_check_ui\nshow_farm_check_ui()"
)


def show_ui() -> Any:
    """Open the dockable Maya Shader Health Inspector panel from script/menu/shelf."""

    return show_panel()


def show_farm_check_ui() -> Any:
    """Open the Farm tab and run deadline_critical preflight from menu/shelf."""

    return show_farm_check_panel()


def close_ui(*, delete: bool = True) -> None:
    """Close the dockable Maya Shader Health Inspector panel."""

    close_panel(delete=delete)


def validate_scene_action(
    *,
    profile_id: str = DEFAULT_PROFILE_ID,
    asset_class_id: str = "",
    studio_config: Optional[Any] = None,
    extra_rule_paths: tuple[Path, ...] = (),
    user_config: Optional[UserPreferences] = None,
) -> Any:
    """Validate the current Maya scene and return a UI-friendly result object."""

    return _validate(
        scan_scope="scene",
        profile_id=profile_id,
        asset_class_id=asset_class_id,
        studio_config=studio_config,
        extra_rule_paths=extra_rule_paths,
        user_config=user_config,
    )


def validate_selection_action(
    *,
    profile_id: str = DEFAULT_PROFILE_ID,
    asset_class_id: str = "",
    studio_config: Optional[Any] = None,
    extra_rule_paths: tuple[Path, ...] = (),
    user_config: Optional[UserPreferences] = None,
) -> Any:
    """Validate the current Maya selection and return a UI-friendly result object."""

    return _validate(
        scan_scope="selection",
        profile_id=profile_id,
        asset_class_id=asset_class_id,
        studio_config=studio_config,
        extra_rule_paths=extra_rule_paths,
        user_config=user_config,
    )


def waive_issue_action(result: Any, *, reason: str, approved_by: str = "artist") -> Any:
    """Persist a waiver for a failed validation result and return the sidecar path."""

    if getattr(result, "status", "") != "failed":
        raise ValueError("Only failed issues can be waived.")
    snapshot_path = getattr(result, "_scene_path", None) or _current_scene_path()
    sidecar_path = waiver_sidecar_path_for_scene(snapshot_path)
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
    sidecar_path = waiver_sidecar_path_for_scene(snapshot_path)
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
    sidecar_path = waiver_sidecar_path_for_scene(snapshot_path)
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


def select_node_action(node_name: str) -> NavigationActionResult:
    """Select a Maya node from a UI action."""

    return select_node(_maya_node_name(node_name))


def open_in_hypershade_action(
    node_name: str,
    *,
    material_name: Optional[str] = None,
) -> NavigationActionResult:
    """Open Hypershade focused on the issue material from a UI action."""

    maya_cmds = _maya_cmds()
    candidates: list[str] = []
    if material_name:
        candidates.append(_maya_node_name(material_name))
    if node_name:
        node = _maya_node_name(node_name)
        if node not in candidates:
            candidates.append(node)
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
    """Install Maya menu entries that open and close the dockable panel."""

    cmds = _maya_cmds()
    menu_parent = parent or MAYA_MAIN_WINDOW
    if cmds.menu(MENU_NAME, query=True, exists=True):
        cmds.deleteUI(MENU_NAME, menu=True)
    menu_name = cmds.menu(MENU_NAME, label=MENU_LABEL, parent=menu_parent, tearOff=True)
    cmds.menuItem(label=OPEN_MENU_ITEM_LABEL, parent=menu_name, command=lambda *_: show_ui())
    cmds.menuItem(
        label=FARM_CHECK_MENU_ITEM_LABEL,
        parent=menu_name,
        command=lambda *_: show_farm_check_ui(),
    )
    cmds.menuItem(divider=True, parent=menu_name)
    cmds.menuItem(label=CLOSE_MENU_ITEM_LABEL, parent=menu_name, command=lambda *_: close_ui())
    return str(menu_name)


def uninstall_menu() -> None:
    """Remove the Maya menu entry if it exists."""

    cmds = _maya_cmds()
    if cmds.menu(MENU_NAME, query=True, exists=True):
        cmds.deleteUI(MENU_NAME, menu=True)


def install_shelf(parent: Optional[str] = None) -> str:
    """Install a Maya shelf tab and button that opens the dockable panel."""

    cmds = _maya_cmds()
    shelf_parent = parent or _maya_shelf_top_level()

    if not cmds.shelfLayout(SHELF_NAME, query=True, exists=True):
        cmds.shelfLayout(SHELF_NAME, parent=shelf_parent)

    if cmds.shelfButton(SHELF_BUTTON_NAME, query=True, exists=True):
        cmds.deleteUI(SHELF_BUTTON_NAME, control=True)
    if cmds.shelfButton(FARM_CHECK_SHELF_BUTTON_NAME, query=True, exists=True):
        cmds.deleteUI(FARM_CHECK_SHELF_BUTTON_NAME, control=True)

    cmds.shelfButton(
        SHELF_BUTTON_NAME,
        parent=SHELF_NAME,
        label=SHELF_BUTTON_LABEL,
        annotation=SHELF_BUTTON_ANNOTATION,
        image1="commandButton.png",
        sourceType="python",
        command=OPEN_UI_PYTHON_COMMAND,
    )
    cmds.shelfButton(
        FARM_CHECK_SHELF_BUTTON_NAME,
        parent=SHELF_NAME,
        label=FARM_CHECK_SHELF_BUTTON_LABEL,
        annotation=FARM_CHECK_SHELF_BUTTON_ANNOTATION,
        image1="commandButton.png",
        sourceType="python",
        command=FARM_CHECK_UI_PYTHON_COMMAND,
    )
    return SHELF_NAME


def uninstall_shelf() -> None:
    """Remove the Shader Health shelf buttons if they exist."""

    cmds = _maya_cmds()
    if cmds.shelfButton(SHELF_BUTTON_NAME, query=True, exists=True):
        cmds.deleteUI(SHELF_BUTTON_NAME, control=True)
    if cmds.shelfButton(FARM_CHECK_SHELF_BUTTON_NAME, query=True, exists=True):
        cmds.deleteUI(FARM_CHECK_SHELF_BUTTON_NAME, control=True)


def uninstall_ui() -> None:
    """Remove Shader Health UI entrypoints for the current session."""

    close_ui(delete=True)
    uninstall_shelf()
    uninstall_menu()


_UI_INSTALLED = False


def install_ui() -> None:
    """Install all Maya UI entrypoints for the current session."""

    global _UI_INSTALLED
    if _UI_INSTALLED:
        return
    install_menu()
    install_shelf()
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
) -> Any:
    from shader_health.maya.scanner import scan_scene, scan_selection, selection_node_names

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
        )
    else:
        run = run_validation(
            raw_snapshot,
            profile_id=profile_id,
            asset_class_id=asset_class_id or None,
            scan_scope=scan_scope,
            studio_config=studio_config,
            extra_rule_paths=extra_rule_paths,
        )
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
    from shader_health.reports import write_json_report

    validation = _validate(scan_scope="scene", profile_id=DEFAULT_PROFILE_ID)
    output_path = _runtime_output_path(path, validation.snapshot.scene_path, "report", "json")
    write_json_report(output_path, validation.snapshot, validation.results)
    return _runtime_result("export_json_report", output_path, "JSON report exported.")


def _export_html_report(path: Optional[str]) -> Any:
    from shader_health.reports.html_report import write_html_report

    validation = _validate(scan_scope="scene", profile_id=DEFAULT_PROFILE_ID)
    output_path = _runtime_output_path(path, validation.snapshot.scene_path, "report", "html")
    write_html_report(output_path, validation.snapshot, validation.results)
    return _runtime_result("export_html_report", output_path, "HTML report exported.")


def _export_shader_manifest(path: Optional[str]) -> Any:
    from shader_health.maya import export_actions

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
    from shader_health.maya import export_actions

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
    from shader_health.maya import export_actions

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
    sidecar = _runtime_output_path(None, scene_path, "manifest", "json")
    if sidecar.is_file():
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
    if scene_path:
        scene = Path(scene_path)
        output_dir = scene.parent
        scene_stem = scene.stem
    else:
        output_dir = Path.cwd()
        scene_stem = "untitled_scene"
    return output_dir / f"{scene_stem}_shader_health_{suffix}.{extension}"


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
