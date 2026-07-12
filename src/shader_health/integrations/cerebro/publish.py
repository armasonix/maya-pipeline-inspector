"""Cerebro validation publish helpers."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from shader_health.integrations.cerebro.adapter import (
    probe_cerebro_runtime,
)
from shader_health.integrations.cerebro.client import (
    CerebroClient,
    cerebro_dependency_error_message,
)
from shader_health.integrations.cerebro.config import CerebroConfig
from shader_health.integrations.trackers.base import TrackerPublishResult
from shader_health.integrations.trackers.publish import (
    ValidationPublishPayload,
    format_validation_publish_summary,
    scene_task_lookup_candidates,
    scene_task_lookup_name,
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

    task_id = resolve_task_id(client, config, payload)
    if task_id is None:
        tried = ", ".join(task_url_candidates(config, payload)) or "(none)"
        root_tasks = client.list_root_task_names()
        visible_projects = client.list_visible_project_names()
        root_hint = ""
        if visible_projects:
            preview = ", ".join(visible_projects[:8])
            root_hint = f" Visible Cerebro projects: {preview}."
        elif root_tasks:
            preview = ", ".join(root_tasks[:8])
            root_hint = f" Visible Cerebro root tasks: {preview}."
        else:
            root_hint = (
                " API user sees no projects/tasks — in Cerebro admin grant "
                f"'{config.normalized_api_user}' visibility on project "
                f"'{config.project}'."
            )
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
                f"'{config.project}'. Tried: {tried}.{root_hint}"
            ),
        )

    note = client.create_task_note(
        task_id=task_id,
        content=format_validation_publish_summary(payload),
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

    from shader_health.integrations.trackers.publish import validation_publish_payload_from_run

    payload = validation_publish_payload_from_run(result, report_path=report_path)
    return publish_validation_summary(
        studio_config,
        payload,
        client_factory=client_factory,
    )
