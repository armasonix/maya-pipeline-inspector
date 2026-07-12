from pipeline_inspector.core import RuleResult, compute_health_score


def make_result(
    severity: str,
    *,
    status: str = "failed",
    block_publish: bool = False,
    block_deadline: bool = False,
    auto_fix_available: bool = False,
) -> RuleResult:
    return RuleResult(
        rule_id=f"test.{severity}.{status}",
        severity=severity,
        status=status,
        title="Test Rule",
        message="Test message.",
        why="Test explanation.",
        owner="shader_td",
        block_publish=block_publish,
        block_deadline=block_deadline,
        auto_fix_available=auto_fix_available,
    )


def test_health_score_starts_at_100_without_failed_results():
    score = compute_health_score([])

    assert score.score == 100
    assert score.raw_score == 100
    assert score.to_dict()["score"] == 100


def test_health_score_penalizes_failed_critical_error_warning_only():
    score = compute_health_score(
        [
            make_result("critical"),
            make_result("error"),
            make_result("error"),
            make_result("warning"),
            make_result("warning"),
            make_result("warning"),
            make_result("info"),
        ]
    )

    assert score.raw_score == 46
    assert score.score == 46
    assert score.critical == 1
    assert score.error == 2
    assert score.warning == 3
    assert score.info == 1


def test_health_score_ignores_passed_and_skipped_results():
    score = compute_health_score(
        [
            make_result("critical", status="passed", block_deadline=True),
            make_result("critical", status="skipped", block_publish=True),
            make_result("warning", status="passed"),
        ]
    )

    assert score.score == 100
    assert score.critical == 0
    assert score.warning == 0
    assert score.block_publish is False
    assert score.block_deadline is False


def test_blocking_critical_caps_score_at_49():
    score = compute_health_score(
        [
            make_result("critical", block_publish=True),
        ]
    )

    assert score.raw_score == 75
    assert score.score == 49
    assert score.block_publish is True
    assert score.block_deadline is False
    assert score.capped_by_blocking_critical is True


def test_noncritical_blocking_issue_does_not_apply_critical_cap():
    score = compute_health_score(
        [
            make_result("error", block_deadline=True),
        ]
    )

    assert score.raw_score == 90
    assert score.score == 90
    assert score.block_publish is False
    assert score.block_deadline is True
    assert score.capped_by_blocking_critical is False


def test_health_score_clamps_to_zero():
    score = compute_health_score(
        [
            make_result("critical"),
            make_result("critical"),
            make_result("critical"),
            make_result("critical"),
            make_result("critical"),
        ]
    )

    assert score.raw_score == -25
    assert score.score == 0


def test_health_score_counts_auto_fixable_failed_results():
    score = compute_health_score(
        [
            make_result("warning", auto_fix_available=True),
            make_result("error", auto_fix_available=True),
            make_result("critical", status="passed", auto_fix_available=True),
        ]
    )

    assert score.auto_fixable == 2
