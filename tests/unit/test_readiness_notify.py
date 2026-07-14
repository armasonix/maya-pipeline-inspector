from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline_inspector.integrations.readiness.engine import ReadinessCheckResult, ReadinessReport
from pipeline_inspector.integrations.readiness.notify import send_readiness_report_to_telegram
from pipeline_inspector.integrations.telegram.client import HttpRequest, TelegramResponse
from pipeline_inspector.studio_config import (
    ConnectorSettings,
    ReadinessSettings,
    ReadinessSupportContacts,
    StudioConfig,
    TelegramConnectorSettings,
)


@dataclass
class FakeTelegramClient:
    config: Any
    sent_messages: list[str]

    def send_message(self, text: str) -> TelegramResponse:
        self.sent_messages.append(text)
        return TelegramResponse(status_code=200, body="{}", json_data={"ok": True})


def test_send_readiness_report_to_telegram_uses_support_chat_id():
    studio_config = StudioConfig(
        connectors=ConnectorSettings(
            telegram=TelegramConnectorSettings(
                enabled=True,
                bot_token="123:abc",
                chat_id="-10042",
            )
        ),
        readiness=ReadinessSettings(
            support=ReadinessSupportContacts(
                sysadmin_telegram_chat_id="-10099",
                support_telegram_chat_id="-10077",
            )
        ),
    )
    report = ReadinessReport(
        results=(
            ReadinessCheckResult(
                check_id="env_var:PIPELINE_ROOT",
                category="env_var",
                label="Environment variable PIPELINE_ROOT",
                ok=False,
                message="Required environment variable 'PIPELINE_ROOT' is not set.",
            ),
        ),
        ok=False,
        summary="1 of 1 readiness checks failed.",
        host_name="ws-01",
        maya_version="2025",
    )
    captured: list[str] = []

    def factory(config: Any) -> FakeTelegramClient:
        client = FakeTelegramClient(config=config, sent_messages=captured)
        return client

    result = send_readiness_report_to_telegram(
        studio_config,
        report,
        recipient="support",
        client_factory=factory,
    )

    assert result.sent is True
    assert result.chat_id == "-10077"
    assert captured
    assert "PIPELINE_ROOT" in captured[0]


def test_send_readiness_report_to_telegram_requires_enabled_connector():
    studio_config = StudioConfig(
        connectors=ConnectorSettings(
            telegram=TelegramConnectorSettings(enabled=False, bot_token="123:abc", chat_id="-1")
        ),
        readiness=ReadinessSettings(
            support=ReadinessSupportContacts(sysadmin_telegram_chat_id="-10099")
        ),
    )
    report = ReadinessReport(results=(), ok=True, summary="ok")

    result = send_readiness_report_to_telegram(
        studio_config,
        report,
        recipient="sysadmin",
    )

    assert result.sent is False
    assert result.error_message == "telegram_connector_disabled"
