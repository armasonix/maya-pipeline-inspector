from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from pipeline_inspector.core.scoring import HealthScore
from pipeline_inspector.integrations.trackers.base import TrackerPublishResult
from pipeline_inspector.integrations.trackers.publish_dispatcher import (
    format_tracker_publish_status,
    publish_validation_to_first_tracker,
)
from pipeline_inspector.studio_config import (
    ConnectorSettings,
    FtrackConnectorSettings,
    ShotGridConnectorSettings,
    StudioConfig,
)


def _validation_result() -> SimpleNamespace:
    return SimpleNamespace(
        snapshot=SimpleNamespace(
            scene_path="/tmp/hero.ma",
            scanned_at_utc="2026-07-10T12:00:00Z",
        ),
        scan_scope="scene",
        profile_id="publish_strict",
        asset_class_id="",
        health_score=HealthScore(
            score=40,
            raw_score=40,
            critical=1,
            block_publish=True,
        ),
    )


def test_publish_validation_to_first_tracker_returns_none_when_no_tracker_enabled():
    config = StudioConfig(connectors=ConnectorSettings())

    outcome = publish_validation_to_first_tracker(config, _validation_result())

    assert outcome is None


def test_publish_validation_to_first_tracker_uses_first_enabled_tracker():
    config = StudioConfig(
        connectors=ConnectorSettings(
            ftrack=FtrackConnectorSettings(enabled=False),
            shotgrid=ShotGridConnectorSettings(
                enabled=True,
                site_url="https://studio.shotgrid.autodesk.com",
                script_name="pipeline_inspector",
                api_key="secret",
                project="Demo Project",
            ),
        )
    )
    expected = TrackerPublishResult(published=True, external_url="99")

    with patch(
        "pipeline_inspector.integrations.shotgrid.publish.maybe_publish_validation_summary",
        return_value=expected,
    ) as publish_mock:
        outcome = publish_validation_to_first_tracker(config, _validation_result())

    assert outcome is not None
    assert outcome.tracker_id == "shotgrid"
    assert outcome.display_name == "ShotGrid"
    assert outcome.result == expected
    publish_mock.assert_called_once_with(config, _validation_result(), report_path="")


def test_format_tracker_publish_status_describes_success_skip_and_failure():
    assert "enable a task tracker" in format_tracker_publish_status(None).lower()

    published = format_tracker_publish_status(
        SimpleNamespace(
            display_name="Ftrack",
            result=TrackerPublishResult(published=True, external_url="note-7"),
        )
    )
    assert "Ftrack" in published
    assert "published" in published
    assert "note-7" in published

    skipped = format_tracker_publish_status(
        SimpleNamespace(
            display_name="Cerebro",
            result=TrackerPublishResult(published=False, skipped_reason="task_not_found"),
        )
    )
    assert "skipped" in skipped
    assert "task_not_found" in skipped

    failed = format_tracker_publish_status(
        SimpleNamespace(
            display_name="ShotGrid",
            result=TrackerPublishResult(published=False, error_message="shotgrid_api_error"),
        )
    )
    assert "failed" in failed
    assert "shotgrid_api_error" in failed

    attached = format_tracker_publish_status(
        SimpleNamespace(
            display_name="Ftrack",
            result=TrackerPublishResult(
                published=True,
                external_url="note-7",
                metadata={"component_id": "comp-1"},
            ),
        )
    )
    assert "HTML report attached" in attached
