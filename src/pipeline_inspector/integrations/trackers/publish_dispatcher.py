"""Dispatch validation publish actions to the first enabled task tracker."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pipeline_inspector.integrations.trackers.base import TrackerPublishResult
from pipeline_inspector.studio_config import StudioConfig
from pipeline_inspector.trackers_registry import first_enabled_tracker

TrackerPublishFn = Callable[..., TrackerPublishResult]


@dataclass(frozen=True)
class TrackerPublishOutcome:
    """Outcome from publishing a validation summary to one tracker."""

    tracker_id: str
    display_name: str
    result: TrackerPublishResult


def preload_tracker_publish_modules(studio_config: StudioConfig | None) -> str:
    """Import the enabled tracker publish module on the UI thread."""

    config = studio_config or StudioConfig.default()
    tracker = first_enabled_tracker(config)
    if tracker is None:
        return ""
    _tracker_publish_fn(tracker.id)
    return tracker.id


def publish_validation_to_first_tracker(
    studio_config: StudioConfig | None,
    result: Any,
    *,
    report_path: str = "",
) -> TrackerPublishOutcome | None:
    """Publish a validation summary using the first enabled tracker connector."""

    # region agent log
    import json
    import os
    import time
    from pathlib import Path

    _dispatch_started = time.time()
    try:
        with (Path(__file__).resolve().parents[3] / "debug-618f4f.log").open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    {
                        "sessionId": "618f4f",
                        "runId": "post-fix",
                        "hypothesisId": "H6",
                        "location": "publish_dispatcher.publish_validation_to_first_tracker",
                        "message": "dispatch_enter",
                        "data": {},
                        "timestamp": int(time.time() * 1000),
                    }
                )
                + "\n"
            )
            handle.flush()
            os.fsync(handle.fileno())
    except (OSError, TypeError, ValueError):
        pass
    # endregion

    config = studio_config or StudioConfig.default()
    tracker = first_enabled_tracker(config)
    if tracker is None:
        return None

    publish_fn = _tracker_publish_fn(tracker.id)
    # region agent log
    try:
        with (Path(__file__).resolve().parents[3] / "debug-618f4f.log").open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    {
                        "sessionId": "618f4f",
                        "runId": "post-fix",
                        "hypothesisId": "H6",
                        "location": "publish_dispatcher.publish_validation_to_first_tracker",
                        "message": "before_publish_fn",
                        "data": {
                            "tracker_id": tracker.id,
                            "elapsed_ms": int((time.time() - _dispatch_started) * 1000),
                        },
                        "timestamp": int(time.time() * 1000),
                    }
                )
                + "\n"
            )
            handle.flush()
            os.fsync(handle.fileno())
    except (OSError, TypeError, ValueError):
        pass
    # endregion
    publish_result = publish_fn(
        config,
        result,
        report_path=report_path,
    )
    # region agent log
    try:
        with (Path(__file__).resolve().parents[3] / "debug-618f4f.log").open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    {
                        "sessionId": "618f4f",
                        "runId": "post-fix",
                        "hypothesisId": "H6",
                        "location": "publish_dispatcher.publish_validation_to_first_tracker",
                        "message": "dispatch_exit",
                        "data": {
                            "tracker_id": tracker.id,
                            "published": publish_result.published,
                            "elapsed_ms": int((time.time() - _dispatch_started) * 1000),
                        },
                        "timestamp": int(time.time() * 1000),
                    }
                )
                + "\n"
            )
            handle.flush()
            os.fsync(handle.fileno())
    except (OSError, TypeError, ValueError):
        pass
    # endregion
    return TrackerPublishOutcome(
        tracker_id=tracker.id,
        display_name=tracker.display_name,
        result=publish_result,
    )


def format_tracker_publish_status(outcome: TrackerPublishOutcome | None) -> str:
    """Return a user-visible Reports tab status message for tracker publish."""

    if outcome is None:
        return (
            "Send to Tracker skipped вЂ” enable a task tracker in Settings в†’ Connectors."
        )

    display_name = outcome.display_name
    publish_result = outcome.result
    if publish_result.published:
        note_ref = publish_result.external_url or publish_result.metadata.get("note_id", "")
        attachment_ref = (
            publish_result.metadata.get("component_id")
            or publish_result.metadata.get("attachment_id")
        )
        attachment_error = (publish_result.metadata.get("attachment_error") or "").strip()
        if note_ref and attachment_ref:
            return (
                f"{display_name}: validation summary published "
                f"(ref {note_ref}, HTML report attached)."
            )
        if note_ref:
            if attachment_error:
                return (
                    f"{display_name}: validation summary published "
                    f"(ref {note_ref}; HTML attachment failed: {attachment_error})."
                )
            return f"{display_name}: validation summary published (ref {note_ref})."
        if attachment_ref:
            return f"{display_name}: validation summary published with HTML report attached."
        return f"{display_name}: validation summary published."

    if publish_result.skipped_reason:
        detail = (publish_result.error_message or "").strip()
        if detail and detail != publish_result.skipped_reason:
            return f"{display_name}: skipped ({publish_result.skipped_reason}) — {detail}"
        return f"{display_name}: skipped ({publish_result.skipped_reason})."

    if publish_result.error_message:
        return f"{display_name}: failed ({publish_result.error_message})."

    return f"{display_name}: publish did not complete."


def _tracker_publish_fn(tracker_id: str) -> TrackerPublishFn:
    if tracker_id == "ftrack":
        from pipeline_inspector.integrations.ftrack.publish import (
            maybe_publish_validation_summary as ftrack_publish,
        )

        return ftrack_publish
    if tracker_id == "shotgrid":
        from pipeline_inspector.integrations.shotgrid.publish import (
            maybe_publish_validation_summary as shotgrid_publish,
        )

        return shotgrid_publish
    if tracker_id == "cerebro":
        from pipeline_inspector.integrations.cerebro.publish import (
            maybe_publish_validation_summary as cerebro_publish,
        )

        return cerebro_publish
    raise ValueError(f"Unsupported tracker connector id: {tracker_id}")
