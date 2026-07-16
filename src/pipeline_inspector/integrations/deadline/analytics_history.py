"""Append-only JSONL history for Deadline farm analytics snapshots."""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def append_farm_analytics_history(
    path: str | Path,
    payload: Mapping[str, Any],
) -> Path:
    """Append one analytics snapshot as a JSONL record."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
    return output_path


def load_recent_shot_submit_counts(
    path: str | Path,
    *,
    window_hours: float,
    now_epoch: float,
) -> dict[str, int]:
    """Count prior shot-key submissions inside a history window."""

    history_path = Path(path)
    if not history_path.is_file():
        return {}

    window_seconds = max(window_hours, 0.01) * 3600.0
    counts: dict[str, int] = {}
    for line in history_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        collected_at = float(record.get("collected_at_epoch") or 0.0)
        if collected_at <= 0 or now_epoch - collected_at > window_seconds:
            continue
        shot_intel = record.get("shot_intelligence") or {}
        for entry in shot_intel.get("rerender_watchlist") or []:
            shot_key = str(entry.get("shot_key") or "").strip()
            if not shot_key:
                continue
            counts[shot_key] = counts.get(shot_key, 0) + int(entry.get("submit_count") or 0)
    return counts
