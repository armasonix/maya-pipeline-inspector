from __future__ import annotations

import json
from pathlib import Path

from shader_health.core import (
    GraphSnapshot,
    MaterialSnapshot,
    NodeSnapshot,
    ShadingEngineSnapshot,
    VrayMaterialMetadata,
    VraySceneMetadata,
)
from shader_health.maya.snapshot_enrichment import prepare_snapshot_for_validation
from shader_health.maya.vray_enrichment import enrich_vray_metadata

FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "snapshots"


def test_enrich_vray_metadata_attaches_material_and_scene_fields():
    snapshot = GraphSnapshot(
        scene_path="D:/show/asset/shading/hero.ma",
        renderer="vray",
        nodes=[
            NodeSnapshot(
                id="node:vraySettings",
                name="vraySettings",
                type_name="VRaySettingsNode",
            ),
            NodeSnapshot(
                id="node:hero_mtl",
                name="hero_mtl",
                type_name="VRayMtl",
                attrs={
                    "rlmd": 8,
                    "rrmd": 4,
                    "fde": True,
                    "gfr": True,
                    "brdf": 3,
                },
            ),
        ],
        materials=[
            MaterialSnapshot(
                node_id="node:hero_mtl",
                name="hero_mtl",
                type_name="VRayMtl",
                renderer_family="vray",
                shading_engines=["node:hero_sg"],
                texture_nodes=["node:file_roughness", "node:file_normal"],
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

    enriched = enrich_vray_metadata(snapshot)
    material = enriched.materials[0]
    scene_meta = enriched.vray_scene_metadata

    assert scene_meta == VraySceneMetadata(
        has_vray_plugin=True,
        vray_plugin_node_ids=["node:vraySettings"],
        vray_material_count=1,
        has_vray_materials=True,
    )
    assert material.vray_metadata == VrayMaterialMetadata(
        texture_count=2,
        displacement_linked=True,
        subdivision_enabled=True,
        reflection_max_depth=8,
        refraction_max_depth=4,
        limit_attrs={
            "reflection_max_depth": 8,
            "refraction_max_depth": 4,
            "brdf": 3,
            "force_displacement": True,
            "generate_gi_for_backfaces": True,
        },
    )


def test_enrich_vray_metadata_is_safe_without_vray_nodes():
    snapshot = GraphSnapshot(
        scene_path="D:/show/asset/shading/hero.ma",
        renderer="arnold",
        nodes=[
            NodeSnapshot(
                id="node:hero_mtl",
                name="hero_mtl",
                type_name="aiStandardSurface",
            )
        ],
        materials=[
            MaterialSnapshot(
                node_id="node:hero_mtl",
                name="hero_mtl",
                type_name="aiStandardSurface",
                renderer_family="arnold",
            )
        ],
    )

    enriched = enrich_vray_metadata(snapshot)

    assert enriched.materials[0].vray_metadata is None
    assert enriched.vray_scene_metadata == VraySceneMetadata()


def test_prepare_snapshot_for_validation_includes_vray_metadata():
    snapshot = GraphSnapshot(
        scene_path="D:/show/asset/shading/hero.ma",
        renderer="vray",
        nodes=[
            NodeSnapshot(
                id="node:hero_mtl",
                name="hero_mtl",
                type_name="VRayMtl",
                attrs={"rlmd": 6, "rrmd": 6},
            )
        ],
        materials=[
            MaterialSnapshot(
                node_id="node:hero_mtl",
                name="hero_mtl",
                type_name="VRayMtl",
                texture_nodes=["node:file_roughness"],
            )
        ],
    )

    prepared = prepare_snapshot_for_validation(snapshot)

    assert prepared.vray_scene_metadata is not None
    assert prepared.vray_scene_metadata.has_vray_materials is True
    assert prepared.materials[0].vray_metadata is not None
    assert prepared.materials[0].vray_metadata.texture_count == 1


def test_vray_material_policy_fixture_round_trips(tmp_path: Path):
    fixture_path = FIXTURES_ROOT / "vray_material_policy.json"
    raw_snapshot = GraphSnapshot.from_json(fixture_path.read_text(encoding="utf-8"))
    prepared = prepare_snapshot_for_validation(raw_snapshot)
    payload = prepared.to_dict()

    assert payload["vray_scene_metadata"]["has_vray_materials"] is True
    assert payload["materials"][0]["vray_metadata"]["texture_count"] == 1
    assert payload["materials"][0]["vray_metadata"]["reflection_max_depth"] == 8

    round_trip = GraphSnapshot.from_dict(payload)
    assert round_trip.vray_scene_metadata == prepared.vray_scene_metadata
    assert round_trip.materials[0].vray_metadata == prepared.materials[0].vray_metadata

    output_path = tmp_path / "vray_material_policy_enriched.json"
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    restored = GraphSnapshot.from_json(output_path.read_text(encoding="utf-8"))
    assert restored == round_trip
