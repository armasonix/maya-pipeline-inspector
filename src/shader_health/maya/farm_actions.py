"""Maya Farm tab actions for Deadline integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shader_health.integrations.deadline import (
    DeadlineClient,
    DeadlineConfig,
    DeadlineSubmitError,
    FarmSceneState,
    FarmValidationResult,
    evaluate_farm_submit_eligibility,
    submit_shader_health_validation_job,
)
from shader_health.integrations.deadline.eligibility import FarmEligibilityResult
from shader_health.ui.farm_tab import FarmTabState

RENDERER_PLUGIN_CANDIDATES = {
    "vray": ("vrayformaya", "vray"),
    "arnold": ("mtoa",),
}


@dataclass(frozen=True)
class FarmPreflightActionResult:
    """Result from an in-panel farm preflight run."""

    succeeded: bool
    message: str
    tab_state: FarmTabState
    eligibility: FarmEligibilityResult | None = None


@dataclass(frozen=True)
class FarmSubmitActionResult:
    """Result from submitting a farm validation utility job."""

    succeeded: bool
    message: str
    tab_state: FarmTabState
    job_id: str = ""


DeadlineClientFactory = Callable[[DeadlineConfig], DeadlineClient]


def collect_farm_scene_state(*, cmds: Any | None = None) -> FarmSceneState:
    """Collect Maya scene readiness signals for the farm eligibility gate."""

    maya_cmds = cmds or _maya_cmds()
    scene_saved = not bool(maya_cmds.file(query=True, modified=True))
    return FarmSceneState(
        scene_saved=scene_saved,
        renderer_plugin_loaded=_renderer_plugin_loaded(maya_cmds),
    )


def farm_validation_result_from_summary(summary: Any) -> FarmValidationResult:
    """Build a farm validation result from a validation summary object."""

    block_publish = bool(getattr(summary, "block_publish", False))
    block_deadline = bool(getattr(summary, "block_deadline", False))
    return FarmValidationResult(
        validator_exit_code=_validator_exit_code_from_blocks(
            block_publish=block_publish,
            block_deadline=block_deadline,
        ),
        block_publish=block_publish,
        block_deadline=block_deadline,
    )


def default_farm_report_path(scene_path: str | Path) -> Path:
    """Return the default JSON report path written by farm validation."""

    scene = Path(scene_path)
    return scene.with_name(f"{scene.stem}_shader_health_farm.json")


def default_command_script_path(scene_path: str | Path) -> Path:
    """Return the default CommandScript aux file path beside the scene."""

    scene = Path(scene_path)
    return scene.with_name(f"{scene.stem}_shader_health_deadline_command.txt")


def check_deadline_connection(
    config: DeadlineConfig | None = None,
    *,
    client_factory: DeadlineClientFactory | None = None,
) -> FarmTabState:
    """Ping the configured Deadline Web Service and return connection status."""

    effective_config = config or DeadlineConfig.from_env()
    factory = client_factory or (lambda cfg: DeadlineClient(cfg))
    client = factory(effective_config)
    try:
        reachable = client.ping()
    except Exception as exc:  # noqa: BLE001
        return FarmTabState(
            api_url=effective_config.api_url,
            connection_status=f"error: {exc}",
            connection_reachable=False,
            status_message="Deadline connection check failed.",
        )
    status = "connected" if reachable else "no response"
    return FarmTabState(
        api_url=effective_config.api_url,
        connection_status=status,
        connection_reachable=reachable,
        status_message=(
            "Deadline Web Service is reachable."
            if reachable
            else "Deadline Web Service did not respond to ping."
        ),
    )


def run_farm_preflight_action(
    *,
    summary: Any | None,
    scene_state: FarmSceneState | None = None,
    config: DeadlineConfig | None = None,
    connection_state: FarmTabState | None = None,
    last_job_id: str = "",
) -> FarmPreflightActionResult:
    """Evaluate farm eligibility from the latest validation summary."""

    effective_config = config or DeadlineConfig.from_env()
    base_state = connection_state or check_deadline_connection(effective_config)
    effective_scene_state = scene_state or collect_farm_scene_state()
    if summary is None:
        return FarmPreflightActionResult(
            succeeded=False,
            message="Validate the scene first, then run Farm Preflight.",
            tab_state=_merge_tab_state(
                base_state,
                scene_state=effective_scene_state,
                last_job_id=last_job_id,
                status_message="Farm preflight requires a validation summary.",
            ),
        )

    validation_result = farm_validation_result_from_summary(summary)
    eligibility = evaluate_farm_submit_eligibility(validation_result, effective_scene_state)
    message = _eligibility_message(eligibility)
    scene_path = _safe_current_scene_path()
    last_report = str(default_farm_report_path(scene_path)) if scene_path else ""
    return FarmPreflightActionResult(
        succeeded=eligibility.allowed,
        message=message,
        eligibility=eligibility,
        tab_state=_merge_tab_state(
            base_state,
            scene_state=effective_scene_state,
            eligibility=eligibility,
            last_report_path=last_report,
            last_job_id=last_job_id,
            status_message=message,
        ),
    )


def submit_farm_validation_action(
    *,
    scene_path: str,
    scene_state: FarmSceneState | None = None,
    validation_result: FarmValidationResult | None = None,
    config: DeadlineConfig | None = None,
    connection_state: FarmTabState | None = None,
    command_script_path: Path | None = None,
    report_path: Path | None = None,
    client_factory: DeadlineClientFactory | None = None,
) -> FarmSubmitActionResult:
    """Submit a Deadline CommandScript utility job for Shader Health validation."""

    if not scene_path:
        return FarmSubmitActionResult(
            succeeded=False,
            message="Save the scene before submitting farm validation.",
            tab_state=FarmTabState(status_message="Farm submit requires a saved scene path."),
        )

    effective_config = config or DeadlineConfig.from_env()
    base_state = connection_state or check_deadline_connection(
        effective_config,
        client_factory=client_factory,
    )
    if not base_state.connection_reachable:
        return FarmSubmitActionResult(
            succeeded=False,
            message="Deadline Web Service is unreachable. Refresh connection and retry.",
            tab_state=base_state,
        )

    effective_scene_state = scene_state or collect_farm_scene_state()
    scene = Path(scene_path)
    effective_report = report_path or default_farm_report_path(scene)
    effective_command_script = command_script_path or default_command_script_path(scene)
    factory = client_factory or (lambda cfg: DeadlineClient(cfg))
    client = factory(effective_config)

    try:
        submit_result = submit_shader_health_validation_job(
            client=client,
            scene_path=scene,
            report_path=effective_report,
            config=effective_config,
            command_script_path=effective_command_script,
            scene_state=effective_scene_state,
            validation_result=validation_result,
        )
    except DeadlineSubmitError as exc:
        eligibility = None
        if validation_result is not None:
            eligibility = evaluate_farm_submit_eligibility(
                validation_result,
                effective_scene_state,
            )
        return FarmSubmitActionResult(
            succeeded=False,
            message=str(exc),
            tab_state=_merge_tab_state(
                base_state,
                scene_state=effective_scene_state,
                eligibility=eligibility,
                last_report_path=str(effective_report),
                status_message=str(exc),
            ),
        )

    message = (
        f"Submitted Deadline validation job {submit_result.job_id}. "
        f"Report path: {submit_result.report_path}"
    )
    eligibility = submit_result.eligibility
    return FarmSubmitActionResult(
        succeeded=True,
        message=message,
        job_id=submit_result.job_id,
        tab_state=_merge_tab_state(
            base_state,
            scene_state=effective_scene_state,
            eligibility=eligibility,
            last_report_path=str(submit_result.report_path),
            last_job_id=submit_result.job_id,
            status_message=message,
        ),
    )


def _merge_tab_state(
    base: FarmTabState,
    *,
    scene_state: FarmSceneState,
    eligibility: FarmEligibilityResult | None = None,
    last_report_path: str = "",
    last_job_id: str = "",
    status_message: str = "",
) -> FarmTabState:
    return FarmTabState(
        integration_enabled=base.integration_enabled,
        api_url=base.api_url,
        connection_status=base.connection_status,
        connection_reachable=base.connection_reachable,
        scene_saved=scene_state.scene_saved,
        renderer_plugin_loaded=scene_state.renderer_plugin_loaded,
        eligibility_decision=(
            eligibility.decision.value if eligibility else base.eligibility_decision
        ),
        eligibility_allowed=eligibility.allowed if eligibility else base.eligibility_allowed,
        last_report_path=last_report_path or base.last_report_path,
        last_job_id=last_job_id or base.last_job_id,
        status_message=status_message or base.status_message,
    )


def _eligibility_message(eligibility: FarmEligibilityResult) -> str:
    if eligibility.decision.value == "warn":
        warnings = ", ".join(eligibility.warnings) or "publish-only issues"
        return f"Farm preflight warning: {warnings}. Submission may proceed with caution."
    if eligibility.allowed:
        return "Farm preflight passed. Scene is eligible for farm validation submit."
    reasons = ", ".join(eligibility.reasons) or "blocked"
    return f"Farm preflight blocked: {reasons}."


def _renderer_plugin_loaded(cmds: Any) -> bool:
    renderer = ""
    if cmds.objExists("defaultRenderGlobals"):
        renderer = str(cmds.getAttr("defaultRenderGlobals.currentRenderer") or "").strip().lower()
    candidates = RENDERER_PLUGIN_CANDIDATES.get(renderer, ())
    if not candidates:
        return True
    return any(cmds.pluginInfo(plugin_name, query=True, loaded=True) for plugin_name in candidates)


def _validator_exit_code_from_blocks(*, block_publish: bool, block_deadline: bool) -> int:
    if block_deadline:
        return 2
    if block_publish:
        return 1
    return 0


def _current_scene_path() -> str:
    return _safe_current_scene_path()


def _safe_current_scene_path() -> str:
    try:
        return str(_maya_cmds().file(query=True, sceneName=True) or "")
    except (ImportError, ModuleNotFoundError):
        return ""


def _maya_cmds() -> Any:
    import maya.cmds as cmds  # type: ignore[import-not-found]

    return cmds
