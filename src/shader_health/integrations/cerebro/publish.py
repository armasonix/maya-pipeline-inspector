"""Cerebro validation publish helpers."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from shader_health.integrations.cerebro.client import CerebroClient
from shader_health.integrations.cerebro.config import CerebroConfig
from shader_health.integrations.trackers.base import TrackerPublishResult
from shader_health.integrations.trackers.publish import (
    ValidationPublishPayload,
    format_validation_publish_summary,
)
from shader_health.studio_config import StudioConfig, resolve_cerebro_config

CerebroClientFactory = Callable[[CerebroConfig], CerebroClient]


def _task_id_from_payload(payload: ValidationPublishPayload) -> int | None:
    for key in ("task_id", "cerebro_task_id"):
        raw_value = str(payload.metadata.get(key, "") or "").strip()
        if raw_value.isdigit():
            return int(raw_value)
    return None


def _task_url_from_payload(payload: ValidationPublishPayload) -> str:
    for key in ("task_url", "cerebro_task_url"):
        raw_value = str(payload.metadata.get(key, "") or "").strip()
        if raw_value:
            return raw_value
    return ""


def build_task_url(project: str, scene_name: str) -> str:
    """Build a Cerebro task locator from project and scene name."""

    project_part = project.strip().strip("/")
    scene_part = scene_name.strip().strip("/")
    if not project_part or not scene_part:
        return ""
    return f"/{project_part}/{scene_part}"


def resolve_task_id(
    client: CerebroClient,
    config: CerebroConfig,
    payload: ValidationPublishPayload,
) -> int | None:
    """Resolve the Cerebro task id from payload metadata or project/scene lookup."""

    explicit_task_id = _task_id_from_payload(payload)
    if explicit_task_id is not None:
        return explicit_task_id

    task_url = _task_url_from_payload(payload)
    if not task_url:
        task_url = build_task_url(config.project, payload.scene_name)
    if not task_url:
        return None

    return client.resolve_task_id(task_url)


def publish_validation_summary(
    studio_config: StudioConfig | None,
    payload: ValidationPublishPayload,
    *,
    client_factory: CerebroClientFactory | None = None,
) -> TrackerPublishResult:
    """Publish a validation summary as a Cerebro task note."""

    config = resolve_cerebro_config(studio_config)
    if config is None:
        return TrackerPublishResult(published=False, skipped_reason="disabled")

    factory = client_factory or CerebroClient
    client = factory(config)
    task_id = resolve_task_id(client, config, payload)
    if task_id is None:
        return TrackerPublishResult(published=False, skipped_reason="task_not_found")

    note = client.create_task_note(
        task_id=task_id,
        content=format_validation_publish_summary(payload),
    )
    if note is None:
        return TrackerPublishResult(published=False, error_message="cerebro_api_error")

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
    client_factory: CerebroClientFactory | None = None,
) -> TrackerPublishResult:
    """Build a publish payload from a validation run and send it to Cerebro."""

    from shader_health.integrations.trackers.publish import validation_publish_payload_from_run

    payload = validation_publish_payload_from_run(result, report_path=report_path)
    return publish_validation_summary(
        studio_config,
        payload,
        client_factory=client_factory,
    )
