"""Resolve reporter display names from enabled task trackers."""
from __future__ import annotations

from pipeline_inspector.core.governance import ROLE_LABELS, PipelineRole
from pipeline_inspector.integrations.cerebro.users import fetch_cerebro_user_display_name
from pipeline_inspector.integrations.ftrack.users import fetch_ftrack_user_display_name
from pipeline_inspector.integrations.trackers.role_resolver import resolve_tracker_username
from pipeline_inspector.studio_config import StudioConfig
from pipeline_inspector.user_config import UserPreferences


def _humanize_username(username: str) -> str:
    normalized = username.replace(".", " ").replace("_", " ").strip()
    return normalized.title() if normalized else "Unknown user"


def resolve_tracker_display_name(
    studio_config: StudioConfig | None,
    *,
    user: UserPreferences | None = None,
) -> str:
    """Return the best available display name for the current tracker user."""

    username = resolve_tracker_username(user)
    if not username:
        return "Unknown user"

    if studio_config is not None:
        for fetch_name in (
            fetch_ftrack_user_display_name,
            fetch_cerebro_user_display_name,
        ):
            display_name = fetch_name(studio_config, username=username).strip()
            if display_name and display_name.lower() != username.lower():
                return display_name
            if display_name:
                return display_name

    return _humanize_username(username)


def format_reporter_line(
    *,
    display_name: str,
    pipeline_role: PipelineRole,
) -> str:
    """Format a supervisor report header like ``John Doe (Technical Artist)``."""

    name = str(display_name or "").strip() or "Unknown user"
    role_label = ROLE_LABELS.get(pipeline_role, pipeline_role)
    return f"{name} ({role_label})"
