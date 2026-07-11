"""CLI helpers for validating JSON rule packs."""
from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from shader_health.core.rule_loader import DEFAULT_RULE_ROOT
from shader_health.core.rule_pack_validation import RuleValidationFailure, validate_paths

EXIT_RULE_VALIDATION_OK = 0
EXIT_RULE_VALIDATION_ERROR = 1


def validate_rule_paths(
    paths: Sequence[Path | str],
    *,
    quiet: bool = False,
) -> int:
    """Validate rule JSON files or folders and print a summary."""

    normalized = [Path(path) for path in paths] if paths else [DEFAULT_RULE_ROOT]
    try:
        file_count, rule_count = validate_paths(normalized)
    except RuleValidationFailure as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_RULE_VALIDATION_ERROR

    if not quiet:
        print(f"Validated {rule_count} rule(s) from {file_count} file(s).")
    return EXIT_RULE_VALIDATION_OK
