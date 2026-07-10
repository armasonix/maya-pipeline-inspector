"""Bug report relay payload schema."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BUG_REPORT_PAYLOAD_SCHEMA_VERSION = "1.0"


def scene_basename(scene_path: str) -> str:
    """Return a privacy-safe scene filename from Maya/Windows or POSIX paths."""

    if not scene_path:
        return "unsaved scene"
    normalized = scene_path.replace("\\", "/").rstrip("/")
    name = Path(normalized).name
    return name or "unsaved scene"


@dataclass(frozen=True)
class BugReportPayload:
    """Normalized bug report payload sent to the studio relay."""

    title: str
    description: str
    plugin_version: str
    scene_basename: str
    schema_version: str = BUG_REPORT_PAYLOAD_SCHEMA_VERSION
    app_name: str = ""
    maya_version: str = ""
    os_user: str = ""
    machine_id: str = ""
    validation_summary: str = ""
    profile_id: str = ""
    health_score: int | None = None
    steps_to_reproduce: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize the payload for multipart relay submission."""

        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "title": self.title,
            "description": self.description,
            "plugin_version": self.plugin_version,
            "scene_basename": self.scene_basename,
            "app_name": self.app_name,
            "maya_version": self.maya_version,
            "os_user": self.os_user,
            "machine_id": self.machine_id,
            "validation_summary": self.validation_summary,
            "profile_id": self.profile_id,
            "steps_to_reproduce": self.steps_to_reproduce,
        }
        if self.health_score is not None:
            payload["health_score"] = int(self.health_score)
        return payload

    def to_json(self) -> str:
        """Return the JSON document posted as the multipart payload field."""

        return json.dumps(self.to_dict(), ensure_ascii=False)
