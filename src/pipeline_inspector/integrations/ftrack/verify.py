"""Ftrack connector verification helpers."""
from __future__ import annotations

from dataclasses import dataclass

from pipeline_inspector.integrations.ftrack.client import FtrackClient
from pipeline_inspector.integrations.ftrack.helpers import (
    ftrack_username_hint,
    is_auth_exception,
    sample_project_names,
)
from pipeline_inspector.integrations.ftrack.queries import (
    list_projects_expression,
    ping_user_expression,
)
from pipeline_inspector.studio_config import StudioConfig, resolve_ftrack_config


@dataclass(frozen=True)
class FtrackConnectionStatus:
    """Result of a live Ftrack connectivity check."""

    ok: bool
    message: str
    project_count: int = 0
    sample_project_names: tuple[str, ...] = ()


def verify_ftrack_connection(
    studio_config: StudioConfig | None,
    *,
    client_factory: type[FtrackClient] | None = None,
) -> FtrackConnectionStatus:
    """Ping Ftrack and list visible projects for the configured API user."""

    config = resolve_ftrack_config(studio_config)
    if config is None:
        return FtrackConnectionStatus(
            ok=False,
            message="Ftrack connector is disabled or incomplete.",
        )

    factory = client_factory or FtrackClient
    client = factory(config)
    rows, status_code, exception_message = client.query_rows(ping_user_expression())
    if status_code != 200:
        return FtrackConnectionStatus(
            ok=False,
            message=f"Ftrack API HTTP {status_code} at {config.endpoint_url}.",
        )
    if exception_message:
        if is_auth_exception(exception_message):
            return FtrackConnectionStatus(
                ok=False,
                message=(
                    f"Authentication failed: {exception_message}."
                    f"{ftrack_username_hint(config.api_user)}"
                ),
            )
        return FtrackConnectionStatus(
            ok=False,
            message=f"Ftrack query failed: {exception_message}.",
        )
    if not rows:
        return FtrackConnectionStatus(
            ok=False,
            message=(
                "Ftrack accepted the request but returned no user record."
                f"{ftrack_username_hint(config.api_user)}"
            ),
        )

    project_rows, project_status, project_exception = client.query_rows(list_projects_expression())
    if project_status != 200:
        return FtrackConnectionStatus(
            ok=False,
            message=f"Project listing failed with HTTP {project_status}.",
        )
    if project_exception:
        if is_auth_exception(project_exception):
            return FtrackConnectionStatus(
                ok=False,
                message=(
                    f"Authentication failed while listing projects: {project_exception}."
                    f"{ftrack_username_hint(config.api_user)}"
                ),
            )
        return FtrackConnectionStatus(
            ok=False,
            message=f"Project listing failed: {project_exception}.",
        )

    sample_names = sample_project_names(project_rows, limit=8)
    configured = config.project.strip()
    if configured:
        target = configured.casefold()
        matched = any(
            str(row.get(field, "") or "").strip().casefold() == target
            for row in project_rows
            for field in ("name", "full_name")
        )
        if matched:
            return FtrackConnectionStatus(
                ok=True,
                message=f"Connected. Project '{configured}' is visible to this API user.",
                project_count=len(project_rows),
                sample_project_names=sample_names,
            )
        if sample_names:
            return FtrackConnectionStatus(
                ok=False,
                message=(
                    f"Connected, but project '{configured}' was not found. "
                    f"Visible projects: {', '.join(sample_names)}."
                ),
                project_count=len(project_rows),
                sample_project_names=sample_names,
            )
        return FtrackConnectionStatus(
            ok=False,
            message=(
                f"Connected, but project '{configured}' was not found and "
                "no projects are visible to this API user."
            ),
            project_count=0,
        )

    if sample_names:
        return FtrackConnectionStatus(
            ok=True,
            message=f"Connected. Visible projects: {', '.join(sample_names)}.",
            project_count=len(project_rows),
            sample_project_names=sample_names,
        )
    return FtrackConnectionStatus(
        ok=True,
        message="Connected, but no projects are visible to this API user.",
        project_count=0,
    )
