"""Cerebro connector verification helpers."""
from __future__ import annotations

from dataclasses import dataclass

from pipeline_inspector.integrations.cerebro.client import CerebroClient
from pipeline_inspector.integrations.cerebro.config import cerebro_auth_hint
from pipeline_inspector.studio_config import StudioConfig, resolve_cerebro_config


@dataclass(frozen=True)
class CerebroConnectionStatus:
    """Result of a live Cerebro connectivity check."""

    ok: bool
    message: str


def verify_cerebro_connection(
    studio_config: StudioConfig | None,
    *,
    client_factory: type[CerebroClient] | None = None,
) -> CerebroConnectionStatus:
    """Ping the Cerebro database API with configured credentials."""

    config = resolve_cerebro_config(studio_config)
    if config is None:
        return CerebroConnectionStatus(
            ok=False,
            message="Cerebro connector is disabled or incomplete.",
        )

    factory = client_factory or CerebroClient
    client = factory(config)
    if client.ping():
        return CerebroConnectionStatus(
            ok=True,
            message=(
                f"Cerebro connected to {config.db_host}:{config.resolved_db_port} "
                f"as {config.api_user}."
            ),
        )

    error = client.last_error.strip() or "connect_failed"
    if "Invalid credentials" in error or "cerebro_auth_error" in error:
        return CerebroConnectionStatus(
            ok=False,
            message=f"Cerebro authentication failed. {cerebro_auth_hint()} Last error: {error}",
        )
    return CerebroConnectionStatus(ok=False, message=f"Cerebro connection failed: {error}")
