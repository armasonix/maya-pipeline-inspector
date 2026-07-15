"""Resolve Cerebro session role/group names for governance."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pipeline_inspector.integrations.cerebro.client import CerebroClient
from pipeline_inspector.studio_config import StudioConfig, resolve_cerebro_config

CerebroClientFactory = Callable[[Any], CerebroClient]


def fetch_cerebro_role_names(
    studio_config: StudioConfig | None,
    *,
    username: str = "",
    client_factory: CerebroClientFactory | None = None,
) -> tuple[str, ...]:
    """Return Cerebro role/group names visible for the configured API session."""

    config = resolve_cerebro_config(studio_config)
    if config is None:
        return ()

    factory = client_factory or CerebroClient
    client = factory(config)
    if not client.ping():
        return ()

    list_roles = getattr(client, "list_role_names", None)
    if list_roles is None:
        return ()
    return tuple(list_roles(username=username))
