from __future__ import annotations

import json
from pathlib import Path

from shader_health.core.manifest_gate import ManifestGatePolicy
from shader_health.core.rule_loader import RuleOverride
from shader_health.integrations.deadline.config import DeadlineConfig
from shader_health.studio_config import (
    LEGACY_STUDIO_CONFIG_SCHEMA_VERSION,
    STUDIO_CONFIG_FILENAME,
    STUDIO_CONFIG_SCHEMA_VERSION,
    BugReportSettings,
    ConnectorSettings,
    DeadlineConnectorSettings,
    PipelineSettings,
    StudioConfig,
    StudioEnvironmentSettings,
    StudioUiSettings,
    StudioUpdatesSettings,
    WaiverDefaultsSettings,
    load_studio_config,
    merge_studio_rule_overrides,
    resolve_deadline_config,
    resolve_studio_config_for_headless,
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
        pipeline=PipelineSettings(
            require_tx_derivatives=False,
            waiver_defaults=WaiverDefaultsSettings(
                default_approved_by="pipeline_td",
                default_expiry_days=14,
                allow_critical_waivers=True,
            ),
            manifest_gate_defaults=ManifestGatePolicy(
                max_new_changes=1,
                max_fingerprint_changes=2,
                block_on_new_textures=False,
            ),
            pinned_workflow_profile_ids=("artist_relaxed",),
            pinned_asset_class_profile_ids=("asset_class_hero",),
        ),
    )

    save_studio_config(path, original)
    loaded = load_studio_config(path)

    assert loaded.studio_name == "Demo Studio"
    assert loaded.pipeline.require_tx_derivatives is False
    assert loaded.pipeline.waiver_defaults.default_approved_by == "pipeline_td"
    assert loaded.pipeline.waiver_defaults.default_expiry_days == 14
    assert loaded.pipeline.waiver_defaults.allow_critical_waivers is True
    assert loaded.pipeline.manifest_gate_defaults.max_new_changes == 1
    assert loaded.pipeline.manifest_gate_defaults.max_fingerprint_changes == 2
    assert loaded.pipeline.manifest_gate_defaults.block_on_new_textures is False
    assert loaded.pipeline.pinned_workflow_profile_ids == ("artist_relaxed",)
    assert loaded.pipeline.pinned_asset_class_profile_ids == ("asset_class_hero",)
    assert loaded.config_path == path.resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == STUDIO_CONFIG_SCHEMA_VERSION
    assert payload["pipeline"]["require_tx_derivatives"] is False
    assert payload["pipeline"]["waiver_defaults"]["default_approved_by"] == "pipeline_td"
    assert payload["studio_environment"]["texture_root"] == ""
    assert payload["bug_report"]["enabled"] is False


