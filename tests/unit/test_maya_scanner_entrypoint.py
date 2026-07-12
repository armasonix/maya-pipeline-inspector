import logging
from pathlib import Path
from typing import Any

from pipeline_inspector.core import GraphSnapshot
from pipeline_inspector.maya import ScanOptions, scan_scene, scan_selection


class FakeCmds:
    def __init__(self):
        self.selection = ["|world|char_demo:body_geo"]
        self.node_types = {
            "|world|char_demo:body_geo": "mesh",
            "char_demo:demoSG": "shadingEngine",
            "char_demo:demo_mtl": "VRayMtl",
            "char_demo:file_albedo": "file",
            "char_demo:file_roughness": "file",
        }
        self.attrs = {
            "defaultRenderGlobals.currentRenderer": "vray",
            "char_demo:file_albedo.fileTextureName": "$ASSET_ROOT/tex/albedo.<UDIM>.exr",
            "char_demo:file_albedo.colorSpace": "ACEScg",
            "char_demo:file_albedo.uvTilingMode": 3,
            "char_demo:file_roughness.fileTextureName": "$ASSET_ROOT/tex/roughness.<UDIM>.exr",
            "char_demo:file_roughness.uvTilingMode": 3,
            "char_demo:demo_mtl.diffuseColor": [(1.0, 1.0, 1.0)],
            "char_demo:demo_mtl.reflectionGlossiness": 0.5,
        }
        self.referenced_nodes = {"char_demo:file_albedo"}
        self.locked_nodes = {"char_demo:file_roughness"}

    def file(self, *args, **kwargs):
        del args
        if kwargs.get("query") and kwargs.get("sceneName"):
            return "D:/show/assets/char/demo/shading/demo_shading.ma"
        return ""

    def about(self, *args, **kwargs):
        del args
        if kwargs.get("version"):
            return "2025"
        return ""

    def getAttr(self, attr):
        if attr == "char_demo:file_roughness.colorSpace":
            raise RuntimeError("colorSpace is unreadable in this test")
        return self.attrs.get(attr)

    def ls(self, *args, **kwargs):
        del args
        if kwargs.get("selection") and kwargs.get("long"):
            return list(self.selection)
        if kwargs.get("type") == "shadingEngine":
            return ["char_demo:demoSG"]
        return []

    def nodeType(self, node):
        return self.node_types.get(node, "unknown")

    def sets(self, node, **kwargs):
        if node == "char_demo:demoSG" and kwargs.get("query"):
            return ["|world|char_demo:body_geo"]
        return []

    def listConnections(self, item, **kwargs):
        if kwargs.get("type") == "shadingEngine":
            if item == "|world|char_demo:body_geo":
                return ["char_demo:demoSG"]
            return []

        if item == "char_demo:demoSG.surfaceShader":
            return ["char_demo:demo_mtl"]
        if item in {
            "char_demo:demoSG.displacementShader",
            "char_demo:demoSG.volumeShader",
        }:
            return []

        if item == "char_demo:demo_mtl" and kwargs.get("connections"):
            return [
                "char_demo:demo_mtl.diffuseColor",
                "char_demo:file_albedo.outColor",
                "char_demo:demo_mtl.reflectionGlossiness",
                "char_demo:file_roughness.outAlpha",
            ]

        return []

    def referenceQuery(self, node, **kwargs):
        if kwargs.get("isNodeReferenced"):
            return node in self.referenced_nodes
        if kwargs.get("filename") and node in self.referenced_nodes:
            return "D:/show/assets/char/demo/demo_rig.ma"
        return None

    def lockNode(self, node, **kwargs):
        if kwargs.get("query") and kwargs.get("lock"):
            return [node in self.locked_nodes]
        return [False]


class MinimalCmds:
    pass


def test_scan_scene_returns_graph_snapshot_metadata_from_injected_cmds():
    snapshot = scan_scene(cmds_module=FakeCmds())

    assert isinstance(snapshot, GraphSnapshot)
    assert snapshot.scene_path == "D:/show/assets/char/demo/shading/demo_shading.ma"
    assert snapshot.maya_version == "2025"
    assert snapshot.renderer == "vray"
    assert snapshot.scan_scope == "scene"
    assert snapshot.scanned_at_utc.endswith("Z")


