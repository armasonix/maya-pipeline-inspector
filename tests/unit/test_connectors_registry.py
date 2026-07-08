from __future__ import annotations

from tests.unit.test_settings_panel import FakeQtWidgets

from shader_health.connectors_registry import (
    CONNECTORS,
    get_connector,
    iter_connectors,
    read_connectors_from_settings_view,
    resolve_connector,
)
from shader_health.studio_config import (
    ConnectorSettings,
    DeadlineConnectorSettings,
    StudioConfig,
)
from shader_health.ui import settings_panel


def test_iter_connectors_includes_deadline():
    connectors = iter_connectors()

    assert len(connectors) == 1
    assert connectors[0].id == "deadline"
    assert connectors[0].display_name == "Thinkbox Deadline"
    assert connectors[0].settings_dataclass is DeadlineConnectorSettings


def test_get_connector_returns_none_for_unknown_id():
    assert get_connector("telegram") is None
    assert get_connector("deadline") is CONNECTORS[0]


def test_read_connectors_preserves_extra_connectors_from_base():
    view = settings_panel.build_settings_view(
        FakeQtWidgets,
        config=StudioConfig(
            connectors=ConnectorSettings(
                deadline=DeadlineConnectorSettings(enabled=True),
                extra={"telegram": {"enabled": True, "chat_id": "123"}},
            )
        ),
    )
    base = ConnectorSettings(
        deadline=DeadlineConnectorSettings(enabled=False),
        extra={"telegram": {"enabled": True, "chat_id": "123"}},
    )

    connectors = read_connectors_from_settings_view(view, FakeQtWidgets, base=base)

    assert connectors.deadline.enabled is True
    assert connectors.extra["telegram"]["chat_id"] == "123"


def test_resolve_connector_delegates_to_deadline_resolver():
    config = StudioConfig(
        connectors=ConnectorSettings(
            deadline=DeadlineConnectorSettings(
                enabled=True,
                web_service_host="farm.local",
                web_service_port=8081,
            )
        )
    )

    resolved = resolve_connector(config, "deadline")

    assert resolved is not None
    assert resolved.api_url == "http://farm.local:8081"
    assert resolve_connector(config, "unknown") is None
