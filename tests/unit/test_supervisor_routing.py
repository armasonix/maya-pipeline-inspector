from __future__ import annotations

from pipeline_inspector.core.governance import (
    build_permission_resolver,
)
from pipeline_inspector.core.supervisor_routing import resolve_supervisor_route
from pipeline_inspector.integrations.trackers.role_resolver import resolve_tracker_role_candidates
from pipeline_inspector.studio_config import (
    CerebroConnectorSettings,
    ConnectorSettings,
    FtrackConnectorSettings,
    GovernanceSettings,
    StudioConfig,
    SupervisorRoute,
)
from pipeline_inspector.user_config import UserPreferences


def test_resolve_supervisor_route_for_reporter_role():
    governance = GovernanceSettings(
        supervisor_routes={
            "technical_artist": SupervisorRoute(
                supervisor_label="Lead TD",
                telegram_chat_id="-100111",
            )
        }
    )

    decision = resolve_supervisor_route(governance, "technical_artist")

    assert decision is not None
    assert decision.route.telegram_chat_id == "-100111"
    assert "Lead TD" in decision.reason


def test_resolve_supervisor_route_returns_none_without_targets():
    governance = GovernanceSettings(
        supervisor_routes={
            "technical_artist": SupervisorRoute(supervisor_label="Lead TD"),
        }
    )

    assert resolve_supervisor_route(governance, "technical_artist") is None


def test_resolve_tracker_role_candidates_prefers_ftrack_then_cerebro(monkeypatch):
    studio = StudioConfig(
        connectors=ConnectorSettings(
            ftrack=FtrackConnectorSettings(enabled=True),
            cerebro=CerebroConnectorSettings(enabled=True),
        )
    )

    monkeypatch.setattr(
        "pipeline_inspector.integrations.trackers.role_resolver.fetch_ftrack_security_role_names",
        lambda *_args, **_kwargs: ("Artist",),
    )
    monkeypatch.setattr(
        "pipeline_inspector.integrations.trackers.role_resolver.fetch_cerebro_role_names",
        lambda *_args, **_kwargs: ("TD Group",),
    )

    assert resolve_tracker_role_candidates(studio, user=UserPreferences()) == (
        "Artist",
        "TD Group",
    )


def test_build_permission_resolver_uses_tracker_role_map():
    studio = StudioConfig(
        governance=GovernanceSettings(
            tracker_role_map={"Artist": "technical_artist"},
        ),
    )

    resolver = build_permission_resolver(
        studio=studio,
        user=UserPreferences(assigned_role="pipeline_td"),
        tracker_role="Artist",
    )

    assert resolver.effective_role == "technical_artist"
    assert resolver.role_source == "tracker_role"


def test_producer_role_is_no_longer_supported():
    resolver = build_permission_resolver(
        studio=StudioConfig.default(),
        user=UserPreferences(assigned_role="producer"),
    )

    assert resolver.effective_role == "technical_artist"
    assert resolver.role_source == "default"
