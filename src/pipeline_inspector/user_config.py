"""Per-user plugin preferences loaded from JSON."""
from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Optional

from pipeline_inspector.studio_config import StudioConfig

USER_CONFIG_SCHEMA_VERSION = "1.0"
USER_CONFIG_ENV_VAR = "PIPELINE_INSPECTOR_USER_CONFIG"
LEGACY_USER_CONFIG_ENV_VAR = "SHADER_HEALTH_USER_CONFIG"
USER_CONFIG_DIRNAME = ".pipeline_inspector"
LEGACY_USER_CONFIG_DIRNAME = ".shader_health"
USER_CONFIG_FILENAME = "user.json"
DEFAULT_USER_DOCS_URL = "https://github.com/armasonix/maya-pipeline-inspector/wiki"
DEFAULT_MAX_ISSUES_DISPLAYED = 500
SUPPORTED_USER_THEMES = frozenset({"classic", "dark"})
SUPPORTED_UI_DENSITIES = frozenset({"compact", "comfortable"})
SUPPORTED_SCAN_SCOPES = frozenset({"scene", "selection"})


@dataclass(frozen=True)
class UserUpdatesSettings:
    """User preference for in-app update checks."""

    check_on_startup: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"check_on_startup": self.check_on_startup}

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> UserUpdatesSettings:
        if not data:
            return cls()
        return cls(check_on_startup=bool(data.get("check_on_startup", False)))


@dataclass(frozen=True)
class UserPreferences:
    """Persistent per-user settings for Pipeline Inspector."""

    schema_version: str = USER_CONFIG_SCHEMA_VERSION
    default_profile_id: str = ""
    default_asset_class_id: str = ""
    default_scan_scope: str = "scene"
    theme: str = "classic"
    ui_density: str = "comfortable"
    extra_rule_paths: tuple[str, ...] = ()
    debug_logging: bool = False
    max_issues_displayed: int = DEFAULT_MAX_ISSUES_DISPLAYED
    mayapy_path: str = ""
    docs_url: str = DEFAULT_USER_DOCS_URL
    assigned_role: str = "technical_artist"
    tracker_username: str = ""
    updates: UserUpdatesSettings = UserUpdatesSettings()
    config_path: Optional[Path] = None

    def with_updates(
        self,
        *,
        schema_version: Optional[str] = None,
        default_profile_id: Optional[str] = None,
        default_asset_class_id: Optional[str] = None,
        default_scan_scope: Optional[str] = None,
        theme: Optional[str] = None,
        ui_density: Optional[str] = None,
        extra_rule_paths: Optional[Sequence[str]] = None,
        debug_logging: Optional[bool] = None,
        max_issues_displayed: Optional[int] = None,
        mayapy_path: Optional[str] = None,
        docs_url: Optional[str] = None,
        assigned_role: Optional[str] = None,
        tracker_username: Optional[str] = None,
        updates: Optional[UserUpdatesSettings] = None,
        config_path: Optional[Path] = None,
    ) -> UserPreferences:
        return replace(
            self,
            schema_version=self.schema_version if schema_version is None else schema_version,
            default_profile_id=(
                self.default_profile_id if default_profile_id is None else default_profile_id
            ),
            default_asset_class_id=(
                self.default_asset_class_id
                if default_asset_class_id is None
                else default_asset_class_id
            ),
            default_scan_scope=(
                self.default_scan_scope if default_scan_scope is None else default_scan_scope
            ),
            theme=self.theme if theme is None else theme,
            ui_density=self.ui_density if ui_density is None else ui_density,
            extra_rule_paths=(
                self.extra_rule_paths
                if extra_rule_paths is None
                else tuple(extra_rule_paths)
            ),
            debug_logging=self.debug_logging if debug_logging is None else debug_logging,
            max_issues_displayed=(
                self.max_issues_displayed
                if max_issues_displayed is None
                else max_issues_displayed
            ),
            mayapy_path=self.mayapy_path if mayapy_path is None else mayapy_path,
            docs_url=self.docs_url if docs_url is None else docs_url,
            assigned_role=self.assigned_role if assigned_role is None else assigned_role,
            tracker_username=(
                self.tracker_username if tracker_username is None else tracker_username
            ),
            updates=self.updates if updates is None else updates,
            config_path=self.config_path if config_path is None else config_path,
        )

    def normalized(self) -> UserPreferences:
        if self.schema_version == USER_CONFIG_SCHEMA_VERSION:
            return self
        return replace(self, schema_version=USER_CONFIG_SCHEMA_VERSION)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "default_profile_id": self.default_profile_id,
            "default_asset_class_id": self.default_asset_class_id,
            "default_scan_scope": self.default_scan_scope,
            "theme": self.theme,
            "ui_density": self.ui_density,
            "extra_rule_paths": list(self.extra_rule_paths),
            "debug_logging": self.debug_logging,
            "max_issues_displayed": int(self.max_issues_displayed),
            "mayapy_path": self.mayapy_path,
            "docs_url": self.docs_url,
            "assigned_role": self.assigned_role,
            "tracker_username": self.tracker_username,
            "updates": self.updates.to_dict(),
        }

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
        *,
        config_path: Path | None = None,
    ) -> UserPreferences:
        schema_version = str(data.get("schema_version", USER_CONFIG_SCHEMA_VERSION))
        extra_paths_raw = data.get("extra_rule_paths")
        extra_rule_paths: tuple[str, ...] = ()
        if isinstance(extra_paths_raw, Sequence) and not isinstance(extra_paths_raw, (str, bytes)):
            extra_rule_paths = tuple(str(path) for path in extra_paths_raw)
        updates_raw = data.get("updates")
        updates = (
            UserUpdatesSettings.from_mapping(updates_raw)
            if isinstance(updates_raw, Mapping)
            else UserUpdatesSettings()
        )
        scan_scope = str(data.get("default_scan_scope", "scene") or "scene")
        if scan_scope not in SUPPORTED_SCAN_SCOPES:
            scan_scope = "scene"
        theme = str(data.get("theme", "classic") or "classic")
        if theme not in SUPPORTED_USER_THEMES:
            theme = "classic"
        ui_density = str(data.get("ui_density", "comfortable") or "comfortable")
        if ui_density not in SUPPORTED_UI_DENSITIES:
            ui_density = "comfortable"
        return cls(
            schema_version=schema_version,
            default_profile_id=str(data.get("default_profile_id", "") or ""),
            default_asset_class_id=str(data.get("default_asset_class_id", "") or ""),
            default_scan_scope=scan_scope,
            theme=theme,
            ui_density=ui_density,
            extra_rule_paths=extra_rule_paths,
            debug_logging=bool(data.get("debug_logging", False)),
            max_issues_displayed=int(
                data.get("max_issues_displayed", DEFAULT_MAX_ISSUES_DISPLAYED)
            ),
            mayapy_path=str(data.get("mayapy_path", "") or ""),
            docs_url=str(data.get("docs_url", DEFAULT_USER_DOCS_URL) or DEFAULT_USER_DOCS_URL),
            assigned_role=str(data.get("assigned_role", "technical_artist") or "technical_artist"),
            tracker_username=str(data.get("tracker_username", "") or ""),
            updates=updates,
            config_path=config_path,
        )

    @classmethod
    def default(cls) -> UserPreferences:
        discovered = discover_user_config_path()
        if discovered is None:
            return cls(config_path=default_user_config_path())
        return load_user_config(discovered)


