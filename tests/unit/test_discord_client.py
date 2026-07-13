from __future__ import annotations

import json

from pipeline_inspector.integrations.discord import DiscordClient, DiscordConfig, DiscordResponse
from pipeline_inspector.integrations.discord.client import HttpRequest


def test_discord_client_ping_returns_true_for_no_content_response():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> DiscordResponse:
        captured.append(request)
        _ = timeout
        return DiscordResponse(status_code=204, body="", json_data=None)

    client = DiscordClient(
        DiscordConfig(webhook_url="https://discord.com/api/webhooks/1/token"),
        transport=transport,
    )

    assert client.ping() is True
    assert captured[0].method == "POST"
    assert captured[0].url == "https://discord.com/api/webhooks/1/token"
    assert captured[0].headers["User-Agent"].startswith("PipelineInspector/")
    assert captured[0].body is not None
    payload = json.loads(captured[0].body.decode("utf-8"))
    assert payload["embeds"][0]["title"] == "Pipeline Inspector"


def test_discord_client_ping_returns_false_for_http_error():
    def transport(_request: HttpRequest, _timeout: float) -> DiscordResponse:
        return DiscordResponse(status_code=404, body='{"message": "Unknown Webhook"}', json_data={})

    client = DiscordClient(
        DiscordConfig(webhook_url="https://discord.com/api/webhooks/bad/token"),
        transport=transport,
    )

    assert client.ping() is False


def test_discord_client_send_embed_posts_embed_payload():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> DiscordResponse:
        captured.append(request)
        _ = timeout
        return DiscordResponse(status_code=200, body="{}", json_data={})

    client = DiscordClient(
        DiscordConfig(webhook_url="https://discord.com/api/webhooks/42/secret"),
        transport=transport,
    )
    embed = {
        "title": "Pipeline Inspector: Publish block",
        "description": "Health score: **40/100**",
        "color": 0xE74C3C,
        "fields": [{"name": "Scene", "value": "hero.ma", "inline": True}],
    }
    response = client.send_embed(embed)

    assert response.status_code == 200
    assert captured[0].body is not None
    payload = json.loads(captured[0].body.decode("utf-8"))
    assert payload["embeds"][0]["title"] == "Pipeline Inspector: Publish block"
    assert payload["embeds"][0]["fields"][0]["value"] == "hero.ma"
