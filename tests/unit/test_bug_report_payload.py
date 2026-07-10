from __future__ import annotations

import json

from shader_health.integrations.bug_report.payload import (
    BUG_REPORT_PAYLOAD_SCHEMA_VERSION,
    BugReportPayload,
    scene_basename,
)
from shader_health.integrations.bug_report.relay_client import build_multipart_body
from shader_health.version import APP_NAME, __version__


def test_scene_basename_normalizes_windows_and_posix_paths():
    assert scene_basename(r"C:\shots\hero.ma") == "hero.ma"
    assert scene_basename("/tmp/hero.ma") == "hero.ma"
    assert scene_basename("") == "unsaved scene"


def test_bug_report_payload_serializes_privacy_safe_fields():
    payload = BugReportPayload(
        title="Validation crash",
        description="Panel freezes after Validate Scene.",
        plugin_version=__version__,
        scene_basename=scene_basename(r"\\farm\assets\hero\hero.ma"),
        app_name=APP_NAME,
        maya_version="2024.2",
        os_user="artist",
        machine_id="workstation-01",
        validation_summary="Health 42/100; 2 critical issues.",
        profile_id="publish_strict",
        health_score=42,
        steps_to_reproduce="Open scene\nValidate Scene",
    )

    data = payload.to_dict()

    assert data["schema_version"] == BUG_REPORT_PAYLOAD_SCHEMA_VERSION
    assert data["title"] == "Validation crash"
    assert data["scene_basename"] == "hero.ma"
    assert data["health_score"] == 42
    assert "\\\\farm" not in json.dumps(data)


def test_build_multipart_body_includes_payload_json_and_jpeg_file():
    payload = BugReportPayload(
        title="Missing textures",
        description="False positives on UDIM tiles.",
        plugin_version="0.5.0",
        scene_basename="hero.ma",
    )
    screenshot = b"\xff\xd8\xff\xe0" + b"fake-jpeg-bytes"

    body, content_type = build_multipart_body(
        fields={"payload": payload.to_json()},
        files={"screenshot": ("screenshot.jpg", "image/jpeg", screenshot)},
        boundary="test-boundary",
    )

    text = body.decode("utf-8", errors="replace")
    assert content_type == "multipart/form-data; boundary=test-boundary"
    assert 'name="payload"' in text
    assert "Missing textures" in text
    assert 'name="screenshot"; filename="screenshot.jpg"' in text
    assert "Content-Type: image/jpeg" in text
    assert b"fake-jpeg-bytes" in body
