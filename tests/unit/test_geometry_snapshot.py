from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline_inspector.core import (
    BoundingBoxSnapshot,
    GraphSnapshot,
    ShapeSnapshot,
    ValidationEngine,
)
from pipeline_inspector.core.rule_schema import RuleDefinition, RuleSchemaError

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "snapshots"
    / "common_geometry_foundation.json"
)


def test_shape_snapshot_dict_round_trip():
    shape = ShapeSnapshot(
        node_id="mesh:body_geo",
        name="body_geo",
        full_name="|world|char_demo:body_geo",
        type_name="mesh",
        transform_id="transform:body_geo",
        polygon_count=6,
        vertex_count=8,
        face_count=12,
        edge_count=18,
        world_bbox=BoundingBoxSnapshot(
            min_x=-1.0,
            min_y=-2.0,
            min_z=-3.0,
            max_x=4.0,
            max_y=5.0,
            max_z=6.0,
        ),
        topology_fingerprint="sha256:demo",
        instancing_key="mesh:body_geo",
        proxy_attrs={"intermediateObject": False},
        namespace="char_demo",
    )

    restored = ShapeSnapshot.from_dict(shape.to_dict())

    assert restored == shape


def test_geometry_fixture_loads_and_round_trips():
    snapshot = GraphSnapshot.from_dict(json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))

    assert len(snapshot.shapes) == 1
    assert snapshot.shapes[0].node_id == "mesh:body_geo"
    assert snapshot.shapes[0].vertex_count == 8

    restored = GraphSnapshot.from_dict(snapshot.to_dict())
    assert restored == snapshot


def test_validation_engine_targets_shape_scope():
    snapshot = GraphSnapshot.from_dict(json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))
    engine = ValidationEngine()

    targets = engine._targets_for_scope(snapshot, "shape")

    assert len(targets) == 1
    assert targets[0].kind == "shape"
    assert targets[0].target_id == "mesh:body_geo"
    assert isinstance(targets[0].obj, ShapeSnapshot)


def test_validation_engine_geometry_scope_alias_matches_shape():
    snapshot = GraphSnapshot.from_dict(json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))
    engine = ValidationEngine()

    shape_targets = engine._targets_for_scope(snapshot, "shape")
    geometry_targets = engine._targets_for_scope(snapshot, "geometry")

    assert geometry_targets == shape_targets


def test_rule_definition_accepts_shape_and_geometry_scopes():
    for scope in ("shape", "geometry"):
        rule = RuleDefinition.from_dict(
            {
                "schema_version": "1.0",
                "id": f"common.geometry.{scope}.info",
                "name": "Geometry scope",
                "enabled": True,
                "scope": scope,
                "severity": "info",
                "owner": "pipeline",
                "message": "Geometry snapshot target.",
                "why": "Foundation test.",
                "renderer": ["common"],
                "match": {},
                "check": {
                    "type": "attribute_equals",
                    "attribute": "vertex_count",
                    "expected": 8,
                },
                "policy": {},
            }
        )
        assert rule.scope == scope


def test_rule_definition_rejects_unknown_geometry_scope():
    with pytest.raises(RuleSchemaError, match="scope must be one of"):
        RuleDefinition.from_dict(
            {
                "schema_version": "1.0",
                "id": "common.geometry.invalid.info",
                "name": "Invalid geometry scope",
                "enabled": True,
                "scope": "mesh_node",
                "severity": "info",
                "owner": "pipeline",
                "message": "Invalid.",
                "why": "Invalid.",
                "renderer": ["common"],
                "match": {},
                "check": {
                    "type": "attribute_equals",
                    "attribute": "vertex_count",
                    "expected": 1,
                },
                "policy": {},
            }
        )
