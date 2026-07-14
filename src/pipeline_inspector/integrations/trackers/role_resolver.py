"""Unified tracker role resolution for governance."""
from __future__ import annotations

import os

from pipeline_inspector.integrations.cerebro.roles import fetch_cerebro_role_names
from pipeline_inspector.integrations.ftrack.roles import fetch_ftrack_security_role_names
from pipeline_inspector.studio_config import StudioConfig
from pipeline_inspector.user_config import UserPreferences

TRACKER_USER_ENV_VAR = "PIPELINE_INSPECTOR_TRACKER_USER"


def resolve_tracker_username(user: UserPreferences | None = None) -> str:
    """Return the tracker username used for Ftrack/Cerebro role lookups."""

    env_value = os.environ.get(TRACKER_USER_ENV_VAR, "").strip()
    if env_value:
        return env_value
    if user is not None:
        tracker_username = str(getattr(user, "tracker_username", "") or "").strip()
        if tracker_username:
            return tracker_username
    return os.environ.get("USERNAME", "").strip() or os.environ.get("USER", "").strip()


def resolve_tracker_role_candidates(
    studio: StudioConfig | None,
    *,
    user: UserPreferences | None = None,
) -> tuple[str, ...]:
    """Return raw tracker role names from enabled Ftrack and Cerebro connectors."""

    if studio is None:
        return ()

    username = resolve_tracker_username(user)
    candidates: list[str] = []
    for name in fetch_ftrack_security_role_names(studio, username=username):
        if name not in candidates:
            candidates.append(name)
    for name in fetch_cerebro_role_names(studio, username=username):
        if name not in candidates:
            candidates.append(name)
    return tuple(candidates)


def resolve_tracker_role_for_runtime(
    studio: StudioConfig | None,
    *,
    user: UserPreferences | None = None,
) -> str | None:
    """Return the first tracker role candidate for governance resolution."""

    from pipeline_inspector.core.governance import tracker_role_from_environment

    env_role = tracker_role_from_environment()
    if env_role:
        return env_role

    candidates = resolve_tracker_role_candidates(studio, user=user)
    if not candidates:
        return None
    return candidates[0]
