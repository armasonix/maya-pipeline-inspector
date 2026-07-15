"""Cerebro validation publish helpers."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pipeline_inspector.integrations.cerebro.adapter import (
    probe_cerebro_runtime,
)
from pipeline_inspector.integrations.cerebro.client import (
    CerebroClient,
    cerebro_dependency_error_message,
)
from pipeline_inspector.integrations.cerebro.config import CerebroConfig
from pipeline_inspector.integrations.trackers.base import TrackerPublishResult
from pipeline_inspector.integrations.trackers.publish import (
    ValidationPublishPayload,
    format_tracker_note_content,
    format_validation_publish_summary,
    scene_task_lookup_candidates,
    scene_task_lookup_name,
)
from pipeline_inspector.integrations.trackers.report_bundle import TrackerReportBundle
from pipeline_inspector.studio_config import StudioConfig, resolve_cerebro_config

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


def build_task_url(project: str, task_name: str) -> str:
    """Build a Cerebro task locator from project and task name."""

    project_part = project.strip().strip("/")
    task_part = task_name.strip().strip("/")
    if not project_part or not task_part:
        return ""
    return f"/{project_part}/{task_part}"


def task_url_candidates(
    config: CerebroConfig,
    payload: ValidationPublishPayload,
) -> tuple[str, ...]:
    """Return Cerebro task locator paths to try for a validation payload."""

    explicit_url = _task_url_from_payload(payload)
    if explicit_url:
        return (explicit_url,)

    candidates: list[str] = []
    seen: set[str] = set()
    project_part = config.project.strip().strip("/")
    for lookup_name in scene_task_lookup_candidates(payload.scene_name):
        task_part = lookup_name.strip().strip("/")
        if not task_part:
            continue
        for task_url in (
            f"/{project_part}/{task_part}",
            f"/{project_part}/{task_part}/",
        ):
            if task_url not in seen:
                seen.add(task_url)
                candidates.append(task_url)
    return tuple(candidates)


def resolve_task_id(
    client: CerebroClient,
    config: CerebroConfig,
    payload: ValidationPublishPayload,
) -> int | None:
    """Resolve the Cerebro task id from payload metadata or project/scene lookup."""

    explicit_task_id = _task_id_from_payload(payload)
    if explicit_task_id is not None:
        return explicit_task_id

    for task_url in task_url_candidates(config, payload):
        task_id = client.resolve_task_id(task_url)
        if task_id is not None:
            return task_id

    for lookup_name in scene_task_lookup_candidates(payload.scene_name):
        task_id = client.resolve_task_in_project(config.project, lookup_name)
        if task_id is not None:
            return task_id

    return None


def resolve_task_id_for_publish(
    client: CerebroClient,
    config: CerebroConfig,
    payload: ValidationPublishPayload,
) -> int | None:
    """Resolve a Cerebro task id using fast URL lookups only.

    Publish avoids ``resolve_task_in_project`` because it can walk large task
    trees and block the Maya UI for a long time.
    """

    explicit_task_id = _task_id_from_payload(payload)
    if explicit_task_id is not None:
        return explicit_task_id

    for task_url in task_url_candidates(config, payload):
        task_id = client.resolve_task_id(task_url)
        if task_id is not None:
            return task_id

    return None


def publish_validation_summary(
    studio_config: StudioConfig | None,
    payload: ValidationPublishPayload,
    *,
    report_bundle: TrackerReportBundle | None = None,
    client_factory: CerebroClientFactory | None = None,
) -> TrackerPublishResult:
    """Publish a validation summary as a Cerebro task note."""

    config = resolve_cerebro_config(studio_config)
    if config is None:
        return TrackerPublishResult(published=False, skipped_reason="disabled")

    if client_factory is None:
        _module, import_error = probe_cerebro_runtime(
            service_tools_path=config.service_tools_path,
            server_url=config.normalized_server_url,
        )
        if _module is None:
            return TrackerPublishResult(
                published=False,
                error_message=import_error or cerebro_dependency_error_message(),
            )

    factory = client_factory or CerebroClient
    client = factory(config)
    # region agent log
    import json
    import time
    from pathlib import Path as LogPath

    _publish_started = time.time()
    try:
        with (LogPath(__file__).resolve().parents[3] / "debug-618f4f.log").open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    {
                        "sessionId": "618f4f",
                        "runId": "pre-fix",
                        "hypothesisId": "H3",
                        "location": "cerebro.publish_validation_summary",
                        "message": "before_ping",
                        "data": {
                            "timeout_seconds": config.timeout_seconds,
                            "project": config.project,
                            "scene_name": payload.scene_name,
                        },
                        "timestamp": int(time.time() * 1000),
                    }
                )
                + "\n"
            )
    except (OSError, TypeError, ValueError):
        pass
    # endregion
    if not client.ping():
        if client.last_error == "py_cerebro_missing":
            _module, import_error = probe_cerebro_runtime(
                service_tools_path=config.service_tools_path,
                server_url=config.normalized_server_url,
            )
            return TrackerPublishResult(
                published=False,
                error_message=import_error or cerebro_dependency_error_message(),
            )
        if "Invalid credentials" in (client.last_error or ""):
            return TrackerPublishResult(
                published=False,
                error_message=f"cerebro_auth_error: {client.last_error}",
            )
        return TrackerPublishResult(
            published=False,
            error_message=f"cerebro_connect_error: {client.last_error or 'connect_failed'}",
        )

    # region agent log
    try:
        with (LogPath(__file__).resolve().parents[3] / "debug-618f4f.log").open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    {
                        "sessionId": "618f4f",
                        "runId": "pre-fix",
                        "hypothesisId": "H3",
                        "location": "cerebro.publish_validation_summary",
                        "message": "after_ping",
                        "data": {
                            "elapsed_ms": int((time.time() - _publish_started) * 1000),
                        },
                        "timestamp": int(time.time() * 1000),
                    }
                )
                + "\n"
            )
    except (OSError, TypeError, ValueError):
        pass
    # endregion

    _resolve_started = time.time()
    task_id = resolve_task_id_for_publish(client, config, payload)
    # region agent log
    try:
        with (LogPath(__file__).resolve().parents[3] / "debug-618f4f.log").open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    {
                        "sessionId": "618f4f",
                        "runId": "pre-fix",
                        "hypothesisId": "H4",
                        "location": "cerebro.publish_validation_summary",
                        "message": "after_resolve_task_id",
                        "data": {
                            "elapsed_ms": int((time.time() - _resolve_started) * 1000),
                            "task_id": task_id,
                            "candidate_count": len(task_url_candidates(config, payload)),
                        },
                        "timestamp": int(time.time() * 1000),
                    }
                )
                + "\n"
            )
    except (OSError, TypeError, ValueError):
        pass
    # endregion
    if task_id is None:
        tried = ", ".join(task_url_candidates(config, payload)) or "(none)"
        if client.last_error and client.last_error not in ("", "task_not_found"):
            return TrackerPublishResult(
                published=False,
                error_message=f"cerebro_connect_error: {client.last_error}",
            )
        return TrackerPublishResult(
            published=False,
            skipped_reason="task_not_found",
            error_message=(
                "Create a Cerebro task named like the scene stem "
                f"('{scene_task_lookup_name(payload.scene_name)}') under project "
                f"'{config.project}'. Tried: {tried}."
            ),
        )

    note_content = _tracker_note_content(payload, report_bundle)
    # region agent log
    try:
        with (LogPath(__file__).resolve().parents[3] / "debug-618f4f.log").open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    {
                        "sessionId": "618f4f",
                        "runId": "pre-fix",
                        "hypothesisId": "H5",
                        "location": "cerebro.publish_validation_summary",
                        "message": "before_create_task_note",
                        "data": {
                            "task_id": task_id,
                            "note_content_len": len(note_content),
                        },
                        "timestamp": int(time.time() * 1000),
                    }
                )
                + "\n"
            )
    except (OSError, TypeError, ValueError):
        pass
    # endregion
    note = client.create_task_note(
        task_id=task_id,
        content=note_content,
    )
    if note is None:
        if client.last_error == "task_definition_missing":
            return TrackerPublishResult(
                published=False,
                error_message="cerebro_api_error: task has no definition message for notes",
            )
        return TrackerPublishResult(
            published=False,
            error_message=f"cerebro_api_error: {client.last_error or 'note_create_failed'}",
        )

    metadata: dict[str, str] = {"task_id": str(task_id)}
    note_id = str(note.get("id", "") or "").strip()
    if note_id:
        metadata["note_id"] = note_id

    if config.set_pause_status_on_publish and config.pause_status_name.strip():
        status_set = client.set_task_status(task_id, config.pause_status_name)
        if status_set:
            metadata["task_status"] = config.pause_status_name
        elif client.last_error:
            metadata["task_status_error"] = client.last_error

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

    from pipeline_inspector.integrations.trackers.publish import validation_publish_payload_from_run
    from pipeline_inspector.integrations.trackers.report_bundle import (
        build_tracker_report_bundle_from_run,
    )

    report_bundle = build_tracker_report_bundle_from_run(
        result,
        report_path=report_path,
        include_html=False,
    )
    payload = validation_publish_payload_from_run(
        result,
        report_path=report_bundle.html_report_path or report_path,
    )
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
            include_report_path_reference=bool(payload.report_path),
        )
    return format_validation_publish_summary(payload)
