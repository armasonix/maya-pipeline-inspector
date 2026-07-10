from __future__ import annotations

from types import SimpleNamespace

from shader_health.core.manifest_gate import ManifestGatePolicy  # noqa: F401
from shader_health.core.scoring import HealthScore
from shader_health.integrations.trackers.publish import (
    ValidationPublishPayload,
    format_validation_publish_summary,
    scene_basename,
    slack_thread_ts_from_tracker_metadata,
    tracker_metadata_from_run,
    validation_publish_payload_from_run,
)


def _run_result(**overrides: object) -> SimpleNamespace:
    defaults = {
        "snapshot": SimpleNamespace(
            scene_path=r"C:\shots\hero.ma",
            scanned_at_utc="2026-07-10T12:00:00Z",
        ),
        "scan_scope": "scene",
        "profile_id": "publish_strict",
        "asset_class_id": "character",
        "health_score": HealthScore(
            score=42,
            raw_score=42,
            critical=2,
            error=1,
            warning=3,
            info=0,
            block_publish=True,
            block_deadline=False,
        ),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_scene_basename_normalizes_windows_and_posix_paths():
    assert scene_basename(r"C:\shots\hero.ma") == "hero.ma"
    assert scene_basename("/tmp/hero.ma") == "hero.ma"
    assert scene_basename("") == "unsaved scene"


def test_validation_publish_payload_from_run_reads_snapshot_and_health():
    payload = validation_publish_payload_from_run(
        _run_result(),
        report_path=r"\\farm\render\hero_shader_health_report.json",
        metadata={"thread_ts": "123.456"},
    )

    assert payload.scene_name == "hero.ma"
    assert payload.scene_path == r"C:\shots\hero.ma"
    assert payload.profile_id == "publish_strict"
    assert payload.asset_class_id == "character"
    assert payload.health_score == 42
    assert payload.block_publish is True
    assert payload.block_deadline is False
    assert payload.validated_at_utc == "2026-07-10T12:00:00Z"
    assert payload.report_path.endswith("hero_shader_health_report.json")
    assert payload.metadata["thread_ts"] == "123.456"


def test_tracker_metadata_from_run_reads_pipeline_metadata_mapping():
    result = _run_result(
        tracker_metadata={
            "task_id": "task-7",
            "thread_ts": "1710000000.000100",
            "empty": "",
        }
    )

    assert tracker_metadata_from_run(result) == {
        "task_id": "task-7",
        "thread_ts": "1710000000.000100",
    }


def test_validation_publish_payload_from_run_merges_tracker_metadata_from_result():
    result = _run_result(
        tracker_metadata={
            "task_id": "task-7",
            "slack_thread_ts": "1710000000.000200",
        }
    )

    payload = validation_publish_payload_from_run(
        result,
        metadata={"thread_ts": "override"},
    )

    assert payload.metadata["task_id"] == "task-7"
    assert payload.metadata["slack_thread_ts"] == "1710000000.000200"
    assert payload.metadata["thread_ts"] == "override"


def test_slack_thread_ts_from_tracker_metadata_accepts_thread_ts_aliases():
    assert slack_thread_ts_from_tracker_metadata({"thread_ts": "123.456"}) == "123.456"
    assert (
        slack_thread_ts_from_tracker_metadata({"slack_thread_ts": "789.012"})
        == "789.012"
    )
    assert slack_thread_ts_from_tracker_metadata({}) is None


def test_validation_publish_payload_profile_and_block_labels():
    payload = ValidationPublishPayload(
        scene_name="hero.ma",
        scene_path="/tmp/hero.ma",
        scan_scope="selection",
        profile_id="publish_strict",
        asset_class_id="character",
        health_score=10,
        critical_count=1,
        error_count=0,
        warning_count=0,
        info_count=0,
        block_publish=True,
        block_deadline=True,
        validated_at_utc="2026-07-10T12:00:00Z",
    )

    assert payload.profile_label() == "publish_strict+character"
    assert payload.block_status_label() == "Publish block, Deadline block"


def test_format_validation_publish_summary_includes_core_fields_and_report_path():
    payload = validation_publish_payload_from_run(
        _run_result(),
        report_path=r"\\farm\render\hero_shader_health_report.json",
    )

    message = format_validation_publish_summary(payload)

    assert "Shader Health validation summary (Publish block)" in message
    assert "Scene: hero.ma" in message
    assert "Profile: publish_strict+character" in message
    assert "Scope: Scene" in message
    assert "Health: 42/100" in message
    assert "Issues: 2 critical, 1 error, 3 warning, 0 info" in message
    assert "Validated at: 2026-07-10T12:00:00Z" in message
    assert r"Report: \\farm\render\hero_shader_health_report.json" in message
