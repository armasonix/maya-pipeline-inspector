from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

from pipeline_inspector.core.manifest_gate import ManifestGatePolicy  # noqa: F401
from pipeline_inspector.core.scoring import HealthScore
from pipeline_inspector.integrations.cerebro import CerebroClient, CerebroConfig
from pipeline_inspector.integrations.cerebro.publish import (
    build_task_url,
    maybe_publish_validation_summary,
    publish_validation_summary,
    resolve_task_id,
    resolve_task_id_for_publish,
    task_url_candidates,
)
from pipeline_inspector.integrations.trackers.publish import ValidationPublishPayload
from pipeline_inspector.studio_config import (
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
    project_children: dict[int, dict[str, int]] = field(default_factory=dict)
    definition_message_ids: dict[int, int] = field(default_factory=dict)
    notes: list[tuple[int, int, str]] = field(default_factory=list)
    status_updates: list[tuple[int, str]] = field(default_factory=list)
    next_message_id: int = 100

    def connect(self, user: str, password: str) -> bool:
        self.connected = True
        self.credentials = (user, password)
        return True

    def task_by_url(self, task_url: str) -> int | None:
        task_id = self.task_urls.get(task_url)
        if task_id is None:
            return None
        return task_id

    def resolve_task_in_project(self, project: str, task_name: str) -> int | None:
        project_id = self.task_urls.get(f"/{project}") or self.task_urls.get(f"/{project}/")
        if project_id is None:
            return None
        return self.project_children.get(project_id, {}).get(task_name)

    def task_definition_message_id(self, task_id: int) -> int | None:
        return self.definition_message_ids.get(task_id)

    def add_note(self, task_id: int, parent_message_id: int, html_text: str) -> int | None:
        self.notes.append((task_id, parent_message_id, html_text))
        message_id = self.next_message_id
        self.next_message_id += 1
        return message_id

    def set_task_status(self, task_id: int, status_name: str) -> bool:
        self.status_updates.append((task_id, status_name))
        return True


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


def test_build_task_url_formats_project_and_task_name():
    assert build_task_url("Demo Project", "hero") == "/Demo Project/hero"


def test_task_url_candidates_try_scene_stem_before_full_filename():
    config = _cerebro_settings().to_cerebro_config()
    assert config is not None
    candidates = task_url_candidates(
        config,
        _payload(scene_name="pipeline_inspector_demo_broken.ma"),
    )
    assert candidates == (
        "/Demo Project/pipeline_inspector_demo_broken",
        "/Demo Project/pipeline_inspector_demo_broken/",
        "/Demo Project/pipeline_inspector_demo_broken.ma",
        "/Demo Project/pipeline_inspector_demo_broken.ma/",
    )


def test_resolve_task_id_falls_back_to_project_children():
    database = FakeCerebroDatabase(
        task_urls={"/Demo Project": 10},
        project_children={10: {"pipeline_inspector_demo_broken": 55}},
        definition_message_ids={55: 7},
    )
    client = CerebroClient(
        CerebroConfig(
            server_url="https://db5.cerebrohq.com/dapi5/rpc.php",
            api_user="api@studio",
            api_password="secret",
            project="Demo Project",
        ),
        database_port=database,
    )

    task_id = resolve_task_id(
        client,
        client.config,
        _payload(scene_name="pipeline_inspector_demo_broken.ma"),
    )

    assert task_id == 55


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


def test_resolve_task_id_falls_back_to_scene_stem():
    database = FakeCerebroDatabase(
        task_urls={"/Demo Project/hero": 42},
    )
    client = CerebroClient(
        CerebroConfig(
            server_url="cerebrohq.com",
            api_user="pipeline.bot",
            api_password="secret",
            project="Demo Project",
        ),
        database_port=database,
    )

    task_id = resolve_task_id(client, client.config, _payload(scene_name="hero.ma"))

    assert task_id == 42
    assert database.connected is True


def test_resolve_task_id_for_publish_skips_project_tree_search():
    database = FakeCerebroDatabase(
        task_urls={"/Demo Project/hero": 42},
        project_children={10: {"hero": 99}},
    )
    client = CerebroClient(
        CerebroConfig(
            server_url="cerebrohq.com",
            api_user="pipeline.bot",
            api_password="secret",
            project="Demo Project",
        ),
        database_port=database,
    )

    task_id = resolve_task_id_for_publish(
        client,
        client.config,
        _payload(scene_name="hero.ma"),
    )

    assert task_id == 42
    assert database.connected is True


def test_publish_validation_summary_creates_task_note_from_scene_lookup():
    database = FakeCerebroDatabase(
        task_urls={"/Demo Project/hero": 42},
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
    assert "Health Validation Result" in database.notes[0][2]


def test_publish_validation_summary_skips_when_task_not_found():
    database = FakeCerebroDatabase()

    result = publish_validation_summary(
        _studio_config(_cerebro_settings()),
        _payload(),
        client_factory=lambda config: CerebroClient(config, database_port=database),
    )

    assert result.published is False
    assert result.skipped_reason == "task_not_found"
    assert "pipeline_inspector_demo_broken" not in (result.error_message or "")


def test_publish_validation_summary_reports_missing_py_cerebro():
    result = publish_validation_summary(
        _studio_config(_cerebro_settings(service_tools_path="")),
        _payload(),
    )

    assert result.published is False
    assert result.error_message == "service_tools_path_empty"


def test_maybe_publish_validation_summary_accepts_validation_run_result():
    database = FakeCerebroDatabase(
        task_urls={"/Demo Project/hero": 42},
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
