from __future__ import annotations

from pipeline_inspector.integrations.slack.blocks import (
    ValidationBlocksContext,
    build_optional_report_link,
    format_validation_blocks,
    route_matched_events,
    webhook_url_for_event,
)
from pipeline_inspector.studio_config import (
    SLACK_NOTIFY_EVENT_BLOCK_DEADLINE,
    SLACK_NOTIFY_EVENT_BLOCK_PUBLISH,
    SlackConnectorSettings,
)


def _context(**overrides: object) -> ValidationBlocksContext:
    defaults = {
        "scene_name": "hero.ma",
        "scene_path": r"C:\shots\hero.ma",
        "scan_scope": "scene",
        "profile_id": "publish_strict",
        "asset_class_id": "",
        "health_score": 42,
        "critical_count": 2,
        "error_count": 1,
        "warning_count": 3,
        "info_count": 0,
        "block_publish": True,
        "block_deadline": False,
    }
    defaults.update(overrides)
    return ValidationBlocksContext(**defaults)


def test_webhook_url_for_event_routes_publish_and_deadline_separately():
    settings = SlackConnectorSettings(
        publish_webhook_url="https://hooks.slack.com/publish",
        deadline_webhook_url="https://hooks.slack.com/deadline",
    )

    assert webhook_url_for_event(settings, SLACK_NOTIFY_EVENT_BLOCK_PUBLISH) == (
        "https://hooks.slack.com/publish"
    )
    assert webhook_url_for_event(settings, SLACK_NOTIFY_EVENT_BLOCK_DEADLINE) == (
        "https://hooks.slack.com/deadline"
    )


def test_route_matched_events_returns_only_configured_webhooks():
    settings = SlackConnectorSettings(
        publish_webhook_url="https://hooks.slack.com/publish",
        deadline_webhook_url="",
        notify_on=("block_publish", "block_deadline"),
    )

    routes = route_matched_events(
        settings,
        (SLACK_NOTIFY_EVENT_BLOCK_PUBLISH, SLACK_NOTIFY_EVENT_BLOCK_DEADLINE),
    )

    assert routes == ((SLACK_NOTIFY_EVENT_BLOCK_PUBLISH, "https://hooks.slack.com/publish"),)


def test_build_optional_report_link_uses_render_root_and_scene_stem():
    link = build_optional_report_link(
        scene_path=r"\\farm\assets\hero\hero.ma",
        render_root=r"\\farm\render",
    )

    assert link is not None
    assert link.replace("\\", "/").endswith(
        "/reports/validation/hero_pipeline_inspector_report.json"
    )


def test_format_validation_blocks_uses_unified_chat_layout():
    payload = format_validation_blocks(
        _context(asset_class_id="character"),
        matched_events=(SLACK_NOTIFY_EVENT_BLOCK_PUBLISH,),
        report_link=r"\\farm\render\hero_pipeline_inspector_report.json",
    )

    summary_text = payload["blocks"][0]["text"]["text"]
    assert summary_text.startswith("🔍 Health Validation · Publish block")
    assert "📊 Actual Issue list:" in summary_text
    assert "publish_strict+character" in summary_text
    assert "- Publish block" in summary_text
    assert "hero_pipeline_inspector_report.json" in payload["blocks"][1]["text"]["text"]


def test_format_validation_blocks_includes_thread_ts_when_provided():
    payload = format_validation_blocks(
        _context(),
        matched_events=(SLACK_NOTIFY_EVENT_BLOCK_PUBLISH,),
    )

    assert "thread_ts" not in payload

    threaded = format_validation_blocks(
        _context(),
        matched_events=(SLACK_NOTIFY_EVENT_BLOCK_PUBLISH,),
        thread_ts="1710000000.000100",
    )

    assert threaded["thread_ts"] == "1710000000.000100"


def test_format_validation_blocks_includes_reporter_line_at_top():
    payload = format_validation_blocks(
        _context(),
        matched_events=(SLACK_NOTIFY_EVENT_BLOCK_PUBLISH,),
        reporter_line="John Doe (Technical Artist)",
    )

    assert payload["blocks"][0]["text"]["text"] == "*From:* John Doe (Technical Artist)"
    assert payload["blocks"][1]["text"]["text"].startswith("🔍 Health Validation")
