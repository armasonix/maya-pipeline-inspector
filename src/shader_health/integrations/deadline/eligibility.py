"""Farm submit eligibility gate for Deadline integration."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from shader_health.integrations.deadline.preflight import (
    PREFLIGHT_ERROR,
    SUBMISSION_ALLOWED,
    SUBMISSION_BLOCKED,
    VALIDATOR_CONFIG_ERROR,
    VALIDATOR_DEADLINE_BLOCK,
    VALIDATOR_OK,
    VALIDATOR_PUBLISH_BLOCK,
    VALIDATOR_RUNTIME_ERROR,
)


class FarmEligibilityDecision(str, Enum):
    """High-level farm submit decision."""

    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"

@dataclass(frozen=True)
class FarmSceneState:
    """Maya scene context evaluated alongside validation output."""

    scene_saved: bool = True
    renderer_plugin_loaded: bool = True

@dataclass(frozen=True)
class FarmValidationResult:
    """Normalized validation outcome for farm eligibility checks."""

    validator_exit_code: int
    block_publish: bool = False
    block_deadline: bool = False

    @classmethod
    def from_validator_exit_code(cls, validator_exit_code: int) -> FarmValidationResult:
        """Build a result using validator exit-code semantics only."""

        block_publish = validator_exit_code == VALIDATOR_PUBLISH_BLOCK
        block_deadline = validator_exit_code == VALIDATOR_DEADLINE_BLOCK
        return cls(
            validator_exit_code=validator_exit_code,
            block_publish=block_publish,
            block_deadline=block_deadline,
        )

    @classmethod
    def from_json_report(cls, report: Mapping[str, Any]) -> FarmValidationResult:
        """Build a result from a Shader Health JSON report payload."""

        block_publish = bool(report.get("block_publish", False))
        block_deadline = bool(report.get("block_deadline", False))
        blocking = report.get("blocking")
        if isinstance(blocking, Mapping):
            block_publish = block_publish or bool(blocking.get("publish", False))
            block_deadline = block_deadline or bool(blocking.get("deadline", False))

        score = report.get("score")
        if isinstance(score, Mapping):
            block_publish = block_publish or bool(score.get("block_publish", False))
            block_deadline = block_deadline or bool(score.get("block_deadline", False))

        return cls(
            validator_exit_code=_validator_exit_code_from_blocks(
                block_publish=block_publish,
                block_deadline=block_deadline,
            ),
            block_publish=block_publish,
            block_deadline=block_deadline,
        )

@dataclass(frozen=True)
class FarmEligibilityResult:
    """Farm submit eligibility decision with machine-readable reasons."""

    decision: FarmEligibilityDecision
    allowed: bool
    exit_code: int
    reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

def evaluate_farm_submit_eligibility(
    result: FarmValidationResult,
    scene_state: FarmSceneState,
) -> FarmEligibilityResult:
    """Evaluate whether a scene can be submitted to the farm.

    Priority order:

    1. Block on validator runtime/config errors.
    2. Block on unsaved scenes.
    3. Block on missing renderer plug-ins.
    4. Block on ``block_deadline`` / validator exit code 2.
    5. Warn (but allow) on publish-only blocking issues.
    6. Allow when validator exit code is 0 with no blockers.
    """

    if result.validator_exit_code in (VALIDATOR_RUNTIME_ERROR, VALIDATOR_CONFIG_ERROR):
        return _blocked(
            exit_code=PREFLIGHT_ERROR,
            reasons=("validation_error",),
        )

    if not scene_state.scene_saved:
        return _blocked(
            exit_code=PREFLIGHT_ERROR,
            reasons=("scene_unsaved",),
        )

    if not scene_state.renderer_plugin_loaded:
        return _blocked(
            exit_code=PREFLIGHT_ERROR,
            reasons=("renderer_plugin_missing",),
        )

    if result.block_deadline or result.validator_exit_code == VALIDATOR_DEADLINE_BLOCK:
        return _blocked(
            exit_code=SUBMISSION_BLOCKED,
            reasons=("block_deadline",),
        )

    if result.block_publish or result.validator_exit_code == VALIDATOR_PUBLISH_BLOCK:
        return FarmEligibilityResult(
            decision=FarmEligibilityDecision.WARN,
            allowed=True,
            exit_code=SUBMISSION_ALLOWED,
            warnings=("block_publish",),
        )

    if result.validator_exit_code == VALIDATOR_OK:
        return FarmEligibilityResult(
            decision=FarmEligibilityDecision.ALLOW,
            allowed=True,
            exit_code=SUBMISSION_ALLOWED,
        )

    return _blocked(
        exit_code=PREFLIGHT_ERROR,
        reasons=("validation_error",),
    )

def _blocked(*, exit_code: int, reasons: tuple[str, ...]) -> FarmEligibilityResult:
    return FarmEligibilityResult(
        decision=FarmEligibilityDecision.BLOCK,
        allowed=False,
        exit_code=exit_code,
        reasons=reasons,
    )

def _validator_exit_code_from_blocks(
    *,
    block_publish: bool,
    block_deadline: bool,
) -> int:
    if block_deadline:
        return VALIDATOR_DEADLINE_BLOCK
    if block_publish:
        return VALIDATOR_PUBLISH_BLOCK
    return VALIDATOR_OK
