"""Shared result types for task tracker publish actions."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from pipeline_inspector.integrations.trackers.publish import ValidationPublishPayload


@dataclass(frozen=True)
class TrackerPublishResult:
    """Outcome from publishing a validation summary to a task tracker."""

    published: bool
    skipped_reason: str = ""
    error_message: str = ""
    external_url: str = ""
    metadata: Mapping[str, str] = field(default_factory=dict)

class TrackerPublisher(Protocol):
    """Contract implemented by Ftrack, ShotGrid, and Cerebro connectors."""

    def publish_validation_summary(
        self,
        payload: ValidationPublishPayload,
    ) -> TrackerPublishResult:
        """Publish a validation summary to the configured tracker."""
