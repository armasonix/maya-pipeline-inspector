"""Headless command line entrypoints."""
from __future__ import annotations

import argparse
import importlib
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

from shader_health.core import (
    GraphSnapshot,
    RuleDefinition,
    RuleLoadError,
    RuleResult,
    ValidationEngine,
    load_rule_stack,
    summarize_results,
)
from shader_health.reports import write_json_report

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
    return parser


def validate_command(args: argparse.Namespace) -> int:
    try:
        snapshot = _load_snapshot(Path(args.input_path), args.input_kind)
        renderer_ids = tuple(args.renderer or _snapshot_renderer_ids(snapshot))
        rules = _load_rules(
            rule_root=_rule_root_path(args.rule_root),
            profile_path=_optional_path(args.profile),
            renderer_ids=renderer_ids,
            extra_rule_paths=tuple(Path(path) for path in args.extra_rules),
        )
        results = ValidationEngine().validate(snapshot, rules)
        write_json_report(args.report, snapshot, results)
        return _exit_code(results)
    except RuleLoadError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    except Exception as exc:  # noqa: BLE001
        print(f"Runtime error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR


def _load_rules(
    *,
    rule_root: Optional[Path],
    profile_path: Optional[Path],
    renderer_ids: tuple[str, ...],
    extra_rule_paths: tuple[Path, ...],
) -> list[RuleDefinition]:
    if rule_root is None:
        return load_rule_stack(
            renderer_ids=renderer_ids,
            profile_path=profile_path,
            extra_rule_paths=extra_rule_paths,
        )
    return load_rule_stack(
        rule_root=rule_root,
        renderer_ids=renderer_ids,
        profile_path=profile_path,
        extra_rule_paths=extra_rule_paths,
    )


def _rule_root_path(value: Optional[str]) -> Optional[Path]:
    if not value:
        return None
    path = Path(value)
    if not path.exists():
        raise RuleLoadError(f"Rule root does not exist: {path}")
    return path


def _optional_path(value: Optional[str]) -> Optional[Path]:
    return Path(value) if value else None


def _snapshot_renderer_ids(snapshot: GraphSnapshot) -> tuple[str, ...]:
    return (snapshot.renderer,) if snapshot.renderer else ()


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


def _exit_code(results: Sequence[RuleResult]) -> int:
    summary = summarize_results(results)
    if summary.block_deadline:
        return EXIT_DEADLINE_BLOCK
    if summary.block_publish:
        return EXIT_PUBLISH_BLOCK
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