def test_scan_scene_collects_shading_engine_and_material_network():
    snapshot = scan_scene(cmds_module=FakeCmds())

    assert len(snapshot.shading_engines) == 1
    engine = snapshot.shading_engines[0]
    assert engine.node_id == "node:char_demo:demoSG"
    assert engine.surface_shader == "node:char_demo:demo_mtl"
    assert engine.members == ["|world|char_demo:body_geo"]

    assert len(snapshot.materials) == 1
    material = snapshot.materials[0]
    assert material.node_id == "node:char_demo:demo_mtl"
    assert material.type_name == "VRayMtl"
    assert material.renderer_family == "vray"
    assert material.shading_engines == ["node:char_demo:demoSG"]
    assert material.assigned_shapes == ["|world|char_demo:body_geo"]
    assert material.texture_nodes == [
        "node:char_demo:file_albedo",
        "node:char_demo:file_roughness",
    ]
    assert material.graph_node_count == 3
    assert material.graph_depth == 2


def test_scan_scene_collects_upstream_nodes_and_connections():
    snapshot = scan_scene(cmds_module=FakeCmds())
    nodes = {node.id: node for node in snapshot.nodes}

    assert "node:char_demo:demoSG" in nodes
    assert "node:char_demo:demo_mtl" in nodes
    assert "node:char_demo:file_albedo" in nodes
    assert "node:char_demo:file_roughness" in nodes
    assert nodes["node:char_demo:file_albedo"].classification == ["texture", "file"]
    assert nodes["node:char_demo:demo_mtl"].classification == ["material"]

    connection_keys = {
        (item.src_node, item.src_attr, item.dst_node, item.dst_attr)
        for item in snapshot.connections
    }
    assert (
        "node:char_demo:file_albedo",
        "outColor",
        "node:char_demo:demo_mtl",
        "diffuseColor",
    ) in connection_keys
    assert (
        "node:char_demo:file_roughness",
        "outAlpha",
        "node:char_demo:demo_mtl",
        "reflectionGlossiness",
    ) in connection_keys
    assert (
        "node:char_demo:demo_mtl",
        "outColor",
        "node:char_demo:demoSG",
        "surfaceShader",
    ) in connection_keys


def test_scan_scene_collects_node_attrs_reference_lock_and_namespace(caplog):
    caplog.set_level(logging.DEBUG, logger="pipeline_inspector.maya.scanner")

    snapshot = scan_scene(cmds_module=FakeCmds())
    nodes = {node.id: node for node in snapshot.nodes}

    albedo = nodes["node:char_demo:file_albedo"]
    assert albedo.namespace == "char_demo"
    assert albedo.referenced is True
    assert albedo.reference_path == "D:/show/assets/char/demo/demo_rig.ma"
    assert albedo.locked is False
    assert albedo.attrs["fileTextureName"] == "$ASSET_ROOT/tex/albedo.<UDIM>.exr"
    assert albedo.attrs["colorSpace"] == "ACEScg"
    assert albedo.attrs["uvTilingMode"] == 3

    roughness = nodes["node:char_demo:file_roughness"]
    assert roughness.namespace == "char_demo"
    assert roughness.referenced is False
    assert roughness.reference_path is None
    assert roughness.locked is True
    assert roughness.attrs["fileTextureName"] == "$ASSET_ROOT/tex/roughness.<UDIM>.exr"
    assert "colorSpace" not in roughness.attrs
    assert "Skipping unreadable Maya attribute char_demo:file_roughness.colorSpace" in caplog.text


def test_scan_selection_collects_connected_shading_engine_graph():
    snapshot = scan_selection(cmds_module=FakeCmds())

    assert snapshot.scan_scope == "selection"
    assert "node:|world|char_demo:body_geo" in {node.id for node in snapshot.nodes}
    assert len(snapshot.shading_engines) == 1
    assert snapshot.shading_engines[0].node_id == "node:char_demo:demoSG"
    assert snapshot.materials[0].node_id == "node:char_demo:demo_mtl"


def test_scan_scene_handles_missing_optional_cmds_safely():
    snapshot = scan_scene(cmds_module=MinimalCmds())

    assert snapshot.scene_path == ""
    assert snapshot.maya_version == ""
    assert snapshot.renderer is None
    assert snapshot.scan_scope == "scene"
    assert snapshot.nodes == []
    assert snapshot.connections == []
    assert snapshot.materials == []
    assert snapshot.shading_engines == []


def test_scan_options_are_available_for_future_scanner_expansion():
    options = ScanOptions(
        include_references=False,
        include_file_dependencies=False,
        include_connections=False,
    )

    assert options.include_references is False
    assert options.include_file_dependencies is False
    assert options.include_connections is False

