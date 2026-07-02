"""Headless command line entrypoints."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from shader_health.core import GraphSnapshot, RuleLoadError, ValidationEngine, load_rule_stack, summarize_results
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
    validate = subparsers.add_parser("validate", help="Validate a Maya scene or snapshot.")
    validate.add_argument("input_path", help="Maya scene path or GraphSnapshot JSON path.")
    validate.add_argument("--input-kind", choices=(INPUT_AUTO, INPUT_SCENE, INPUT_SNAPSHOT), default=INPUT_AUTO)
    validate.add_argument("--report", required=True, help="Output JSON report path.")
    validate.add_argument("--rule-root", help="Rule root folder. Defaults to packaged rules.")
    validate.add_argument("--profile", help="Profile JSON path.")
    validate.add_argument("--renderer", action="append", default=[], help="Renderer rule pack id to include.")
    validate.add_argument("--extra-rules", action="append", default=[], help="Extra rule file or folder.")
    return parser


def validate_command(args: argparse.Namespace) -> int:
    try:
        snapshot = _load_snapshot(Path(args.input_path), args.input_kind)
        renderer_ids = tuple(args.renderer or ([snapshot.renderer] if snapshot.renderer else []))
        rules = load_rule_stack(
            **_rule_stack_kwargs(
                args.rule_root,
                args.profile,
                renderer_ids,
                args.extra_rules,
            )
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


def _rule_stack_kwargs(
    rule_root: Optional[str],
    profile: Optional[str],
    renderer_ids: tuple[str, ...],
    extra_rules: Sequence[str],
) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "renderer_ids": renderer_ids,
        "extra_rule_paths": tuple(Path(path) for path in extra_rules),
    }
    if rule_root:
        kwargs["rule_root"] = Path(rule_root)
    if profile:
        kwargs["profile_path"] = Path(profile)
    return kwargs


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
        from maya import cmds  # type: ignore[import-not-found]
        from shader_health.maya.scanner import scan_scene
    except ImportError as exc:
        raise RuntimeError("scene validation requires Autodesk Maya / mayapy") from exc
    cmds.file(str(path), open=True, force=True)
    return scan_scene()


def _exit_code(results: Sequence[object]) -> int:
    summary = summarize_results(results)
    if summary.block_deadline:
        return EXIT_DEADLINE_BLOCK
    if summary.block_publish:
        return EXIT_PUBLISH_BLOCK
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
