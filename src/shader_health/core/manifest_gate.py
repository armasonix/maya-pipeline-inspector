"""Manifest regression gate evaluation for pipeline automation."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Optional

JsonDict = dict[str, Any]

@dataclass(frozen=True)
class ManifestGatePolicy:
    """Policy thresholds for manifest regression gates."""

    max_new_changes: int = 0
    max_fingerprint_changes: int = 0
    block_on_new_textures: bool = True

    @classmethod
    def from_mapping(cls, data: Optional[Mapping[str, Any]]) -> ManifestGatePolicy:
        if not data:
            return cls()
        return cls(
            max_new_changes=int(data.get("max_new_changes", 0)),
            max_fingerprint_changes=int(data.get("max_fingerprint_changes", 0)),
            block_on_new_textures=bool(data.get("block_on_new_textures", True)),
        )

@dataclass(frozen=True)
class ManifestGateResult:
    blocked: bool
    reasons: tuple[str, ...]
    diff_summary: Mapping[str, Any]

    def to_dict(self) -> JsonDict:
        return {
            "manifest_regression_blocked": self.blocked,
            "reasons": list(self.reasons),
            "diff_summary": dict(self.diff_summary),
        }

def evaluate_manifest_gate(
    old_manifest: Mapping[str, Any],
    new_manifest: Mapping[str, Any],
    *,
    policy: Optional[ManifestGatePolicy] = None,
) -> ManifestGateResult:
    """Evaluate whether a manifest diff should block publish."""

    from shader_health.reports.manifest_diff import build_manifest_diff

    gate_policy = policy or ManifestGatePolicy()
    diff = build_manifest_diff(old_manifest, new_manifest)
    summary = diff.get("summary", {})
    changed = diff.get("issues", {}).get("changed", [])

    reasons: list[str] = []
    new_count = int(summary.get("new", 0))

    if new_count > gate_policy.max_new_changes:
        reasons.append(f"new manifest entries {new_count} > {gate_policy.max_new_changes}")

    fingerprint_changes = _fingerprint_change_count(changed)
    if fingerprint_changes > gate_policy.max_fingerprint_changes:
        reasons.append(
            "graph fingerprint changes "
            f"{fingerprint_changes} > {gate_policy.max_fingerprint_changes}"
        )

    if gate_policy.block_on_new_textures and _new_texture_count(diff) > 0:
        reasons.append("new texture dependencies detected")

    return ManifestGateResult(
        blocked=bool(reasons),
        reasons=tuple(reasons),
        diff_summary=summary if isinstance(summary, Mapping) else {},
    )

def _fingerprint_change_count(changed: Any) -> int:
    if not isinstance(changed, list):
        return 0
    count = 0
    for entry in changed:
        if not isinstance(entry, Mapping):
            continue
        for change in entry.get("changes", ()):
            if isinstance(change, Mapping) and change.get("field") == "graph_fingerprint":
                count += 1
    return count

def _new_texture_count(diff: Mapping[str, Any]) -> int:
    issues = diff.get("issues", {})
    if not isinstance(issues, Mapping):
        return 0
    new_entries = issues.get("new", [])
    if not isinstance(new_entries, list):
        return 0
    return sum(
        1 for entry in new_entries if isinstance(entry, Mapping) and entry.get("kind") == "texture"
    )
