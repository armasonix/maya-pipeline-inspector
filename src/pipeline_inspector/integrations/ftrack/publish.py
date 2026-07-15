"""Ftrack validation publish helpers."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pipeline_inspector.integrations.ftrack.client import FtrackClient
from pipeline_inspector.integrations.ftrack.components import attach_html_report_to_task
from pipeline_inspector.integrations.ftrack.config import FtrackConfig
from pipeline_inspector.integrations.ftrack.helpers import (
    ftrack_username_hint,
    is_auth_exception,
    sample_project_names,
)
from pipeline_inspector.integrations.ftrack.queries import (
    list_projects_expression,
    project_by_full_name_expression,
    project_by_name_expression,
    task_by_name_expression,
    task_by_project_id_expression,
    task_by_project_name_expression,
)
from pipeline_inspector.integrations.trackers.base import TrackerPublishResult
from pipeline_inspector.integrations.trackers.publish import (
    ValidationPublishPayload,
    format_tracker_note_content,
    format_validation_publish_summary,
    scene_task_lookup_candidates,
    scene_task_lookup_name,
)
from pipeline_inspector.integrations.trackers.report_bundle import TrackerReportBundle
from pipeline_inspector.studio_config import StudioConfig, resolve_ftrack_config

FtrackClientFactory = Callable[[FtrackConfig], FtrackClient]


def _escape_query_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _task_id_from_payload(payload: ValidationPublishPayload) -> str:
    for key in ("task_id", "ftrack_task_id"):
        task_id = str(payload.metadata.get(key, "") or "").strip()
        if task_id:
            return task_id
    return ""


def _ftrack_username_hint(api_user: str) -> str:
    return ftrack_username_hint(api_user)


def _sample_project_names(rows: list[dict[str, Any]], *, limit: int = 5) -> tuple[str, ...]:
    return sample_project_names(rows, limit=limit)


def _resolve_project_id(client: FtrackClient, project_name: str) -> tuple[str | None, int, str]:
    """Resolve a Ftrack project id from configured project name or full_name."""

    escaped = _escape_query_value(project_name.strip())
    if not escaped:
        return None, 0, ""
    last_status = 200
    last_exception = ""
    for expression in (
        project_by_name_expression(escaped),
        project_by_full_name_expression(escaped),
    ):
        rows, status_code, exception_message = client.query_rows(expression)
        last_status = status_code
        if exception_message:
            last_exception = exception_message
        if status_code != 200:
            continue
        if exception_message:
            if is_auth_exception(exception_message):
                return None, status_code, exception_message
            continue
        if rows:
            project_id = str(rows[0].get("id", "") or "").strip()
            if project_id:
                return project_id, status_code, ""

    rows, status_code, exception_message = client.query_rows(list_projects_expression())
    last_status = status_code
    if exception_message:
        last_exception = exception_message
    if status_code != 200:
        return None, last_status, last_exception
    if exception_message:
        return None, status_code, exception_message

    target = project_name.strip().casefold()
    for row in rows:
        project_id = str(row.get("id", "") or "").strip()
        if not project_id:
            continue
        for field in ("name", "full_name"):
            value = str(row.get(field, "") or "").strip()
            if value.casefold() == target:
                return project_id, status_code, ""

    return None, last_status, last_exception


def _query_tasks(
    client: FtrackClient,
    expression: str,
) -> tuple[list[dict[str, Any]], int]:
    rows, status_code, exception_message = client.query_rows(expression)
    if status_code != 200:
        return [], status_code
    if exception_message:
        return [], status_code
    return rows, status_code


def resolve_task_id(
    client: FtrackClient,
    config: FtrackConfig,
    payload: ValidationPublishPayload,
) -> str | None:
    """Resolve the Ftrack task id from payload metadata or project/scene lookup."""

    explicit_task_id = _task_id_from_payload(payload)
    if explicit_task_id:
        return explicit_task_id

    project_id, project_status, project_exception = _resolve_project_id(client, config.project)
    project = _escape_query_value(config.project)
    expressions: list[str] = []
    for lookup_name in scene_task_lookup_candidates(payload.scene_name):
        scene_name = _escape_query_value(lookup_name)
        if project_id:
            expressions.append(
                task_by_project_id_expression(
                    project_id=project_id,
                    task_name=scene_name,
                )
            )
        expressions.append(
            task_by_project_name_expression(
                project_name=project,
                task_name=scene_name,
            )
        )
        expressions.append(task_by_name_expression(scene_name))

    seen: set[str] = set()
    for expression in expressions:
        if expression in seen:
            continue
        seen.add(expression)
        tasks, _status_code = _query_tasks(client, expression)
        for task in tasks:
            if project_id:
                task_project_id = str(task.get("project_id", "") or "").strip()
                if task_project_id and task_project_id != project_id:
                    continue
            task_id = str(task.get("id", "") or "").strip()
            if task_id:
                return task_id

    return None


def publish_validation_summary(
    studio_config: StudioConfig | None,
    payload: ValidationPublishPayload,
    *,
    report_bundle: TrackerReportBundle | None = None,
    client_factory: FtrackClientFactory | None = None,
) -> TrackerPublishResult:
    """Publish a validation summary as an Ftrack task note."""

    config = resolve_ftrack_config(studio_config)
    if config is None:
        return TrackerPublishResult(published=False, skipped_reason="disabled")

    factory = client_factory or FtrackClient
    client = factory(config)
    project_id, project_status, project_exception = _resolve_project_id(client, config.project)
    if project_status != 200:
        return TrackerPublishResult(
            published=False,
            error_message=f"ftrack_api_error: project lookup HTTP {project_status}",
        )
    if project_exception:
        if is_auth_exception(project_exception):
            return TrackerPublishResult(
                published=False,
                error_message=(
                    f"ftrack_auth_error: {project_exception}."
                    f"{_ftrack_username_hint(config.api_user)}"
                ),
            )
        return TrackerPublishResult(
            published=False,
            error_message=f"ftrack_query_error: {project_exception}.",
        )
    if project_id is None:
        rows, _, list_exception = client.query_rows(list_projects_expression())
        if list_exception:
            if is_auth_exception(list_exception):
                return TrackerPublishResult(
                    published=False,
                    error_message=(
                        f"ftrack_auth_error: {list_exception}."
                        f"{_ftrack_username_hint(config.api_user)}"
                    ),
                )
            return TrackerPublishResult(
                published=False,
                error_message=f"ftrack_query_error: {list_exception}.",
            )
        sample_names = _sample_project_names(rows)
        if not rows:
            hint = (
                " Ftrack returned zero visible projects for this API user."
                " If you use a global API key, grant it access to private projects"
                " or use your personal API key."
                f"{_ftrack_username_hint(config.api_user)}"
            )
        elif sample_names:
            hint = f" Visible Ftrack projects: {', '.join(sample_names)}."
        else:
            hint = _ftrack_username_hint(config.api_user)
        return TrackerPublishResult(
            published=False,
            skipped_reason=(
                f"project_not_found: no Ftrack project named '{config.project}'. "
                "Check Settings → Connectors → Ftrack → Project."
                f"{hint}"
            ),
        )

    task_id = resolve_task_id(client, config, payload)
    if task_id is None:
        stem = scene_task_lookup_name(payload.scene_name)
        lookup_hint = (
            f"'{stem}'"
            if stem and stem != payload.scene_name
            else f"'{payload.scene_name}'"
        )
        return TrackerPublishResult(
            published=False,
            skipped_reason=(
                "task_not_found: no Task named "
                f"{lookup_hint} in Ftrack project '{config.project}'. "
                "Task name should match the scene name without .ma/.mb, "
                "or pass task_id metadata."
            ),
        )

    note_result = client.create_task_note(
        task_id=task_id,
        content=_tracker_note_content(payload, report_bundle),
    )
    if note_result.entity is None:
        if note_result.exception_message:
            return TrackerPublishResult(
                published=False,
                error_message=f"ftrack_api_error: {note_result.exception_message}",
            )
        return TrackerPublishResult(
            published=False,
            error_message=(
                f"ftrack_api_error: note create failed (HTTP {note_result.status_code})."
            ),
        )

    note = note_result.entity
    note_id = str(note.get("id", "") or "").strip()
    metadata: dict[str, str] = {}
    if note_id:
        metadata["note_id"] = note_id

    if report_bundle is not None and report_bundle.html_report_path:
        component_id, attach_error = attach_html_report_to_task(
            client,
            task_id=task_id,
            file_path=report_bundle.html_report_path,
            filename=report_bundle.attachment_filename,
        )
        if component_id:
            metadata["component_id"] = component_id
        elif attach_error:
            metadata["attachment_error"] = attach_error

    status_result = client.update_task_status(
        task_id=task_id,
        status_name=config.task_status_name,
    )
    if not status_result.exception_message:
        metadata["task_status"] = config.task_status_name

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

    from pipeline_inspector.integrations.trackers.publish import validation_publish_payload_from_run
    from pipeline_inspector.integrations.trackers.report_bundle import (
        build_tracker_report_bundle_from_run,
    )

    report_bundle = build_tracker_report_bundle_from_run(result, report_path=report_path)
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
        )
    return format_validation_publish_summary(payload)
