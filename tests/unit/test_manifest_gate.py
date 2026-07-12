from __future__ import annotations

from pipeline_inspector.core.manifest_gate import ManifestGatePolicy, evaluate_manifest_gate


def test_manifest_gate_blocks_new_textures():
    old_manifest = {
        "materials": [
            {
                "node_id": "node:hero_mtl",
                "name": "hero_mtl",
                "textures": [],
            }
        ]
    }
    new_manifest = {
        "materials": [
            {
                "node_id": "node:hero_mtl",
                "name": "hero_mtl",
                "textures": [
                    {
                        "node_id": "node:file_albedo",
                        "attr": "fileTextureName",
                        "node_name": "file_albedo",
                    }
                ],
            }
        ]
    }

    result = evaluate_manifest_gate(
        old_manifest,
        new_manifest,
        policy=ManifestGatePolicy(block_on_new_textures=True),
    )

    assert result.blocked is True
    assert any("new texture" in reason for reason in result.reasons)


def test_manifest_gate_allows_fingerprint_drift_within_budget():
    old_manifest = {
        "materials": [
            {
                "node_id": "node:hero_mtl",
                "name": "hero_mtl",
                "graph_fingerprint": "sha256:old",
                "textures": [],
            }
        ]
    }
    new_manifest = {
        "materials": [
            {
                "node_id": "node:hero_mtl",
                "name": "hero_mtl",
                "graph_fingerprint": "sha256:new",
                "textures": [],
            }
        ]
    }

    result = evaluate_manifest_gate(
        old_manifest,
        new_manifest,
        policy=ManifestGatePolicy(max_fingerprint_changes=1),
    )

    assert result.blocked is False
