"""Validate JSON rule packs against the RuleDefinition schema."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from shader_health.core.rule_loader import DEFAULT_RULE_ROOT  # noqa: E402
from shader_health.core.rule_pack_validation import (  # noqa: E402
    RuleValidationFailure,
    validate_paths,
)

__all__ = [
    "DEFAULT_RULE_ROOT",
    "RuleValidationFailure",
    "collect_rule_ids",
    "find_json_files",
    "iter_rule_objects",
    "load_json_file",
    "validate_paths",
    "validate_rule_file",
    "validate_rule_object",
]

from shader_health.core.rule_pack_validation import (  # noqa: E402
    collect_rule_ids,
    find_json_files,
    iter_rule_objects,
    load_json_file,
    validate_rule_file,
    validate_rule_object,
)


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
