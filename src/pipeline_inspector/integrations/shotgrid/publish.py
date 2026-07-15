"""ShotGrid validation publish helpers."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pipeline_inspector.integrations.shotgrid.attachments import attach_html_report_to_note
from pipeline_inspector.integrations.shotgrid.client import ShotGridClient
from pipeline_inspector.integrations.shotgrid.config import ShotGridConfig
from pipeline_inspector.integrations.trackers.base import TrackerPublishResult
from pipeline_inspector.integrations.trackers.publish import (
    ValidationPublishPayload,
    format_tracker_note_content,
    format_validation_publish_summary,
)
from pipeline_inspector.integrations.trackers.report_bundle import TrackerReportBundle
from pipeline_inspector.studio_config import StudioConfig, resolve_shotgrid_config

ShotGridClientFactory = Callable[[ShotGridConfig], ShotGridClient]

def _entity_id_from_payload(
    payload: ValidationPublishPayload,
    entity_type: str,
) -> int | None:
    keys: tuple[str, ...]
    if entity_type == "Asset":
        keys = ("asset_id", "shotgrid_asset_id", "entity_id")
    else:
        keys = ("shot_id", "shotgrid_shot_id", "entity_id")

    for key in keys:
        raw_value = str(payload.metadata.get(key, "") or "").strip()
        if raw_value.isdigit():
            return int(raw_value)
    return None

def resolve_entity(
    client: ShotGridClient,
    config: ShotGridConfig,
    payload: ValidationPublishPayload,
) -> tuple[str, int] | None:
    """Resolve the ShotGrid entity type and id from metadata or project/code lookup."""

    entity_type = config.normalized_entity_type
    explicit_entity_id = _entity_id_from_payload(payload, entity_type)
    if explicit_entity_id is not None:
        return entity_type, explicit_entity_id

    entity = client.find_entity(
        entity_type=entity_type,
        code=payload.scene_name,
        project_name=config.project,
    )
    if entity is None:
        return None

    raw_entity_id = entity.get("id")
    if isinstance(raw_entity_id, int):
        return entity_type, raw_entity_id
    if isinstance(raw_entity_id, str) and raw_entity_id.isdigit():
        return entity_type, int(raw_entity_id)
    return None

def publish_validation_summary(
    studio_config: StudioConfig | None,
    payload: ValidationPublishPayload,
    *,
    report_bundle: TrackerReportBundle | None = None,
    client_factory: ShotGridClientFactory | None = None,
) -> TrackerPublishResult:
    """Publish a validation summary as a ShotGrid note on an Asset or Shot."""

    config = resolve_shotgrid_config(studio_config)
    if config is None:
        return TrackerPublishResult(published=False, skipped_reason="disabled")

    factory = client_factory or ShotGridClient
    client = factory(config)
    resolved_entity = resolve_entity(client, config, payload)
    if resolved_entity is None:
        return TrackerPublishResult(published=False, skipped_reason="entity_not_found")

    entity_type, entity_id = resolved_entity
    project_id = client.find_project_id(config.project)
    if project_id is None:
        return TrackerPublishResult(published=False, skipped_reason="project_not_found")

    note = client.create_entity_note(
        content=_tracker_note_content(payload, report_bundle),
        project_id=project_id,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    if note is None:
        return TrackerPublishResult(published=False, error_message="shotgrid_api_error")

    note_id = str(note.get("id", "") or "").strip()
    metadata = {"note_id": note_id} if note_id else {}

    if report_bundle is not None and report_bundle.html_report_path and note_id.isdigit():
        attachment_id, attach_error = attach_html_report_to_note(
            client,
            note_id=int(note_id),
            file_path=report_bundle.html_report_path,
            filename=report_bundle.attachment_filename,
        )
        if attachment_id:
            metadata["attachment_id"] = attachment_id
        elif attach_error:
            metadata["attachment_error"] = attach_error

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
    client_factory: ShotGridClientFactory | None = None,
) -> TrackerPublishResult:
    """Build a publish payload from a validation run and send it to ShotGrid."""

    from pipeline_inspector.integrations.trackers.publish import validation_publish_payload_from_run
    from pipeline_inspector.integrations.trackers.report_bundle import (
        build_tracker_report_bundle_from_run,
    )

    report_bundle = build_tracker_report_bundle_from_run(result, report_path=report_path)
    payload = validation_publish_payload_from_run(result, report_path="")
    return publish_validation_summary(
        studio_config,
        payload,
        report_bundle=report_bundle,
        client_factory=client_factory,
    )


def _tracker_note_content(
    payload: ValidationPublishPayload,
    report_bundle: TrackerReportBundle | None,
) -> str:
    if report_bundle is not None:
        return format_tracker_note_content(
            payload,
            markdown_note=report_bundle.markdown_note,
        )
    return format_validation_publish_summary(payload)
