"""Shared Maya validation pipeline for UI and headless entrypoints."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from shader_health.core import (
    GraphSnapshot,
    RuleDefinition,
    RuleLoadError,
    RuleResult,
    ValidationEngine,
    apply_waivers,
    build_fix_plan,
    compute_health_score,
    load_rule_stack,
    load_waiver_sidecar,
    summarize_results,
)
from shader_health.core.rule_loader import DEFAULT_RULE_ROOT, load_profile
from shader_health.maya.snapshot_enrichment import (
    enrich_rule_results,
    prepare_snapshot_for_validation,
)

PROFILE_ROOT = DEFAULT_RULE_ROOT / "profiles"
DEFAULT_PROFILE_ID = "artist_relaxed"


@dataclass(frozen=True)
class ValidationRunResult:
    """Normalized validation output for UI and CLI consumers."""

    snapshot: GraphSnapshot
    results: tuple[RuleResult, ...]
    rules: tuple[RuleDefinition, ...]
    fix_plan: Any
    summary: Any
    health_score: Any
    message: str
    scan_scope: str
    profile_id: str


def packaged_profile_path(profile_id: str) -> Path:
    """Return the packaged profile JSON path for a known profile id."""

    normalized = profile_id.strip()
    if not normalized:
        raise RuleLoadError("profile id is required")
    path = PROFILE_ROOT / f"{normalized}.json"
    if not path.is_file():
        raise RuleLoadError(f"Unknown profile: {normalized}")
    return path


def list_packaged_profile_ids() -> tuple[str, ...]:
    """Return sorted packaged profile ids."""

    if not PROFILE_ROOT.is_dir():
        return ()
    return tuple(
        sorted(path.stem for path in PROFILE_ROOT.glob("*.json") if path.is_file())
    )


def waiver_sidecar_path_for_scene(scene_path: str) -> Optional[Path]:
    """Return the default waiver sidecar path beside a Maya scene."""

    if not scene_path:
        return None
    scene = Path(scene_path)
    if not scene.name:
        return None
    return scene.with_name(f"{scene.stem}.shader_health_waivers.json")


def run_validation(
    snapshot: GraphSnapshot,
    *,
    profile_id: str = DEFAULT_PROFILE_ID,
    profile_path: Optional[Path] = None,
    rule_root: Optional[Path] = None,
    extra_rule_paths: tuple[Path, ...] = (),
    waiver_sidecar_path: Optional[Path] = None,
    scan_scope: str = "scene",
) -> ValidationRunResult:
    """Validate an enriched snapshot using packaged rules, profile, and waivers."""

    enriched = prepare_snapshot_for_validation(snapshot)
    resolved_profile = profile_path or packaged_profile_path(profile_id)
    profile = load_profile(resolved_profile)
    renderer_ids = (enriched.renderer,) if enriched.renderer else ()
    rules = load_rule_stack(
        rule_root=rule_root or DEFAULT_RULE_ROOT,
        renderer_ids=renderer_ids,
        profile_path=resolved_profile,
        extra_rule_paths=extra_rule_paths,
    )
    results = list(ValidationEngine().validate(enriched, rules))
    sidecar_path = waiver_sidecar_path or waiver_sidecar_path_for_scene(enriched.scene_path)
    if sidecar_path is not None and sidecar_path.is_file():
        results = list(apply_waivers(results, load_waiver_sidecar(sidecar_path)))
    results = enrich_rule_results(enriched, results)
    fix_plan = build_fix_plan(results, rules, enriched)
    summary = summarize_results(results)
    health_score = compute_health_score(results)
    failed_count = sum(1 for item in results if item.status == "failed")
    scope_label = "selection" if scan_scope == "selection" else "scene"
    message = (
        f"{scope_label.title()} validated with profile {profile.id}. "
        f"{failed_count} failed issue(s). Health: {health_score.score}/100."
    )
    return ValidationRunResult(
        snapshot=enriched,
        results=tuple(results),
        rules=tuple(rules),
        fix_plan=fix_plan,
        summary=summary,
        health_score=health_score,
        message=message,
        scan_scope=scan_scope,
        profile_id=profile.id,
    )
