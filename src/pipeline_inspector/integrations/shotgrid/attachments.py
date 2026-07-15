"""ShotGrid attachment helpers for HTML report uploads."""
from __future__ import annotations

import mimetypes
from pathlib import Path

from pipeline_inspector.integrations.shotgrid.client import ShotGridClient


def attach_html_report_to_note(
    client: ShotGridClient,
    *,
    note_id: int,
    file_path: str,
    filename: str,
) -> tuple[str, str]:
    """Upload an HTML report and attach it to a ShotGrid note.

    Returns ``(attachment_id, error_message)``. ``attachment_id`` is empty on failure.
    """

    normalized_note_id = int(note_id)
    source_path = Path(file_path)
    if normalized_note_id <= 0 or not source_path.is_file():
        return "", "missing_note_or_report_file"

    mime_type = mimetypes.guess_type(filename)[0] or "text/html"
    response = client.upload_note_attachment(
        note_id=normalized_note_id,
        file_bytes=source_path.read_bytes(),
        filename=filename,
        mime_type=mime_type,
    )
    if response.status_code not in (200, 201):
        return "", f"shotgrid_upload_failed_http_{response.status_code}"
    attachment_id = _attachment_id_from_upload_response(response.json_data)
    return attachment_id or "attached", ""


def _attachment_id_from_upload_response(json_data: object) -> str:
    if not isinstance(json_data, dict):
        return ""
    data = json_data.get("data")
    if isinstance(data, dict):
        raw_id = data.get("id")
        if raw_id is not None:
            return str(raw_id)
    return ""
