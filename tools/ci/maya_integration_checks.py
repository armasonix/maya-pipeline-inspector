"""JSON assertion helpers for Maya integration smoke steps."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_validate_report(path: Path) -> None:
    payload = _load(path)
    if "health_score" not in payload:
        print("::error::Validate smoke report missing health_score", file=sys.stderr)
        raise SystemExit(1)
    print(f"Validate smoke health_score={payload['health_score']}")


def check_manifest(path: Path) -> None:
    payload = _load(path)
    version = payload.get("manifest_schema_version")
    if version != "1.1":
        print(
            f"::error::Expected manifest schema 1.1, got {version!r}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    print("Manifest smoke schema 1.1 OK")


def check_gate_report(path: Path) -> None:
    payload = _load(path)
    if payload.get("manifest_regression_blocked"):
        print(
            "::error::Gate smoke expected no regression when baseline matches current export",
            file=sys.stderr,
        )
        raise SystemExit(1)
    print("Manifest gate smoke OK")


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    if len(args) != 2:
        print("usage: maya_integration_checks.py <validate|manifest|gate> <path>", file=sys.stderr)
        return 2
    command, raw_path = args
    path = Path(raw_path)
    if command == "validate":
        check_validate_report(path)
    elif command == "manifest":
        check_manifest(path)
    elif command == "gate":
        check_gate_report(path)
    else:
        print(f"unknown command: {command}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
