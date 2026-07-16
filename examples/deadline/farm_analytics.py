"""Collect Deadline farm analytics from the Web Service."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pipeline_inspector.integrations.deadline import (
    DeadlineClient,
    DeadlineConfig,
    collect_farm_analytics,
    farm_analytics_to_dict,
    format_farm_analytics_summary,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Collect Deadline farm analytics via the Web Service.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional Deadline JSON config. Defaults to PIPELINE_INSPECTOR_DEADLINE_* env vars.",
    )
    parser.add_argument(
        "--pool",
        default="",
        help="Optional pool name filter for utilization metrics.",
    )
    parser.add_argument(
        "--window-hours",
        type=float,
        default=24.0,
        help="Throughput window in hours for completed jobs.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON instead of a human-readable summary.",
    )
    parser.add_argument(
        "--html",
        type=Path,
        help="Write a management-facing HTML report to this path.",
    )
    parser.add_argument(
        "--history-path",
        type=Path,
        help="Append this analytics snapshot to a JSONL history file.",
    )
    parser.add_argument(
        "--shot-key-pattern",
        default="",
        help="Optional regex override for extracting shot keys from job metadata.",
    )
    args = parser.parse_args(argv)

    config = DeadlineConfig.from_json(args.config) if args.config else DeadlineConfig.from_env()
    client = DeadlineClient(config)
    try:
        report = collect_farm_analytics(
            client,
            pool_filter=str(args.pool or "").strip() or None,
            window_hours=float(args.window_hours),
            history_path=args.history_path,
            shot_key_pattern=str(args.shot_key_pattern or "").strip() or None,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Farm analytics failed: {exc}", file=sys.stderr)
        return 3

    if args.html:
        from pipeline_inspector.reports.farm_html_report import write_farm_html_report

        try:
            written = write_farm_html_report(args.html, report, api_url=config.api_url)
        except Exception as exc:  # noqa: BLE001
            print(f"Farm HTML report failed: {exc}", file=sys.stderr)
            return 3
        print(f"Deadline farm HTML report exported: {written}")

    if args.json:
        print(json.dumps(farm_analytics_to_dict(report), indent=2))
    elif not args.html:
        print(format_farm_analytics_summary(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
