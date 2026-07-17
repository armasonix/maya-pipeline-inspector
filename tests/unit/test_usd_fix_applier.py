from __future__ import annotations

from pathlib import Path

import pytest

pxr = pytest.importorskip("pxr")

from pipeline_inspector.core.fix_plan import FixAction
from pipeline_inspector.usd.fix_applier import apply_usd_fix_actions


def test_apply_rename_node_updates_usd_prim_name(tmp_path: Path) -> None:
    usd_path = tmp_path / "asset.usda"
    usd_path.write_text(
        '\n'.join(
            [
                "#usda 1.0",
                "(",
                ")",
                'def Shader "demo_albedo_v002_1"',
                "{",
                '    uniform token info:id = "UsdUVTexture"',
                "}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    action = FixAction(
        fix_id="studio.naming.texture.pattern:prim:/demo_albedo_v002_1:rename_node",
        rule_id="studio.naming.texture.pattern",
        title="rename",
        fix_type="rename_node",
        risk="low",
        target_kind="node",
        target_id="prim:/demo_albedo_v002_1",
        target_node="/demo_albedo_v002_1",
        before_value="demo_albedo_v002_1",
        after_value="t_demo_albedo_v002_1",
    )

    records = apply_usd_fix_actions(usd_path, [action])

    assert len(records) == 1
    assert records[0].succeeded is True
    updated = usd_path.read_text(encoding="utf-8")
    assert 'def Shader "t_demo_albedo_v002_1"' in updated
    assert 'def Shader "demo_albedo_v002_1"' not in updated


def test_apply_rename_node_resolves_nested_prim_by_short_name(tmp_path: Path) -> None:
    usd_path = tmp_path / "asset.usda"
    usd_path.write_text(
        "\n".join(
            [
                "#usda 1.0",
                "(",
                ")",
                'def Scope "Materials"',
                "{",
                '    def Shader "demo_albedo_v002_1"',
                "    {",
                '        uniform token info:id = "UsdUVTexture"',
                "    }",
                "}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    action = FixAction(
        fix_id="studio.naming.texture.pattern:prim:/demo_albedo_v002_1:rename_node",
        rule_id="studio.naming.texture.pattern",
        title="rename",
        fix_type="rename_node",
        risk="low",
        target_kind="node",
        target_id="prim:/demo_albedo_v002_1",
        target_node="/demo_albedo_v002_1",
        before_value="demo_albedo_v002_1",
        after_value="t_demo_albedo_v002_1",
    )

    records = apply_usd_fix_actions(usd_path, [action])

    assert len(records) == 1
    assert records[0].succeeded is True
    assert records[0].after_value == "/Materials/t_demo_albedo_v002_1"
    updated = usd_path.read_text(encoding="utf-8")
    assert 'def Shader "t_demo_albedo_v002_1"' in updated
    assert 'def Shader "demo_albedo_v002_1"' not in updated


def test_apply_rename_texture_file_updates_asset_path_and_prim(tmp_path: Path) -> None:
    texture_path = tmp_path / "demo_albedo_v002_1.exr"
    texture_path.write_bytes(b"pixels")
    usd_path = tmp_path / "asset.usda"
    usd_path.write_text(
        "\n".join(
            [
                "#usda 1.0",
                "(",
                ")",
                'def Shader "demo_albedo_v002_1"',
                "{",
                '    uniform token info:id = "UsdUVTexture"',
                f'    asset inputs:file = @{texture_path.name}@',
                "}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    renamed_texture = tmp_path / "t_demo_albedo_v002_1.exr"
    action = FixAction(
        fix_id="studio.naming.texture.pattern:prim:/demo_albedo_v002_1:rename_texture_file",
        rule_id="studio.naming.texture.pattern",
        title="rename texture file",
        fix_type="rename_texture_file",
        risk="medium",
        target_kind="node",
        target_id="prim:/demo_albedo_v002_1",
        target_node="/demo_albedo_v002_1",
        target_attr="file",
        before_value=texture_path.name,
        after_value=renamed_texture.name,
        params={
            "resolved_before": str(texture_path),
            "node_name_before": "demo_albedo_v002_1",
            "node_name_after": "t_demo_albedo_v002_1",
            "is_udim": False,
        },
    )

    records = apply_usd_fix_actions(usd_path, [action])

    assert len(records) == 1
    assert records[0].succeeded is True
    assert renamed_texture.is_file()
    assert not texture_path.exists()
    updated = usd_path.read_text(encoding="utf-8")
    assert renamed_texture.name in updated
    assert 'def Shader "t_demo_albedo_v002_1"' in updated
