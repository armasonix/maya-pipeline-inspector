"""Shared Maya validation pipeline for UI and headless entrypoints."""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Optional

from pipeline_inspector.core import (
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
from pipeline_inspector.core.rule_loader import DEFAULT_RULE_ROOT, ProfileDefinition, load_profile
from pipeline_inspector.maya.snapshot_enrichment import (
    enrich_rule_results,
    prepare_snapshot_for_validation,
)
from pipeline_inspector.studio_config import (
    StudioConfig,
    StudioEnvironmentSettings,
    merge_studio_rule_overrides,
)
from pipeline_inspector.user_config import UserPreferences

PROFILE_ROOT = DEFAULT_RULE_ROOT / "profiles"
DEFAULT_PROFILE_ID = "artist_relaxed"
ASSET_CLASS_NONE_ID = ""
PIPELINE_ONLY_PROFILE_IDS = frozenset({"ci_headless"})
WORKFLOW_PROFILE_IDS = frozenset(
    {
        "artist_relaxed",
        "publish_strict",
        "deadline_critical",
        "supervisor_full",
    }
)
ASSET_CLASS_PROFILE_IDS = frozenset(
    {
        "asset_class_hero",
        "asset_class_prop",
        "asset_class_background",
    }
)


def _studio_environment_for_validation(
    studio_config: Optional[StudioConfig],
) -> Optional[StudioEnvironmentSettings]:
    if studio_config is None:
        return None
    return studio_config.studio_environment


@dataclass(frozen=True)
class ProfileOption:
    """One selectable profile entry for Maya UI dropdowns."""

    profile_id: str
    display_name: str


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
    asset_class_id: str = ""


def profile_kind(profile_id: str) -> str:
    """Return profile_kind inferred from id when not stored in JSON."""

    normalized = profile_id.strip()
    if normalized.startswith("asset_class_"):
        return "asset_class"
    if normalized in PIPELINE_ONLY_PROFILE_IDS:
        return "pipeline"
    return "workflow"


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


def list_workflow_profile_options() -> tuple[ProfileOption, ...]:
    """Return workflow profiles shown in the Maya UI."""

    options: list[ProfileOption] = []
    for profile_id in sorted(WORKFLOW_PROFILE_IDS):
        profile = load_profile(packaged_profile_path(profile_id))
        options.append(ProfileOption(profile_id=profile.id, display_name=profile.display_name))
    return tuple(options)


def list_asset_class_profile_options() -> tuple[ProfileOption, ...]:
    """Return asset class overlay profiles for the Maya UI."""

    options: list[ProfileOption] = []
    for profile_id in sorted(ASSET_CLASS_PROFILE_IDS):
        profile = load_profile(packaged_profile_path(profile_id))
        options.append(ProfileOption(profile_id=profile.id, display_name=profile.display_name))
    return tuple(options)


def compose_profiles(
    workflow_id: str,
    asset_class_id: Optional[str] = None,
) -> ProfileDefinition:
    """Merge a workflow profile with an optional asset class overlay."""

    workflow = load_profile(packaged_profile_path(workflow_id))
    normalized_asset_class = (asset_class_id or "").strip()
    kind = profile_kind(workflow.id)

    if kind == "pipeline":
        if normalized_asset_class:
            raise RuleLoadError(
                f"Asset class overlay is not supported for pipeline profile {workflow.id!r}"
            )
        return workflow

    if kind != "workflow":
        raise RuleLoadError(f"Expected workflow profile, got {workflow.id!r}")

    if not normalized_asset_class:
        return workflow

    asset_class = load_profile(packaged_profile_path(normalized_asset_class))
    if profile_kind(asset_class.id) != "asset_class":
        raise RuleLoadError(f"Expected asset class profile, got {asset_class.id!r}")

    merged_overrides = dict(workflow.rule_overrides)
    merged_overrides.update(asset_class.rule_overrides)
    manifest_diff_policy = (
        asset_class.manifest_diff_policy
        if normalized_asset_class
        else workflow.manifest_diff_policy
    )
    return replace(
        workflow,
        rule_overrides=merged_overrides,
        manifest_diff_policy=manifest_diff_policy,
    )


def waiver_sidecar_path_for_scene(scene_path: str) -> Optional[Path]:
    """Return the default waiver sidecar path beside a Maya scene."""

    if not scene_path:
        return None
    scene = Path(scene_path)
    if not scene.name:
        return None
    return scene.with_name(f"{scene.stem}.pipeline_inspector_waivers.json")


def fix_audit_sidecar_path_for_scene(scene_path: str) -> Optional[Path]:
    """Return the default fix audit sidecar path beside a Maya scene."""

    if not scene_path:
        return None
    scene = Path(scene_path)
    if not scene.name:
        return None
    return scene.with_name(f"{scene.stem}.pipeline_inspector_fix_audit.json")


def resolve_waiver_sidecar_path(scene_path: str) -> Optional[Path]:
    """Return waiver sidecar path, falling back to the legacy Shader Health filename."""

    primary = waiver_sidecar_path_for_scene(scene_path)
    if primary is not None and primary.is_file():
        return primary
    if not scene_path:
        return primary
    scene = Path(scene_path)
    if not scene.name:
        return primary
    legacy = scene.with_name(f"{scene.stem}.shader_health_waivers.json")
    if legacy.is_file():
        return legacy
    return primary


def resolve_fix_audit_sidecar_path(scene_path: str) -> Optional[Path]:
    """Return fix-audit sidecar path, falling back to the legacy Shader Health filename."""

    primary = fix_audit_sidecar_path_for_scene(scene_path)
    if primary is not None and primary.is_file():
        return primary
    if not scene_path:
        return primary
    scene = Path(scene_path)
    if not scene.name:
        return primary
    legacy = scene.with_name(f"{scene.stem}.shader_health_fix_audit.json")
    if legacy.is_file():
        return legacy
    return primary


def persist_fix_apply_audit(
    apply_report: Any,
    *,
    scene_path: str,
    profile_id: str,
    audit_sidecar_path: Optional[Path] = None,
    applied_at_utc: Optional[str] = None,
) -> tuple[Optional[Path], dict[str, Any]]:
    """Append an apply session to the scene fix audit sidecar."""

    from pipeline_inspector.core.fix_audit import (
        append_fix_audit_session,
        build_fix_audit_session,
    )

    session = build_fix_audit_session(
        scene_path=scene_path,
        profile_id=profile_id,
        apply_report=apply_report,
        applied_at_utc=applied_at_utc,
    )
    session_dict = session.to_dict()
    sidecar_path = audit_sidecar_path or resolve_fix_audit_sidecar_path(scene_path)
    if sidecar_path is None:
        return None, session_dict
    written_path = append_fix_audit_session(sidecar_path, session)
    return written_path, session_dict


def run_validation(
    snapshot: GraphSnapshot,
    *,
    profile_id: str = DEFAULT_PROFILE_ID,
    asset_class_id: Optional[str] = None,
    profile_path: Optional[Path] = None,
    rule_root: Optional[Path] = None,
    extra_rule_paths: tuple[Path, ...] = (),
    waiver_sidecar_path: Optional[Path] = None,
    scan_scope: str = "scene",
    studio_config: Optional[StudioConfig] = None,
    session_rule_overrides: Optional[dict[str, Any]] = None,
) -> ValidationRunResult:
    """Validate an enriched snapshot using packaged rules, profile, and waivers."""

    enriched = prepare_snapshot_for_validation(
        snapshot,
        studio_environment=_studio_environment_for_validation(studio_config),
    )
    normalized_asset_class = (asset_class_id or "").strip()
    if profile_path is not None:
        profile = load_profile(profile_path)
        effective_profile_id = profile.id
    else:
        profile = compose_profiles(profile_id, normalized_asset_class or None)
        effective_profile_id = profile_id
    if studio_config is not None:
        profile = replace(
            profile,
            rule_overrides=merge_studio_rule_overrides(profile.rule_overrides, studio_config),
        )
    if session_rule_overrides:
        from pipeline_inspector.core.rule_browser import merge_session_rule_overrides
        from pipeline_inspector.core.rule_loader import RuleOverride

        normalized_overrides = {
            str(rule_id): (
                override
                if isinstance(override, RuleOverride)
                else RuleOverride.from_dict(str(rule_id), override)
            )
            for rule_id, override in session_rule_overrides.items()
        }
        profile = replace(
            profile,
            rule_overrides=merge_session_rule_overrides(
                profile.rule_overrides,
                normalized_overrides,
            ),
        )
    if session_rule_overrides:
        from pipeline_inspector.core.rule_browser import merge_session_rule_overrides
        from pipeline_inspector.core.rule_loader import RuleOverride

        normalized_overrides = {
            str(rule_id): (
                override
                if isinstance(override, RuleOverride)
                else RuleOverride.from_dict(str(rule_id), override)
            )
            for rule_id, override in session_rule_overrides.items()
        }
        profile = replace(
            profile,
            rule_overrides=merge_session_rule_overrides(
                profile.rule_overrides,
                normalized_overrides,
            ),
        )
    renderer_ids = (enriched.renderer,) if enriched.renderer else ()
    rules = load_rule_stack(
        rule_root=rule_root or DEFAULT_RULE_ROOT,
        renderer_ids=renderer_ids,
        profile=profile,
        extra_rule_paths=extra_rule_paths,
    )
    results = list(ValidationEngine().validate(enriched, rules))
    sidecar_path = waiver_sidecar_path or resolve_waiver_sidecar_path(enriched.scene_path)
    if sidecar_path is not None and sidecar_path.is_file():
        results = list(apply_waivers(results, load_waiver_sidecar(sidecar_path)))
    results = enrich_rule_results(enriched, results)
    fix_plan = build_fix_plan(
        results,
        rules,
        enriched,
        studio_environment=_studio_environment_for_validation(studio_config),
    )
    summary = summarize_results(results)
    health_score = compute_health_score(results)
    failed_count = sum(1 for item in results if item.status == "failed")
    scope_label = "selection" if scan_scope == "selection" else "scene"
    profile_label = effective_profile_id
    if normalized_asset_class:
        profile_label = f"{effective_profile_id}+{normalized_asset_class}"
    message = (
        f"{scope_label.title()} validated with profile {profile_label}. "
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
        profile_id=effective_profile_id,
        asset_class_id=normalized_asset_class,
    )


def run_validation_for_user(
    snapshot: GraphSnapshot,
    *,
    user_config: UserPreferences,
    studio_config: Optional[StudioConfig] = None,
    scan_scope: Optional[str] = None,
    profile_id: Optional[str] = None,
    asset_class_id: Optional[str] = None,
    profile_path: Optional[Path] = None,
    rule_root: Optional[Path] = None,
    waiver_sidecar_path: Optional[Path] = None,
    session_rule_overrides: Optional[dict[str, Any]] = None,
) -> ValidationRunResult:
    """Validate a snapshot using merged user preference defaults."""

    from pipeline_inspector.runtime_preferences import user_validation_preferences

    prefs = user_validation_preferences(
        user_config,
        scan_scope=scan_scope,
        profile_id=profile_id,
        asset_class_id=asset_class_id,
    )
    return run_validation(
        snapshot,
        profile_id=prefs.profile_id,
        asset_class_id=prefs.asset_class_id or None,
        profile_path=profile_path,
        rule_root=rule_root,
        extra_rule_paths=prefs.extra_rule_paths,
        waiver_sidecar_path=waiver_sidecar_path,
        scan_scope=prefs.scan_scope,
        studio_config=studio_config,
        session_rule_overrides=session_rule_overrides,
    )
