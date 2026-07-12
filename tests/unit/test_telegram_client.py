from __future__ import annotations

from pipeline_inspector.integrations.telegram import (
    TelegramClient,
    TelegramConfig,
    TelegramResponse,
)
from pipeline_inspector.integrations.telegram.client import HttpRequest


def test_telegram_client_ping_returns_true_for_ok_get_me():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> TelegramResponse:
        captured.append(request)
        _ = timeout
        return TelegramResponse(
            status_code=200,
            body='{"ok": true, "result": {"username": "pipeline_inspector_bot"}}',
            json_data={"ok": True, "result": {"username": "pipeline_inspector_bot"}},
        )

    client = TelegramClient(
        TelegramConfig(bot_token="123:abc", chat_id="999"),
        transport=transport,
    )

    assert client.ping() is True
    assert captured[0].method == "GET"
    assert captured[0].url.endswith("/bot123:abc/getMe")


def test_telegram_client_ping_returns_false_for_http_error():
    def transport(_request: HttpRequest, _timeout: float) -> TelegramResponse:
        return TelegramResponse(status_code=401, body='{"ok": false}', json_data={"ok": False})

    client = TelegramClient(
        TelegramConfig(bot_token="bad-token", chat_id="999"),
        transport=transport,
    )

    assert client.ping() is False


def test_telegram_client_send_message_posts_chat_id_and_text():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> TelegramResponse:
        captured.append(request)
        _ = timeout
        return TelegramResponse(
            status_code=200,
            body='{"ok": true, "result": {"message_id": 42}}',
            json_data={"ok": True, "result": {"message_id": 42}},
        )

    client = TelegramClient(
        TelegramConfig(bot_token="123:abc", chat_id="-100123"),
        transport=transport,
    )
    response = client.send_message("Publish blocked in char.ma")

    assert response.status_code == 200
    assert captured[0].method == "POST"
    assert captured[0].url.endswith("/bot123:abc/sendMessage")
    assert captured[0].body is not None
    assert b'"chat_id": "-100123"' in captured[0].body
    assert b"Publish blocked in char.ma" in captured[0].body
