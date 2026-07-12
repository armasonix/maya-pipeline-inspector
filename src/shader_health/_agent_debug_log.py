"""Temporary agent debug logging for Maya UI sessions. Remove after verification."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_SESSION_ID = "88835a"
_LOG_PATH = Path(__file__).resolve().parents[2] / "debug-88835a.log"


def agent_debug_log(
    hypothesis_id: str,
    location: str,
    message: str,
    data: dict[str, Any] | None = None,
    *,
    run_id: str = "pre-fix",
) -> None:
    # region agent log
    payload = {
        "sessionId": _SESSION_ID,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }
    try:
        with _LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        pass
    # endregion
