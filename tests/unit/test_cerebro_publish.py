from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

from shader_health.core.manifest_gate import ManifestGatePolicy  # noqa: F401
from shader_health.core.scoring import HealthScore
from shader_health.integrations.cerebro import CerebroClient, CerebroConfig
from shader_health.integrations.cerebro.publish import (
    build_task_url,
    maybe_publish_validation_summary,
    publish_validation_summary,
    resolve_task_id,
)
from shader_health.integrations.trackers.publish import ValidationPublishPayload
from shader_health.studio_config import (
    CerebroConnectorSettings,
    ConnectorSettings,
    StudioConfig,
    resolve_cerebro_config,
)


@dataclass
class FakeCerebroDatabase:
    connected: bool = False
    credentials: tuple[str, str] = ("", "")
    task_urls: dict[str, int] = field(default_factory=dict)
    definition_message_ids: dict[int, int] = field(default_factory=dict)
    notes: list[tuple[int, int, str]] = field(default_factory=list)
    next_message_id: int = 100

    def connect(self, user: str, password: str) -> bool:
        self.connected = True
        self.credentials = (user, password)
        return True

    def task_by_url(self, task_url: str) -> int | None:
        return self.task_urls.get(task_url)

    def task_definition_message_id(self, task_id: int) -> int | None:
        return self.definition_message_ids.get(task_id)

    def add_note(self, task_id: int, parent_message_id: int, html_text: str) -> int | None:
        self.notes.append((task_id, parent_message_id, html_text))
        message_id = self.next_message_id
        self.next_message_id += 1
        return message_id


def _payload(**overrides: object) -> ValidationPublishPayload:
    defaults = {
        "scene_name": "hero.ma",
        "scene_path": r"C:\shots\hero.ma",
        "scan_scope": "scene",
        "profile_id": "publish_strict",
        "asset_class_id": "",
        "health_score": 42,
        "critical_count": 1,
        "error_count": 0,
        "warning_count": 0,
        "info_count": 0,
        "block_publish": True,
        "block_deadline": False,
        "validated_at_utc": "2026-07-10T12:00:00Z",
    }
    defaults.update(overrides)
    return ValidationPublishPayload(**defaults)


def _cerebro_settings(**overrides: object) -> CerebroConnectorSettings:
    defaults = {
        "enabled": True,
        "server_url": "cerebrohq.com:45432",
        "api_user": "pipeline.bot",
        "api_password": "secret",
        "project": "Demo Project",
    }
    defaults.update(overrides)
    return CerebroConnectorSettings(**defaults)


def _studio_config(cerebro: CerebroConnectorSettings) -> StudioConfig:
    return StudioConfig(connectors=ConnectorSettings(cerebro=cerebro))


def test_resolve_cerebro_config_requires_complete_settings():
    assert resolve_cerebro_config(_studio_config(_cerebro_settings())) is not None
    assert resolve_cerebro_config(_studio_config(_cerebro_settings(enabled=False))) is None
    assert resolve_cerebro_config(_studio_config(_cerebro_settings(api_password=""))) is None


def test_build_task_url_formats_project_and_scene():
    assert build_task_url("Demo Project", "hero.ma") == "/Demo Project/hero.ma"


def test_resolve_task_id_prefers_payload_metadata():
    database = FakeCerebroDatabase()
    client = CerebroClient(
        CerebroConfig(
            server_url="cerebrohq.com",
            api_user="pipeline.bot",
            api_password="secret",
            project="Demo Project",
        ),
        database_port=database,
    )

    task_id = resolve_task_id(
        client,
        client.config,
        _payload(metadata={"task_id": "99"}),
    )

    assert task_id == 99
    assert database.connected is False


def test_publish_validation_summary_creates_task_note_from_scene_lookup():
    database = FakeCerebroDatabase(
        task_urls={"/Demo Project/hero.ma": 42},
        definition_message_ids={42: 7},
    )

    def client_factory(config: CerebroConfig) -> CerebroClient:
        return CerebroClient(config, database_port=database)

    result = publish_validation_summary(
        _studio_config(_cerebro_settings()),
        _payload(),
        client_factory=client_factory,
    )

    assert result.published is True
    assert result.external_url == "100"
    assert result.metadata["note_id"] == "100"
    assert len(database.notes) == 1
    assert "Shader Health validation summary" in database.notes[0][2]


def test_publish_validation_summary_skips_when_task_not_found():
    database = FakeCerebroDatabase()

    result = publish_validation_summary(
        _studio_config(_cerebro_settings()),
        _payload(),
        client_factory=lambda config: CerebroClient(config, database_port=database),
    )

    assert result.published is False
    assert result.skipped_reason == "task_not_found"


def test_maybe_publish_validation_summary_accepts_validation_run_result():
    database = FakeCerebroDatabase(
        task_urls={"/Demo Project/hero.ma": 42},
        definition_message_ids={42: 7},
    )

    run_result = SimpleNamespace(
        snapshot=SimpleNamespace(
            scene_path="/tmp/hero.ma",
            scanned_at_utc="2026-07-10T12:00:00Z",
        ),
        scan_scope="scene",
        profile_id="publish_strict",
        asset_class_id="",
        health_score=HealthScore(
            score=40,
            raw_score=40,
            critical=1,
            block_publish=True,
        ),
    )

    result = maybe_publish_validation_summary(
        _studio_config(_cerebro_settings()),
        run_result,
        client_factory=lambda config: CerebroClient(config, database_port=database),
    )

    assert result.published is True
