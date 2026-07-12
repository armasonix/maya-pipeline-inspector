"""Compare two shader manifest JSON files and write deterministic JSON diff.

Deprecated wrapper: prefer `python -m pipeline_inspector diff OLD.json NEW.json`.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Optional

from pipeline_inspector.reports.manifest_diff_cli import run_manifest_diff


def main(argv: Optional[Sequence[str]] = None) -> int:
    return run_manifest_diff(argv)


if __name__ == "__main__":
    raise SystemExit(main())
