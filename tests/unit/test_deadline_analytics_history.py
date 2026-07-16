from __future__ import annotations

import json
from pathlib import Path

from pipeline_inspector.integrations.deadline.analytics_history import (
    append_farm_analytics_history,
    load_recent_shot_submit_counts,
)


def test_append_and_load_farm_analytics_history(tmp_path: Path):
    history_path = tmp_path / "farm_history.jsonl"
    payload = {
        "collected_at_epoch": 1_000_000.0,
        "shot_intelligence": {
            "rerender_watchlist": [
                {"shot_key": "show_seq010_sh010", "submit_count": 2},
            ]
        },
    }

    append_farm_analytics_history(history_path, payload)
    append_farm_analytics_history(history_path, payload)

    lines = history_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["shot_intelligence"]["rerender_watchlist"][0]["shot_key"]

    counts = load_recent_shot_submit_counts(
        history_path,
        window_hours=24.0,
        now_epoch=1_000_000.0 + 60.0,
    )
    assert counts["show_seq010_sh010"] == 4
