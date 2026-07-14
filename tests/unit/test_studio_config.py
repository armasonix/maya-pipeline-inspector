from __future__ import annotations

import json
from pathlib import Path

from pipeline_inspector.core.manifest_gate import ManifestGatePolicy
from pipeline_inspector.core.rule_loader import RuleOverride
from pipeline_inspector.integrations.bug_report.config import DEFAULT_PUBLIC_BUG_REPORT_RELAY_URL
from pipeline_inspector.integrations.deadline.config import DeadlineConfig
from pipeline_inspector.studio_config import (
    LEGACY_STUDIO_CONFIG_SCHEMA_VERSION,
    STUDIO_CONFIG_FILENAME,
    STUDIO_CONFIG_SCHEMA_VERSION,
    BugReportSettings,
    ConnectorSettings,
    DeadlineConnectorSettings,
    DiscordConnectorSettings,
    PipelineSettings,
    ReadinessCheckRequirements,
    ReadinessSettings,
    ReadinessSupportContacts,
    SlackConnectorSettings,
    SoftwareVersionRequirement,
    StudioConfig,
    StudioEnvironmentSettings,
    StudioUiSettings,
    StudioUpdatesSettings,
    TelegramConnectorSettings,
    WaiverDefaultsSettings,
    load_studio_config,
    merge_studio_rule_overrides,
    resolve_bug_report_config,
    resolve_deadline_config,
    resolve_discord_config,
    resolve_slack_config,
    resolve_studio_config_for_headless,
    resolve_telegram_config,
    parse_software_version_requirements,
    save_studio_config,
)


def test_resolve_bug_report_config_uses_public_relay_without_api_key():
    config = StudioConfig(
        bug_report=BugReportSettings(
            enabled=True,
            relay_url="",
            api_key="",
        )
    )

    resolved = resolve_bug_report_config(config)

    assert resolved is not None
    assert resolved.relay_url == DEFAULT_PUBLIC_BUG_REPORT_RELAY_URL
    assert resolved.api_key == ""


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
            telegram=TelegramConnectorSettings(
                enabled=True,
                bot_token="token",
                chat_id="12345",
                notify_on=("block_publish",),
            ),
            discord=DiscordConnectorSettings(
                enabled=True,
                webhook_url="https://discord.com/api/webhooks/1/secret",
                notify_on=("block_deadline",),
            ),
            slack=SlackConnectorSettings(
                enabled=True,
                publish_webhook_url="https://hooks.slack.com/publish",
                deadline_webhook_url="https://hooks.slack.com/deadline",
                notify_on=("block_publish",),
                include_report_link=False,
            ),
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
    assert loaded.connectors.telegram.enabled is True
    assert loaded.connectors.telegram.chat_id == "12345"
    assert loaded.connectors.telegram.bot_token == "token"
    assert loaded.connectors.telegram.notify_on == ("block_publish",)
    assert loaded.connectors.discord.enabled is True
    assert loaded.connectors.discord.webhook_url == "https://discord.com/api/webhooks/1/secret"
    assert loaded.connectors.discord.notify_on == ("block_deadline",)
    assert loaded.connectors.slack.enabled is True
    assert loaded.connectors.slack.publish_webhook_url == "https://hooks.slack.com/publish"
    assert loaded.connectors.slack.deadline_webhook_url == "https://hooks.slack.com/deadline"
    assert loaded.connectors.slack.notify_on == ("block_publish",)
    assert loaded.connectors.slack.include_report_link is False


