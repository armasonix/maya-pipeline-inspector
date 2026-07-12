from __future__ import annotations

import json
from pathlib import Path

from pipeline_inspector.core import GraphSnapshot
from pipeline_inspector.maya.displacement_enrichment import enrich_displacement_metadata
from pipeline_inspector.maya.snapshot_enrichment import prepare_snapshot_for_validation

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "snapshots"


def _load_fixture(name: str) -> GraphSnapshot:
    payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return GraphSnapshot.from_dict(payload)


def test_safe_material_has_low_displacement_risk_metadata():
    snapshot = _load_fixture("displacement_risk_safe.json")

    enriched = enrich_displacement_metadata(
        prepare_snapshot_for_validation(snapshot)
    )
    material = enriched.materials[0]

    assert material.displacement_metadata is not None
    metadata = material.displacement_metadata
    assert metadata.has_displacement is False
    assert metadata.risk_score == 0.0
    assert metadata.risk_hint == "low"


def test_high_vray_displacement_profiles_risk_metadata():
    snapshot = _load_fixture("displacement_risk_high_vray.json")

    enriched = prepare_snapshot_for_validation(snapshot)
    material = enriched.materials[0]
    metadata = material.displacement_metadata

    assert metadata is not None
    assert metadata.has_displacement is True
    assert metadata.displacement_node_ids == ["node:displacementShader1"]
    assert metadata.max_amount == 12.0
    assert metadata.texture_linked is True
    assert metadata.subdivision_enabled is True
    assert metadata.bounds_min == 0.0
    assert metadata.bounds_max == 4.0
    assert metadata.bounds_span == 4.0
    assert metadata.force_displacement is True
    assert metadata.risk_score >= 20.0
    assert metadata.risk_hint == "critical"
