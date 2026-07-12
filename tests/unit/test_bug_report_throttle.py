from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pipeline_inspector.integrations.bug_report.config import BugReportRelayConfig
from pipeline_inspector.integrations.bug_report.throttle import (
    RATE_LIMITED_SKIPPED_REASON,
    evaluate_bug_report_throttle,
    format_rate_limit_message,
    record_bug_report_submission,
    throttle_actor_key,
)


def _config(*, max_reports_per_day: int = 2) -> BugReportRelayConfig:
    return BugReportRelayConfig(
        relay_url="https://pipeline.studio.internal/shader-health/bug-report",
        api_key="studio-secret",
        max_reports_per_day=max_reports_per_day,
    )


def test_evaluate_bug_report_throttle_allows_submission_under_daily_limit(tmp_path: Path):
    state_path = tmp_path / "bug_report_throttle.json"
    now = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)

    record_bug_report_submission(
        machine_id="workstation-01",
        os_user="artist",
        now_utc=now,
        state_path=state_path,
    )

    decision = evaluate_bug_report_throttle(
        _config(max_reports_per_day=2),
        machine_id="workstation-01",
        os_user="artist",
        now_utc=now,
        state_path=state_path,
    )

    assert decision.allowed is True
    assert decision.reports_today == 1
    assert decision.max_reports_per_day == 2


def test_evaluate_bug_report_throttle_blocks_when_daily_limit_reached(tmp_path: Path):
    state_path = tmp_path / "bug_report_throttle.json"
    now = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)

    record_bug_report_submission(
        machine_id="workstation-01",
        os_user="artist",
        now_utc=now,
        state_path=state_path,
    )
    record_bug_report_submission(
        machine_id="workstation-01",
        os_user="artist",
        now_utc=now,
        state_path=state_path,
    )

    decision = evaluate_bug_report_throttle(
        _config(max_reports_per_day=2),
        machine_id="workstation-01",
        os_user="artist",
        now_utc=now,
        state_path=state_path,
    )

    assert decision.allowed is False
    assert decision.skipped_reason == RATE_LIMITED_SKIPPED_REASON
    assert decision.reports_today == 2
    assert "2/2" in format_rate_limit_message(decision)


def test_evaluate_bug_report_throttle_resets_counts_on_new_utc_day(tmp_path: Path):
    state_path = tmp_path / "bug_report_throttle.json"

    record_bug_report_submission(
        machine_id="workstation-01",
        os_user="artist",
        now_utc=datetime(2026, 7, 10, 23, 0, tzinfo=timezone.utc),
        state_path=state_path,
    )
    record_bug_report_submission(
        machine_id="workstation-01",
        os_user="artist",
        now_utc=datetime(2026, 7, 10, 23, 30, tzinfo=timezone.utc),
        state_path=state_path,
    )

    decision = evaluate_bug_report_throttle(
        _config(max_reports_per_day=2),
        machine_id="workstation-01",
        os_user="artist",
        now_utc=datetime(2026, 7, 11, 1, 0, tzinfo=timezone.utc),
        state_path=state_path,
    )

    assert decision.allowed is True
    assert decision.reports_today == 0


def test_evaluate_bug_report_throttle_isolates_machine_and_user_keys(tmp_path: Path):
    state_path = tmp_path / "bug_report_throttle.json"
    now = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)

    record_bug_report_submission(
        machine_id="workstation-01",
        os_user="artist",
        now_utc=now,
        state_path=state_path,
    )
    record_bug_report_submission(
        machine_id="workstation-01",
        os_user="artist",
        now_utc=now,
        state_path=state_path,
    )

    other_user = evaluate_bug_report_throttle(
        _config(max_reports_per_day=2),
        machine_id="workstation-01",
        os_user="lead_td",
        now_utc=now,
        state_path=state_path,
    )
    other_machine = evaluate_bug_report_throttle(
        _config(max_reports_per_day=2),
        machine_id="workstation-02",
        os_user="artist",
        now_utc=now,
        state_path=state_path,
    )

    assert other_user.allowed is True
    assert other_machine.allowed is True
    assert throttle_actor_key(machine_id="workstation-01", os_user="artist") != (
        throttle_actor_key(machine_id="workstation-01", os_user="lead_td")
    )
