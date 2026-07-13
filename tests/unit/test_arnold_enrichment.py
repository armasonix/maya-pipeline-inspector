from __future__ import annotations

import json
from pathlib import Path

from pipeline_inspector.core import (
    ArnoldMaterialMetadata,
    ArnoldSceneMetadata,
    GraphSnapshot,
    MaterialSnapshot,
    NodeSnapshot,
    ShadingEngineSnapshot,
)
from pipeline_inspector.maya.arnold_enrichment import enrich_arnold_metadata
from pipeline_inspector.maya.snapshot_enrichment import prepare_snapshot_for_validation

FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "snapshots"


def test_enrich_arnold_metadata_attaches_material_and_scene_fields():
    snapshot = GraphSnapshot(
        scene_path="D:/show/asset/shading/hero.ma",
        renderer="arnold",
        nodes=[
            NodeSnapshot(
                id="node:defaultArnoldRenderOptions",
                name="defaultArnoldRenderOptions",
                type_name="aiOptions",
            ),
            NodeSnapshot(
                id="node:hero_proxyStandIn",
                name="hero_proxyStandIn",
                type_name="aiStandIn",
            ),
            NodeSnapshot(
                id="node:hero_mtl",
                name="hero_mtl",
                type_name="aiStandardSurface",
                attrs={
                    "specularRoughness": 0.35,
                    "metalness": 0.0,
                    "transmission": 0.0,
                    "transmissionDepth": 8,
                    "opacity": 1.0,
                },
            ),
            NodeSnapshot(
                id="node:disp_shader",
                name="disp_shader",
                type_name="displacementShader",
                attrs={"scale": 2.0},
            ),
        ],
        materials=[
            MaterialSnapshot(
                node_id="node:hero_mtl",
                name="hero_mtl",
                type_name="aiStandardSurface",
                renderer_family="arnold",
                shading_engines=["node:hero_sg"],
                texture_nodes=["node:file_basecolor", "node:file_roughness"],
                displacement_nodes=["node:disp_shader"],
                graph_node_count=4,
                graph_depth=2,
            )
        ],
        shading_engines=[
            ShadingEngineSnapshot(
                node_id="node:hero_sg",
                name="hero_sg",
                surface_shader="node:hero_mtl",
                displacement_shader="node:disp_shader",
                members=["mesh:hero_body"],
            )
        ],
    )

    enriched = enrich_arnold_metadata(snapshot)
    material = enriched.materials[0]
    scene_meta = enriched.arnold_scene_metadata

    assert scene_meta == ArnoldSceneMetadata(
        has_arnold_plugin=True,
        arnold_plugin_node_ids=["node:defaultArnoldRenderOptions"],
        arnold_material_count=1,
        has_arnold_materials=True,
        stand_in_node_ids=["node:hero_proxyStandIn"],
        stand_in_count=1,
        has_stand_ins=True,
    )
    assert material.arnold_metadata == ArnoldMaterialMetadata(
        texture_count=2,
        displacement_linked=True,
        specular_roughness=0.35,
        metalness=0.0,
        transmission_weight=0.0,
        transmission_depth=8,
        key_attrs={
            "specular_roughness": 0.35,
            "metalness": 0.0,
            "transmission_weight": 0.0,
            "transmission_depth": 8,
            "opacity": 1.0,
        },
    )


def test_enrich_arnold_metadata_is_safe_without_arnold_nodes():
    snapshot = GraphSnapshot(
        scene_path="D:/show/asset/shading/hero.ma",
        renderer="vray",
        nodes=[
            NodeSnapshot(
                id="node:hero_mtl",
                name="hero_mtl",
                type_name="VRayMtl",
            )
        ],
        materials=[
            MaterialSnapshot(
                node_id="node:hero_mtl",
                name="hero_mtl",
                type_name="VRayMtl",
                renderer_family="vray",
            )
        ],
    )

    enriched = enrich_arnold_metadata(snapshot)

    assert enriched.materials[0].arnold_metadata is None
    assert enriched.arnold_scene_metadata == ArnoldSceneMetadata()


def test_prepare_snapshot_for_validation_includes_arnold_metadata():
    snapshot = GraphSnapshot(
        scene_path="D:/show/asset/shading/hero.ma",
        renderer="arnold",
        nodes=[
            NodeSnapshot(
                id="node:hero_mtl",
                name="hero_mtl",
                type_name="aiStandardSurface",
                attrs={"specularRoughness": 0.5, "metalness": 1.0},
            )
        ],
        materials=[
            MaterialSnapshot(
                node_id="node:hero_mtl",
                name="hero_mtl",
                type_name="aiStandardSurface",
                texture_nodes=["node:file_roughness"],
            )
        ],
    )

    prepared = prepare_snapshot_for_validation(snapshot)

    assert prepared.arnold_scene_metadata is not None
    assert prepared.arnold_scene_metadata.has_arnold_materials is True
    assert prepared.materials[0].arnold_metadata is not None
    assert prepared.materials[0].arnold_metadata.texture_count == 1
    assert prepared.materials[0].arnold_metadata.metalness == 1.0


def test_arnold_material_policy_fixture_round_trips(tmp_path: Path):
    fixture_path = FIXTURES_ROOT / "arnold_material_policy.json"
    raw_snapshot = GraphSnapshot.from_json(fixture_path.read_text(encoding="utf-8"))
    prepared = prepare_snapshot_for_validation(raw_snapshot)
    payload = prepared.to_dict()

    assert payload["arnold_scene_metadata"]["has_arnold_materials"] is True
    assert payload["arnold_scene_metadata"]["has_arnold_plugin"] is True
    assert payload["arnold_scene_metadata"]["has_stand_ins"] is True
    assert payload["materials"][0]["arnold_metadata"]["texture_count"] == 2
    assert payload["materials"][0]["arnold_metadata"]["specular_roughness"] == 0.35
    assert payload["materials"][0]["arnold_metadata"]["transmission_depth"] == 8

    round_trip = GraphSnapshot.from_dict(payload)
    assert round_trip.arnold_scene_metadata == prepared.arnold_scene_metadata
    assert round_trip.materials[0].arnold_metadata == prepared.materials[0].arnold_metadata

    output_path = tmp_path / "arnold_material_policy_enriched.json"
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    restored = GraphSnapshot.from_json(output_path.read_text(encoding="utf-8"))
    assert restored == round_trip
