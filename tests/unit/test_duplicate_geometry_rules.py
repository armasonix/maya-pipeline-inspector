from __future__ import annotations

from pathlib import Path

from pipeline_inspector.core import (
    BoundingBoxSnapshot,
    GraphSnapshot,
    RuleDefinition,
    ShapeSnapshot,
    ValidationEngine,
    load_rule_file,
)

ROOT = Path(__file__).resolve().parents[2]
RULE_PATH = ROOT / "src" / "pipeline_inspector" / "rules" / "common" / "duplicate_geometry.json"
TWINS_FIXTURE = ROOT / "tests" / "fixtures" / "snapshots" / "duplicate_geometry_twins.json"
INSTANCES_FIXTURE = ROOT / "tests" / "fixtures" / "snapshots" / "duplicate_geometry_instances.json"


def load_duplicate_geometry_rules() -> dict[str, RuleDefinition]:
    return {rule.id: rule for rule in load_rule_file(RULE_PATH)}


def _bbox() -> BoundingBoxSnapshot:
    return BoundingBoxSnapshot(
        min_x=0.0,
        min_y=0.0,
        min_z=0.0,
        max_x=10.0,
        max_y=5.0,
        max_z=2.0,
    )


def _mesh_shape(
    *,
    node_id: str,
    name: str,
    instancing_key: str,
    topology: str = "sha256:geo_twin_a",
    bbox: BoundingBoxSnapshot | None = None,
    proxy_attrs: dict | None = None,
    referenced: bool = False,
    type_name: str = "mesh",
) -> ShapeSnapshot:
    return ShapeSnapshot(
        node_id=node_id,
        name=name,
        type_name=type_name,
        polygon_count=1200,
        world_bbox=bbox or _bbox(),
        topology_fingerprint=topology,
        instancing_key=instancing_key,
        proxy_attrs=proxy_attrs or {},
        referenced=referenced,
    )


def twin_geometry_snapshot() -> GraphSnapshot:
    return GraphSnapshot(
        scene_path="demo.ma",
        renderer="common",
        shapes=[
            _mesh_shape(
                node_id="mesh:body_geo",
                name="body_geo",
                instancing_key="mesh:body_geo",
            ),
            _mesh_shape(
                node_id="mesh:body_geo_copy",
                name="body_geo_copy",
                instancing_key="mesh:body_geo_copy",
            ),
        ],
    )


def test_duplicate_geometry_rule_pack_has_production_defaults():
    rules = load_duplicate_geometry_rules()
    fingerprint = rules["common.geometry.duplicate.fingerprint"]
    scan_cap = rules["common.geometry.duplicate.scan_cap"]

    assert fingerprint.scope == "graph"
    assert fingerprint.severity == "warning"
    assert fingerprint.owner == "modeling_td"
    assert fingerprint.check.type == "duplicate_geometry"
    assert fingerprint.check.params["max_shapes"] == 500
    assert fingerprint.check.params["min_group_size"] == 2
    assert fingerprint.policy.auto_fix_allowed is False

    assert scan_cap.check.type == "duplicate_geometry_scan_budget"
    assert scan_cap.check.params["max_shapes"] == 500


def test_duplicate_geometry_fingerprint_rule_fails_for_twin_meshes():
    rule = load_duplicate_geometry_rules()["common.geometry.duplicate.fingerprint"]
    result = ValidationEngine().validate(twin_geometry_snapshot(), [rule])[0]

    assert result.status == "failed"
    assert result.target_kind == "graph"
    assert result.current_value == 1
    assert result.evidence["duplicate_groups"][0]["count"] == 2
    assert result.evidence["duplicate_groups"][0]["shape_ids"] == [
        "mesh:body_geo",
        "mesh:body_geo_copy",
    ]


