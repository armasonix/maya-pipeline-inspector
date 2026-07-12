"""Material Health Score calculation.

The health score is derived from failed validation results only. Severity and
blocking policy remain separate concepts: a critical issue does not block unless
its result has explicit block flags.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from shader_health.core.rule_schema import RuleResult


@dataclass(frozen=True)
class HealthScore:
    """Computed material/scene health score."""

    score: int
    raw_score: int
    critical: int = 0
    error: int = 0
    warning: int = 0
    info: int = 0
    block_publish: bool = False
    block_deadline: bool = False
    auto_fixable: int = 0
    capped_by_blocking_critical: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "score": self.score,
            "raw_score": self.raw_score,
            "critical": self.critical,
            "error": self.error,
            "warning": self.warning,
            "info": self.info,
            "block_publish": self.block_publish,
            "block_deadline": self.block_deadline,
            "auto_fixable": self.auto_fixable,
            "capped_by_blocking_critical": self.capped_by_blocking_critical,
        }

def compute_health_score(results: Iterable[RuleResult]) -> HealthScore:
    """Compute a simple MVP health score from failed results.

    MVP scoring model:

    - start at 100;
    - failed critical: -25 each;
    - failed error: -10 each;
    - failed warning: -3 each;
    - failed info: -0 each;
    - clamp to 0..100;
    - if a failed critical result explicitly blocks publish or Deadline,
      cap final score at 49.
    """

    critical = 0
    error = 0
    warning = 0
    info = 0
    block_publish = False
    block_deadline = False
    auto_fixable = 0
    capped_by_blocking_critical = False

    for result in results:
        if result.status != "failed":
            continue

        if result.severity == "critical":
            critical += 1
            if result.block_publish or result.block_deadline:
                capped_by_blocking_critical = True
        elif result.severity == "error":
            error += 1
        elif result.severity == "warning":
            warning += 1
        elif result.severity == "info":
            info += 1

        block_publish = block_publish or result.block_publish
        block_deadline = block_deadline or result.block_deadline
        if result.auto_fix_available:
            auto_fixable += 1

    raw_score = 100 - critical * 25 - error * 10 - warning * 3
    score = max(0, min(100, raw_score))

    if capped_by_blocking_critical:
        score = min(score, 49)

    return HealthScore(
        score=score,
        raw_score=raw_score,
        critical=critical,
        error=error,
        warning=warning,
        info=info,
        block_publish=block_publish,
        block_deadline=block_deadline,
        auto_fixable=auto_fixable,
        capped_by_blocking_critical=capped_by_blocking_critical,
    )
