"""Maya Farm tab actions for Deadline integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pipeline_inspector.integrations.deadline import (
    DeadlineClient,
    DeadlineConfig,
    DeadlineSubmitError,
    FarmAnalyticsReport,
    FarmSceneState,
    FarmValidationResult,
    collect_farm_analytics,
    evaluate_farm_submit_eligibility,
    format_farm_analytics_summary,
    submit_pipeline_inspector_validation_job,
)
from pipeline_inspector.integrations.deadline.eligibility import FarmEligibilityResult
from pipeline_inspector.ui.farm_tab import FarmTabState

if TYPE_CHECKING:
    from pipeline_inspector.maya.export_actions import ExportActionResult

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
    return scene.with_name(f"{scene.stem}_pipeline_inspector_farm.json")

def default_command_script_path(scene_path: str | Path) -> Path:
    """Return the default CommandScript aux file path beside the scene."""

    scene = Path(scene_path)
    return scene.with_name(f"{scene.stem}_pipeline_inspector_deadline_command.txt")

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


def collect_farm_analytics_report(
    config: DeadlineConfig | None = None,
    *,
    pool_filter: str | None = None,
    client_factory: DeadlineClientFactory | None = None,
    window_hours: float = 24.0,
    history_path: str | Path | None = None,
    shot_key_pattern: str | None = None,
) -> FarmAnalyticsReport:
    """Collect Deadline farm analytics for the Farm tab or headless callers."""

    effective_config = config or DeadlineConfig.from_env()
    factory = client_factory or (lambda cfg: DeadlineClient(cfg))
    return collect_farm_analytics(
        factory(effective_config),
        pool_filter=pool_filter,
        window_hours=window_hours,
        history_path=history_path,
        shot_key_pattern=shot_key_pattern,
    )


def format_farm_analytics_status(report: FarmAnalyticsReport) -> str:
    """Return a Farm-tab friendly analytics status line."""

    return format_farm_analytics_summary(report)


def export_farm_html_report(
    path: str | Path | None = None,
    *,
    config: DeadlineConfig | None = None,
    pool_filter: str | None = None,
    window_hours: float = 24.0,
    client_factory: DeadlineClientFactory | None = None,
    scene_path: str | Path | None = None,
) -> ExportActionResult:
    """Collect farm analytics and write a management HTML report."""

    from pipeline_inspector.maya.export_actions import ExportActionResult
    from pipeline_inspector.reports.farm_html_report import write_farm_html_report

    effective_config = config or DeadlineConfig.from_env()
    report = collect_farm_analytics_report(
        effective_config,
        pool_filter=pool_filter,
        client_factory=client_factory,
        window_hours=window_hours,
    )
    output_path = _farm_html_report_path(path, scene_path)
    written_path = write_farm_html_report(
        output_path,
        report,
        api_url=effective_config.api_url,
    )
    return ExportActionResult(
        action="export_farm_html_report",
        path=str(written_path),
        succeeded=True,
        message="Deadline farm HTML report exported.",
    )


def _farm_html_report_path(
    path: str | Path | None,
    scene_path: str | Path | None,
) -> Path:
    if path:
        return Path(path)
    scene = Path(str(scene_path or "unsaved_scene.ma"))
    stem = scene.stem or "unsaved_scene"
    return scene.with_name(f"{stem}_deadline_farm_report.html")


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
    """Submit a Deadline CommandScript utility job for Pipeline Inspector validation."""

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
        submit_result = submit_pipeline_inspector_validation_job(
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
    import maya.cmds as cmds

    return cmds
