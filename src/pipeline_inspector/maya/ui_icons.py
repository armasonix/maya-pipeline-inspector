"""Maya menu/shelf icon path resolution and Qt icon loading."""
from __future__ import annotations

import json
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ICON_MAIN = "main"
ICON_SETTINGS = "settings"
ICON_VALIDATE_SCENE = "validate_scene"
ICON_REPORTS = "reports"
ICON_READINESS_CHECK = "readiness_check"
ICON_FARM_CHECK = "farm_check"
ICON_DOCUMENTATION = "documentation"
ICON_CHECK_FOR_UPDATES = "check_for_updates"
ICON_CLOSE = "close"
ICON_WIKI = "wiki"
ICON_REPORT_BUG = "report_bug"

STANDALONE_ICON_IDS: tuple[str, ...] = (
    ICON_MAIN,
    ICON_SETTINGS,
    ICON_VALIDATE_SCENE,
    ICON_REPORTS,
    ICON_READINESS_CHECK,
    ICON_FARM_CHECK,
    ICON_DOCUMENTATION,
    ICON_CHECK_FOR_UPDATES,
)

MENU_ONLY_ICON_IDS: tuple[str, ...] = (ICON_CLOSE,)

PANEL_HEADER_ICON_IDS: tuple[str, ...] = (
    ICON_WIKI,
    ICON_REPORT_BUG,
    ICON_CHECK_FOR_UPDATES,
)

_ICON_FILENAMES: Mapping[str, str] = {
    ICON_MAIN: "pipeline_inspector_main.png",
    ICON_SETTINGS: "pipeline_inspector_settings.png",
    ICON_VALIDATE_SCENE: "pipeline_inspector_validate_scene.png",
    ICON_REPORTS: "pipeline_inspector_reports.png",
    ICON_READINESS_CHECK: "pipeline_inspector_readiness_check.png",
    ICON_FARM_CHECK: "pipeline_inspector_farm_check.png",
    ICON_DOCUMENTATION: "pipeline_inspector_wiki.png",
    ICON_CHECK_FOR_UPDATES: "pipeline_inspector_check_for_updates.png",
    ICON_CLOSE: "pipeline_inspector_close.png",
    ICON_WIKI: "pipeline_inspector_wiki.png",
    ICON_REPORT_BUG: "pipeline_inspector_report_bug.png",
}