@dataclass(frozen=True)
class MergedRuntimeConfig:
    """Studio and user layers loaded together at panel runtime."""

    studio: StudioConfig
    user: UserPreferences


def merge_runtime_config(studio: StudioConfig, user: UserPreferences) -> MergedRuntimeConfig:
    """Combine studio policy and user preferences for panel runtime."""

    return MergedRuntimeConfig(studio=studio, user=user)


def default_user_config_path() -> Path:
    return Path.home() / USER_CONFIG_DIRNAME / USER_CONFIG_FILENAME


def _first_existing_file(candidates: tuple[Path, ...]) -> Path | None:
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _config_env_path(*env_vars: str) -> str:
    for env_var in env_vars:
        value = os.environ.get(env_var, "").strip()
        if value:
            return value
    return ""


def discover_user_config_path() -> Path | None:
    """Return the first discovered user config path, if any."""

    env_path = _config_env_path(USER_CONFIG_ENV_VAR, LEGACY_USER_CONFIG_ENV_VAR)
    if env_path:
        candidate = Path(env_path)
        if candidate.is_file():
            return candidate

    return _first_existing_file(
        (
            default_user_config_path(),
            Path.home() / LEGACY_USER_CONFIG_DIRNAME / USER_CONFIG_FILENAME,
        )
    )


def infer_local_mayapy_path() -> str:
    """Return the running mayapy executable path when launched from Maya."""

    import sys

    executable = Path(sys.executable).resolve()
    if executable.stem.lower() == "mayapy":
        return str(executable)
    return ""


def enrich_user_preferences(config: UserPreferences) -> UserPreferences:
    """Fill derived user defaults that should not require manual JSON edits."""

    if config.mayapy_path.strip():
        return config
    inferred = infer_local_mayapy_path()
    if not inferred:
        return config
    return config.with_updates(mayapy_path=inferred)


def load_user_config(path: Path) -> UserPreferences:
    """Load user preferences from a JSON file."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"User config must be a JSON object: {path}")
    return UserPreferences.from_dict(payload, config_path=path.resolve())


def save_user_config(path: Path, config: UserPreferences) -> Path:
    """Write user preferences to a JSON file."""

    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = config.normalized().to_dict()
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
