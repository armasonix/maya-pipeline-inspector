"""Resolve Ftrack user display names for notifications."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pipeline_inspector.integrations.ftrack.client import FtrackClient
from pipeline_inspector.integrations.ftrack.queries import user_by_username_expression
from pipeline_inspector.studio_config import StudioConfig, resolve_ftrack_config

FtrackClientFactory = Callable[[Any], FtrackClient]


def _format_ftrack_user_name(row: dict[str, Any]) -> str:
    first_name = str(row.get("first_name", "") or "").strip()
    last_name = str(row.get("last_name", "") or "").strip()
    full_name = f"{first_name} {last_name}".strip()
    if full_name:
        return full_name
    return str(row.get("username", "") or "").strip()


def fetch_ftrack_user_display_name(
    studio_config: StudioConfig | None,
    *,
    username: str,
    client_factory: FtrackClientFactory | None = None,
) -> str:
    """Return a human-readable Ftrack user name for the given username."""

    normalized = str(username or "").strip()
    if not normalized:
        return ""

    config = resolve_ftrack_config(studio_config)
    if config is None:
        return ""

    factory = client_factory or FtrackClient
    rows = factory(config).query(user_by_username_expression(normalized))
    if not rows:
        return normalized
    return _format_ftrack_user_name(rows[0]) or normalized
