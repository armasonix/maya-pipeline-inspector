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

from pipeline_inspector.core.rule_loader import DEFAULT_RULE_ROOT  # noqa: E402
from pipeline_inspector.core.rule_pack_validation import (  # noqa: E402
    RuleValidationFailure,
    collect_rule_ids,
    find_json_files,
    iter_rule_objects,
    load_json_file,
    validate_paths,
    validate_rule_file,
    validate_rule_object,
)
from pipeline_inspector.rules_cli import validate_rule_paths  # noqa: E402

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
    "validate_rule_paths",
]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Maya Pipeline Inspector JSON rule packs."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[DEFAULT_RULE_ROOT],
        help="Rule file or directory paths. Defaults to src/pipeline_inspector/rules.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print errors.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    return validate_rule_paths(tuple(args.paths), quiet=bool(args.quiet))


if __name__ == "__main__":
    raise SystemExit(main())
