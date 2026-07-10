"""Ftrack validation publish helpers."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from shader_health.integrations.ftrack.client import FtrackClient
from shader_health.integrations.ftrack.config import FtrackConfig
from shader_health.integrations.trackers.base import TrackerPublishResult
from shader_health.integrations.trackers.publish import (
    ValidationPublishPayload,
    format_validation_publish_summary,
)
from shader_health.studio_config import StudioConfig, resolve_ftrack_config

FtrackClientFactory = Callable[[FtrackConfig], FtrackClient]


def _escape_query_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _task_id_from_payload(payload: ValidationPublishPayload) -> str:
    for key in ("task_id", "ftrack_task_id"):
        task_id = str(payload.metadata.get(key, "") or "").strip()
        if task_id:
            return task_id
    return ""


def resolve_task_id(
    client: FtrackClient,
    config: FtrackConfig,
    payload: ValidationPublishPayload,
) -> str | None:
    """Resolve the Ftrack task id from payload metadata or project/scene lookup."""

    explicit_task_id = _task_id_from_payload(payload)
    if explicit_task_id:
        return explicit_task_id

    project = _escape_query_value(config.project)
    scene_name = _escape_query_value(payload.scene_name)
    expression = (
        f'Task where project.name is "{project}" and name is "{scene_name}"'
    )
    tasks = client.query(expression)
    if not tasks:
        return None
    task_id = str(tasks[0].get("id", "") or "").strip()
    return task_id or None


def publish_validation_summary(
    studio_config: StudioConfig | None,
    payload: ValidationPublishPayload,
    *,
    client_factory: FtrackClientFactory | None = None,
) -> TrackerPublishResult:
    """Publish a validation summary as an Ftrack task note."""

    config = resolve_ftrack_config(studio_config)
    if config is None:
        return TrackerPublishResult(published=False, skipped_reason="disabled")

    factory = client_factory or FtrackClient
    client = factory(config)
    task_id = resolve_task_id(client, config, payload)
    if task_id is None:
        return TrackerPublishResult(published=False, skipped_reason="task_not_found")

    note = client.create_task_note(
        task_id=task_id,
        content=format_validation_publish_summary(payload),
    )
    if note is None:
        return TrackerPublishResult(published=False, error_message="ftrack_api_error")

    note_id = str(note.get("id", "") or "").strip()
    metadata = {"note_id": note_id} if note_id else {}
    return TrackerPublishResult(
        published=True,
        external_url=note_id,
        metadata=metadata,
    )


def maybe_publish_validation_summary(
    studio_config: StudioConfig | None,
    result: Any,
    *,
    report_path: str = "",
    client_factory: FtrackClientFactory | None = None,
) -> TrackerPublishResult:
    """Build a publish payload from a validation run and send it to Ftrack."""

    from shader_health.integrations.trackers.publish import validation_publish_payload_from_run

    payload = validation_publish_payload_from_run(result, report_path=report_path)
    return publish_validation_summary(
        studio_config,
        payload,
        client_factory=client_factory,
    )
