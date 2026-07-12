from __future__ import annotations

from pipeline_inspector.integrations.discord.embed import (
    ValidationEmbedContext,
    format_validation_embed,
    validation_embed_context_from_mapping,
)
from pipeline_inspector.studio_config import (
    DISCORD_NOTIFY_EVENT_BLOCK_DEADLINE,
    DISCORD_NOTIFY_EVENT_BLOCK_PUBLISH,
)


def test_validation_embed_context_from_mapping_reads_fields():
    context = validation_embed_context_from_mapping(
        ValidationEmbedContext(
            scene_name="hero.ma",
            scan_scope="selection",
            profile_id="lookdev",
            asset_class_id="character",
            health_score=61,
            critical_count=1,
            error_count=2,
            warning_count=4,
            info_count=1,
            block_publish=True,
            block_deadline=True,
        )
    )

    assert context.scene_name == "hero.ma"
    assert context.profile_id == "lookdev"
    assert context.health_score == 61


def test_format_validation_embed_uses_unified_chat_layout():
    embed = format_validation_embed(
        ValidationEmbedContext(
            scene_name="hero.ma",
            scan_scope="scene",
            profile_id="publish_strict",
            asset_class_id="character",
            health_score=42,
            critical_count=2,
            error_count=1,
            warning_count=3,
            info_count=0,
            block_publish=True,
            block_deadline=False,
        ),
        matched_events=(DISCORD_NOTIFY_EVENT_BLOCK_PUBLISH,),
    )

    assert embed["title"] == "🔍 Health Validation · Publish block"
    assert "🔴 Health score: 42/100" in embed["description"]
    assert "📊 Actual Issue list:" in embed["description"]
    assert "- Publish block" in embed["description"]
    assert embed["color"] == 0xE74C3C
    assert "fields" not in embed


def test_format_validation_embed_uses_mixed_color_for_both_block_events():
    embed = format_validation_embed(
        ValidationEmbedContext(
            scene_name="hero.ma",
            scan_scope="scene",
            profile_id="lookdev",
            asset_class_id="",
            health_score=10,
            critical_count=1,
            error_count=0,
            warning_count=0,
            info_count=0,
            block_publish=True,
            block_deadline=True,
        ),
        matched_events=(
            DISCORD_NOTIFY_EVENT_BLOCK_PUBLISH,
            DISCORD_NOTIFY_EVENT_BLOCK_DEADLINE,
        ),
    )

    assert embed["title"] == "🔍 Health Validation · Publish block, Deadline block"
    assert "- Publish block" in embed["description"]
    assert "- Deadline block" in embed["description"]
    assert embed["color"] == 0xC0392B
