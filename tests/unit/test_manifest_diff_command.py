from __future__ import annotations

import copy
import json
from pathlib import Path

from shader_health.reports.manifest_diff import (
    MANIFEST_DIFF_SCHEMA_VERSION,
    build_manifest_diff,
    dumps_manifest_diff,
)
from tools.diff_manifests import main as diff_manifests_main


def old_manifest() -> dict[str, object]:
    return {
        "manifest_schema_version": "1.0",
        "scene_path": "old_scene.ma",
        "renderer": "vray",
        "materials": [
            {
                "node_id": "node:hero_mtl",
                "name": "hero_mtl",
                "type_name": "VRayMtl",
                "renderer_family": "vray",
                "shading_engines": ["node:hero_sg"],
                "assigned_shapes": ["mesh:hero_body"],
                "graph_fingerprint": "sha256:old_graph",
                "graph_node_count": 8,
                "graph_depth": 3,
                "textures": [
                    {
                        "node_id": "node:file_albedo",
                        "node_name": "file_albedo",
                        "type_name": "file",
                        "semantic": "base_color",
                        "attr": "fileTextureName",
                        "raw_path": "albedo_v001.exr",
                        "resolved_path": "P:/asset/albedo_v001.exr",
                        "exists": True,
                        "extension": ".exr",
                        "version": "001",
                        "latest_version": "002",
                        "is_udim": False,
                        "udim_tiles": [],
                        "missing_udim_tiles": [],
                    },
                    {
                        "node_id": "node:file_mask",
                        "node_name": "file_mask",
                        "type_name": "file",
                        "semantic": "mask",
                        "attr": "fileTextureName",
                        "raw_path": "mask_v001.exr",
                        "resolved_path": "P:/asset/mask_v001.exr",
                        "exists": True,
                        "extension": ".exr",
                        "version": "001",
                        "latest_version": "001",
                        "is_udim": False,
                        "udim_tiles": [],
                        "missing_udim_tiles": [],
                    },
                ],
            }
        ],
    }


def new_manifest() -> dict[str, object]:
    manifest = copy.deepcopy(old_manifest())
    material = manifest["materials"][0]
    material["graph_fingerprint"] = "sha256:new_graph"
    material["textures"] = [
        {
            "node_id": "node:file_albedo",
            "node_name": "file_albedo",
            "type_name": "file",
            "semantic": "base_color",
            "attr": "fileTextureName",
            "raw_path": "albedo_v002.exr",
            "resolved_path": "P:/asset/albedo_v002.exr",
            "exists": True,
            "extension": ".exr",
            "version": "002",
            "latest_version": "002",
            "is_udim": False,
            "udim_tiles": [],
            "missing_udim_tiles": [],
        },
        {
            "node_id": "node:file_roughness",
            "node_name": "file_roughness",
            "type_name": "file",
            "semantic": "roughness",
            "attr": "fileTextureName",
            "raw_path": "roughness_v001.exr",
            "resolved_path": "P:/asset/roughness_v001.exr",
            "exists": True,
            "extension": ".exr",
            "version": "001",
            "latest_version": "001",
            "is_udim": False,
            "udim_tiles": [],
            "missing_udim_tiles": [],
        },
    ]
    manifest["scene_path"] = "new_scene.ma"
    return manifest


def test_manifest_diff_lists_new_resolved_and_changed_issues():
    diff = build_manifest_diff(old_manifest(), new_manifest())

    assert diff["manifest_diff_schema_version"] == MANIFEST_DIFF_SCHEMA_VERSION
    assert diff["old_manifest_schema_version"] == "1.0"
    assert diff["new_manifest_schema_version"] == "1.0"
    assert diff["summary"] == {"new": 1, "resolved": 1, "changed": 2}

    issues = diff["issues"]
    assert issues["new"][0]["kind"] == "texture"
    assert issues["new"][0]["label"] == "file_roughness"
    assert issues["resolved"][0]["label"] == "file_mask"

    changed_ids = {issue["id"]: issue for issue in issues["changed"]}
    material_issue = changed_ids["material:node:hero_mtl"]
    assert material_issue["changes"] == [
        {
            "field": "graph_fingerprint",
            "old": "sha256:old_graph",
            "new": "sha256:new_graph",
        }
    ]

    texture_issue = changed_ids["texture:node:hero_mtl:node:file_albedo:fileTextureName"]
    changed_fields = {change["field"] for change in texture_issue["changes"]}
    assert {"raw_path", "resolved_path", "version"}.issubset(changed_fields)


def test_manifest_diff_json_output_is_deterministic():
    first = dumps_manifest_diff(old_manifest(), new_manifest())
    second = dumps_manifest_diff(old_manifest(), new_manifest())

    assert first == second
    assert first.endswith("\n")
    assert json.loads(first)["summary"]["changed"] == 2


def test_manifest_diff_command_writes_json_output(tmp_path: Path):
    old_path = tmp_path / "old_manifest.json"
    new_path = tmp_path / "new_manifest.json"
    out_path = tmp_path / "diff" / "manifest_diff.json"
    old_path.write_text(json.dumps(old_manifest()), encoding="utf-8")
    new_path.write_text(json.dumps(new_manifest()), encoding="utf-8")

    exit_code = diff_manifests_main(
        [str(old_path), str(new_path), "--out", str(out_path)]
    )

    assert exit_code == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["manifest_diff_schema_version"] == MANIFEST_DIFF_SCHEMA_VERSION
    assert payload["summary"] == {"new": 1, "resolved": 1, "changed": 2}
