"""Ftrack component upload helpers for HTML report attachments."""
from __future__ import annotations

import base64
import hashlib
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from pipeline_inspector.integrations.ftrack.client import FtrackClient, _extract_batch_operation

BinaryTransport = Callable[[str, bytes, Mapping[str, str], float], int]


def attach_html_report_to_note(
    client: FtrackClient,
    *,
    note_id: str,
    file_path: str,
    filename: str,
    binary_transport: BinaryTransport | None = None,
) -> tuple[str, str]:
    """Attach an HTML report to a Ftrack note via NoteComponent.

    Returns ``(component_id, error_message)``. ``component_id`` is empty on failure.
    """

    normalized_note_id = str(note_id or "").strip()
    source_path = Path(file_path)
    if not normalized_note_id or not source_path.is_file():
        return "", "missing_note_or_report_file"

    location_id = _server_location_id(client)
    if not location_id:
        return "", "ftrack_server_location_not_found"

    file_bytes = source_path.read_bytes()
    component_id = str(uuid.uuid4())
    create_response = client.request(
        [
            {
                "action": "create",
                "entity_type": "Component",
                "entity_key": [component_id],
                "entity_data": {
                    "__entity_type__": "Component",
                    "id": component_id,
                    "name": filename,
                    "file_type": source_path.suffix.lstrip(".") or "html",
                    "size": len(file_bytes),
                },
            }
        ]
    )
    entity, exception_message = _extract_batch_operation(create_response.json_data)
    if create_response.status_code != 200 or exception_message or entity is None:
        message = exception_message or f"component_create_failed_http_{create_response.status_code}"
        return "", message

    metadata_response = client.request(
        [
            {
                "action": "get_upload_metadata",
                "component_id": component_id,
                "file_name": filename,
                "file_size": len(file_bytes),
                "checksum": _content_md5(file_bytes),
            }
        ]
    )
    upload_meta, upload_error = _extract_upload_metadata(metadata_response.json_data)
    if metadata_response.status_code != 200 or upload_error or upload_meta is None:
        message = upload_error or f"upload_metadata_failed_http_{metadata_response.status_code}"
        return "", message

    upload_url = str(upload_meta.get("url", "") or "").strip()
    if not upload_url:
        return "", "upload_metadata_missing_url"

    headers = {
        str(key): str(value)
        for key, value in upload_meta.get("headers", {}).items()
        if str(key).strip()
    }
    if "Content-MD5" not in headers:
        headers["Content-MD5"] = _content_md5(file_bytes)
    if "Content-Type" not in headers:
        headers["Content-Type"] = "text/html"
    if "Content-Disposition" not in headers:
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'

    transport = binary_transport or _default_binary_transport
    upload_status = transport(upload_url, file_bytes, headers, client.config.timeout_seconds)
    if upload_status != 200:
        return "", f"component_upload_failed_http_{upload_status}"

    finalize_response = client.request(
        [
            {
                "action": "create",
                "entity_type": "ComponentLocation",
                "entity_data": {
                    "__entity_type__": "ComponentLocation",
                    "component_id": component_id,
                    "location_id": location_id,
                },
            }
        ]
    )
    finalize_entity, finalize_error = _extract_batch_operation(finalize_response.json_data)
    if finalize_response.status_code != 200 or finalize_error or finalize_entity is None:
        message = (
            finalize_error
            or f"component_location_failed_http_{finalize_response.status_code}"
        )
        return "", message

    note_component_id = str(uuid.uuid4())
    link_response = client.request(
        [
            {
                "action": "create",
                "entity_type": "NoteComponent",
                "entity_key": [note_component_id],
                "entity_data": {
                    "__entity_type__": "NoteComponent",
                    "id": note_component_id,
                    "component_id": component_id,
                    "note_id": normalized_note_id,
                },
            }
        ]
    )
    link_entity, link_error = _extract_batch_operation(link_response.json_data)
    if link_response.status_code != 200 or link_error or link_entity is None:
        message = link_error or f"note_component_failed_http_{link_response.status_code}"
        return "", message

    return component_id, ""


def _server_location_id(client: FtrackClient) -> str:
    rows = client.query('select id from Location where name is "ftrack.server"')
    if not rows:
        return ""
    return str(rows[0].get("id", "") or "").strip()


def _content_md5(file_bytes: bytes) -> str:
    digest = base64.b64encode(hashlib.md5(file_bytes).digest()).decode("ascii")
    return digest.rstrip("\n")


def _default_binary_transport(
    url: str,
    body: bytes,
    headers: Mapping[str, str],
    timeout: float,
) -> int:
    import urllib.error
    import urllib.request

    request = urllib.request.Request(
        url,
        data=body,
        headers=dict(headers),
        method="PUT",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)


def _extract_upload_metadata(json_data: Any) -> tuple[dict[str, Any] | None, str]:
    if not isinstance(json_data, list) or not json_data:
        return None, "empty_upload_metadata"
    first = json_data[0]
    if not isinstance(first, dict):
        return None, "invalid_upload_metadata"
    _, exception_message = _extract_batch_operation(json_data)
    if exception_message:
        return None, exception_message

    for candidate in (
        first,
        first.get("data"),
        first.get("metadata"),
        first.get("upload_metadata"),
    ):
        if isinstance(candidate, dict) and str(candidate.get("url", "") or "").strip():
            return candidate, ""
    return None, exception_message or "missing_upload_metadata"

