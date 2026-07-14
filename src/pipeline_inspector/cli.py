"""Headless command line entrypoints."""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Optional

from pipeline_inspector.core import GraphSnapshot, RuleLoadError
from pipeline_inspector.core.fix_plan import FixPlan, fix_plan_from_export
from pipeline_inspector.core.governance import build_permission_resolver_from_runtime
from pipeline_inspector.core.manifest_gate import evaluate_manifest_gate
from pipeline_inspector.core.rule_loader import DEFAULT_RULE_ROOT, load_profile
from pipeline_inspector.maya.validation_pipeline import (
    DEFAULT_PROFILE_ID,
    fix_audit_sidecar_path_for_scene,
    persist_fix_apply_audit,
    run_validation,
)
from pipeline_inspector.reports import write_json_report
from pipeline_inspector.reports.fix_plan_export import write_fix_plan_export
from pipeline_inspector.reports.manifest import build_shader_manifest, write_shader_manifest
from pipeline_inspector.reports.manifest_diff_cli import (
    EXIT_INPUT_ERROR as DIFF_EXIT_INPUT_ERROR,
)
from pipeline_inspector.reports.manifest_diff_cli import (
    execute_manifest_diff,
    load_manifest_json,
)
from pipeline_inspector.rules_cli import validate_rule_paths
from pipeline_inspector.studio_config import StudioConfig, resolve_studio_config_for_headless
from pipeline_inspector.user_config import UserPreferences
from pipeline_inspector.util.paths import normalize_cli_path

_MAYA_STANDALONE_INITIALIZED = False

EXIT_OK = 0
EXIT_PUBLISH_BLOCK = 1
EXIT_DEADLINE_BLOCK = 2
EXIT_RUNTIME_ERROR = 3
EXIT_CONFIG_ERROR = 4

INPUT_AUTO = "auto"
INPUT_SCENE = "scene"
INPUT_SNAPSHOT = "snapshot"
ASSET_CLASS_ID_HELP = (
    "Optional asset class overlay: asset_class_hero, asset_class_prop, asset_class_background."
)


def _add_asset_class_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--asset-class-id", default="", help=ASSET_CLASS_ID_HELP)


