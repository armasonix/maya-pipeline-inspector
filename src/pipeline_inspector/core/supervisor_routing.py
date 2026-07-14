"""Route validation and readiness reports to supervisor notification targets."""
from __future__ import annotations

from dataclasses import dataclass

from pipeline_inspector.core.governance import ROLE_LABELS, PipelineRole
from pipeline_inspector.studio_config import GovernanceSettings, SupervisorRoute


@dataclass(frozen=True)
class SupervisorRoutingDecision:
    """Resolved supervisor destination for a reporter role."""

    reporter_role: PipelineRole
    route: SupervisorRoute
    reason: str


def resolve_supervisor_route(
    governance: GovernanceSettings,
    reporter_role: PipelineRole,
) -> SupervisorRoutingDecision | None:
    """Return the configured supervisor route for a reporter pipeline role."""

    route = governance.supervisor_routes.get(reporter_role)
    if route is None:
        return None
    if not _route_has_target(route):
        return None
    reporter_label = ROLE_LABELS.get(reporter_role, reporter_role)
    supervisor_label = route.supervisor_label.strip() or "Supervisor"
    return SupervisorRoutingDecision(
        reporter_role=reporter_role,
        route=route,
        reason=(
            f"Reports from {reporter_label} route to {supervisor_label} "
            "per studio governance policy."
        ),
    )


def _route_has_target(route: SupervisorRoute) -> bool:
    return bool(
        route.telegram_chat_id.strip()
        or route.discord_webhook_url.strip()
        or route.slack_webhook_url.strip()
    )
