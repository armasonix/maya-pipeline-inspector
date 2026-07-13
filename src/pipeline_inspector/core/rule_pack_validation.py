"""Shared rule pack validation helpers used by validate_rules.py and authoring UI."""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from pipeline_inspector.core.rule_loader import (
    DEFAULT_RULE_ROOT,
    RuleLoadError,
    load_profile,
    validate_profile_overrides,
)
from pipeline_inspector.core.rule_schema import RuleDefinition, RuleSchemaError

JsonDict = dict[str, Any]


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


def iter_rule_objects(payload: Any, path: Path | None = None) -> list[Mapping[str, Any]]:
    label = str(path) if path is not None else "rule draft"
    if isinstance(payload, Mapping):
        if "rules" not in payload:
            return [payload]

        rules = payload["rules"]
        if not isinstance(rules, list):
            raise RuleValidationFailure(f"{label}: 'rules' must be a list")
        return [
            _require_mapping(item, label, index)
            for index, item in enumerate(rules, start=1)
        ]

    if isinstance(payload, list):
        return [
            _require_mapping(item, label, index)
            for index, item in enumerate(payload, start=1)
        ]

    raise RuleValidationFailure(
        f"{label}: root must be an object, a list, or an object with 'rules'"
    )


def validate_rule_object(raw_rule: Mapping[str, Any]) -> RuleDefinition:
    """Validate one rule object against the RuleDefinition schema."""

    try:
        return RuleDefinition.from_dict(raw_rule)
    except RuleSchemaError as exc:
        raise RuleValidationFailure(f"rule schema: {exc}") from exc


def validate_rule_file(path: Path) -> list[RuleDefinition]:
    payload = load_json_file(path)
    rules: list[RuleDefinition] = []
    for index, raw_rule in enumerate(iter_rule_objects(payload, path), start=1):
        try:
            rules.append(RuleDefinition.from_dict(raw_rule))
        except RuleSchemaError as exc:
            raise RuleValidationFailure(f"{path}: rule #{index}: {exc}") from exc
    return rules


def collect_rule_ids(paths: Iterable[Path]) -> frozenset[str]:
    """Collect rule ids from validated JSON rule files."""

    rule_ids: set[str] = set()
    for path in find_json_files(paths):
        for rule in validate_rule_file(path):
            rule_ids.add(rule.id)
    return frozenset(rule_ids)


def validate_paths(
    paths: Iterable[Path],
    *,
    rule_root: Path = DEFAULT_RULE_ROOT,
) -> tuple[int, int]:
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

    profiles_root = rule_root / "profiles"
    validating_packaged_rules = any(
        path.resolve() == rule_root.resolve() or rule_root.resolve() in path.resolve().parents
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


def _require_mapping(value: Any, path: str, index: int) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuleValidationFailure(f"{path}: rule #{index} must be an object")
    return value
