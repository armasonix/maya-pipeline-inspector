from __future__ import annotations

import pytest

from pipeline_inspector.core.governance import (
    DEFAULT_PIPELINE_ROLE,
    build_permission_resolver,
    normalize_pipeline_role,
    resolve_effective_role,
)
from pipeline_inspector.studio_config import GovernanceSettings, StudioConfig
from pipeline_inspector.user_config import UserPreferences


def test_normalize_pipeline_role_accepts_labels_and_ids():
    assert normalize_pipeline_role("Pipeline TD") == "pipeline_td"
    assert normalize_pipeline_role("technical_artist") == "technical_artist"
    assert normalize_pipeline_role("Administrator") == "admin"
    assert normalize_pipeline_role("unknown role") is None


def test_resolve_effective_role_priority_studio_tracker_user_default():
    governance = GovernanceSettings(
        enforced_role="",
        tracker_role_map={"Pipeline Supervisor": "pipeline_td"},
    )
    studio = StudioConfig(governance=governance)
    user = UserPreferences(assigned_role="producer")

    role, source = resolve_effective_role(
        governance=studio.governance,
        user=user,
        tracker_role="Pipeline Supervisor",
    )
    assert role == "pipeline_td"
    assert source == "tracker_role"

    locked = StudioConfig(governance=GovernanceSettings(enforced_role="admin"))
    role, source = resolve_effective_role(
        governance=locked.governance,
        user=user,
        tracker_role="Pipeline Supervisor",
    )
    assert role == "admin"
    assert source == "studio_policy"

    role, source = resolve_effective_role(
        governance=governance,
        user=user,
        tracker_role=None,
    )
    assert role == "producer"
    assert source == "user_preference"

    role, source = resolve_effective_role(
        governance=GovernanceSettings(),
        user=UserPreferences(assigned_role=""),
        tracker_role=None,
    )
    assert role == DEFAULT_PIPELINE_ROLE
    assert source == "default"


@pytest.mark.parametrize(
    ("role", "capability", "expected"),
    [
        ("technical_artist", "edit_studio_settings", False),
        ("technical_artist", "apply_safe_fixes", True),
        ("technical_support", "apply_risky_fixes", True),
        ("pipeline_td", "manage_rules", True),
        ("producer", "submit_farm", True),
        ("producer", "apply_risky_fixes", False),
        ("admin", "edit_connectors", True),
    ],
)
def test_capability_matrix(role, capability, expected):
    resolver = build_permission_resolver(
        studio=StudioConfig.default(),
        user=UserPreferences(assigned_role=role),
    )
    assert resolver.allows(capability) is expected


def test_studio_capability_denials_remove_granted_capabilities():
    studio = StudioConfig(
        governance=GovernanceSettings(
            capability_denials={"producer": ("submit_farm",)},
        )
    )
    resolver = build_permission_resolver(
        studio=studio,
        user=UserPreferences(assigned_role="producer"),
    )

    assert resolver.allows("apply_safe_fixes") is True
    assert resolver.allows("submit_farm") is False


def test_require_returns_actionable_denial_reason():
    resolver = build_permission_resolver(
        studio=StudioConfig.default(),
        user=UserPreferences(assigned_role="technical_artist"),
    )

    decision = resolver.require("edit_studio_settings")

    assert decision.allowed is False
    assert "Technical Artist" in decision.reason
    assert decision.role_source == "user_preference"
