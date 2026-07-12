from __future__ import annotations

from pathlib import Path

import pytest

from pipeline_inspector.core import GraphSnapshot, RuleResult
from pipeline_inspector.core.waivers import (
    WaiverSidecar,
    apply_waivers,
    create_waiver_from_result,
    load_waiver_sidecar,
    revoke_waiver,
    write_waiver_sidecar,
)
from pipeline_inspector.reports import build_json_report


def test_create_waiver_from_issue_result():
    result = _failed_result()

    waiver = create_waiver_from_result(
        result,
        reason="Approved hero close-up exception.",
        approved_by="supervisor",
        created_at_utc="2026-07-02T08:00:00Z",
        expires_at_utc="2026-08-02T08:00:00Z",
    )

    assert waiver.rule_id == result.rule_id
    assert waiver.target_id == result.target_id
    assert waiver.target_node == result.node
    assert waiver.matches(result) is True


def test_load_and_write_waiver_sidecar(tmp_path: Path):
    sidecar = WaiverSidecar((_waiver(),))
    path = tmp_path / "scene.pipeline_inspector_waivers.json"

    write_waiver_sidecar(path, sidecar)
    loaded = load_waiver_sidecar(path)

    assert loaded.to_dict() == sidecar.to_dict()


def test_apply_waivers_marks_matching_failed_result_as_waived():
    result = _failed_result()
    sidecar = WaiverSidecar((_waiver(),))

    waived = apply_waivers(
        [result],
        sidecar,
        now_utc="2026-07-03T08:00:00Z",
    )[0]

    assert waived.status == "waived"
    assert waived.block_publish is False
    assert waived.block_deadline is False
    assert waived.auto_fix_available is False
    assert waived.evidence["waiver"]["reason"] == "Approved exception."


def test_expired_waiver_is_ignored():
    result = _failed_result()
    expired = _waiver(expires_at_utc="2026-07-01T08:00:00Z")

    resolved = apply_waivers(
        [result],
        WaiverSidecar((expired,)),
        now_utc="2026-07-03T08:00:00Z",
    )[0]

    assert resolved.status == "failed"
    assert resolved.block_publish is True


def test_json_report_includes_waived_issue():
    waived = apply_waivers(
        [_failed_result()],
        WaiverSidecar((_waiver(),)),
        now_utc="2026-07-03T08:00:00Z",
    )

    report = build_json_report(GraphSnapshot(), waived)

    assert report["status"] == "passed"
    assert report["results"][0]["status"] == "waived"
    assert report["results"][0]["evidence"]["waiver"]["approved_by"] == "lead"


def test_revoke_waiver_removes_record_and_round_trips(tmp_path: Path):
    sidecar = WaiverSidecar((_waiver(),))
    path = tmp_path / "scene.pipeline_inspector_waivers.json"
    write_waiver_sidecar(path, sidecar)

    updated = revoke_waiver(sidecar, sidecar.waivers[0].id)
    write_waiver_sidecar(path, updated)
    loaded = load_waiver_sidecar(path)

    assert loaded.waivers == ()
    assert updated.to_dict() == loaded.to_dict()


def test_revoke_waiver_unknown_id_raises():
    sidecar = WaiverSidecar((_waiver(),))

    with pytest.raises(ValueError, match="Unknown waiver id"):
        revoke_waiver(sidecar, "missing-waiver-id")


def test_waiver_status_label_marks_expired_records():
    active = _waiver(expires_at_utc="2026-08-02T08:00:00Z")
    expired = _waiver(expires_at_utc="2026-07-01T08:00:00Z")

    from pipeline_inspector.core.waivers import waiver_status_label

    assert waiver_status_label(active, now_utc="2026-07-03T08:00:00Z") == "active"
    assert waiver_status_label(expired, now_utc="2026-07-03T08:00:00Z") == "expired"


def _waiver(*, expires_at_utc: str = "2026-08-02T08:00:00Z"):
    return create_waiver_from_result(
        _failed_result(),
        reason="Approved exception.",
        approved_by="lead",
        created_at_utc="2026-07-02T08:00:00Z",
        expires_at_utc=expires_at_utc,
    )


def _failed_result() -> RuleResult:
    return RuleResult(
        rule_id="common.texture.colorspace.data_raw",
        severity="critical",
        status="failed",
        title="Data textures must use Raw color space",
        message="Data texture uses color space.",
        why="Data textures must not be color transformed.",
        owner="shader_td",
        target_kind="node",
        target_id="node:file1",
        node="file1",
        plug="colorSpace",
        current_value="ACEScg",
        expected_value="Raw",
        block_publish=True,
        block_deadline=True,
        auto_fix_available=True,
        fix_id="set_attr",
    )
