"""Compare two shader manifest JSON files and write deterministic JSON diff."""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Optional

from shader_health.reports.manifest_diff import dumps_manifest_diff

JsonDict = dict[str, Any]


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old_manifest", type=Path)
    parser.add_argument("new_manifest", type=Path)
    parser.add_argument("--out", type=Path, default=None, help="Optional output JSON path.")
    args = parser.parse_args(argv)

    old_manifest = _load_json_object(args.old_manifest)
    new_manifest = _load_json_object(args.new_manifest)
    output = dumps_manifest_diff(old_manifest, new_manifest)

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0


def _load_json_object(path: Path) -> JsonDict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"Manifest must be a JSON object: {path}")
    return data


if __name__ == "__main__":
    raise SystemExit(main())
