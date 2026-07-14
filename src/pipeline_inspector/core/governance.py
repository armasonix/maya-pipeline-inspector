"""Role-based capability resolution for studio governance."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal, Optional

from pipeline_inspector.studio_config import GovernanceSettings, StudioConfig
from pipeline_inspector.user_config import UserPreferences

Capability = Literal[
    "apply_safe_fixes",
    "apply_risky_fixes",
    "submit_farm",
    "manage_rules",
    "edit_connectors",
    "edit_studio_settings",
]

PipelineRole = Literal[
    "technical_artist",
    "technical_support",
    "pipeline_td",
    "producer",
    "admin",
]

RoleSource = Literal["studio_policy", "tracker_role", "user_preference", "default"]

DEFAULT_PIPELINE_ROLE: PipelineRole = "technical_artist"

ROLE_LABELS: dict[PipelineRole, str] = {
    "technical_artist": "Technical Artist",
    "technical_support": "Technical Support",
    "pipeline_td": "Pipeline TD",
    "producer": "Producer",
    "admin": "Admin",
}

ROLE_OPTIONS: tuple[tuple[str, PipelineRole], ...] = tuple(
    (ROLE_LABELS[role_id], role_id) for role_id in ROLE_LABELS
)

TRACKER_ROLE_ENV_VAR = "PIPELINE_INSPECTOR_TRACKER_ROLE"

ROLE_CAPABILITY_MATRIX: dict[PipelineRole, frozenset[Capability]] = {
    "technical_artist": frozenset(
        {
            "apply_safe_fixes",
            "submit_farm",
        }
    ),
    "technical_support": frozenset(
        {
            "apply_safe_fixes",
            "apply_risky_fixes",
            "submit_farm",
        }
    ),
    "pipeline_td": frozenset(
        {
            "apply_safe_fixes",
            "apply_risky_fixes",
            "submit_farm",
            "manage_rules",
            "edit_connectors",
            "edit_studio_settings",
        }
    ),
    "producer": frozenset(
        {
            "apply_safe_fixes",
            "submit_farm",
        }
    ),
    "admin": frozenset(
        {
            "apply_safe_fixes",
            "apply_risky_fixes",
            "submit_farm",
            "manage_rules",
            "edit_connectors",
            "edit_studio_settings",
        }
    ),
}

_ROLE_ALIASES: dict[str, PipelineRole] = {
    "technical_artist": "technical_artist",
    "technical artist": "technical_artist",
    "artist": "technical_artist",
    "technical_support": "technical_support",
    "technical support": "technical_support",
    "support": "technical_support",
    "pipeline_td": "pipeline_td",
    "pipeline td": "pipeline_td",
    "td": "pipeline_td",
    "producer": "producer",
    "admin": "admin",
    "administrator": "admin",
}


@dataclass(frozen=True)
class PermissionDecision:
    """Outcome of a single capability check."""

    allowed: bool
    capability: Capability
    effective_role: PipelineRole
    role_source: RoleSource
    reason: str


@dataclass(frozen=True)
class PermissionResolver:
    """Resolve whether the current runtime context may perform an action."""

    effective_role: PipelineRole
    role_source: RoleSource
    allowed_capabilities: frozenset[Capability]

    def allows(self, capability: Capability) -> bool:
        return capability in self.allowed_capabilities

    def require(self, capability: Capability) -> PermissionDecision:
        if self.allows(capability):
            return PermissionDecision(
                allowed=True,
                capability=capability,
                effective_role=self.effective_role,
                role_source=self.role_source,
                reason=(
                    f"Allowed for {ROLE_LABELS[self.effective_role]} "
                    f"({self.role_source.replace('_', ' ')})."
                ),
            )
        return PermissionDecision(
            allowed=False,
            capability=capability,
            effective_role=self.effective_role,
            role_source=self.role_source,
            reason=format_permission_denial(capability, self),
        )


def normalize_pipeline_role(value: str | None) -> Optional[PipelineRole]:
    normalized = str(value or "").strip().casefold().replace("-", "_")
    if not normalized:
        return None
    return _ROLE_ALIASES.get(normalized.replace(" ", "_")) or _ROLE_ALIASES.get(
        normalized.replace("_", " ")
    )


def resolve_effective_role(
    *,
    governance: GovernanceSettings,
    user: UserPreferences,
    tracker_role: str | None = None,
) -> tuple[PipelineRole, RoleSource]:
    enforced = normalize_pipeline_role(governance.enforced_role)
    if enforced is not None:
        return enforced, "studio_policy"

    tracker_normalized = str(tracker_role or "").strip()
    if tracker_normalized:
        mapped = governance.tracker_role_map.get(
            tracker_normalized,
            tracker_normalized,
        )
        tracker_resolved = normalize_pipeline_role(mapped)
        if tracker_resolved is not None:
            return tracker_resolved, "tracker_role"

    user_role = normalize_pipeline_role(user.assigned_role)
    if user_role is not None:
        return user_role, "user_preference"

    return DEFAULT_PIPELINE_ROLE, "default"


def resolve_allowed_capabilities(
    role: PipelineRole,
    governance: GovernanceSettings,
) -> frozenset[Capability]:
    base = ROLE_CAPABILITY_MATRIX.get(role, ROLE_CAPABILITY_MATRIX[DEFAULT_PIPELINE_ROLE])
    denied = {
        str(item).strip()
        for item in governance.capability_denials.get(role, ())
        if str(item).strip()
    }
    return frozenset(capability for capability in base if capability not in denied)


def build_permission_resolver(
    *,
    studio: StudioConfig,
    user: UserPreferences,
    tracker_role: str | None = None,
) -> PermissionResolver:
    effective_role, role_source = resolve_effective_role(
        governance=studio.governance,
        user=user,
        tracker_role=tracker_role,
    )
    allowed_capabilities = resolve_allowed_capabilities(effective_role, studio.governance)
    return PermissionResolver(
        effective_role=effective_role,
        role_source=role_source,
        allowed_capabilities=allowed_capabilities,
    )


def tracker_role_from_environment() -> str | None:
    value = os.environ.get(TRACKER_ROLE_ENV_VAR, "").strip()
    return value or None


def build_permission_resolver_from_runtime(
    *,
    studio: StudioConfig | None = None,
    user: UserPreferences | None = None,
    tracker_role: str | None = None,
) -> PermissionResolver:
    return build_permission_resolver(
        studio=studio or StudioConfig.default(),
        user=user or UserPreferences.default(),
        tracker_role=tracker_role if tracker_role is not None else tracker_role_from_environment(),
    )


def format_permission_denial(capability: Capability, resolver: PermissionResolver) -> str:
    capability_label = capability.replace("_", " ")
    role_label = ROLE_LABELS[resolver.effective_role]
    source_label = resolver.role_source.replace("_", " ")
    return (
        f"{capability_label.title()} is not allowed for {role_label} "
        f"(resolved from {source_label})."
    )
