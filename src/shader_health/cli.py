"""Headless command line entrypoints."""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Optional

from shader_health.core import GraphSnapshot, RuleLoadError
from shader_health.core.fix_plan import FixPlan, fix_plan_from_export
from shader_health.core.manifest_gate import evaluate_manifest_gate
from shader_health.core.rule_loader import load_profile
from shader_health.maya.validation_pipeline import (
    DEFAULT_PROFILE_ID,
    run_validation,
)
from shader_health.reports import write_json_report
from shader_health.reports.fix_plan_export import write_fix_plan_export
from shader_health.reports.manifest import build_shader_manifest
from shader_health.reports.manifest_diff_cli import (
    EXIT_INPUT_ERROR as DIFF_EXIT_INPUT_ERROR,
)
from shader_health.reports.manifest_diff_cli import (
    execute_manifest_diff,
    load_manifest_json,
)

EXIT_OK = 0
EXIT_PUBLISH_BLOCK = 1
EXIT_DEADLINE_BLOCK = 2
EXIT_RUNTIME_ERROR = 3
EXIT_CONFIG_ERROR = 4

INPUT_AUTO = "auto"
INPUT_SCENE = "scene"
INPUT_SNAPSHOT = "snapshot"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "validate":
        return validate_command(args)
    if args.command == "diff":
        return diff_command(args)
    if args.command == "gate":
        return gate_command(args)
    if args.command == "apply-fixes":
        return apply_fixes_command(args)
    parser.print_help()
    return EXIT_CONFIG_ERROR


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="shader_health")
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
    return parser


def validate_command(args: argparse.Namespace) -> int:
    try:
        snapshot = _load_snapshot(Path(args.input_path), args.input_kind)
        if args.renderer:
            snapshot = _snapshot_with_renderer(snapshot, tuple(args.renderer))
        run = run_validation(
            snapshot,
            profile_id=str(args.profile_id),
            profile_path=_optional_path(args.profile),
            rule_root=_rule_root_path(args.rule_root),
            extra_rule_paths=tuple(Path(path) for path in args.extra_rules),
            waiver_sidecar_path=_optional_path(args.waiver_sidecar),
            scan_scope="scene",
        )
        write_json_report(args.report, run.snapshot, run.results)
        if args.export_fix_plan and run.fix_plan.total:
            write_fix_plan_export(
                args.export_fix_plan,
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
                Path(args.baseline_manifest),
                profile_path=_optional_path(args.profile),
                profile_id=str(args.profile_id),
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
        snapshot = _load_snapshot(Path(args.input_path), args.input_kind)
        return _manifest_gate_exit(
            snapshot,
            Path(args.baseline_manifest),
            profile_path=_optional_path(args.profile),
            profile_id=str(args.profile_id),
            out_path=_optional_path(args.out),
        )
    except RuleLoadError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    except Exception as exc:  # noqa: BLE001
        print(f"Runtime error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR


def apply_fixes_command(args: argparse.Namespace) -> int:
    try:
        scene_path = Path(args.input_path)
        fix_plan = _load_fix_plan_for_scene(
            scene_path,
            profile_id=str(args.profile_id),
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


def diff_command(args: argparse.Namespace) -> int:
    exit_code = execute_manifest_diff(
        Path(args.old_manifest),
        Path(args.new_manifest),
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
    out_path: Optional[Path] = None,
) -> int:
    baseline_manifest = load_manifest_json(baseline_path)
    current_manifest = build_shader_manifest(snapshot)
    policy = _manifest_gate_policy(profile_path, profile_id)
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


def _manifest_gate_policy(profile_path: Optional[Path], profile_id: str):
    from shader_health.maya.validation_pipeline import packaged_profile_path

    resolved_profile = profile_path or packaged_profile_path(profile_id)
    profile = load_profile(resolved_profile)
    return profile.manifest_diff_policy


def _load_fix_plan_for_scene(
    scene_path: Path,
    *,
    profile_id: str,
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
    cmds = importlib.import_module("maya.cmds")
    fix_applier = importlib.import_module("shader_health.maya.fix_applier")
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
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _rule_root_path(value: Optional[str]) -> Optional[Path]:
    if not value:
        return None
    path = Path(value)
    if not path.exists():
        raise RuleLoadError(f"Rule root does not exist: {path}")
    return path


def _optional_path(value: Optional[str]) -> Optional[Path]:
    return Path(value) if value else None


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
        scanner = importlib.import_module("shader_health.maya.scanner")
    except ImportError as exc:
        raise RuntimeError("scene validation requires Autodesk Maya / mayapy") from exc

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
    from shader_health.core import summarize_results

    summary = summarize_results(results)
    if summary.block_deadline:
        return EXIT_DEADLINE_BLOCK
    if summary.block_publish:
        return EXIT_PUBLISH_BLOCK
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
