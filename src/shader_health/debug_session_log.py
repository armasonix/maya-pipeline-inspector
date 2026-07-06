"""Append-only NDJSON debug logging for local Maya/UI verification sessions."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

SESSION_ID = "ee1eca"
DEBUG_LOG_PATH = Path(__file__).resolve().parents[2] / "debug-ee1eca.log"


def write_debug_log(
    *,
    location: str,
    message: str,
    data: dict[str, Any],
    hypothesis_id: str,
    run_id: str = "pre-fix",
) -> None:
    # region agent log
    payload = {
        "sessionId": SESSION_ID,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    try:
        with DEBUG_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
    except OSError:
        return
    # endregion
