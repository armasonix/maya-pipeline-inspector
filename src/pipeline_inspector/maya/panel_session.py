"""Persist last-loaded studio and user config paths for the Maya panel."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from pipeline_inspector.studio_config import (
    StudioConfig,
    discover_studio_config_path,
    load_studio_config,
)
from pipeline_inspector.user_config import (
    UserPreferences,
    default_user_config_path,
    discover_user_config_path,
    enrich_user_preferences,
    load_user_config,
)

PANEL_SESSION_FILENAME = "panel_session.json"
PANEL_SESSION_DIRNAME = ".pipeline_inspector"
LEGACY_PANEL_SESSION_DIRNAME = ".shader_health"


@dataclass(frozen=True)
class PanelSessionState:
    """Last config file paths chosen in the Maya panel."""

    studio_config_path: str = ""
    user_config_path: str = ""
    last_plugin_version: str = ""
    panel_visible: bool = False
    table_column_widths: dict[str, tuple[int, ...]] = field(default_factory=dict)
    validate_splitter_sizes: tuple[int, ...] = ()


def panel_session_path() -> Path:
    return Path.home() / PANEL_SESSION_DIRNAME / PANEL_SESSION_FILENAME


def _resolve_panel_session_path() -> Path:
    primary = panel_session_path()
    if primary.is_file():
        return primary
    legacy = Path.home() / LEGACY_PANEL_SESSION_DIRNAME / PANEL_SESSION_FILENAME
    if legacy.is_file():
        return legacy
    return primary


def load_panel_session() -> PanelSessionState:
    path = _resolve_panel_session_path()
    if not path.is_file():
        return PanelSessionState()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return PanelSessionState()
    if not isinstance(payload, dict):
        return PanelSessionState()
    return PanelSessionState(
        studio_config_path=str(payload.get("studio_config_path", "") or "").strip(),
        user_config_path=str(payload.get("user_config_path", "") or "").strip(),
        last_plugin_version=str(payload.get("last_plugin_version", "") or "").strip(),
        panel_visible=bool(payload.get("panel_visible", False)),
        table_column_widths=_parse_table_column_widths(payload.get("table_column_widths")),
        validate_splitter_sizes=_parse_splitter_sizes(payload.get("validate_splitter_sizes")),
    )


def save_panel_session(
    *,
    studio_config_path: Path | None = None,
    user_config_path: Path | None = None,
    last_plugin_version: str | None = None,
    panel_visible: bool | None = None,
    table_column_widths: dict[str, tuple[int, ...]] | None = None,
    validate_splitter_sizes: tuple[int, ...] | None = None,
) -> None:
    """Write remembered config paths, preserving omitted fields."""

    current = load_panel_session()
    studio_value = (
        str(studio_config_path.resolve())
        if studio_config_path is not None
        else current.studio_config_path
    )
    user_value = (
        str(user_config_path.resolve())
        if user_config_path is not None
        else current.user_config_path
    )
    version_value = (
        str(last_plugin_version or "").strip()
        if last_plugin_version is not None
        else current.last_plugin_version
    )
    visible_value = (
        bool(panel_visible)
        if panel_visible is not None
        else current.panel_visible
    )
    widths_value = (
        dict(table_column_widths)
        if table_column_widths is not None
        else current.table_column_widths
    )
    splitter_value = (
        tuple(int(size) for size in validate_splitter_sizes)
        if validate_splitter_sizes is not None
        else current.validate_splitter_sizes
    )
    path = panel_session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "studio_config_path": studio_value,
        "user_config_path": user_value,
        "last_plugin_version": version_value,
        "panel_visible": visible_value,
        "table_column_widths": {
            key: list(widths) for key, widths in sorted(widths_value.items())
        },
        "validate_splitter_sizes": list(splitter_value),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def remember_studio_config_path(config_path: Path | None) -> None:
    if config_path is None:
        return
    save_panel_session(studio_config_path=config_path)


def remember_user_config_path(config_path: Path | None) -> None:
    if config_path is None:
        return
    save_panel_session(user_config_path=config_path)


def remember_plugin_version(version: str) -> None:
    save_panel_session(last_plugin_version=str(version or "").strip())


def remember_panel_visible(visible: bool) -> None:
    save_panel_session(panel_visible=visible)


def remember_table_column_widths(table_key: str, widths: tuple[int, ...]) -> None:
    """Persist one table's column widths in the Maya panel session."""

    key = str(table_key or "").strip()
    cleaned = tuple(int(width) for width in widths if int(width) > 0)
    if not key or not cleaned:
        return
    current = load_panel_session()
    updated = dict(current.table_column_widths)
    updated[key] = cleaned
    save_panel_session(table_column_widths=updated)


def remember_validate_splitter_sizes(sizes: tuple[int, ...]) -> None:
    """Persist the Validate tab issues/details splitter sizes."""

    cleaned = tuple(int(size) for size in sizes if int(size) > 0)
    if len(cleaned) < 2:
        return
    save_panel_session(validate_splitter_sizes=cleaned)


def _parse_table_column_widths(raw: object) -> dict[str, tuple[int, ...]]:
    if not isinstance(raw, dict):
        return {}
    parsed: dict[str, tuple[int, ...]] = {}
    for table_key, widths in raw.items():
        key = str(table_key or "").strip()
        if not key or not isinstance(widths, list):
            continue
        cleaned = tuple(int(width) for width in widths if int(width) > 0)
        if cleaned:
            parsed[key] = cleaned
    return parsed


def _parse_splitter_sizes(raw: object) -> tuple[int, ...]:
    if not isinstance(raw, list):
        return ()
    cleaned = tuple(int(size) for size in raw if int(size) > 0)
    if len(cleaned) < 2:
        return ()
    return cleaned


def load_runtime_configs_from_session() -> tuple[StudioConfig, UserPreferences]:
    """Load studio and user configs using remembered paths, then discovery."""

    session = load_panel_session()
    studio_config = _load_studio_config(session.studio_config_path)
    user_config = _load_user_config(session.user_config_path)
    return studio_config, user_config


def _load_studio_config(session_path: str) -> StudioConfig:
    if session_path:
        remembered = Path(session_path)
        if remembered.is_file():
            return load_studio_config(remembered)
    discovered = discover_studio_config_path()
    if discovered is not None:
        return load_studio_config(discovered)
    return StudioConfig()


def _load_user_config(session_path: str) -> UserPreferences:
    if session_path:
        remembered = Path(session_path)
        if remembered.is_file():
            return enrich_user_preferences(load_user_config(remembered))
    discovered = discover_user_config_path()
    if discovered is not None:
        return enrich_user_preferences(load_user_config(discovered))
    return enrich_user_preferences(
        UserPreferences(config_path=default_user_config_path())
    )
