"""Dispatch validation publish actions to the first enabled task tracker."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from shader_health.integrations.trackers.base import TrackerPublishResult
from shader_health.studio_config import StudioConfig
from shader_health.trackers_registry import first_enabled_tracker

TrackerPublishFn = Callable[..., TrackerPublishResult]


@dataclass(frozen=True)
class TrackerPublishOutcome:
    """Outcome from publishing a validation summary to one tracker."""

    tracker_id: str
    display_name: str
    result: TrackerPublishResult


def publish_validation_to_first_tracker(
    studio_config: StudioConfig | None,
    result: Any,
    *,
    report_path: str = "",
) -> TrackerPublishOutcome | None:
    """Publish a validation summary using the first enabled tracker connector."""

    config = studio_config or StudioConfig.default()
    tracker = first_enabled_tracker(config)
    if tracker is None:
        return None

    publish_fn = _tracker_publish_fn(tracker.id)
    publish_result = publish_fn(
        config,
        result,
        report_path=report_path,
    )
    return TrackerPublishOutcome(
        tracker_id=tracker.id,
        display_name=tracker.display_name,
        result=publish_result,
    )


def format_tracker_publish_status(outcome: TrackerPublishOutcome | None) -> str:
    """Return a user-visible Reports tab status message for tracker publish."""

    if outcome is None:
        return (
            "Send to Tracker skipped — enable a task tracker in Settings → Connectors."
        )

    display_name = outcome.display_name
    publish_result = outcome.result
    if publish_result.published:
        note_ref = publish_result.external_url or publish_result.metadata.get("note_id", "")
        if note_ref:
            return f"{display_name}: validation summary published (ref {note_ref})."
        return f"{display_name}: validation summary published."

    if publish_result.skipped_reason:
        return f"{display_name}: skipped ({publish_result.skipped_reason})."

    if publish_result.error_message:
        return f"{display_name}: failed ({publish_result.error_message})."

    return f"{display_name}: publish did not complete."


def _tracker_publish_fn(tracker_id: str) -> TrackerPublishFn:
    if tracker_id == "ftrack":
        from shader_health.integrations.ftrack.publish import (
            maybe_publish_validation_summary as ftrack_publish,
        )

        return ftrack_publish
    if tracker_id == "shotgrid":
        from shader_health.integrations.shotgrid.publish import (
            maybe_publish_validation_summary as shotgrid_publish,
        )

        return shotgrid_publish
    if tracker_id == "cerebro":
        from shader_health.integrations.cerebro.publish import (
            maybe_publish_validation_summary as cerebro_publish,
        )

        return cerebro_publish
    raise ValueError(f"Unsupported tracker connector id: {tracker_id}")
