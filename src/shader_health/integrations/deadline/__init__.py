"""Thinkbox Deadline 10 on-prem integration for Shader Health Inspector."""

from shader_health.integrations.deadline.client import (
    DeadlineClient,
    DeadlineClientError,
    DeadlineResponse,
    HttpRequest,
    HttpTransport,
    default_http_transport,
)
from shader_health.integrations.deadline.config import (
    DEFAULT_PROFILE_ID,
    DeadlineConfig,
)
from shader_health.integrations.deadline.eligibility import (
    FarmEligibilityDecision,
    FarmEligibilityResult,
    FarmSceneState,
    FarmValidationResult,
    evaluate_farm_submit_eligibility,
)
from shader_health.integrations.deadline.preflight import (
    PREFLIGHT_ERROR,
    SUBMISSION_ALLOWED,
    SUBMISSION_BLOCKED,
    VALIDATOR_CONFIG_ERROR,
    VALIDATOR_DEADLINE_BLOCK,
    VALIDATOR_OK,
    VALIDATOR_PUBLISH_BLOCK,
    VALIDATOR_RUNTIME_ERROR,
    DeadlinePreflightResult,
    blocked_message,
    build_validator_command,
    run_deadline_preflight,
)

__all__ = [
    "DEFAULT_PROFILE_ID",
    "DeadlineClient",
    "DeadlineClientError",
    "DeadlineConfig",
    "DeadlinePreflightResult",
    "DeadlineResponse",
    "FarmEligibilityDecision",
    "FarmEligibilityResult",
    "FarmSceneState",
    "FarmValidationResult",
    "HttpRequest",
    "HttpTransport",
    "PREFLIGHT_ERROR",
    "SUBMISSION_ALLOWED",
    "SUBMISSION_BLOCKED",
    "VALIDATOR_CONFIG_ERROR",
    "VALIDATOR_DEADLINE_BLOCK",
    "VALIDATOR_OK",
    "VALIDATOR_PUBLISH_BLOCK",
    "VALIDATOR_RUNTIME_ERROR",
    "blocked_message",
    "build_validator_command",
    "default_http_transport",
    "evaluate_farm_submit_eligibility",
    "run_deadline_preflight",
]
