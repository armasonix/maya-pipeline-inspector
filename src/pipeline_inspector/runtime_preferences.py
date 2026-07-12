"""Map persisted user preferences into runtime pipeline and UI defaults."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pipeline_inspector.maya.validation_pipeline import DEFAULT_PROFILE_ID
from pipeline_inspector.user_config import SUPPORTED_SCAN_SCOPES, UserPreferences


@dataclass(frozen=True)
class UserValidationPreferences:
    """Validation inputs derived from user preferences."""

    profile_id: str
    asset_class_id: str
    scan_scope: str
    extra_rule_paths: tuple[Path, ...]

def resolved_profile_id(user: UserPreferences, override: str | None = None) -> str:
    """Return the workflow profile id from user prefs with a safe fallback."""

    candidate = (override or user.default_profile_id or DEFAULT_PROFILE_ID).strip()
    return candidate or DEFAULT_PROFILE_ID

def resolved_asset_class_id(user: UserPreferences, override: str | None = None) -> str:
    """Return the asset class overlay id from user prefs or an override."""

    if override is not None:
        return override.strip()
    return (user.default_asset_class_id or "").strip()

def resolved_scan_scope(user: UserPreferences, override: str | None = None) -> str:
    """Return the default validation scan scope from user prefs."""

    candidate = (override or user.default_scan_scope or "scene").strip() or "scene"
    if candidate not in SUPPORTED_SCAN_SCOPES:
        return "scene"
    return candidate

def user_extra_rule_paths(user: UserPreferences) -> tuple[Path, ...]:
    """Return resolved extra rule path entries from user preferences."""

    return tuple(
        Path(path)
        for path in user.extra_rule_paths
        if str(path).strip()
    )

def user_validation_preferences(
    user: UserPreferences,
    *,
    scan_scope: str | None = None,
    profile_id: str | None = None,
    asset_class_id: str | None = None,
) -> UserValidationPreferences:
    """Build validation defaults from user preferences and optional overrides."""

    return UserValidationPreferences(
        profile_id=resolved_profile_id(user, profile_id),
        asset_class_id=resolved_asset_class_id(user, asset_class_id),
        scan_scope=resolved_scan_scope(user, scan_scope),
        extra_rule_paths=user_extra_rule_paths(user),
    )
