"""Client-side bug report submission throttling."""
from __future__ import annotations

import getpass
import json
import socket
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shader_health.integrations.bug_report.config import BugReportRelayConfig
from shader_health.user_config import USER_CONFIG_DIRNAME

BUG_REPORT_THROTTLE_SCHEMA_VERSION = "1.0"
BUG_REPORT_THROTTLE_FILENAME = "bug_report_throttle.json"
RATE_LIMITED_SKIPPED_REASON = "rate_limited"


@dataclass(frozen=True)
class BugReportThrottleDecision:
    """Outcome from evaluating the local per-machine/user daily limit."""

    allowed: bool
    reports_today: int = 0
    max_reports_per_day: int = 0
    skipped_reason: str = ""


def default_throttle_state_path() -> Path:
    """Return the default local throttle state file path."""

    return Path.home() / USER_CONFIG_DIRNAME / BUG_REPORT_THROTTLE_FILENAME


def resolve_machine_id() -> str:
    """Return a stable machine identifier for local throttling."""

    try:
        hostname = socket.gethostname().strip()
    except OSError:
        hostname = ""
    return hostname or "unknown-host"


def resolve_os_user() -> str:
    """Return the current OS username for local throttling."""

    try:
        username = getpass.getuser().strip()
    except Exception:  # noqa: BLE001
        username = ""
    return username or "unknown-user"


def throttle_actor_key(*, machine_id: str = "", os_user: str = "") -> str:
    """Build the throttle key used to isolate machine/user submission counts."""

    machine = machine_id.strip() or resolve_machine_id()
    user = os_user.strip() or resolve_os_user()
    return f"{machine}:{user}"


def evaluate_bug_report_throttle(
    config: BugReportRelayConfig,
    *,
    machine_id: str = "",
    os_user: str = "",
    now_utc: datetime | None = None,
    state_path: Path | None = None,
) -> BugReportThrottleDecision:
    """Return whether a submission is allowed under the local daily limit."""

    limit = _normalized_daily_limit(config.max_reports_per_day)
    if limit <= 0:
        return BugReportThrottleDecision(
            allowed=True,
            max_reports_per_day=limit,
        )

    moment = now_utc or datetime.now(timezone.utc)
    actor = throttle_actor_key(machine_id=machine_id, os_user=os_user)
    state = _load_throttle_state(state_path or default_throttle_state_path())
    reports_today = _reports_today_for_actor(state, actor=actor, day=_utc_day(moment))
    if reports_today >= limit:
        return BugReportThrottleDecision(
            allowed=False,
            reports_today=reports_today,
            max_reports_per_day=limit,
            skipped_reason=RATE_LIMITED_SKIPPED_REASON,
        )
    return BugReportThrottleDecision(
        allowed=True,
        reports_today=reports_today,
        max_reports_per_day=limit,
    )


def record_bug_report_submission(
    *,
    machine_id: str = "",
    os_user: str = "",
    now_utc: datetime | None = None,
    state_path: Path | None = None,
) -> None:
    """Persist one successful local submission for the current UTC day."""

    moment = now_utc or datetime.now(timezone.utc)
    actor = throttle_actor_key(machine_id=machine_id, os_user=os_user)
    path = state_path or default_throttle_state_path()
    state = _load_throttle_state(path)
    day = _utc_day(moment)
    actors = dict(state.get("actors", {}))
    current = actors.get(actor, {})
    if not isinstance(current, Mapping):
        current = {}
    count = (
        0
        if str(current.get("day", "") or "") != day
        else int(current.get("count", 0) or 0)
    )
    actors[actor] = {"day": day, "count": count + 1}
    _save_throttle_state(
        path,
        {
            "schema_version": BUG_REPORT_THROTTLE_SCHEMA_VERSION,
            "actors": actors,
        },
    )


def format_rate_limit_message(decision: BugReportThrottleDecision) -> str:
    """Return a user-visible message for a blocked local throttle decision."""

    return (
        "Daily bug report limit reached "
        f"({decision.reports_today}/{decision.max_reports_per_day})."
    )


def _normalized_daily_limit(max_reports_per_day: int) -> int:
    try:
        value = int(max_reports_per_day)
    except (TypeError, ValueError):
        return 0
    return max(0, value)


def _utc_day(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).date().isoformat()


def _load_throttle_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema_version": BUG_REPORT_THROTTLE_SCHEMA_VERSION, "actors": {}}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": BUG_REPORT_THROTTLE_SCHEMA_VERSION, "actors": {}}
    if not isinstance(raw, dict):
        return {"schema_version": BUG_REPORT_THROTTLE_SCHEMA_VERSION, "actors": {}}
    actors = raw.get("actors")
    if not isinstance(actors, dict):
        actors = {}
    return {
        "schema_version": str(raw.get("schema_version", BUG_REPORT_THROTTLE_SCHEMA_VERSION)),
        "actors": actors,
    }


def _save_throttle_state(path: Path, state: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(state), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _reports_today_for_actor(state: Mapping[str, Any], *, actor: str, day: str) -> int:
    actors = state.get("actors")
    if not isinstance(actors, Mapping):
        return 0
    current = actors.get(actor)
    if not isinstance(current, Mapping):
        return 0
    if str(current.get("day", "") or "") != day:
        return 0
    try:
        return max(0, int(current.get("count", 0) or 0))
    except (TypeError, ValueError):
        return 0
