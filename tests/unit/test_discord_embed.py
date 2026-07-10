from __future__ import annotations

from shader_health.integrations.discord.embed import (
    ValidationEmbedContext,
    format_validation_embed,
    validation_embed_context_from_mapping,
)
from shader_health.studio_config import (
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


def test_format_validation_embed_includes_profile_overlay_and_issue_fields():
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

    assert embed["title"] == "Shader Health: Publish block"
    assert "42/100" in embed["description"]
    assert embed["color"] == 0xE74C3C
    field_names = [field["name"] for field in embed["fields"]]
    assert field_names == ["Scene", "Profile", "Scope", "Issues"]
    assert embed["fields"][0]["value"] == "hero.ma"
    assert embed["fields"][1]["value"] == "publish_strict+character"
    assert "2 critical" in embed["fields"][3]["value"]


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

    assert embed["title"] == "Shader Health: Publish block, Deadline block"
    assert embed["color"] == 0xC0392B