def test_scan_scene_collects_file_texture_dependencies(tmp_path, monkeypatch):
    asset_root = tmp_path / "assets"
    tex_root = asset_root / "tex"
    tex_root.mkdir(parents=True)

    (tex_root / "albedo_v001.1001.exr").write_bytes(b"albedo-1001")
    (tex_root / "albedo_v001.1003.exr").write_bytes(b"albedo-1003")
    (tex_root / "albedo_v002.1001.exr").write_bytes(b"albedo-v002")
    (tex_root / "roughness_v001.1001.exr").write_bytes(b"roughness-1001")

    monkeypatch.setenv("ASSET_ROOT", str(asset_root).replace("\\", "/"))

    cmds = FakeCmds()
    cmds.attrs["char_demo:file_albedo.fileTextureName"] = (
        "$ASSET_ROOT/tex/albedo_v001.<UDIM>.exr"
    )
    cmds.attrs["char_demo:file_roughness.fileTextureName"] = (
        "$ASSET_ROOT/tex/roughness_v001.<UDIM>.exr"
    )

    snapshot = scan_scene(cmds_module=cmds)
    dependencies = {item.node_id: item for item in snapshot.file_dependencies}

    assert set(dependencies) == {
        "node:char_demo:file_albedo",
        "node:char_demo:file_roughness",
    }

    albedo = dependencies["node:char_demo:file_albedo"]
    assert albedo.attr == "fileTextureName"
    assert albedo.raw_path == "$ASSET_ROOT/tex/albedo_v001.<UDIM>.exr"
    assert albedo.resolved_path is not None
    assert albedo.resolved_path.endswith("/tex/albedo_v001.<UDIM>.exr")
    assert albedo.exists is True
    assert albedo.is_udim is True
    assert albedo.udim_tiles == [1001, 1003]
    assert albedo.missing_udim_tiles == [1002]
    assert albedo.extension == ".exr"
    assert albedo.version == "001"
    assert albedo.latest_version == "002"
    assert albedo.mtime_utc is not None
    assert albedo.size_bytes is not None

    roughness = dependencies["node:char_demo:file_roughness"]
    assert roughness.exists is True
    assert roughness.udim_tiles == [1001]
    assert roughness.missing_udim_tiles == []
    assert roughness.version == "001"
    assert roughness.latest_version == "001"


def test_scan_scene_skips_texture_version_when_filename_has_no_version_token(
    tmp_path: Path,
    monkeypatch: Any,
):
    asset_root = tmp_path / "assets"
    tex_root = asset_root / "tex"
    tex_root.mkdir(parents=True)
    (tex_root / "albedo.1001.exr").write_bytes(b"albedo-1001")
    (tex_root / "albedo.1002.exr").write_bytes(b"albedo-1002")

    monkeypatch.setenv("ASSET_ROOT", str(asset_root).replace("\\", "/"))

    cmds = FakeCmds()
    cmds.attrs["char_demo:file_albedo.fileTextureName"] = "$ASSET_ROOT/tex/albedo.<UDIM>.exr"

    snapshot = scan_scene(cmds_module=cmds)
    albedo = {item.node_id: item for item in snapshot.file_dependencies}[
        "node:char_demo:file_albedo"
    ]

    assert albedo.version is None
    assert albedo.latest_version is None


def test_scan_options_can_skip_file_dependency_collection():
    snapshot = scan_scene(
        options=ScanOptions(include_file_dependencies=False),
        cmds_module=FakeCmds(),
    )

    assert snapshot.file_dependencies == []

class MutationTrackingCmds(FakeCmds):
    def __init__(self):
        super().__init__()
        self.mutation_calls = []

    def setAttr(self, *args, **kwargs):
        del args, kwargs
        self.mutation_calls.append("setAttr")

    def delete(self, *args, **kwargs):
        del args, kwargs
        self.mutation_calls.append("delete")

    def connectAttr(self, *args, **kwargs):
        del args, kwargs
        self.mutation_calls.append("connectAttr")

    def disconnectAttr(self, *args, **kwargs):
        del args, kwargs
        self.mutation_calls.append("disconnectAttr")


def test_scan_scene_collects_reference_snapshot_grouping():
    snapshot = scan_scene(cmds_module=FakeCmds())

    assert len(snapshot.references) == 1
    reference = snapshot.references[0]

    assert reference.namespace == "char_demo"
    assert reference.path == "D:/show/assets/char/demo/demo_rig.ma"
    assert reference.loaded is True
    assert reference.locked is False
    assert reference.node_ids == ["node:char_demo:file_albedo"]


def test_scan_scene_does_not_call_mutating_maya_commands():
    cmds = MutationTrackingCmds()

    snapshot = scan_scene(cmds_module=cmds)

    assert snapshot.references
    assert cmds.mutation_calls == []
