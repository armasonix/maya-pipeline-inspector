"""Resolve Cerebro user display names for notifications."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pipeline_inspector.integrations.cerebro.adapter import normalize_cerebro_field
from pipeline_inspector.integrations.cerebro.client import CerebroClient
from pipeline_inspector.studio_config import StudioConfig, resolve_cerebro_config

CerebroClientFactory = Callable[[Any], CerebroClient]


def fetch_cerebro_user_display_name(
    studio_config: StudioConfig | None,
    *,
    username: str,
    client_factory: CerebroClientFactory | None = None,
) -> str:
    """Return a human-readable Cerebro user name for the given login."""

    normalized = normalize_cerebro_field(username)
    if not normalized:
        return ""

    config = resolve_cerebro_config(studio_config)
    if config is None:
        return ""

    factory = client_factory or CerebroClient
    client = factory(config)
    if not client.ping():
        return normalized

    lookup_name = getattr(client, "lookup_user_display_name", None)
    if lookup_name is None:
        return normalized
    display_name = str(lookup_name(username=normalized) or "").strip()
    return display_name or normalized
