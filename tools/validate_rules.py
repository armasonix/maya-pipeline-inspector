"""Validate JSON rule packs against the RuleDefinition schema."""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from shader_health.core.rule_loader import (  # noqa: E402
    RuleLoadError,
    load_profile,
    validate_profile_overrides,
)
from shader_health.core.rule_schema import RuleDefinition, RuleSchemaError  # noqa: E402

DEFAULT_RULE_ROOT = REPO_ROOT / "src" / "shader_health" / "rules"


class RuleValidationFailure(Exception):
    """Raised when a rule file cannot be validated."""


def find_json_files(paths: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(
                sorted(
                    item
                    for item in path.rglob("*.json")
                    if item.is_file() and "profiles" not in item.parts
                )
            )
        elif path.is_file():
            files.append(path)
        else:
            raise RuleValidationFailure(f"Path does not exist: {path}")
    return sorted(files)


def load_json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuleValidationFailure(f"{path}: invalid JSON: {exc}") from exc
    except OSError as exc:
        raise RuleValidationFailure(f"{path}: cannot read file: {exc}") from exc


def iter_rule_objects(payload: Any, path: Path) -> list[Mapping[str, Any]]:
    if isinstance(payload, Mapping):
        if "rules" not in payload:
            return [payload]

        rules = payload["rules"]
        if not isinstance(rules, list):
            raise RuleValidationFailure(f"{path}: 'rules' must be a list")
        return [
            _require_mapping(item, path, index)
            for index, item in enumerate(rules, start=1)
        ]

    if isinstance(payload, list):
        return [
            _require_mapping(item, path, index)
            for index, item in enumerate(payload, start=1)
        ]

    raise RuleValidationFailure(
        f"{path}: root must be an object, a list, or an object with 'rules'"
    )


def _require_mapping(value: Any, path: Path, index: int) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuleValidationFailure(f"{path}: rule #{index} must be an object")
    return value


def validate_rule_file(path: Path) -> list[RuleDefinition]:
    payload = load_json_file(path)
    rules: list[RuleDefinition] = []
    for index, raw_rule in enumerate(iter_rule_objects(payload, path), start=1):
        try:
            rules.append(RuleDefinition.from_dict(raw_rule))
        except RuleSchemaError as exc:
            raise RuleValidationFailure(f"{path}: rule #{index}: {exc}") from exc
    return rules


def validate_paths(paths: Iterable[Path]) -> tuple[int, int]:
    paths_list = list(paths)
    files = find_json_files(paths_list)
    file_count = 0
    rule_count = 0
    rules_by_id: dict[str, RuleDefinition] = {}

    for path in files:
        rules = validate_rule_file(path)
        file_count += 1
        rule_count += len(rules)
        for rule in rules:
            rules_by_id[rule.id] = rule

    profiles_root = DEFAULT_RULE_ROOT / "profiles"
    validating_packaged_rules = any(
        path.resolve() == DEFAULT_RULE_ROOT.resolve()
        or DEFAULT_RULE_ROOT.resolve() in path.resolve().parents
        for path in paths_list
    )
    if validating_packaged_rules and profiles_root.is_dir():
        for profile_path in sorted(profiles_root.glob("*.json")):
            profile = load_profile(profile_path)
            try:
                validate_profile_overrides(profile, rules_by_id)
            except RuleLoadError as exc:
                raise RuleValidationFailure(str(exc)) from exc

    return file_count, rule_count


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Maya Shader Health Inspector JSON rule packs."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[DEFAULT_RULE_ROOT],
        help="Rule file or directory paths. Defaults to src/shader_health/rules.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print errors.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        file_count, rule_count = validate_paths(args.paths)
    except RuleValidationFailure as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"Validated {rule_count} rule(s) from {file_count} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
