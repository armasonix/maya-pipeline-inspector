from __future__ import annotations

import pytest

from shader_health.integrations.deadline.eligibility import (
    FarmEligibilityDecision,
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
)

ELIGIBILITY_MATRIX = [
    pytest.param(
        FarmValidationResult(validator_exit_code=VALIDATOR_OK),
        FarmSceneState(),
        FarmEligibilityDecision.ALLOW,
        True,
        SUBMISSION_ALLOWED,
        (),
        (),
        id="allow-clean-validation",
    ),
    pytest.param(
        FarmValidationResult(
            validator_exit_code=VALIDATOR_PUBLISH_BLOCK,
            block_publish=True,
        ),
        FarmSceneState(),
        FarmEligibilityDecision.WARN,
        True,
        SUBMISSION_ALLOWED,
        (),
        ("block_publish",),
        id="warn-publish-block-only",
    ),
    pytest.param(
        FarmValidationResult(
            validator_exit_code=VALIDATOR_DEADLINE_BLOCK,
            block_deadline=True,
        ),
        FarmSceneState(),
        FarmEligibilityDecision.BLOCK,
        False,
        SUBMISSION_BLOCKED,
        ("block_deadline",),
        (),
        id="block-deadline-issues",
    ),
    pytest.param(
        FarmValidationResult(validator_exit_code=VALIDATOR_RUNTIME_ERROR),
        FarmSceneState(),
        FarmEligibilityDecision.BLOCK,
        False,
        PREFLIGHT_ERROR,
        ("validation_error",),
        (),
        id="block-runtime-error",
    ),
    pytest.param(
        FarmValidationResult(validator_exit_code=VALIDATOR_CONFIG_ERROR),
        FarmSceneState(),
        FarmEligibilityDecision.BLOCK,
        False,
        PREFLIGHT_ERROR,
        ("validation_error",),
        (),
        id="block-config-error",
    ),
    pytest.param(
        FarmValidationResult(validator_exit_code=VALIDATOR_OK),
        FarmSceneState(scene_saved=False),
        FarmEligibilityDecision.BLOCK,
        False,
        PREFLIGHT_ERROR,
        ("scene_unsaved",),
        (),
        id="block-unsaved-scene",
    ),
    pytest.param(
        FarmValidationResult(validator_exit_code=VALIDATOR_OK),
        FarmSceneState(renderer_plugin_loaded=False),
        FarmEligibilityDecision.BLOCK,
        False,
        PREFLIGHT_ERROR,
        ("renderer_plugin_missing",),
        (),
        id="block-missing-renderer-plugin",
    ),
    pytest.param(
        FarmValidationResult(
            validator_exit_code=VALIDATOR_PUBLISH_BLOCK,
            block_publish=True,
        ),
        FarmSceneState(scene_saved=False),
        FarmEligibilityDecision.BLOCK,
        False,
        PREFLIGHT_ERROR,
        ("scene_unsaved",),
        (),
        id="unsaved-overrides-publish-warn",
    ),
    pytest.param(
        FarmValidationResult(
            validator_exit_code=VALIDATOR_OK,
            block_deadline=True,
        ),
        FarmSceneState(),
        FarmEligibilityDecision.BLOCK,
        False,
        SUBMISSION_BLOCKED,
        ("block_deadline",),
        (),
        id="block-deadline-flag-with-exit-zero",
    ),
]


@pytest.mark.parametrize(
    (
        "validation_result",
        "scene_state",
        "expected_decision",
        "expected_allowed",
        "expected_exit_code",
        "expected_reasons",
        "expected_warnings",
    ),
    ELIGIBILITY_MATRIX,
)
def test_evaluate_farm_submit_eligibility_matrix(
    validation_result: FarmValidationResult,
    scene_state: FarmSceneState,
    expected_decision: FarmEligibilityDecision,
    expected_allowed: bool,
    expected_exit_code: int,
    expected_reasons: tuple[str, ...],
    expected_warnings: tuple[str, ...],
):
    outcome = evaluate_farm_submit_eligibility(validation_result, scene_state)
    assert outcome.decision is expected_decision
    assert outcome.allowed is expected_allowed
    assert outcome.exit_code == expected_exit_code
    assert outcome.reasons == expected_reasons
    assert outcome.warnings == expected_warnings


def test_farm_validation_result_from_json_report_uses_blocking_section():
    result = FarmValidationResult.from_json_report(
        {
            "block_publish": False,
            "block_deadline": True,
            "blocking": {"publish": False, "deadline": True, "any": True},
        }
    )
    assert result.block_deadline is True
    assert result.validator_exit_code == VALIDATOR_DEADLINE_BLOCK


def test_farm_validation_result_from_validator_exit_code():
    result = FarmValidationResult.from_validator_exit_code(VALIDATOR_PUBLISH_BLOCK)
    assert result.block_publish is True
    assert result.block_deadline is False
