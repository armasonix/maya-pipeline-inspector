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
    args = parser.parse_args(argv)

    config = DeadlineConfig.from_json(args.config) if args.config else DeadlineConfig.from_env()
    client = DeadlineClient(config)
    try:
        report = collect_farm_analytics(
            client,
            pool_filter=str(args.pool or "").strip() or None,
            window_hours=float(args.window_hours),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Farm analytics failed: {exc}", file=sys.stderr)
        return 3

    if args.json:
        print(json.dumps(farm_analytics_to_dict(report), indent=2))
    else:
        print(format_farm_analytics_summary(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
