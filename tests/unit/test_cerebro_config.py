from __future__ import annotations

from shader_health.integrations.cerebro import CerebroConfig
from shader_health.integrations.cerebro.config import resolve_cerebro_server_endpoint


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


def test_cerebro_config_parses_server_api_url_host_and_default_port():
    host, port, source = resolve_cerebro_server_endpoint(
        "https://db5.cerebrohq.com/dapi5/rpc.php",
    )

    assert host == "db5.cerebrohq.com"
    assert port is None
    assert source == "server_api_url"


def test_is_cerebro_rpc_url_detects_server_api_url():
    from shader_health.integrations.cerebro.config import is_cerebro_rpc_url

    assert is_cerebro_rpc_url("https://db5.cerebrohq.com/dapi5/rpc.php") is True
    assert is_cerebro_rpc_url("db5.cerebrohq.com:45432") is False


def test_default_database_port_factory_uses_http_adapter_for_rpc_url():
    from shader_health.integrations.cerebro.adapter import (
        PyCerebroDatabaseAdapter,
        PycerebroHttpDatabaseAdapter,
        default_database_port_factory,
    )

    http_config = CerebroConfig(
        server_url="https://db5.cerebrohq.com/dapi5/rpc.php",
        api_user="api@studio",
        api_password="token",
        project="Demo Project",
    )
    pg_config = CerebroConfig(
        server_url="db5.cerebrohq.com:45432",
        api_user="api@studio",
        api_password="token",
        project="Demo Project",
    )

    assert isinstance(default_database_port_factory(http_config), PycerebroHttpDatabaseAdapter)
    assert isinstance(default_database_port_factory(pg_config), PyCerebroDatabaseAdapter)
