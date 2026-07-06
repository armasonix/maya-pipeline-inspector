"""Shared manifest diff command implementation for CLI and tools."""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Optional

from shader_health.reports.html_manifest_diff import write_html_manifest_diff
from shader_health.reports.manifest_diff import build_manifest_diff, dumps_manifest_diff

EXIT_OK = 0
EXIT_INPUT_ERROR = 4

JsonDict = dict[str, Any]


class ManifestDiffInputError(Exception):
    """Raised when manifest diff inputs are missing or invalid."""


def build_manifest_diff_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare two shader manifest JSON files and write a deterministic diff.",
    )
    parser.add_argument("old_manifest", type=Path, help="Baseline manifest JSON path.")
    parser.add_argument("new_manifest", type=Path, help="Current manifest JSON path.")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional output JSON diff path. Defaults to stdout when omitted.",
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=None,
        help="Optional output HTML diff report path.",
    )
    return parser


def run_manifest_diff(argv: Optional[Sequence[str]] = None) -> int:
    """Parse argv and execute a manifest diff command."""

    args = build_manifest_diff_parser().parse_args(argv)
    return execute_manifest_diff(
        args.old_manifest,
        args.new_manifest,
        out_path=args.out,
        html_path=args.html,
    )


def execute_manifest_diff(
    old_manifest_path: Path,
    new_manifest_path: Path,
    *,
    out_path: Optional[Path] = None,
    html_path: Optional[Path] = None,
) -> int:
    """Compare manifests and write JSON and/or HTML diff outputs."""

    try:
        old_manifest = load_manifest_json(old_manifest_path)
        new_manifest = load_manifest_json(new_manifest_path)
    except ManifestDiffInputError as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR

    diff_payload = build_manifest_diff(old_manifest, new_manifest)
    json_output = dumps_manifest_diff(old_manifest, new_manifest)

    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json_output, encoding="utf-8")
    else:
        sys.stdout.write(json_output)

    if html_path is not None:
        write_html_manifest_diff(html_path, diff_payload)

    return EXIT_OK


def write_manifest_diff_outputs(
    old_manifest: Mapping[str, Any],
    new_manifest: Mapping[str, Any],
    *,
    json_path: Path,
    html_path: Path,
) -> JsonDict:
    """Write JSON and HTML manifest diff artifacts and return the diff payload."""

    diff_payload = build_manifest_diff(old_manifest, new_manifest)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        dumps_manifest_diff(old_manifest, new_manifest),
        encoding="utf-8",
    )
    write_html_manifest_diff(html_path, diff_payload)
    return diff_payload


def load_manifest_json(path: Path) -> JsonDict:
    if not path.is_file():
        raise ManifestDiffInputError(f"Manifest file does not exist: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestDiffInputError(f"Invalid JSON in manifest file {path}: {exc}") from exc
    except OSError as exc:
        raise ManifestDiffInputError(f"Cannot read manifest file {path}: {exc}") from exc

    if not isinstance(data, Mapping):
        raise ManifestDiffInputError(f"Manifest must be a JSON object: {path}")
    return dict(data)
