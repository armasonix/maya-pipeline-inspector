"""Shared notification trigger IDs and validation event matching."""
from __future__ import annotations

from dataclasses import dataclass

NOTIFY_EVENT_BLOCK_PUBLISH = "block_publish"
NOTIFY_EVENT_BLOCK_DEADLINE = "block_deadline"
NOTIFY_EVENT_ON_PASS = "on_pass"
NOTIFY_EVENT_ON_CRITICAL = "on_critical"
NOTIFY_EVENT_ON_FAIL = "on_fail"
NOTIFY_EVENT_ON_READINESS_FAIL = "on_readiness_fail"
NOTIFY_EVENT_ON_FARM_COMPLETE = "on_farm_complete"
NOTIFY_EVENT_SCORE_BELOW = "score_below"

NOTIFY_EVENT_LABELS: dict[str, str] = {
    NOTIFY_EVENT_BLOCK_PUBLISH: "Publish block",
    NOTIFY_EVENT_BLOCK_DEADLINE: "Deadline block",
    NOTIFY_EVENT_ON_PASS: "Validation pass",
    NOTIFY_EVENT_ON_CRITICAL: "Critical issues",
    NOTIFY_EVENT_ON_FAIL: "Failed issues",
    NOTIFY_EVENT_ON_READINESS_FAIL: "Readiness fail",
    NOTIFY_EVENT_ON_FARM_COMPLETE: "Farm job complete",
    NOTIFY_EVENT_SCORE_BELOW: "Score below threshold",
}

VALIDATION_NOTIFY_EVENTS: tuple[tuple[str, str], ...] = (
    (NOTIFY_EVENT_BLOCK_PUBLISH, NOTIFY_EVENT_LABELS[NOTIFY_EVENT_BLOCK_PUBLISH]),
    (NOTIFY_EVENT_BLOCK_DEADLINE, NOTIFY_EVENT_LABELS[NOTIFY_EVENT_BLOCK_DEADLINE]),
    (NOTIFY_EVENT_ON_PASS, NOTIFY_EVENT_LABELS[NOTIFY_EVENT_ON_PASS]),
    (NOTIFY_EVENT_ON_CRITICAL, NOTIFY_EVENT_LABELS[NOTIFY_EVENT_ON_CRITICAL]),
    (NOTIFY_EVENT_ON_FAIL, NOTIFY_EVENT_LABELS[NOTIFY_EVENT_ON_FAIL]),
    (NOTIFY_EVENT_SCORE_BELOW, NOTIFY_EVENT_LABELS[NOTIFY_EVENT_SCORE_BELOW]),
)

STANDALONE_NOTIFY_EVENTS: tuple[tuple[str, str], ...] = (
    (NOTIFY_EVENT_ON_READINESS_FAIL, NOTIFY_EVENT_LABELS[NOTIFY_EVENT_ON_READINESS_FAIL]),
    (NOTIFY_EVENT_ON_FARM_COMPLETE, NOTIFY_EVENT_LABELS[NOTIFY_EVENT_ON_FARM_COMPLETE]),
)

CONNECTOR_NOTIFY_EVENTS: tuple[tuple[str, str], ...] = (
    *VALIDATION_NOTIFY_EVENTS,
    *STANDALONE_NOTIFY_EVENTS,
)


@dataclass(frozen=True)
class ValidationTriggerContext:
    """Normalized validation state used to evaluate notify triggers."""

    block_publish: bool
    block_deadline: bool
    critical_count: int
    health_score: int
    failed_count: int = 0


def describe_validation_notify_skip(
    notify_on: tuple[str, ...],
    context: ValidationTriggerContext,
    *,
    notify_score_below: int | None = None,
) -> str:
    """Explain why no validation notify triggers matched."""

    threshold = int(notify_score_below or 0)
    return (
        "no_matching_events "
        f"(critical={context.critical_count}, failed={context.failed_count}, "
        f"score={context.health_score}, threshold={threshold}, "
        f"block_publish={context.block_publish}, block_deadline={context.block_deadline})"
    )


def validation_trigger_context_from_counts(
    *,
    block_publish: bool,
    block_deadline: bool,
    critical_count: int,
    health_score: int,
    error_count: int = 0,
    warning_count: int = 0,
) -> ValidationTriggerContext:
    """Build a trigger context from validation severity counts."""

    return ValidationTriggerContext(
        block_publish=block_publish,
        block_deadline=block_deadline,
        critical_count=int(critical_count),
        health_score=int(health_score),
        failed_count=int(critical_count) + int(error_count) + int(warning_count),
    )


def match_validation_notify_events(
    notify_on: tuple[str, ...],
    context: ValidationTriggerContext,
    *,
    notify_score_below: int | None = None,
) -> tuple[str, ...]:
    """Return configured validation events that match the current run state."""

    configured = set(notify_on)
    matched: list[str] = []

    if context.block_publish and NOTIFY_EVENT_BLOCK_PUBLISH in configured:
        matched.append(NOTIFY_EVENT_BLOCK_PUBLISH)
    if context.block_deadline and NOTIFY_EVENT_BLOCK_DEADLINE in configured:
        matched.append(NOTIFY_EVENT_BLOCK_DEADLINE)
    if context.critical_count > 0 and NOTIFY_EVENT_ON_CRITICAL in configured:
        matched.append(NOTIFY_EVENT_ON_CRITICAL)
    if context.failed_count > 0 and NOTIFY_EVENT_ON_FAIL in configured:
        matched.append(NOTIFY_EVENT_ON_FAIL)
    if (
        not context.block_publish
        and not context.block_deadline
        and context.critical_count == 0
        and NOTIFY_EVENT_ON_PASS in configured
    ):
        matched.append(NOTIFY_EVENT_ON_PASS)
    threshold = int(notify_score_below or 0)
    if (
        threshold > 0
        and context.health_score < threshold
        and NOTIFY_EVENT_SCORE_BELOW in configured
    ):
        matched.append(NOTIFY_EVENT_SCORE_BELOW)

    return tuple(matched)


def standalone_event_enabled(notify_on: tuple[str, ...], event_id: str) -> bool:
    """Return True when a standalone trigger is enabled in connector settings."""

    return event_id in notify_on
