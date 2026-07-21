"""Optional gated debug logging for agent investigations."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

_SESSION_ID = os.environ.get("PIPELINE_INSPECTOR_DEBUG_SESSION", "").strip()
_LOG_PATH: Path | None = None


def debug_log_enabled() -> bool:
    """Return whether session debug logging is active."""

    return bool(_SESSION_ID)


def _resolve_log_path() -> Path:
    global _LOG_PATH
    if _LOG_PATH is not None:
        return _LOG_PATH

    override = os.environ.get("PIPELINE_INSPECTOR_DEBUG_LOG", "").strip()
    if override:
        _LOG_PATH = Path(override)
        return _LOG_PATH

    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file():
            _LOG_PATH = parent / f"debug-{_SESSION_ID}.log"
            return _LOG_PATH
        if (parent / "src" / "pipeline_inspector").is_dir() and parent.name != "src":
            _LOG_PATH = parent / f"debug-{_SESSION_ID}.log"
            return _LOG_PATH

    _LOG_PATH = Path.cwd() / f"debug-{_SESSION_ID}.log"
    return _LOG_PATH


def write_debug_log(
    location: str,
    message: str,
    data: dict[str, Any] | None = None,
    *,
    hypothesis_id: str = "",
    run_id: str = "",
) -> None:
    """Append one NDJSON debug record when ``PIPELINE_INSPECTOR_DEBUG_SESSION`` is set."""

    if not _SESSION_ID:
        return
    _append_debug_payload(
        _resolve_log_path(),
        location,
        message,
        data,
        hypothesis_id=hypothesis_id,
        run_id=run_id,
        session_id=_SESSION_ID,
    )


def write_agent_cycle_log(
    location: str,
    message: str,
    data: dict[str, Any] | None = None,
    *,
    hypothesis_id: str = "",
    run_id: str = "",
    session_id: str = "",
) -> None:
    """Append NDJSON when ``PIPELINE_INSPECTOR_DEBUG_SESSION`` is set."""

    if not _SESSION_ID:
        return
    if os.environ.get("PIPELINE_INSPECTOR_DISABLE_AGENT_LOG", "").strip():
        return
    active_session_id = session_id or _SESSION_ID
    _append_debug_payload(
        _resolve_log_path(),
        location,
        message,
        data,
        hypothesis_id=hypothesis_id,
        run_id=run_id,
        session_id=active_session_id,
    )


def _append_debug_payload(
    log_path: Path,
    location: str,
    message: str,
    data: dict[str, Any] | None,
    *,
    hypothesis_id: str,
    run_id: str,
    session_id: str,
) -> None:
    try:
        payload: dict[str, Any] = {
            "sessionId": session_id,
            "timestamp": int(time.time() * 1000),
            "location": location,
            "message": message,
            "data": {key: str(value) for key, value in (data or {}).items()},
            "hypothesisId": hypothesis_id,
        }
        if run_id:
            payload["runId"] = run_id
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
    except OSError:
        return
