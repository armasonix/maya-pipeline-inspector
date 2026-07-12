"""Persist last-loaded studio and user config paths for the Maya panel."""
from __future__ import annotations

import json
from dataclasses import dataclass
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
    )


def save_panel_session(
    *,
    studio_config_path: Path | None = None,
    user_config_path: Path | None = None,
) -> None:
    """Write remembered config paths, preserving the other path when omitted."""

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
    path = panel_session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "studio_config_path": studio_value,
        "user_config_path": user_value,
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