def test_studio_config_round_trips_readiness_block(tmp_path: Path):
    path = tmp_path / STUDIO_CONFIG_FILENAME
    original = StudioConfig(
        readiness=ReadinessSettings(
            checks=ReadinessCheckRequirements(
                maya_plugins=("mtoa",),
                mapped_drives=("Z",),
                env_vars=("PIPELINE_ROOT",),
                network_paths=("\\\\farm\\textures",),
                software_version_requirements=(
                    SoftwareVersionRequirement("maya", "2025"),
                ),
            ),
            support=ReadinessSupportContacts(
                sysadmin_telegram_chat_id="-10011",
                support_telegram_chat_id="-10022",
            ),
        )
    )

    save_studio_config(path, original)
    loaded = load_studio_config(path)

    assert loaded.readiness.checks.maya_plugins == ("mtoa",)
    assert loaded.readiness.checks.mapped_drives == ("Z",)
    assert loaded.readiness.checks.env_vars == ("PIPELINE_ROOT",)
    assert loaded.readiness.checks.network_paths == ("\\\\farm\\textures",)
    assert loaded.readiness.checks.software_version_requirements == (
        SoftwareVersionRequirement("maya", "2025"),
    )
    assert loaded.readiness.support.sysadmin_telegram_chat_id == "-10011"
    assert loaded.readiness.support.support_telegram_chat_id == "-10022"


def test_parse_software_version_requirements_preserves_duplicate_products():
    requirements = parse_software_version_requirements(
        "maya=2024\nmaya=2025\nmtoa=5.4.0"
    )

    assert requirements == (
        SoftwareVersionRequirement("maya", "2024"),
        SoftwareVersionRequirement("maya", "2025"),
        SoftwareVersionRequirement("mtoa", "5.4.0"),
    )


def test_parse_software_version_requirements_reads_legacy_dict_and_list_values():
    from_mapping = parse_software_version_requirements({"maya": ["2024", "2025"]})
    legacy = parse_software_version_requirements({"maya": "2025"})

    assert from_mapping == (
        SoftwareVersionRequirement("maya", "2024"),
        SoftwareVersionRequirement("maya", "2025"),
    )
    assert legacy == (SoftwareVersionRequirement("maya", "2025"),)


def test_connector_settings_preserves_extensible_connectors():
    connectors = ConnectorSettings.from_mapping(
        {
            "deadline": {"enabled": True, "web_service_host": "farm.local"},
            "slack": {
                "enabled": True,
                "publish_webhook_url": "https://hooks.slack.com/publish",
            },
            "ftrack": {"enabled": False},
            "custom_tracker": {"enabled": True, "server_url": "https://custom.example"},
        }
    )

    restored = ConnectorSettings.from_mapping(connectors.to_dict())

    assert connectors.deadline.enabled is True
    assert connectors.deadline.web_service_host == "farm.local"
    assert connectors.slack.enabled is True
    assert connectors.slack.publish_webhook_url.startswith("https://hooks.slack.com/")
    assert connectors.ftrack.enabled is False
    assert connectors.extra["custom_tracker"]["server_url"] == "https://custom.example"
    assert restored.to_dict() == connectors.to_dict()


def test_connector_settings_round_trips_tracker_connectors():
    connectors = ConnectorSettings.from_mapping(
        {
            "ftrack": {
                "enabled": True,
                "api_url": "https://studio.ftrackapp.com",
                "api_user": "pipeline.bot",
                "api_key": "secret",
                "project": "Demo Project",
            },
            "shotgrid": {
                "enabled": True,
                "site_url": "https://studio.shotgrid.autodesk.com",
                "script_name": "pipeline_inspector",
                "api_key": "secret",
                "project": "Demo Project",
                "entity_type": "Shot",
            },
            "cerebro": {
                "enabled": True,
                "server_url": "cerebrohq.com:45432",
                "api_user": "pipeline.bot",
                "api_password": "secret",
                "project": "Demo Project",
            },
        }
    )

    restored = ConnectorSettings.from_mapping(connectors.to_dict())

    assert connectors.ftrack.enabled is True
    assert connectors.ftrack.api_url == "https://studio.ftrackapp.com"
    assert connectors.ftrack.project == "Demo Project"
    assert connectors.shotgrid.enabled is True
    assert connectors.shotgrid.site_url == "https://studio.shotgrid.autodesk.com"
    assert connectors.shotgrid.entity_type == "Shot"
    assert connectors.cerebro.enabled is True
    assert connectors.cerebro.server_url == "cerebrohq.com:45432"
    assert connectors.cerebro.project == "Demo Project"
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
        config_path=Path("C:/studio/pipeline_inspector_studio.json"),
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
        config_path=Path("C:/studio/pipeline_inspector_studio.json"),
        connectors=ConnectorSettings(
            deadline=DeadlineConnectorSettings(enabled=False),
        ),
    )

    assert resolve_deadline_config(config) is None


