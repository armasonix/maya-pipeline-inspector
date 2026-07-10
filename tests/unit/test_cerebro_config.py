from __future__ import annotations

from shader_health.integrations.cerebro import CerebroConfig


def test_cerebro_config_parses_server_url_host_and_port():
    config = CerebroConfig(
        server_url="cerebrohq.com:45432",
        api_user="pipeline.bot",
        api_password="secret",
        project="Demo Project",
    )

    assert config.db_host == "cerebrohq.com"
    assert config.resolved_db_port == 45432


def test_cerebro_config_defaults_port_when_server_url_has_no_port():
    config = CerebroConfig(
        server_url="https://cerebrohq.com",
        api_user="pipeline.bot",
        api_password="secret",
        project="Demo Project",
    )

    assert config.db_host == "cerebrohq.com"
    assert config.resolved_db_port == 45432
