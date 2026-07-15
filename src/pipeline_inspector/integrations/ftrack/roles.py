"""Resolve Ftrack security roles for governance and supervisor routing."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pipeline_inspector.integrations.ftrack.client import FtrackClient
from pipeline_inspector.integrations.ftrack.queries import user_security_roles_expression
from pipeline_inspector.studio_config import StudioConfig, resolve_ftrack_config

FtrackClientFactory = Callable[[Any], FtrackClient]


def fetch_ftrack_security_role_names(
    studio_config: StudioConfig | None,
    *,
    username: str,
    client_factory: FtrackClientFactory | None = None,
) -> tuple[str, ...]:
    """Return Ftrack security role names assigned to the given username."""

    normalized = str(username or "").strip()
    if not normalized:
        return ()

    config = resolve_ftrack_config(studio_config)
    if config is None:
        return ()

    factory = client_factory or FtrackClient
    client = factory(config)
    rows = client.query(user_security_roles_expression(normalized))
    names: list[str] = []
    for row in rows:
        name = str(row.get("name", "") or "").strip()
        if name and name not in names:
            names.append(name)
    return tuple(names)