def _debug_log(
    *,
    location: str,
    message: str,
    data: dict[str, Any],
    hypothesis_id: str,
    run_id: str = "pre-fix",
) -> None:
    # region agent log
    payload = {
        "sessionId": "618f4f",
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    try:
        with (repo_root() / "debug-618f4f.log").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
    except OSError:
        return
    # endregion


def repo_root() -> Path:
    """Return the repository root that owns `maya_module/`."""

    return Path(__file__).resolve().parents[3]


def maya_module_icons_directory() -> Path:
    """Return `maya_module/icons/` where artist-provided PNGs are stored."""

    return repo_root() / "maya_module" / "icons"


def icon_filename(icon_id: str) -> str:
    """Return the PNG basename registered for one standalone UI entry."""

    try:
        return _ICON_FILENAMES[icon_id]
    except KeyError as exc:
        raise KeyError(f"Unknown Pipeline Inspector icon id: {icon_id!r}") from exc


def resolve_icon_path(icon_id: str) -> Path:
    """Resolve the absolute PNG path for one standalone UI entry."""

    return maya_module_icons_directory() / icon_filename(icon_id)


def shelf_image_filename(icon_id: str) -> str:
    """Return the Maya shelf `image1` basename for XBMLANGPATH lookup."""

    return icon_filename(icon_id)


def icon_path_exists(icon_id: str) -> bool:
    """Return whether the configured PNG exists on disk."""

    return resolve_icon_path(icon_id).is_file()


def load_qicon(qt_gui: Any, icon_id: str) -> Any:
    """Load a `QIcon` when the PNG exists; otherwise return an empty icon."""

    icon_path = resolve_icon_path(icon_id)
    if not icon_path.is_file():
        return qt_gui.QIcon()
    return qt_gui.QIcon(str(icon_path))


def apply_button_icon(button: Any, qt_gui: Any, icon_id: str) -> bool:
    """Attach an icon to a Qt button when the PNG exists."""

    icon = load_qicon(qt_gui, icon_id)
    is_null = getattr(icon, "isNull", None)
    if is_null is not None and is_null():
        return False
    set_icon = getattr(button, "setIcon", None)
    if set_icon is None:
        return False
    set_icon(icon)
    return True


def apply_panel_header_icons(content: Any, qt_widgets: Any, qt_gui: Any) -> None:
    """Wire panel-header icons for documentation and bug-report actions."""

    from pipeline_inspector.ui.main_window import (
        CHECK_FOR_UPDATES_BUTTON_OBJECT_NAME,
        DOCUMENTATION_BUTTON_OBJECT_NAME,
        REPORT_BUG_BUTTON_OBJECT_NAME,
        SETTINGS_GEAR_BUTTON_OBJECT_NAME,
    )
    from pipeline_inspector.ui.settings_widgets import find_child

    gear_button = find_child(content, qt_widgets.QPushButton, SETTINGS_GEAR_BUTTON_OBJECT_NAME)
    gear_text = ""
    if gear_button is not None:
        gear_text = str(getattr(gear_button, "text", lambda: "")() or "")

    docs_button = find_child(
        content,
        qt_widgets.QPushButton,
        DOCUMENTATION_BUTTON_OBJECT_NAME,
    )
    docs_icon_applied = (
        apply_button_icon(docs_button, qt_gui, ICON_WIKI) if docs_button is not None else False
    )

    report_bug_button = find_child(
        content,
        qt_widgets.QPushButton,
        REPORT_BUG_BUTTON_OBJECT_NAME,
    )
    report_bug_icon_applied = (
        apply_button_icon(report_bug_button, qt_gui, ICON_REPORT_BUG)
        if report_bug_button is not None
        else False
    )

    updates_button = find_child(
        content,
        qt_widgets.QPushButton,
        CHECK_FOR_UPDATES_BUTTON_OBJECT_NAME,
    )
    updates_icon_applied = (
        apply_button_icon(updates_button, qt_gui, ICON_CHECK_FOR_UPDATES)
        if updates_button is not None
        else False
    )

    _debug_log(
        location="ui_icons.apply_panel_header_icons",
        message="panel header icon wiring",
        data={
            "gear_text": gear_text,
            "docs_icon_applied": docs_icon_applied,
            "report_bug_icon_applied": report_bug_icon_applied,
            "updates_icon_applied": updates_icon_applied,
            "wiki_exists": icon_path_exists(ICON_WIKI),
            "report_bug_exists": icon_path_exists(ICON_REPORT_BUG),
        },
        hypothesis_id="A",
    )


def menu_item_image_kwargs(icon_id: str) -> dict[str, str]:
    """Return Maya `menuItem` image kwargs when the PNG exists."""

    if not icon_path_exists(icon_id):
        return {}
    return {"image": shelf_image_filename(icon_id)}


def shelf_button_image_kwargs(icon_id: str) -> dict[str, str]:
    """Return Maya `shelfButton` image kwargs for artist-provided PNGs."""

    if not icon_path_exists(icon_id):
        return {"image1": "commandButton.png"}
    return {"image1": shelf_image_filename(icon_id)}


def standalone_icon_documentation() -> str:
    """Describe shelf/menu image params for artist-provided PNGs."""

    icons_dir = maya_module_icons_directory()
    lines = [
        "Pipeline Inspector standalone menu/shelf icons live under:",
        f"  {icons_dir}",
        "",
        "Maya resolves shelf `image1` and menu `image` basenames via the module",
        "`icons:` path declared in `pipeline_inspector.mod`.",
        "",
        "Expected PNG basenames:",
    ]
    for icon_id in STANDALONE_ICON_IDS:
        lines.append(f"  - {icon_filename(icon_id)}  ({icon_id})")
    lines.append("Menu-only icons:")
    for icon_id in MENU_ONLY_ICON_IDS:
        lines.append(f"  - {icon_filename(icon_id)}  ({icon_id})")
    lines.extend(
        [
            "",
            "Panel header buttons also use:",
            f"  - {icon_filename(ICON_WIKI)}  (Documentation)",
            f"  - {icon_filename(ICON_REPORT_BUG)}  (Report Plugin Bug)",
            "",
            "Replace the placeholder PNGs with studio artwork using the same",
            "filenames. Re-run `install_ui()` or restart Maya to refresh shelf",
            "and menu icons.",
        ]
    )
    return "\n".join(lines)
