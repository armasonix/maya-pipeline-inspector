from __future__ import annotations

from pathlib import Path

from pipeline_inspector.integrations.deadline import (
    DeadlineClient,
    DeadlineConfig,
    FarmSceneState,
    FarmValidationResult,
)
from pipeline_inspector.integrations.deadline.client import DeadlineResponse, HttpRequest
from pipeline_inspector.maya import farm_actions
from pipeline_inspector.ui.farm_tab import FarmTabState


class FakeSummary:
    def __init__(self, *, block_publish: bool = False, block_deadline: bool = False) -> None:
        self.block_publish = block_publish
        self.block_deadline = block_deadline


class FakeCmds:
    def __init__(
        self,
        *,
        modified: bool = False,
        scene_name: str = "D:/show/scene.ma",
        renderer: str = "arnold",
        loaded_plugins: set[str] | None = None,
    ) -> None:
        self.modified = modified
        self.scene_name = scene_name
        self.renderer = renderer
        self.loaded_plugins = loaded_plugins or {"mtoa"}

    def file(self, *args: object, **kwargs: object) -> object:
        if kwargs.get("query") and kwargs.get("modified"):
            return self.modified
        if kwargs.get("query") and kwargs.get("sceneName"):
            return self.scene_name
        return None

    def objExists(self, name: str) -> bool:
        return name == "defaultRenderGlobals"

    def getAttr(self, name: str) -> str:
        if name == "defaultRenderGlobals.currentRenderer":
            return self.renderer
        return ""

    def pluginInfo(self, plugin_name: str, **kwargs: object) -> bool:
        if kwargs.get("query") and kwargs.get("loaded"):
            return plugin_name in self.loaded_plugins
        return False


def test_collect_farm_scene_state_reads_maya_signals():
    state = farm_actions.collect_farm_scene_state(cmds=FakeCmds(modified=True))
    assert state.scene_saved is False
    assert state.renderer_plugin_loaded is True


def test_run_farm_preflight_action_blocks_unsaved_scene():
    result = farm_actions.run_farm_preflight_action(
        summary=FakeSummary(),
        scene_state=FarmSceneState(scene_saved=False),
        connection_state=FarmTabState(connection_reachable=True),
    )
    assert result.succeeded is False
    assert "blocked" in result.message


def test_check_deadline_connection_uses_mock_client():
    class ReachableClient:
        def ping(self) -> bool:
            return True

    state = farm_actions.check_deadline_connection(
        DeadlineConfig(api_url="http://localhost:8081"),
        client_factory=lambda _cfg: ReachableClient(),  # type: ignore[arg-type]
    )
    assert state.connection_reachable is True


def test_submit_farm_validation_action_submits_command_script_job(tmp_path: Path):
    requests: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> DeadlineResponse:
        requests.append(request)
        return DeadlineResponse(status_code=200, body="job-777")

    client = DeadlineClient(DeadlineConfig(mayapy="mayapy"), transport=transport)
    scene = tmp_path / "scene.ma"
    scene.write_text("", encoding="utf-8")

    result = farm_actions.submit_farm_validation_action(
        scene_path=str(scene),
        scene_state=FarmSceneState(),
        validation_result=FarmValidationResult.from_validator_exit_code(0),
        config=DeadlineConfig(),
        connection_state=FarmTabState(
            api_url="http://localhost:8081",
            connection_reachable=True,
        ),
        client_factory=lambda _cfg: client,
    )
    assert result.succeeded is True
    assert result.job_id == "job-777"
    assert result.tab_state.last_job_id == "job-777"
    assert requests


def test_submit_farm_validation_action_blocks_unreachable_service(tmp_path: Path):
    scene = tmp_path / "scene.ma"
    scene.write_text("", encoding="utf-8")
    result = farm_actions.submit_farm_validation_action(
        scene_path=str(scene),
        connection_state=FarmTabState(connection_reachable=False),
    )
    assert result.succeeded is False
    assert "unreachable" in result.message.lower()


def test_default_farm_paths_use_scene_stem(tmp_path: Path):
    scene = tmp_path / "hero.ma"
    assert farm_actions.default_farm_report_path(scene).name == "hero_pipeline_inspector_farm.json"
    assert (
        farm_actions.default_command_script_path(scene).name
        == "hero_pipeline_inspector_deadline_command.txt"
    )
