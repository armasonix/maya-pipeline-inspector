from __future__ import annotations

import json
from pathlib import Path

from shader_health.adapters import (
    ArnoldAdapter,
    CommonMayaAdapter,
    RendererAdapterRegistry,
    VrayAdapter,
)
from shader_health.core import GraphSnapshot
from shader_health.maya.complexity_profiler import profile_material_complexity
from shader_health.maya.snapshot_enrichment import enrich_snapshot

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "snapshots"
REGISTRY = RendererAdapterRegistry([CommonMayaAdapter(), VrayAdapter(), ArnoldAdapter()])


def _load_fixture(name: str) -> GraphSnapshot:
    payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return GraphSnapshot.from_dict(payload)


def test_profile_layered_common_graph_depth_histogram():
    snapshot = _load_fixture("shader_complexity_layered_graph.json")
    material = snapshot.materials[0]
    nodes_by_id = {node.id: node for node in snapshot.nodes}

    profiled = profile_material_complexity(
        material,
        nodes_by_id=nodes_by_id,
        connections=snapshot.connections,
        adapter_registry=REGISTRY,
    )

    assert profiled.graph_node_count == 6
    assert profiled.graph_depth == 4
    assert profiled.complexity_metadata is not None
    metadata = profiled.complexity_metadata
    assert metadata.depth_histogram == {
        "0": 1,
        "1": 1,
        "2": 1,
        "3": 2,
        "4": 1,
    }
    assert metadata.expensive_node_count == 1
    assert metadata.expensive_node_types == {"layeredTexture": 1}
    assert metadata.farm_cost_score == 6.0
    assert metadata.farm_cost_hint == "low"


def test_profile_vray_blend_graph_marks_expensive_nodes_and_medium_farm_cost():
    snapshot = _load_fixture("shader_complexity_over_budget.json")
    material = snapshot.materials[0]
    nodes_by_id = {node.id: node for node in snapshot.nodes}

    profiled = profile_material_complexity(
        material,
        nodes_by_id=nodes_by_id,
        connections=snapshot.connections,
        adapter_registry=REGISTRY,
    )

    assert profiled.graph_node_count == 10
    assert profiled.graph_depth == 3
    metadata = profiled.complexity_metadata
    assert metadata is not None
    assert metadata.expensive_node_count == 2
    assert metadata.expensive_node_types == {
        "VRayBlendMtl": 1,
        "VRayLayeredTex": 1,
    }
    assert metadata.farm_cost_score == 13.5
    assert metadata.farm_cost_hint == "medium"


def test_enrich_snapshot_populates_complexity_metadata_from_fixture():
    snapshot = _load_fixture("shader_complexity_layered_graph.json")

    enriched = enrich_snapshot(snapshot)
    material = enriched.materials[0]

    assert material.graph_node_count == 6
    assert material.graph_depth == 4
    assert material.complexity_metadata is not None
    assert material.complexity_metadata.farm_cost_hint == "low"
    assert material.graph_fingerprint