def _add_studio_config_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--studio-config",
        help=(
            "Studio config JSON path. When omitted, uses PIPELINE_INSPECTOR_STUDIO_CONFIG "
            "or discovered pipeline_inspector_studio.json paths."
        ),
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "validate":
        return validate_command(args)
    if args.command == "diff":
        return diff_command(args)
    if args.command == "gate":
        return gate_command(args)
    if args.command == "manifest":
        return manifest_command(args)
    if args.command == "apply-fixes":
        return apply_fixes_command(args)
    if args.command == "rules":
        return rules_command(args)
    parser.print_help()
    return EXIT_CONFIG_ERROR


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pipeline_inspector")
    subparsers = parser.add_subparsers(dest="command")
    validate = subparsers.add_parser(
        "validate",
        help="Validate a Maya scene or snapshot.",
    )
    validate.add_argument("input_path", help="Maya scene path or GraphSnapshot JSON path.")
    validate.add_argument(
        "--input-kind",
        choices=(INPUT_AUTO, INPUT_SCENE, INPUT_SNAPSHOT),
        default=INPUT_AUTO,
    )
    validate.add_argument("--report", required=True, help="Output JSON report path.")
    validate.add_argument("--rule-root", help="Rule root folder. Defaults to packaged rules.")
    validate.add_argument("--profile", help="Profile JSON path.")
    validate.add_argument(
        "--profile-id",
        default=DEFAULT_PROFILE_ID,
        help="Packaged profile id when --profile is omitted.",
    )
    validate.add_argument(
        "--renderer",
        action="append",
        default=[],
        help="Renderer rule pack id to include.",
    )
    validate.add_argument(
        "--extra-rules",
        action="append",
        default=[],
        help="Extra rule file or folder.",
    )
    validate.add_argument(
        "--waiver-sidecar",
        help="Optional waiver sidecar JSON path.",
    )
    validate.add_argument(
        "--export-fix-plan",
        help="Optional output path for a deterministic fix plan JSON export.",
    )
    validate.add_argument(
        "--baseline-manifest",
        help="Optional approved manifest JSON path for regression gate evaluation.",
    )
    _add_asset_class_argument(validate)
    _add_studio_config_argument(validate)
    diff = subparsers.add_parser(
        "diff",
        help="Compare two shader manifest JSON files.",
    )
    diff.add_argument("old_manifest", help="Baseline manifest JSON path.")
    diff.add_argument("new_manifest", help="Current manifest JSON path.")
    diff.add_argument(
        "--out",
        help="Optional output JSON diff path. Defaults to stdout when omitted.",
    )
    diff.add_argument(
        "--html",
        help="Optional output HTML diff report path.",
    )
    gate = subparsers.add_parser(
        "gate",
        help="Evaluate manifest regression gate against a baseline manifest.",
    )
    gate.add_argument("input_path", help="Maya scene path or GraphSnapshot JSON path.")
    gate.add_argument("baseline_manifest", help="Approved baseline manifest JSON path.")
    gate.add_argument(
        "--input-kind",
        choices=(INPUT_AUTO, INPUT_SCENE, INPUT_SNAPSHOT),
        default=INPUT_AUTO,
    )
    gate.add_argument("--profile", help="Profile JSON path for manifest_diff_policy.")
    gate.add_argument(
        "--profile-id",
        default=DEFAULT_PROFILE_ID,
        help="Packaged profile id when --profile is omitted.",
    )
    gate.add_argument("--out", help="Optional gate result JSON output path.")
    _add_asset_class_argument(gate)
    _add_studio_config_argument(gate)
    manifest = subparsers.add_parser(
        "manifest",
        help="Export a shader manifest from a Maya scene or snapshot.",
    )
    manifest.add_argument("input_path", help="Maya scene path or GraphSnapshot JSON path.")
    manifest.add_argument("--out", required=True, help="Output manifest JSON path.")
    manifest.add_argument(
        "--input-kind",
        choices=(INPUT_AUTO, INPUT_SCENE, INPUT_SNAPSHOT),
        default=INPUT_AUTO,
    )
    manifest.add_argument("--profile", help="Profile JSON path for validation context.")
    manifest.add_argument(
        "--profile-id",
        default=DEFAULT_PROFILE_ID,
        help="Packaged profile id when --profile is omitted.",
    )
    _add_asset_class_argument(manifest)
    _add_studio_config_argument(manifest)
    apply_fixes = subparsers.add_parser(
        "apply-fixes",
        help="Apply planned fixes to a Maya scene (requires mayapy).",
    )
    apply_fixes.add_argument("input_path", help="Maya scene path.")
    apply_fixes.add_argument(
        "--fix-plan",
        help="Fix plan export JSON path. When omitted, fixes are planned from validation.",
    )
    apply_fixes.add_argument("--report", help="Optional apply report JSON output path.")
    apply_fixes.add_argument("--profile", help="Profile JSON path.")
    apply_fixes.add_argument(
        "--profile-id",
        default=DEFAULT_PROFILE_ID,
        help="Packaged profile id when --profile is omitted.",
    )
    apply_fixes.add_argument(
        "--fix-ids",
        action="append",
        default=[],
        help="Apply only the listed fix_id values.",
    )
    apply_fixes.add_argument(
        "--allow-referenced",
        action="store_true",
        help="Allow fixes on referenced nodes.",
    )
    apply_fixes.add_argument(
        "--allow-high-risk",
        action="store_true",
        help="Allow high-risk fixes without supervisor confirmation.",
    )
    apply_fixes.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan fixes without mutating the scene.",
    )
    _add_asset_class_argument(apply_fixes)
    rules = subparsers.add_parser(
        "rules",
        help="Rule pack validation tooling.",
    )
    rules_subparsers = rules.add_subparsers(dest="rules_command")
    rules_validate = rules_subparsers.add_parser(
        "validate",
        help="Validate JSON rule packs against the RuleDefinition schema.",
    )
    rules_validate.add_argument(
        "paths",
        nargs="*",
        help="Rule file or directory paths. Defaults to packaged rules.",
    )
    rules_validate.add_argument(
        "--quiet",
        action="store_true",
        help="Only print errors.",
    )
    return parser


