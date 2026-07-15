from __future__ import annotations

from pipeline_inspector.integrations.trackers.capabilities import (
    TRACKER_CONNECTOR_CAPABILITIES,
    tracker_capabilities,
)
from pipeline_inspector.integrations.trackers.publish import (
    ValidationPublishPayload,
    format_tracker_note_content,
)


def _payload(**overrides: object) -> ValidationPublishPayload:
    defaults = {
        "scene_name": "hero.ma",
        "scene_path": r"C:\shots\hero.ma",
        "scan_scope": "scene",
        "profile_id": "publish_strict",
        "asset_class_id": "",
        "health_score": 42,
        "critical_count": 1,
        "error_count": 0,
        "warning_count": 0,
        "info_count": 0,
        "block_publish": True,
        "block_deadline": False,
        "validated_at_utc": "2026-07-10T12:00:00Z",
    }
    defaults.update(overrides)
    return ValidationPublishPayload(**defaults)


def test_format_tracker_note_content_prefers_markdown():
    note = format_tracker_note_content(
        _payload(),
        markdown_note="# Report\n\n- issue",
    )

    assert note.startswith("# Report")
    assert "Health Validation Result" not in note


def test_format_tracker_note_content_appends_report_path_reference():
    note = format_tracker_note_content(
        _payload(report_path=r"C:\temp\report.html"),
        markdown_note="# Report",
    )

    assert "**Attached report path:** `C:\\temp\\report.html`" in note


def test_tracker_capabilities_describe_attachment_support():
    ftrack = tracker_capabilities("ftrack")
    shotgrid = tracker_capabilities("shotgrid")
    cerebro = tracker_capabilities("cerebro")

    assert ftrack is not None and ftrack.supports_html_attachment is True
    assert shotgrid is not None and shotgrid.supports_html_attachment is True
    assert cerebro is not None and cerebro.supports_html_attachment is False
    assert set(TRACKER_CONNECTOR_CAPABILITIES) == {"ftrack", "shotgrid", "cerebro"}
