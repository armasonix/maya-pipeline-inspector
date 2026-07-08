from __future__ import annotations

import json
from pathlib import Path

from shader_health.core.rule_loader import RuleOverride
from shader_health.integrations.deadline.config import DeadlineConfig
from shader_health.studio_config import (
    STUDIO_CONFIG_FILENAME,
    ConnectorSettings,
    DeadlineConnectorSettings,
    PipelineSettings,
    StudioConfig,
    load_studio_config,
    merge_studio_rule_overrides,
    resolve_deadline_config,
    save_studio_config,
)


def test_studio_config_disables_tx_rules_when_not_required():
    config = StudioConfig(pipeline=PipelineSettings(require_tx_derivatives=False))
    overrides = config.rule_overrides()

    assert set(overrides) == {
        "common.texture.optimized.exists",
        "common.texture.optimized.fresh",
        "common.texture.optimized.udim_tx.missing",
    }
    assert all(override.enabled is False for override in overrides.values())


def test_studio_config_keeps_tx_rules_when_required():
    config = StudioConfig(pipeline=PipelineSettings(require_tx_derivatives=True))
    assert config.rule_overrides() == {}


def test_merge_studio_rule_overrides_layers_on_profile():
    profile_overrides = {
        "common.texture.missing": RuleOverride(rule_id="common.texture.missing", enabled=True),
    }
    studio = StudioConfig(pipeline=PipelineSettings(require_tx_derivatives=False))

    merged = merge_studio_rule_overrides(profile_overrides, studio)

    assert merged["common.texture.missing"].enabled is True
    assert merged["common.texture.optimized.exists"].enabled is False


def test_studio_config_round_trips_through_json_file(tmp_path: Path):
    path = tmp_path / STUDIO_CONFIG_FILENAME
    original = StudioConfig(
        studio_name="Demo Studio",
        pipeline=PipelineSettings(require_tx_derivatives=False),
    )

    save_studio_config(path, original)
    loaded = load_studio_config(path)

    assert loaded.studio_name == "Demo Studio"
    assert loaded.pipeline.require_tx_derivatives is False
    assert loaded.config_path == path.resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["pipeline"]["require_tx_derivatives"] is False


def test_deadline_connector_builds_api_url_from_host_and_port():
    settings = DeadlineConnectorSettings(
        enabled=True,
        web_service_host="10.0.0.8",
        web_service_port=8082,
    )

    assert settings.api_url == "http://10.0.0.8:8082"
    assert settings.to_deadline_config().api_url == "http://10.0.0.8:8082"


def test_deadline_connector_round_trips_in_studio_config_file(tmp_path):
    path = tmp_path / STUDIO_CONFIG_FILENAME
    original = StudioConfig(
        connectors=ConnectorSettings(
            deadline=DeadlineConnectorSettings(
                enabled=True,
                web_service_host="farm.local",
                web_service_port=8081,
                repo_root="\\\\farm\\DeadlineRepository10",
                queue="lookdev",
            )
        )
    )

    save_studio_config(path, original)
    loaded = load_studio_config(path)

    assert loaded.connectors.deadline.enabled is True
    assert loaded.connectors.deadline.web_service_host == "farm.local"
    assert loaded.connectors.deadline.repo_root == "\\\\farm\\DeadlineRepository10"
    assert loaded.connectors.deadline.queue == "lookdev"


def test_resolve_deadline_config_uses_connector_when_enabled():
    config = StudioConfig(
        config_path=Path("C:/studio/shader_health_studio.json"),
        connectors=ConnectorSettings(
            deadline=DeadlineConnectorSettings(
                enabled=True,
                web_service_host="deadline-host",
                web_service_port=9090,
            )
        ),
    )

    resolved = resolve_deadline_config(config)

    assert resolved is not None
    assert resolved.api_url == "http://deadline-host:9090"


def test_resolve_deadline_config_returns_none_when_disabled_in_saved_file():
    config = StudioConfig(
        config_path=Path("C:/studio/shader_health_studio.json"),
        connectors=ConnectorSettings(
            deadline=DeadlineConnectorSettings(enabled=False),
        ),
    )

    assert resolve_deadline_config(config) is None


def test_resolve_deadline_config_returns_none_when_disabled(monkeypatch):
    monkeypatch.delenv("SHADER_HEALTH_DEADLINE_API_URL", raising=False)
    config = StudioConfig(
        connectors=ConnectorSettings(
            deadline=DeadlineConnectorSettings(enabled=False),
        ),
    )

    assert resolve_deadline_config(config) is None


def test_deadline_connector_from_deadline_config_round_trip():
    source = DeadlineConfig(
        api_url="http://render-farm:8081",
        repo_root=Path("\\\\farm\\repo"),
        queue="shader",
    )

    connector = DeadlineConnectorSettings.from_deadline_config(source, enabled=True)

    assert connector.web_service_host == "render-farm"
    assert connector.web_service_port == 8081
    assert connector.repo_root.rstrip("\\/") == "\\\\farm\\repo"
    assert connector.queue == "shader"
