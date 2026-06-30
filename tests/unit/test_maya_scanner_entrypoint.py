from shader_health.core import GraphSnapshot
from shader_health.maya import ScanOptions, scan_scene, scan_selection


class FakeCmds:
    def __init__(self):
        self.selection = ["|world|char_demo:file_roughness", "|world|char_demo:body_geo"]
        self.node_types = {
            "|world|char_demo:file_roughness": "file",
            "|world|char_demo:body_geo": "mesh",
        }

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
        if attr == "defaultRenderGlobals.currentRenderer":
            return "vray"
        return None

    def ls(self, *args, **kwargs):
        del args
        if kwargs.get("selection") and kwargs.get("long"):
            return list(self.selection)
        return []

    def nodeType(self, node):
        return self.node_types.get(node, "unknown")


class MinimalCmds:
    pass


def test_scan_scene_returns_minimal_graph_snapshot_from_injected_cmds():
    snapshot = scan_scene(cmds_module=FakeCmds())

    assert isinstance(snapshot, GraphSnapshot)
    assert snapshot.scene_path == "D:/show/assets/char/demo/shading/demo_shading.ma"
    assert snapshot.maya_version == "2025"
    assert snapshot.renderer == "vray"
    assert snapshot.scan_scope == "scene"
    assert snapshot.scanned_at_utc.endswith("Z")
    assert snapshot.nodes == []


def test_scan_selection_returns_selection_scoped_snapshot_with_lightweight_nodes():
    snapshot = scan_selection(cmds_module=FakeCmds())

    assert snapshot.scan_scope == "selection"
    assert [node.name for node in snapshot.nodes] == ["file_roughness", "body_geo"]
    assert [node.type_name for node in snapshot.nodes] == ["file", "mesh"]
    assert snapshot.nodes[0].full_name == "|world|char_demo:file_roughness"


def test_scan_scene_handles_missing_optional_cmds_safely():
    snapshot = scan_scene(cmds_module=MinimalCmds())

    assert snapshot.scene_path == ""
    assert snapshot.maya_version == ""
    assert snapshot.renderer is None
    assert snapshot.scan_scope == "scene"


def test_scan_options_are_available_for_future_scanner_expansion():
    options = ScanOptions(
        include_references=False,
        include_file_dependencies=False,
        include_connections=False,
    )

    assert options.include_references is False
    assert options.include_file_dependencies is False
    assert options.include_connections is False
