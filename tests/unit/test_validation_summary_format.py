from __future__ import annotations

from shader_health.integrations.messaging.validation_summary import (
    CHAT_SEPARATOR,
    FTRACK_CRITICAL_EMOJI,
    FTRACK_HEADLINE,
    render_validation_summary_text,
    validation_summary_from_fields,
)


def _sample_data(**overrides: object):
    defaults = {
        "scene_name": "hero.ma",
        "profile_label": "publish_strict+character",
        "scope_label": "Scene",
        "health_score": 42,
        "critical_count": 2,
        "error_count": 1,
        "warning_count": 3,
        "info_count": 0,
        "block_publish": True,
        "block_deadline": False,
        "validated_at_utc": "2026-07-10T12:00:00Z",
        "event_labels": "Publish block",
    }
    defaults.update(overrides)
    return validation_summary_from_fields(**defaults)


def test_chat_layout_matches_discord_slack_template():
    message = render_validation_summary_text(_sample_data(), platform="chat")

    assert message.startswith("🔍 Health Validation · Publish block")
    assert "🔴 Health score: 42/100" in message
    assert "📁 Scene: hero.ma" in message
    assert "🎬 Profile: publish_strict+character" in message
    assert "🎯 Scope: Scene" in message
    assert CHAT_SEPARATOR in message
    assert "📊 Actual Issue list:" in message
    assert "🚨 2 critical" in message
    assert "🚫 Current Blocks:" in message
    assert "- Publish block" in message


def test_ftrack_layout_matches_note_template():
    message = render_validation_summary_text(_sample_data(), platform="ftrack")

    assert message.startswith(FTRACK_HEADLINE)
    assert "Scene: hero.ma" in message
    assert "Profile: publish_strict+character" in message
    assert "Scope: Scene" in message
    assert "Health score: 42/100" in message
    assert f"2 critical {FTRACK_CRITICAL_EMOJI}" in message
    assert "1 error ❌" in message
    assert "3 warning ⚠️" in message
    assert "0 info ℹ️" in message
    assert "Blocks: Publish block" in message
    assert "Validated: 2026-07-10T12:00:00Z" in message


def test_ftrack_summary_avoids_unsupported_supplementary_plane_emoji():
    message = render_validation_summary_text(_sample_data(), platform="ftrack")

    assert "🔍" not in message
    assert "📁" not in message
    assert "🚨" not in message


def test_health_emoji_thresholds():
    low = render_validation_summary_text(
        _sample_data(health_score=30),
        platform="chat",
    )
    mid = render_validation_summary_text(
        _sample_data(health_score=65),
        platform="chat",
    )
    high = render_validation_summary_text(
        _sample_data(health_score=90),
        platform="chat",
    )

    assert "🔴 Health score: 30/100" in low
    assert "🟡 Health score: 65/100" in mid
    assert "🟢 Health score: 90/100" in high
