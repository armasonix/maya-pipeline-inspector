from __future__ import annotations

import json

from pipeline_inspector.integrations.slack import SlackClient, SlackResponse
from pipeline_inspector.integrations.slack.client import HttpRequest


def test_slack_client_ping_returns_true_for_ok_response():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> SlackResponse:
        captured.append(request)
        _ = timeout
        return SlackResponse(status_code=200, body="ok", json_data=None)

    client = SlackClient(transport=transport)
    webhook = "https://hooks.slack.com/services/T/B/secret"

    assert client.ping(webhook) is True
    assert captured[0].url == webhook
    payload = json.loads(captured[0].body.decode("utf-8"))
    assert payload["blocks"][0]["type"] == "section"


def test_slack_client_ping_returns_false_for_http_error():
    def transport(_request: HttpRequest, _timeout: float) -> SlackResponse:
        return SlackResponse(status_code=404, body="invalid_token", json_data=None)

    client = SlackClient(transport=transport)

    assert client.ping("https://hooks.slack.com/services/bad") is False


def test_slack_client_send_blocks_posts_block_kit_payload():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> SlackResponse:
        captured.append(request)
        _ = timeout
        return SlackResponse(status_code=200, body="ok", json_data=None)

    client = SlackClient(transport=transport)
    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Pipeline Inspector: Publish block"},
            }
        ]
    }

    response = client.send_blocks("https://hooks.slack.com/services/T/B/publish", payload)

    assert response.status_code == 200
    assert json.loads(captured[0].body.decode("utf-8")) == payload
