"""Compare GUI vs CLI JSON reports for parity smoke tests."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _failed_rule_ids(report: dict) -> list[str]:
    return sorted(
        row["rule_id"]
        for row in report.get("results", [])
        if row.get("status") == "failed"
    )


def compare_validate(gui: dict, cli: dict) -> int:
    errors = 0
    for key in ("health_score", "block_publish", "block_deadline", "status"):
        gv, cv = gui.get(key), cli.get(key)
        ok = gv == cv
        print(f"{key}: GUI={gv} CLI={cv} {'OK' if ok else 'DIFF'}")
        errors += 0 if ok else 1

    gui_failed = _failed_rule_ids(gui)
    cli_failed = _failed_rule_ids(cli)
    ok = gui_failed == cli_failed
    print(
        "failed rule count:",
        len(gui_failed),
        len(cli_failed),
        "OK" if ok else "DIFF",
    )
    if not ok:
        print("only GUI:", sorted(set(gui_failed) - set(cli_failed)))
        print("only CLI:", sorted(set(cli_failed) - set(gui_failed)))
        errors += 1
    return errors


def compare_manifest(gui: dict, cli: dict) -> int:
    errors = 0
    for key in ("manifest_schema_version", "health_score"):
        gv, cv = gui.get(key), cli.get(key)
        ok = gv == cv
        print(f"{key}: GUI={gv} CLI={cv} {'OK' if ok else 'DIFF'}")
        errors += 0 if ok else 1

    gm = len(gui.get("materials", []))
    cm = len(cli.get("materials", []))
    ok = gm == cm
    print(f"materials: GUI={gm} CLI={cm} {'OK' if ok else 'DIFF'}")
    return errors + (0 if ok else 1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gui_report", type=Path)
    parser.add_argument("cli_report", type=Path)
    parser.add_argument(
        "--manifest",
        action="store_true",
        help="Compare manifest JSON instead of validation report.",
    )
    args = parser.parse_args(argv)

    gui = _load(args.gui_report)
    cli = _load(args.cli_report)
    errors = compare_manifest(gui, cli) if args.manifest else compare_validate(gui, cli)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
