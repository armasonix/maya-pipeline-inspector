"""Per-connector tracker publish capabilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

NoteFormat = Literal["markdown", "plain"]


@dataclass(frozen=True)
class TrackerConnectorCapabilities:
    """Describe optional tracker publish features supported by a connector."""

    supports_html_attachment: bool
    supports_set_status: bool
    supports_create_task: bool
    note_format: NoteFormat
    attachment_fallback: str


TRACKER_CONNECTOR_CAPABILITIES: dict[str, TrackerConnectorCapabilities] = {
    "ftrack": TrackerConnectorCapabilities(
        supports_html_attachment=True,
        supports_set_status=True,
        supports_create_task=False,
        note_format="markdown",
        attachment_fallback="Markdown note only when HTML upload fails.",
    ),
    "shotgrid": TrackerConnectorCapabilities(
        supports_html_attachment=True,
        supports_set_status=False,
        supports_create_task=False,
        note_format="markdown",
        attachment_fallback="Markdown note only when HTML upload fails.",
    ),
    "cerebro": TrackerConnectorCapabilities(
        supports_html_attachment=False,
        supports_set_status=True,
        supports_create_task=False,
        note_format="markdown",
        attachment_fallback="Markdown note with optional local report path reference.",
    ),
}


def tracker_capabilities(tracker_id: str) -> TrackerConnectorCapabilities | None:
    """Return publish capabilities for a tracker connector id."""

    return TRACKER_CONNECTOR_CAPABILITIES.get(tracker_id)