def test_duplicate_geometry_fingerprint_rule_passes_for_unique_meshes():
    rule = load_duplicate_geometry_rules()["common.geometry.duplicate.fingerprint"]
    snapshot = GraphSnapshot(
        scene_path="demo.ma",
        renderer="common",
        shapes=[
            _mesh_shape(
                node_id="mesh:body_a",
                name="body_a",
                instancing_key="mesh:body_a",
                topology="sha256:geo_a",
            ),
            _mesh_shape(
                node_id="mesh:body_b",
                name="body_b",
                instancing_key="mesh:body_b",
                topology="sha256:geo_b",
            ),
        ],
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"


def test_duplicate_geometry_fingerprint_rule_ignores_intentional_instance_group():
    rule = load_duplicate_geometry_rules()["common.geometry.duplicate.fingerprint"]
    snapshot = GraphSnapshot.from_json(INSTANCES_FIXTURE.read_text(encoding="utf-8"))

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"


def test_duplicate_geometry_fingerprint_rule_skips_intermediate_meshes():
    rule = load_duplicate_geometry_rules()["common.geometry.duplicate.fingerprint"]
    snapshot = GraphSnapshot(
        scene_path="demo.ma",
        renderer="common",
        shapes=[
            _mesh_shape(
                node_id="mesh:body_geo",
                name="body_geo",
                instancing_key="mesh:body_geo",
                proxy_attrs={"intermediateObject": True},
            ),
            _mesh_shape(
                node_id="mesh:body_geo_copy",
                name="body_geo_copy",
                instancing_key="mesh:body_geo_copy",
            ),
        ],
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"


def test_duplicate_geometry_fingerprint_rule_groups_proxy_standins_by_source_file():
    rule = load_duplicate_geometry_rules()["common.geometry.duplicate.fingerprint"]
    snapshot = GraphSnapshot(
        scene_path="demo.ma",
        renderer="common",
        shapes=[
            _mesh_shape(
                node_id="mesh:proxy_a",
                name="proxy_a",
                instancing_key="mesh:proxy_a",
                type_name="aiStandIn",
                proxy_attrs={"dso": "/assets/hero.ass"},
            ),
            _mesh_shape(
                node_id="mesh:proxy_b",
                name="proxy_b",
                instancing_key="mesh:proxy_b",
                type_name="aiStandIn",
                proxy_attrs={"dso": "/assets/hero.ass"},
            ),
        ],
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.evidence["duplicate_groups"][0]["count"] == 2


def test_duplicate_geometry_fingerprint_rule_honors_match_attributes():
    rule = load_duplicate_geometry_rules()["common.geometry.duplicate.fingerprint"]
    rule = RuleDefinition.from_dict(
        {
            **rule.to_dict(),
            "check": {
                **rule.check.to_dict(),
                "match_attributes": ["displaySmoothMesh"],
            },
        }
    )
    snapshot = GraphSnapshot(
        scene_path="demo.ma",
        renderer="common",
        shapes=[
            _mesh_shape(
                node_id="mesh:body_a",
                name="body_a",
                instancing_key="mesh:body_a",
                proxy_attrs={"displaySmoothMesh": True},
            ),
            _mesh_shape(
                node_id="mesh:body_b",
                name="body_b",
                instancing_key="mesh:body_b",
                proxy_attrs={"displaySmoothMesh": False},
            ),
        ],
    )

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"


def test_duplicate_geometry_fingerprint_rule_truncates_large_scenes():
    rule = load_duplicate_geometry_rules()["common.geometry.duplicate.fingerprint"]
    rule = RuleDefinition.from_dict(
        {
            **rule.to_dict(),
            "check": {
                **rule.check.to_dict(),
                "max_shapes": 1,
            },
        }
    )
    shapes = [
        _mesh_shape(
            node_id=f"mesh:body_{index}",
            name=f"body_{index}",
            instancing_key=f"mesh:body_{index}",
        )
        for index in range(2)
    ]
    snapshot = GraphSnapshot(scene_path="demo.ma", renderer="common", shapes=shapes)

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "passed"
    assert result.evidence["geometry_scan_truncated"] is True
    assert result.evidence["shape_count"] == 2
    assert result.evidence["scanned_shape_count"] == 1


def test_duplicate_geometry_scan_cap_rule_fails_when_shape_budget_exceeded():
    rule = load_duplicate_geometry_rules()["common.geometry.duplicate.scan_cap"]
    rule = RuleDefinition.from_dict(
        {
            **rule.to_dict(),
            "check": {
                **rule.check.to_dict(),
                "max_shapes": 1,
            },
        }
    )
    snapshot = twin_geometry_snapshot()

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.current_value == 2
    assert result.evidence["geometry_scan_truncated"] is True


def test_duplicate_geometry_twins_fixture_fails_fingerprint_rule():
    rule = load_duplicate_geometry_rules()["common.geometry.duplicate.fingerprint"]
    snapshot = GraphSnapshot.from_json(TWINS_FIXTURE.read_text(encoding="utf-8"))

    result = ValidationEngine().validate(snapshot, [rule])[0]

    assert result.status == "failed"
    assert result.evidence["duplicate_groups"][0]["topology_fingerprint"] == "sha256:geo_twin_a"
