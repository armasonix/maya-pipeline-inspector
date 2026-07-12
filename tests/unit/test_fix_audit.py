from __future__ import annotations

from pathlib import Path

from pipeline_inspector.core import GraphSnapshot
from pipeline_inspector.core.fix_audit import (
    FIX_AUDIT_SCHEMA_VERSION,
    FixAuditSession,
    FixAuditSidecar,
    append_fix_audit_session,
    build_fix_audit_session,
    load_fix_audit_sidecar,
    write_fix_audit_sidecar,
)
from pipeline_inspector.maya.fix_applier import AppliedFixRecord, ApplyFixReport
from pipeline_inspector.maya.validation_pipeline import (
    fix_audit_sidecar_path_for_scene,
    persist_fix_apply_audit,
)
from pipeline_inspector.reports import build_json_report


def test_fix_audit_sidecar_path_for_scene():
    path = fix_audit_sidecar_path_for_scene("D:/show/asset/shading/hero.ma")

    assert path == Path("D:/show/asset/shading/hero.pipeline_inspector_fix_audit.json")


def test_build_fix_audit_session_sorts_records_by_fix_id():
    report = ApplyFixReport(
        records=(
            AppliedFixRecord(
                fix_id="z.fix",
                rule_id="rule.z",
                fix_type="set_attr",
                target_node="file2",
                target_attr="colorSpace",
                before_value="Raw",
                after_value="sRGB",
                applied=True,
                message="Fix applied.",
            ),
            AppliedFixRecord(
                fix_id="a.fix",
                rule_id="rule.a",
                fix_type="set_attr",
                target_node="file1",
                target_attr="colorSpace",
                before_value="ACEScg",
                after_value="Raw",
                applied=True,
                message="Fix applied.",
            ),
        ),
        undo_chunk_name="Pipeline Inspector Apply Fixes",
    )

    session = build_fix_audit_session(
        scene_path="D:/show/asset/shading/hero.ma",
        profile_id="artist_relaxed",
        apply_report=report,
        applied_at_utc="2026-07-03T12:00:00Z",
    )

    assert session.scene_path == "D:/show/asset/shading/hero.ma"
    assert session.profile_id == "artist_relaxed"
    assert session.undo_chunk_name == "Pipeline Inspector Apply Fixes"
    assert session.total == 2
    assert session.applied_count == 2
    assert [record["fix_id"] for record in session.records] == ["a.fix", "z.fix"]


def test_load_and_write_fix_audit_sidecar_round_trip(tmp_path: Path):
    session = _sample_session()
    sidecar = FixAuditSidecar(scene_path=session.scene_path, sessions=(session,))
    path = tmp_path / "hero.pipeline_inspector_fix_audit.json"

    write_fix_audit_sidecar(path, sidecar)
    loaded = load_fix_audit_sidecar(path)

    assert loaded.to_dict() == sidecar.to_dict()
    assert loaded.to_dict()["fix_audit_schema_version"] == FIX_AUDIT_SCHEMA_VERSION


def test_append_fix_audit_session_preserves_existing_sessions(tmp_path: Path):
    path = tmp_path / "hero.pipeline_inspector_fix_audit.json"
    first = _sample_session(applied_at_utc="2026-07-03T12:00:00Z")
    second = _sample_session(
        applied_at_utc="2026-07-03T13:00:00Z",
        applied_count=1,
        total=1,
    )

    append_fix_audit_session(path, first)
    append_fix_audit_session(path, second)
    loaded = load_fix_audit_sidecar(path)

    assert len(loaded.sessions) == 2
    assert [item.applied_at_utc for item in loaded.sessions] == [
        "2026-07-03T12:00:00Z",
        "2026-07-03T13:00:00Z",
    ]


def test_persist_fix_apply_audit_writes_sidecar_beside_scene(tmp_path: Path):
    scene_path = tmp_path / "hero.ma"
    scene_path.write_text("scene", encoding="utf-8")
    report = ApplyFixReport(
        records=(
            AppliedFixRecord(
                fix_id="fix.1",
                rule_id="rule.1",
                fix_type="set_attr",
                target_node="file1",
                target_attr="colorSpace",
                before_value="ACEScg",
                after_value="Raw",
                applied=True,
                message="Fix applied.",
            ),
        ),
    )

    written_path, session_dict = persist_fix_apply_audit(
        report,
        scene_path=str(scene_path),
        profile_id="artist_relaxed",
        applied_at_utc="2026-07-03T12:00:00Z",
    )

    assert written_path == scene_path.with_name("hero.pipeline_inspector_fix_audit.json")
    assert session_dict["profile_id"] == "artist_relaxed"
    assert session_dict["records"][0]["fix_id"] == "fix.1"
    loaded = load_fix_audit_sidecar(written_path)
    assert len(loaded.sessions) == 1


def test_json_report_includes_fix_audit_when_provided():
    snapshot = GraphSnapshot(
        scene_path="D:/show/asset/shading/demo.ma",
        maya_version="2025",
        renderer="vray",
        scan_scope="scene",
        scanned_at_utc="2026-07-01T12:00:00Z",
    )
    fix_audit = _sample_session().to_dict()

    report = build_json_report(snapshot, (), fix_audit=fix_audit)

    assert report["fix_audit"] == fix_audit


def test_json_report_omits_fix_audit_without_session_apply():
    snapshot = GraphSnapshot(
        scene_path="D:/show/asset/shading/demo.ma",
        maya_version="2025",
        renderer="vray",
        scan_scope="scene",
        scanned_at_utc="2026-07-01T12:00:00Z",
    )

    report = build_json_report(snapshot, ())

    assert "fix_audit" not in report


def _sample_session(
    *,
    applied_at_utc: str = "2026-07-03T12:00:00Z",
    applied_count: int = 2,
    total: int = 2,
) -> FixAuditSession:
    return FixAuditSession(
        applied_at_utc=applied_at_utc,
        scene_path="D:/show/asset/shading/hero.ma",
        profile_id="artist_relaxed",
        undo_chunk_name="Pipeline Inspector Apply Fixes",
        total=total,
        applied_count=applied_count,
        blocked_count=0,
        failed_count=0,
        records=(
            {
                "fix_id": "a.fix",
                "rule_id": "rule.a",
                "fix_type": "set_attr",
                "target_node": "file1",
                "target_attr": "colorSpace",
                "before_value": "ACEScg",
                "after_value": "Raw",
                "applied": True,
                "blocked": False,
                "message": "Fix applied.",
                "block_reasons": [],
            },
            {
                "fix_id": "z.fix",
                "rule_id": "rule.z",
                "fix_type": "set_attr",
                "target_node": "file2",
                "target_attr": "colorSpace",
                "before_value": "Raw",
                "after_value": "sRGB",
                "applied": True,
                "blocked": False,
                "message": "Fix applied.",
                "block_reasons": [],
            },
        ),
    )