def test_resolve_deadline_config_returns_none_when_disabled(monkeypatch):
    monkeypatch.delenv("PIPELINE_INSPECTOR_DEADLINE_API_URL", raising=False)
    config = StudioConfig(
        connectors=ConnectorSettings(
            deadline=DeadlineConnectorSettings(enabled=False),
        ),
    )

    assert resolve_deadline_config(config) is None


def test_resolve_telegram_config_uses_connector_when_enabled():
    config = StudioConfig(
        connectors=ConnectorSettings(
            telegram=TelegramConnectorSettings(
                enabled=True,
                bot_token="123:abc",
                chat_id="-10042",
            )
        ),
    )

    resolved = resolve_telegram_config(config)

    assert resolved is not None
    assert resolved.bot_token == "123:abc"
    assert resolved.chat_id == "-10042"


def test_resolve_telegram_config_returns_none_when_disabled_or_incomplete():
    disabled = StudioConfig(
        connectors=ConnectorSettings(
            telegram=TelegramConnectorSettings(
                enabled=False,
                bot_token="123:abc",
                chat_id="-10042",
            )
        ),
    )
    incomplete = StudioConfig(
        connectors=ConnectorSettings(
            telegram=TelegramConnectorSettings(enabled=True, bot_token="", chat_id="-10042"),
        ),
    )

    assert resolve_telegram_config(disabled) is None
    assert resolve_telegram_config(incomplete) is None


def test_resolve_discord_config_uses_connector_when_enabled():
    config = StudioConfig(
        connectors=ConnectorSettings(
            discord=DiscordConnectorSettings(
                enabled=True,
                webhook_url="https://discord.com/api/webhooks/9/abc",
            )
        ),
    )

    resolved = resolve_discord_config(config)

    assert resolved is not None
    assert resolved.webhook_url == "https://discord.com/api/webhooks/9/abc"


def test_resolve_discord_config_returns_none_when_disabled_or_incomplete():
    disabled = StudioConfig(
        connectors=ConnectorSettings(
            discord=DiscordConnectorSettings(
                enabled=False,
                webhook_url="https://discord.com/api/webhooks/9/abc",
            )
        ),
    )
    incomplete = StudioConfig(
        connectors=ConnectorSettings(
            discord=DiscordConnectorSettings(enabled=True, webhook_url=""),
        ),
    )

    assert resolve_discord_config(disabled) is None
    assert resolve_discord_config(incomplete) is None


def test_resolve_slack_config_uses_connector_when_enabled():
    config = StudioConfig(
        connectors=ConnectorSettings(
            slack=SlackConnectorSettings(
                enabled=True,
                publish_webhook_url="https://hooks.slack.com/publish",
                deadline_webhook_url="https://hooks.slack.com/deadline",
            )
        ),
    )

    resolved = resolve_slack_config(config)

    assert resolved is not None
    assert resolved.publish_webhook_url == "https://hooks.slack.com/publish"
    assert resolved.deadline_webhook_url == "https://hooks.slack.com/deadline"


def test_resolve_slack_config_returns_none_when_disabled_or_incomplete():
    disabled = StudioConfig(
        connectors=ConnectorSettings(
            slack=SlackConnectorSettings(
                enabled=False,
                publish_webhook_url="https://hooks.slack.com/publish",
            )
        ),
    )
    incomplete = StudioConfig(
        connectors=ConnectorSettings(
            slack=SlackConnectorSettings(
                enabled=True,
                publish_webhook_url="",
                deadline_webhook_url="",
            ),
        ),
    )

    assert resolve_slack_config(disabled) is None
    assert resolve_slack_config(incomplete) is None


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
    monkeypatch.setenv("PIPELINE_INSPECTOR_STUDIO_CONFIG", str(path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))

    resolved = resolve_studio_config_for_headless()

    assert resolved is not None
    assert resolved.studio_name == "Env Studio"
