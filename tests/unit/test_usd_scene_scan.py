from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pipeline_inspector.core.models import GraphSnapshot, NodeSnapshot
from pipeline_inspector.maya.usd_scene_scan import merge_usd_proxy_snapshots
from pipeline_inspector.maya.validation_pipeline import run_validation
from pipeline_inspector.usd.scanner import _infer_semantic_slot, _normalize_colorspace


def test_infer_semantic_slot_detects_albedo_as_base_color() -> None:
    assert _infer_semantic_slot("demo_albedo_v002_1", "UsdUVTexture") == "base_color"
    assert _infer_semantic_slot("demo_roughness_v001", "vray:TexBitmap") == "roughness"


def test_normalize_colorspace_maps_raw_and_srgb() -> None:
    assert _normalize_colorspace("raw") == "Raw"
    assert _normalize_colorspace("sRGB") == "sRGB"


def test_merge_snapshots_preserves_usd_proxy_root_layer() -> None:
    from pipeline_inspector.core.models import GraphSnapshot, UsdStageMetadata
    from pipeline_inspector.maya.usd_scene_scan import _merge_snapshots

    usd_path = Path("D:/assets/hero.usda")
    base = GraphSnapshot(
        scene_path="shot.ma",
        usd_stage_metadata=UsdStageMetadata(root_layer="shot.ma"),
    )
    usd = GraphSnapshot(
        scene_path=str(usd_path),
        usd_stage_metadata=UsdStageMetadata(root_layer=str(usd_path)),
    )

    merged = _merge_snapshots(base, usd, proxy_usd_path=usd_path)

    assert merged.usd_stage_metadata is not None
    assert merged.usd_stage_metadata.root_layer == str(usd_path)


def test_merge_usd_proxy_snapshots_appends_usd_scan(monkeypatch: pytest.MonkeyPatch) -> None:
    base = GraphSnapshot(scene_path="shot.ma", renderer="vray", nodes=[], file_dependencies=[])
    usd_node = NodeSnapshot(
        id="prim:/Base/mtl/albedo",
        name="albedo",
        type_name="Shader",
        attrs={"colorSpace": "Raw", "semantic_slot": "base_color"},
    )
    usd_snapshot = GraphSnapshot(
        scene_path="hero.usda",
        renderer="usd",
        nodes=[usd_node],
        file_dependencies=[],
    )

    monkeypatch.setattr(
        "pipeline_inspector.usd.scanner.scan_usd_stage",
        lambda path, scan_scope="asset": usd_snapshot,
    )

    cmds = MagicMock()
    cmds.ls.return_value = ["|heroStage|heroStageShape"]
    cmds.getAttr.return_value = str(Path("D:/assets/hero.usda"))

    merged = merge_usd_proxy_snapshots(base, cmds)
    assert len(merged.nodes) == 1
    assert merged.nodes[0].attrs["semantic_slot"] == "base_color"


def test_merged_usd_shader_triggers_colorspace_rule() -> None:
    snapshot = GraphSnapshot(
        scene_path="shot.ma",
        renderer="vray",
        nodes=[
            NodeSnapshot(
                id="prim:/Base/mtl/albedo",
                name="demo_albedo_v002_1",
                type_name="Shader",
                attrs={
                    "colorSpace": "Raw",
                    "semantic_slot": "base_color",
                },
            )
        ],
        file_dependencies=[],
        usd_stage_metadata=None,
    )
    snapshot = replace(
        snapshot,
        usd_stage_metadata=__import__(
            "pipeline_inspector.core.models", fromlist=["UsdStageMetadata"]
        ).UsdStageMetadata(has_default_prim=True),
    )
    run = run_validation(snapshot, profile_id="publish_strict")
    failed = {item.rule_id for item in run.results if item.status == "failed"}
    assert "common.texture.colorspace.color_managed" in failed
    fix_types = {action.fix_type for action in run.fix_plan.actions if not action.blocked}
    assert "set_attr" in fix_types