def test_studio_config_loads_legacy_schema_1_0_with_defaults(tmp_path: Path):
    path = tmp_path / STUDIO_CONFIG_FILENAME
    path.write_text(
        json.dumps(
            {
                "schema_version": LEGACY_STUDIO_CONFIG_SCHEMA_VERSION,
                "studio_name": "Legacy Studio",
                "pipeline": {"require_tx_derivatives": True},
                "connectors": {"deadline": {"enabled": False}},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    loaded = load_studio_config(path)

    assert loaded.schema_version == LEGACY_STUDIO_CONFIG_SCHEMA_VERSION
    assert loaded.studio_name == "Legacy Studio"
    assert loaded.pipeline.waiver_defaults.default_expiry_days == 30
    assert loaded.pipeline.manifest_gate_defaults.block_on_new_textures is True
    assert loaded.pipeline.pinned_workflow_profile_ids == ()
    assert loaded.ui.documentation_url == ""
    assert loaded.bug_report.enabled is False
    assert loaded.updates.allow_check is True
    assert loaded.connectors.deadline.enabled is False


def test_studio_config_save_migrates_legacy_schema_to_2_0(tmp_path: Path):
    path = tmp_path / STUDIO_CONFIG_FILENAME
    legacy = StudioConfig(
        schema_version=LEGACY_STUDIO_CONFIG_SCHEMA_VERSION,
        studio_name="Legacy Studio",
    )

    save_studio_config(path, legacy)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == STUDIO_CONFIG_SCHEMA_VERSION
    assert payload["studio_name"] == "Legacy Studio"
    assert "studio_environment" in payload
    assert "bug_report" in payload
    assert "updates" in payload
    assert "ui" in payload


def test_studio_config_schema_2_0_round_trips_new_sections(tmp_path: Path):
    path = tmp_path / STUDIO_CONFIG_FILENAME
    original = StudioConfig(
        studio_name="Network Studio",
        studio_environment=StudioEnvironmentSettings(
            texture_root="\\\\farm\\textures",
            asset_root="\\\\farm\\assets",
            cache_root="\\\\farm\\cache",
            render_root="\\\\farm\\render",
            variable_aliases={"STUDIO_TEXTURE_ROOT": "\\\\farm\\textures"},
        ),
        ui=StudioUiSettings(documentation_url="https://wiki.studio.local/shader-health"),
        bug_report=BugReportSettings(
            enabled=True,
            relay_url="https://pipeline.studio.internal/shader-health/bug-report",
            api_key="studio-secret",
            allow_screenshot=False,
            max_reports_per_day=3,
        ),
        updates=StudioUpdatesSettings(allow_check=False, pinned_version="0.4.0"),
        connectors=ConnectorSettings(
            deadline=DeadlineConnectorSettings(enabled=False),
            extra={
                "telegram": {
                    "enabled": True,
                    "bot_token": "token",
                    "chat_id": "12345",
                }
            },
        ),
    )

    save_studio_config(path, original)
    loaded = load_studio_config(path)

    assert loaded.schema_version == STUDIO_CONFIG_SCHEMA_VERSION
    assert loaded.studio_environment.texture_root == "\\\\farm\\textures"
    assert loaded.studio_environment.variable_aliases["STUDIO_TEXTURE_ROOT"] == "\\\\farm\\textures"
    assert loaded.ui.documentation_url == "https://wiki.studio.local/shader-health"
    assert loaded.bug_report.enabled is True
    assert loaded.bug_report.relay_url.endswith("/bug-report")
    assert loaded.bug_report.api_key == "studio-secret"
    assert loaded.bug_report.allow_screenshot is False
    assert loaded.bug_report.max_reports_per_day == 3
    assert loaded.updates.allow_check is False
    assert loaded.updates.pinned_version == "0.4.0"
    assert loaded.connectors.extra["telegram"]["enabled"] is True
    assert loaded.connectors.extra["telegram"]["chat_id"] == "12345"


def test_connector_settings_preserves_extensible_connectors():
    connectors = ConnectorSettings.from_mapping(
        {
            "deadline": {"enabled": True, "web_service_host": "farm.local"},
            "slack": {"enabled": True, "webhook_url": "https://hooks.slack.com/example"},
            "ftrack": {"enabled": False},
        }
    )

    restored = ConnectorSettings.from_mapping(connectors.to_dict())

    assert connectors.deadline.enabled is True
    assert connectors.deadline.web_service_host == "farm.local"
    assert connectors.extra["slack"]["webhook_url"].startswith("https://hooks.slack.com/")
    assert connectors.extra["ftrack"]["enabled"] is False
    assert restored.to_dict() == connectors.to_dict()


def test_studio_config_default_uses_schema_2_0():
    assert StudioConfig().schema_version == STUDIO_CONFIG_SCHEMA_VERSION


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


def test_resolve_studio_config_for_headless_prefers_explicit_cli_path(tmp_path: Path):
    path = tmp_path / STUDIO_CONFIG_FILENAME
    save_studio_config(
        path,
        StudioConfig(
            studio_name="CLI Studio",
            pipeline=PipelineSettings(require_tx_derivatives=False),
        ),
    )

    resolved = resolve_studio_config_for_headless(cli_path=path)

    assert resolved is not None
    assert resolved.studio_name == "CLI Studio"
    assert resolved.pipeline.require_tx_derivatives is False


def test_resolve_studio_config_for_headless_raises_when_cli_path_missing(tmp_path: Path):
    missing = tmp_path / "missing_studio.json"

    try:
        resolve_studio_config_for_headless(cli_path=missing)
    except ValueError as exc:
        assert "does not exist" in str(exc)
    else:
        raise AssertionError("Expected ValueError for missing studio config path")


def test_resolve_studio_config_for_headless_discovers_env_path(tmp_path: Path, monkeypatch):
    path = tmp_path / "env_studio.json"
    save_studio_config(path, StudioConfig(studio_name="Env Studio"))
    monkeypatch.setenv("SHADER_HEALTH_STUDIO_CONFIG", str(path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))

    resolved = resolve_studio_config_for_headless()

    assert resolved is not None
    assert resolved.studio_name == "Env Studio"