def validate_command(args: argparse.Namespace) -> int:
    try:
        if args.extra_rules:
            resolver = _permission_resolver_from_args(args)
            decision = resolver.require("manage_rules")
            if not decision.allowed:
                print(decision.reason, file=sys.stderr)
                return EXIT_CONFIG_ERROR
        input_path = _cli_path(args.input_path)
        report_path = _cli_path(args.report)
        snapshot = _load_snapshot(input_path, args.input_kind)
        if args.renderer:
            snapshot = _snapshot_with_renderer(snapshot, tuple(args.renderer))
        run = run_validation(
            snapshot,
            profile_id=str(args.profile_id),
            asset_class_id=_asset_class_id_from_args(args),
            profile_path=_optional_path(args.profile),
            rule_root=_rule_root_path(args.rule_root),
            extra_rule_paths=tuple(_cli_path(path) for path in args.extra_rules),
            waiver_sidecar_path=_optional_path(args.waiver_sidecar),
            scan_scope="scene",
            studio_config=_studio_config_from_args(args),
        )
        write_json_report(report_path, run.snapshot, run.results)
        if args.export_fix_plan and run.fix_plan.total:
            write_fix_plan_export(
                _cli_path(args.export_fix_plan),
                run.fix_plan,
                snapshot=run.snapshot,
                profile_id=run.profile_id,
            )
        exit_code = _exit_code(run.results)
        if exit_code != EXIT_OK:
            return exit_code
        if args.baseline_manifest:
            return _manifest_gate_exit(
                run.snapshot,
                _cli_path(args.baseline_manifest),
                profile_path=_optional_path(args.profile),
                profile_id=str(args.profile_id),
                asset_class_id=_asset_class_id_from_args(args),
                studio_config=_studio_config_from_args(args),
            )
        return EXIT_OK
    except RuleLoadError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    except Exception as exc:  # noqa: BLE001
        print(f"Runtime error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR


def gate_command(args: argparse.Namespace) -> int:
    try:
        snapshot = _load_snapshot(_cli_path(args.input_path), args.input_kind)
        return _manifest_gate_exit(
            snapshot,
            _cli_path(args.baseline_manifest),
            profile_path=_optional_path(args.profile),
            profile_id=str(args.profile_id),
            asset_class_id=_asset_class_id_from_args(args),
            out_path=_optional_path(args.out),
            studio_config=_studio_config_from_args(args),
        )
    except RuleLoadError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    except Exception as exc:  # noqa: BLE001
        print(f"Runtime error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR


def manifest_command(args: argparse.Namespace) -> int:
    try:
        snapshot = _load_snapshot(_cli_path(args.input_path), args.input_kind)
        run = run_validation(
            snapshot,
            profile_id=str(args.profile_id),
            asset_class_id=_asset_class_id_from_args(args),
            profile_path=_optional_path(args.profile),
            scan_scope="scene",
            studio_config=_studio_config_from_args(args),
        )
        write_shader_manifest(
            _cli_path(args.out),
            run.snapshot,
            results=run.results,
            health_score=run.health_score.score,
        )
        return EXIT_OK
    except RuleLoadError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    except Exception as exc:  # noqa: BLE001
        print(f"Runtime error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR


def apply_fixes_command(args: argparse.Namespace) -> int:
    try:
        if args.allow_high_risk:
            resolver = _permission_resolver_from_args(args)
            decision = resolver.require("apply_risky_fixes")
            if not decision.allowed:
                print(decision.reason, file=sys.stderr)
                return EXIT_CONFIG_ERROR
        scene_path = _cli_path(args.input_path)
        fix_plan = _load_fix_plan_for_scene(
            scene_path,
            profile_id=str(args.profile_id),
            asset_class_id=_asset_class_id_from_args(args),
            profile_path=_optional_path(args.profile),
            fix_plan_path=_optional_path(args.fix_plan),
        )
        selected_actions = _filter_fix_actions(fix_plan, tuple(args.fix_ids))
        if args.dry_run:
            report = _dry_run_apply_report(selected_actions)
            _write_apply_report(args.report, report)
            return EXIT_OK

        apply_report = _apply_fixes_in_scene(
            scene_path,
            selected_actions,
            allow_referenced=bool(args.allow_referenced),
            allow_high_risk=bool(args.allow_high_risk),
        )
        _write_apply_report(args.report, apply_report.to_dict())
        audit_path, _ = persist_fix_apply_audit(
            apply_report,
            scene_path=str(scene_path),
            profile_id=str(args.profile_id),
            audit_sidecar_path=fix_audit_sidecar_path_for_scene(str(scene_path)),
        )
        if audit_path is not None:
            print(f"Fix audit appended: {audit_path}")
        if apply_report.failed_count:
            return EXIT_RUNTIME_ERROR
        if apply_report.blocked_count and not apply_report.applied_count:
            return EXIT_PUBLISH_BLOCK
        return EXIT_OK
    except RuleLoadError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    except Exception as exc:  # noqa: BLE001
        print(f"Runtime error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR


def rules_command(args: argparse.Namespace) -> int:
    if args.rules_command == "validate":
        return rules_validate_command(args)
    print("Configuration error: rules subcommand required (validate).", file=sys.stderr)
    return EXIT_CONFIG_ERROR


def rules_validate_command(args: argparse.Namespace) -> int:
    paths = tuple(_cli_path(path) for path in args.paths) if args.paths else (DEFAULT_RULE_ROOT,)
    return validate_rule_paths(paths, quiet=bool(args.quiet))


def diff_command(args: argparse.Namespace) -> int:
    exit_code = execute_manifest_diff(
        _cli_path(args.old_manifest),
        _cli_path(args.new_manifest),
        out_path=_optional_path(args.out),
        html_path=_optional_path(args.html),
    )
    if exit_code == DIFF_EXIT_INPUT_ERROR:
        return EXIT_CONFIG_ERROR
    return exit_code


def _manifest_gate_exit(
    snapshot: GraphSnapshot,
    baseline_path: Path,
    *,
    profile_path: Optional[Path],
    profile_id: str,
    asset_class_id: Optional[str] = None,
    out_path: Optional[Path] = None,
    studio_config: Optional[Any] = None,
) -> int:
    baseline_manifest = load_manifest_json(baseline_path)
    run = run_validation(
        snapshot,
        profile_id=profile_id,
        asset_class_id=asset_class_id,
        profile_path=profile_path,
        scan_scope=snapshot.scan_scope or "scene",
        studio_config=studio_config,
    )
    current_manifest = build_shader_manifest(
        run.snapshot,
        results=run.results,
        health_score=run.health_score.score,
    )
    policy = _manifest_gate_policy(profile_path, profile_id, asset_class_id=asset_class_id)
    gate_result = evaluate_manifest_gate(baseline_manifest, current_manifest, policy=policy)
    payload = gate_result.to_dict()
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    if gate_result.blocked:
        for reason in gate_result.reasons:
            print(f"Manifest regression blocked: {reason}", file=sys.stderr)
        return EXIT_PUBLISH_BLOCK
    return EXIT_OK


def _manifest_gate_policy(
    profile_path: Optional[Path],
    profile_id: str,
    *,
    asset_class_id: Optional[str] = None,
):
    from pipeline_inspector.maya.validation_pipeline import compose_profiles

    if profile_path is not None:
        profile = load_profile(profile_path)
    else:
        profile = compose_profiles(profile_id, asset_class_id)
    return profile.manifest_diff_policy


def _load_fix_plan_for_scene(
    scene_path: Path,
    *,
    profile_id: str,
    asset_class_id: Optional[str],
    profile_path: Optional[Path],
    fix_plan_path: Optional[Path],
) -> FixPlan:
    if fix_plan_path is not None:
        payload = json.loads(fix_plan_path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("fix plan export must be a JSON object")
        return fix_plan_from_export(payload)

    snapshot = _snapshot_from_scene(scene_path)
    run = run_validation(
        snapshot,
        profile_id=profile_id,
        asset_class_id=asset_class_id,
        profile_path=profile_path,
        scan_scope="scene",
    )
    return run.fix_plan


def _filter_fix_actions(fix_plan: FixPlan, fix_ids: tuple[str, ...]) -> tuple[Any, ...]:
    if not fix_ids:
        return tuple(action for action in fix_plan.actions if not action.blocked)
    allowed = {fix_id.strip() for fix_id in fix_ids if fix_id.strip()}
    return tuple(action for action in fix_plan.actions if action.fix_id in allowed)


def _apply_fixes_in_scene(
    scene_path: Path,
    actions: Sequence[Any],
    *,
    allow_referenced: bool = False,
    allow_high_risk: bool = False,
) -> Any:
    _ensure_maya_standalone()
    cmds = importlib.import_module("maya.cmds")
    fix_applier = importlib.import_module("pipeline_inspector.maya.fix_applier")
    cmds.file(str(scene_path), open=True, force=True)
    return fix_applier.apply_fix_actions(
        actions,
        cmds=cmds,
        allow_referenced=allow_referenced,
        allow_high_risk=allow_high_risk,
    )


def _dry_run_apply_report(actions: Sequence[Any]) -> dict[str, Any]:
    records = [action.to_dict() for action in actions]
    applied_count = sum(1 for action in actions if not action.blocked)
    blocked_count = sum(1 for action in actions if action.blocked)
    return {
        "dry_run": True,
        "total": len(records),
        "applied_count": applied_count,
        "blocked_count": blocked_count,
        "failed_count": 0,
        "records": records,
    }


def _write_apply_report(path: Optional[str], payload: Mapping[str, Any]) -> None:
    if not path:
        return
    output_path = _cli_path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _rule_root_path(value: Optional[str]) -> Optional[Path]:
    if not value:
        return None
    path = _cli_path(value)
    if not path.exists():
        raise RuleLoadError(f"Rule root does not exist: {path}")
    return path


def _optional_path(value: Optional[str]) -> Optional[Path]:
    return _cli_path(value) if value else None


def _cli_path(value: str | Path) -> Path:
    """Normalize CLI paths (including Git Bash /d/foo MSYS paths on Windows)."""

    return normalize_cli_path(value)


def _asset_class_id_from_args(args: argparse.Namespace) -> Optional[str]:
    normalized = str(getattr(args, "asset_class_id", "") or "").strip()
    return normalized or None


def _studio_config_from_args(args: argparse.Namespace) -> Optional[Any]:
    try:
        return resolve_studio_config_for_headless(
            cli_path=_optional_path(getattr(args, "studio_config", None)),
        )
    except ValueError as exc:
        raise RuleLoadError(str(exc)) from exc


def _permission_resolver_from_args(args: argparse.Namespace):
    studio = _studio_config_from_args(args) or StudioConfig.default()
    user = UserPreferences.default()
    return build_permission_resolver_from_runtime(studio=studio, user=user)


def _ensure_maya_standalone() -> None:
    global _MAYA_STANDALONE_INITIALIZED
    if _MAYA_STANDALONE_INITIALIZED:
        return
    try:
        standalone = importlib.import_module("maya.standalone")
    except ImportError as exc:
        raise RuntimeError("scene validation requires Autodesk Maya / mayapy") from exc
    standalone.initialize(name="python")
    _MAYA_STANDALONE_INITIALIZED = True


def _load_snapshot(path: Path, input_kind: str) -> GraphSnapshot:
    resolved_kind = _resolve_input_kind(path, input_kind)
    if resolved_kind == INPUT_SNAPSHOT:
        return GraphSnapshot.from_json(path.read_text(encoding="utf-8"))
    return _snapshot_from_scene(path)


def _resolve_input_kind(path: Path, input_kind: str) -> str:
    if input_kind != INPUT_AUTO:
        return input_kind
    return INPUT_SNAPSHOT if path.suffix.casefold() == ".json" else INPUT_SCENE


def _snapshot_from_scene(path: Path) -> GraphSnapshot:
    try:
        cmds = importlib.import_module("maya.cmds")
        scanner = importlib.import_module("pipeline_inspector.maya.scanner")
    except ImportError as exc:
        raise RuntimeError("scene validation requires Autodesk Maya / mayapy") from exc

    _ensure_maya_standalone()
    cmds.file(str(path), open=True, force=True)
    snapshot = scanner.scan_scene()
    if not isinstance(snapshot, GraphSnapshot):
        raise RuntimeError("Maya scanner did not return a GraphSnapshot")
    return snapshot


def _snapshot_with_renderer(
    snapshot: GraphSnapshot,
    renderer_ids: tuple[str, ...],
) -> GraphSnapshot:
    if not renderer_ids:
        return snapshot
    from dataclasses import replace

    return replace(snapshot, renderer=renderer_ids[0])


def _exit_code(results: Sequence) -> int:
    from pipeline_inspector.core import summarize_results

    summary = summarize_results(results)
    if summary.block_deadline:
        return EXIT_DEADLINE_BLOCK
    if summary.block_publish:
        return EXIT_PUBLISH_BLOCK
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
