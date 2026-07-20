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


def test_apply_set_attr_syncs_all_usd_shader_colorspace_sources(tmp_path: Path) -> None:
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
                '    asset inputs:file = @demo_albedo_v002_1.exr@',
                '    token inputs:sourceColorSpace = "raw"',
                '    int inputs:color_space = 0',
                "}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    action = FixAction(
        fix_id="common.texture.colorspace.color_managed:prim:/demo_albedo_v002_1:set_attr",
        rule_id="common.texture.colorspace.color_managed",
        title="fix colorspace",
        fix_type="set_attr",
        risk="low",
        target_kind="node",
        target_id="prim:/demo_albedo_v002_1",
        target_node="/demo_albedo_v002_1",
        target_attr="colorSpace",
        before_value="Raw",
        after_value="sRGB",
        params={"resolved_prim_path": "/demo_albedo_v002_1", "attribute": "colorSpace", "value": "sRGB"},
    )

    records = apply_usd_fix_actions(usd_path, [action])

    assert records[0].succeeded is True
    from pipeline_inspector.usd.scanner import scan_usd_stage

    snapshot = scan_usd_stage(usd_path)
    shader = next(node for node in snapshot.nodes if node.type_name == "Shader")
    assert shader.attrs.get("colorSpace") == "sRGB"


def test_apply_set_attr_updates_arnold_image_colorspace_on_filename(tmp_path: Path) -> None:
    usd_path = tmp_path / "asset.usda"
    usd_path.write_text(
        "\n".join(
            [
                "#usda 1.0",
                "(",
                ")",
                'def Shader "demo_albedo_v002_1"',
                "{",
                '    uniform token info:id = "arnold:image"',
                '    asset inputs:filename = @textures/demo_albedo_v002.1001.exr@',
                '    token inputs:sourceColorSpace = "raw"',
                '    string inputs:color_space = "raw"',
                "}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    action = FixAction(
        fix_id="common.texture.colorspace.color_managed:prim:/demo_albedo_v002_1:set_attr",
        rule_id="common.texture.colorspace.color_managed",
        title="fix colorspace",
        fix_type="set_attr",
        risk="low",
        target_kind="node",
        target_id="prim:/demo_albedo_v002_1",
        target_node="/demo_albedo_v002_1",
        target_attr="colorSpace",
        before_value="Raw",
        after_value="sRGB",
        params={"resolved_prim_path": "/demo_albedo_v002_1", "attribute": "colorSpace", "value": "sRGB"},
    )

    records = apply_usd_fix_actions(usd_path, [action])

    assert records[0].succeeded is True
    updated = usd_path.read_text(encoding="utf-8")
    assert 'token inputs:sourceColorSpace = "srgb"' in updated
    assert 'string inputs:color_space = "srgb"' in updated
    assert "asset inputs:file =" not in updated


def test_apply_normalize_path_writes_studio_token_asset_path(tmp_path: Path) -> None:
    textures = tmp_path / "textures"
    textures.mkdir()
    texture_path = textures / "demo_albedo_v002.1001.exr"
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
                '    uniform token info:id = "arnold:image"',
                f'    asset inputs:filename = @{texture_path.resolve().as_posix()}@',
                "}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    from pipeline_inspector.studio_config import StudioEnvironmentSettings

    studio_environment = StudioEnvironmentSettings(
        asset_root=str(tmp_path),
        texture_root=str(textures),
    )
    action = FixAction(
        fix_id="usd.texture.path.local_drive:prim:/demo_albedo_v002_1:normalize_path",
        rule_id="usd.texture.path.local_drive",
        title="normalize",
        fix_type="normalize_path",
        risk="medium",
        target_kind="node",
        target_id="prim:/demo_albedo_v002_1",
        target_node="/demo_albedo_v002_1",
        target_attr="filename",
        before_value=str(texture_path.resolve()),
        after_value="${STUDIO_ASSET_ROOT}/textures/demo_albedo_v002.1001.exr",
        params={"resolved_prim_path": "/demo_albedo_v002_1"},
    )

    records = apply_usd_fix_actions(
        usd_path,
        [action],
        studio_environment=studio_environment,
    )

    assert records[0].succeeded is True
    updated = usd_path.read_text(encoding="utf-8")
    assert (
        "asset inputs:filename = @${STUDIO_ASSET_ROOT}/textures/demo_albedo_v002.1001.exr@"
        in updated
    )
    assert "D:/" not in updated


def test_apply_normalize_path_on_arnold_file_clears_spurious_file_input(tmp_path: Path) -> None:
    textures = tmp_path / "textures"
    textures.mkdir()
    texture_path = textures / "demo_albedo_v002.1001.exr"
    texture_path.write_bytes(b"pixels")
    usd_path = tmp_path / "asset.usda"
    usd_path.write_text(
        "\n".join(
            [
                "#usda 1.0",
                "(",
                ")",
                'def Shader "t_demo_albedo_v002"',
                "{",
                '    uniform token info:id = "arnold:image"',
                f'    asset inputs:file = @{texture_path.resolve()}@',
                '    asset inputs:filename = @""@',
                "}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    studio_environment = pytest.importorskip("pipeline_inspector.studio_config").StudioEnvironmentSettings(
        asset_root=str(tmp_path),
        texture_root=str(textures),
    )
    action = FixAction(
        fix_id="usd.texture.path.local_drive:prim:/t_demo_albedo_v002:normalize_path",
        rule_id="usd.texture.path.local_drive",
        title="normalize",
        fix_type="normalize_path",
        risk="medium",
        target_kind="node",
        target_id="prim:/t_demo_albedo_v002",
        target_node="/t_demo_albedo_v002",
        target_attr="file",
        before_value=str(texture_path.resolve()),
        after_value="textures/demo_albedo_v002.1001.exr",
        params={"resolved_prim_path": "/t_demo_albedo_v002"},
    )

    records = apply_usd_fix_actions(
        usd_path,
        [action],
        studio_environment=studio_environment,
    )

    assert records[0].succeeded is True
    updated = usd_path.read_text(encoding="utf-8")
    assert "inputs:filename = @textures/demo_albedo_v002.1001.exr@" in updated
    assert "inputs:file =" not in updated
    assert "D:/" not in updated


def test_apply_rename_texture_file_on_usd_uv_texture(tmp_path: Path) -> None:
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
