from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from shader_health.core import (
    ConnectionSnapshot,
    FileDependencySnapshot,
    GraphSnapshot,
    MaterialSnapshot,
    NodeSnapshot,
)
from shader_health.core.graph_fingerprint import material_graph_fingerprint
from shader_health.maya.snapshot_enrichment import enrich_snapshot

ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP_PATH = ROOT / "maya_module" / "scripts" / "shader_health_inspector_bootstrap.py"
USER_SETUP_PATH = ROOT / "maya_module" / "scripts" / "userSetup.py"
PLUGIN_PATH = ROOT / "maya_module" / "plug-ins" / "shader_health_inspector.py"


def load_module(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bootstrap_repo_root_resolves_to_repository_root():
    load_module(BOOTSTRAP_PATH, "shader_health_inspector_bootstrap_root")

    repo_root = BOOTSTRAP_PATH.resolve().parents[2]

    assert repo_root == ROOT
    assert (repo_root / "src" / "shader_health").is_dir()


def test_ensure_source_path_adds_repo_src_directory():
    bootstrap = load_module(BOOTSTRAP_PATH, "shader_health_inspector_bootstrap_path")
    src_path = str((ROOT / "src").resolve())
    original_sys_path = list(sys.path)

    try:
        sys.path[:] = [entry for entry in sys.path if entry != src_path]
        bootstrap._ensure_source_path()
        assert sys.path[0] == src_path
    finally:
        sys.path[:] = original_sys_path


def test_bootstrap_install_ui_delegates_to_shader_health_commands(monkeypatch):
    bootstrap = load_module(BOOTSTRAP_PATH, "shader_health_inspector_bootstrap_install")
    calls: list[str] = []

    class FakeCommands:
        @staticmethod
        def install_ui() -> None:
            calls.append("install_ui")

    monkeypatch.setitem(
        sys.modules,
        "shader_health.maya.commands",
        FakeCommands(),
    )
    monkeypatch.setattr(bootstrap, "_ensure_source_path", lambda: None)

    bootstrap.install_ui()

    assert calls == ["install_ui"]


def test_bootstrap_uninstall_ui_delegates_to_shader_health_commands(monkeypatch):
    bootstrap = load_module(BOOTSTRAP_PATH, "shader_health_inspector_bootstrap_uninstall")
    calls: list[str] = []

    class FakeCommands:
        @staticmethod
        def uninstall_ui() -> None:
            calls.append("uninstall_ui")

        @staticmethod
        def reset_ui_install_state() -> None:
            calls.append("reset_ui_install_state")

    monkeypatch.setitem(
        sys.modules,
        "shader_health.maya.commands",
        FakeCommands(),
    )
    monkeypatch.setattr(bootstrap, "_ensure_source_path", lambda: None)

    bootstrap.uninstall_ui()

    assert calls == ["uninstall_ui", "reset_ui_install_state"]


def test_user_setup_import_is_harmless_outside_maya():
    load_module(USER_SETUP_PATH, "shader_health_user_setup_outside_maya")


def test_maya_year_from_version_extracts_four_digit_year():
    bootstrap = load_module(BOOTSTRAP_PATH, "shader_health_inspector_bootstrap_year")

    assert bootstrap.maya_year_from_version("2025") == "2025"
    assert bootstrap.maya_year_from_version("Maya 2024 Update 3") == "2024"
    assert bootstrap.maya_year_from_version("unsupported") is None


def test_plugin_load_candidates_prefers_native_binary_on_windows(monkeypatch):
    bootstrap = load_module(BOOTSTRAP_PATH, "shader_health_inspector_bootstrap_candidates")
    monkeypatch.setattr("sys.platform", "win32")

    assert bootstrap.plugin_load_candidates("2024") == _expected_candidates(bootstrap, "2024")
    assert bootstrap.plugin_load_candidates(None) == _expected_candidates(bootstrap, None)


def _expected_candidates(bootstrap, maya_year: str | None) -> tuple[str, ...]:
    candidates: list[str] = []
    seen: set[str] = set()
    if maya_year:
        year_path = bootstrap.native_plugin_path(maya_year)
        if year_path.is_file():
            text = str(year_path)
            seen.add(text)
            candidates.append(text)
    manager_path = bootstrap.manager_native_plugin_path()
    if manager_path.is_file():
        text = str(manager_path)
        if text not in seen:
            candidates.append(text)
    candidates.append("shader_health_inspector.py")
    return tuple(candidates)


def test_detect_install_mode_native_year(monkeypatch, tmp_path: Path):
    bootstrap = load_module(BOOTSTRAP_PATH, "shader_health_inspector_bootstrap_detect_year")
    year_file = tmp_path / "2024.mll"
    year_file.write_bytes(b"native")
    monkeypatch.setattr(bootstrap, "native_plugin_path", lambda year: year_file)
    monkeypatch.setattr(bootstrap, "manager_native_plugin_path", lambda: tmp_path / "missing.mll")
    monkeypatch.setattr(
        bootstrap,
        "module_root",
        lambda: tmp_path,
    )

    assert bootstrap.detect_install_mode("2024") == bootstrap.INSTALL_MODE_NATIVE_YEAR


def test_detect_install_mode_native_manager(monkeypatch, tmp_path: Path):
    bootstrap = load_module(BOOTSTRAP_PATH, "shader_health_inspector_bootstrap_detect_manager")
    manager_file = tmp_path / "shader_health_inspector.mll"
    manager_file.write_bytes(b"native")
    monkeypatch.setattr(
        bootstrap,
        "native_plugin_path",
        lambda year: tmp_path / "missing" / "shader_health_inspector.mll",
    )
    monkeypatch.setattr(bootstrap, "manager_native_plugin_path", lambda: manager_file)
    monkeypatch.setattr(bootstrap, "module_root", lambda: tmp_path)

    assert bootstrap.detect_install_mode("2024") == bootstrap.INSTALL_MODE_NATIVE_MANAGER


def test_detect_install_mode_python_only(monkeypatch, tmp_path: Path):
    bootstrap = load_module(BOOTSTRAP_PATH, "shader_health_inspector_bootstrap_detect_python")
    plug_ins = tmp_path / "plug-ins"
    plug_ins.mkdir()
    (plug_ins / "shader_health_inspector.py").write_text("# plugin", encoding="utf-8")
    monkeypatch.setattr(
        bootstrap,
        "native_plugin_path",
        lambda year: plug_ins / "missing.mll",
    )
    monkeypatch.setattr(
        bootstrap,
        "manager_native_plugin_path",
        lambda: plug_ins / "missing.mll",
    )
    monkeypatch.setattr(bootstrap, "module_root", lambda: tmp_path)

    assert bootstrap.detect_install_mode("2024") == bootstrap.INSTALL_MODE_PYTHON


def test_detect_install_mode_module_only(monkeypatch, tmp_path: Path):
    bootstrap = load_module(BOOTSTRAP_PATH, "shader_health_inspector_bootstrap_detect_module")
    monkeypatch.setattr(
        bootstrap,
        "native_plugin_path",
        lambda year: tmp_path / "missing.mll",
    )
    monkeypatch.setattr(bootstrap, "manager_native_plugin_path", lambda: tmp_path / "missing.mll")
    monkeypatch.setattr(bootstrap, "module_root", lambda: tmp_path)

    assert bootstrap.detect_install_mode("2024") == bootstrap.INSTALL_MODE_MODULE_ONLY


def test_describe_dual_install_reports_load_order(monkeypatch, tmp_path: Path):
    bootstrap = load_module(BOOTSTRAP_PATH, "shader_health_inspector_bootstrap_describe")
    plug_ins = tmp_path / "plug-ins"
    plug_ins.mkdir()
    (plug_ins / "shader_health_inspector.py").write_text("# plugin", encoding="utf-8")
    monkeypatch.setattr(
        bootstrap,
        "native_plugin_path",
        lambda year: plug_ins / "2024" / "shader_health_inspector.mll",
    )
    monkeypatch.setattr(
        bootstrap,
        "manager_native_plugin_path",
        lambda: plug_ins / "shader_health_inspector.mll",
    )
    monkeypatch.setattr(bootstrap, "module_root", lambda: tmp_path)

    payload = bootstrap.describe_dual_install("2024")

    assert payload["maya_year"] == "2024"
    assert payload["install_mode"] == bootstrap.INSTALL_MODE_PYTHON
    assert payload["load_candidates"] == ["shader_health_inspector.py"]


def test_user_setup_prefers_native_plugin_load(monkeypatch):
    deferred: list[str] = []

    class FakeCmds:
        @staticmethod
        def evalDeferred(callback):
            deferred.append("deferred")
            callback()
            return None

        @staticmethod
        def about(**kwargs):
            if kwargs.get("version"):
                return "2024"
            return ""

        @staticmethod
        def pluginInfo(plugin_name, query=True, loaded=True):
            _ = query, loaded
            if plugin_name == "shader_health_inspector":
                return False
            _ = plugin_name
            return False

        @staticmethod
        def loadPlugin(plugin_name, quiet=True):
            deferred.append(f"load:{plugin_name}:{quiet}")
            return "shader_health_inspector"

        @staticmethod
        def warning(message: str):
            _ = message

    fake_maya = ModuleType("maya")
    fake_maya.cmds = FakeCmds

    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setitem(
        sys.modules,
        "shader_health_inspector_bootstrap",
        load_module(BOOTSTRAP_PATH, "shader_health_inspector_bootstrap_native_user_setup"),
    )
    monkeypatch.setitem(sys.modules, "maya", fake_maya)
    monkeypatch.setitem(sys.modules, "maya.cmds", FakeCmds)

    load_module(USER_SETUP_PATH, "shader_health_user_setup_native_plugin")

    bootstrap = load_module(BOOTSTRAP_PATH, "shader_health_inspector_bootstrap_native_assert")
    expected = str(bootstrap.native_plugin_path("2024"))
    if Path(expected).is_file():
        assert deferred == ["deferred", f"load:{expected}:True"]
    else:
        assert deferred == ["deferred", "load:shader_health_inspector.py:True"]


def test_user_setup_falls_back_to_py_plugin(monkeypatch):
    deferred: list[str] = []

    class FakeCmds:
        @staticmethod
        def evalDeferred(callback):
            deferred.append("deferred")
            callback()
            return None

        @staticmethod
        def about(**kwargs):
            if kwargs.get("version"):
                return "2024"
            return ""

        @staticmethod
        def pluginInfo(plugin_name, query=True, loaded=True):
            _ = query, loaded
            if plugin_name == "shader_health_inspector":
                return False
            _ = plugin_name
            return False

        @staticmethod
        def loadPlugin(plugin_name, quiet=True):
            deferred.append(f"load:{plugin_name}:{quiet}")
            if str(plugin_name).endswith(".mll"):
                raise RuntimeError("native plug-in missing")
            return "shader_health_inspector"

        @staticmethod
        def warning(message: str):
            _ = message

    fake_maya = ModuleType("maya")
    fake_maya.cmds = FakeCmds

    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setitem(
        sys.modules,
        "shader_health_inspector_bootstrap",
        load_module(BOOTSTRAP_PATH, "shader_health_inspector_bootstrap_native_user_setup"),
    )
    monkeypatch.setitem(sys.modules, "maya", fake_maya)
    monkeypatch.setitem(sys.modules, "maya.cmds", FakeCmds)

    load_module(USER_SETUP_PATH, "shader_health_user_setup_py_fallback")

    bootstrap = load_module(BOOTSTRAP_PATH, "shader_health_inspector_bootstrap_py_fallback_assert")
    native_path = str(bootstrap.native_plugin_path("2024"))
    manager_path = str(bootstrap.manager_native_plugin_path())
    expected = ["deferred"]
    if Path(native_path).is_file():
        expected.append(f"load:{native_path}:True")
    if Path(manager_path).is_file():
        expected.append(f"load:{manager_path}:True")
    expected.append("load:shader_health_inspector.py:True")
    assert deferred == expected


def test_user_setup_prefers_plugin_load(monkeypatch):
    deferred: list[str] = []

    class FakeCmds:
        @staticmethod
        def evalDeferred(callback):
            deferred.append("deferred")
            callback()
            return None

        @staticmethod
        def about(**kwargs):
            _ = kwargs
            return ""

        @staticmethod
        def pluginInfo(plugin_name, query=True, loaded=True):
            _ = query, loaded
            if plugin_name == "shader_health_inspector":
                return False
            _ = plugin_name
            return False

        @staticmethod
        def loadPlugin(plugin_name, quiet=True):
            deferred.append(f"load:{plugin_name}:{quiet}")
            return "shader_health_inspector"

        @staticmethod
        def warning(message: str):
            _ = message

    fake_maya = ModuleType("maya")
    fake_maya.cmds = FakeCmds

    monkeypatch.setitem(
        sys.modules,
        "shader_health_inspector_bootstrap",
        load_module(BOOTSTRAP_PATH, "shader_health_inspector_bootstrap_py_user_setup"),
    )
    monkeypatch.setitem(sys.modules, "maya", fake_maya)
    monkeypatch.setitem(sys.modules, "maya.cmds", FakeCmds)

    load_module(USER_SETUP_PATH, "shader_health_user_setup_plugin")

    bootstrap = load_module(
        BOOTSTRAP_PATH,
        "shader_health_inspector_bootstrap_py_user_setup_assert",
    )
    expected = ["deferred"]
    manager_path = str(bootstrap.manager_native_plugin_path())
    if Path(manager_path).is_file():
        expected.append(f"load:{manager_path}:True")
    else:
        expected.append("load:shader_health_inspector.py:True")
    assert deferred == expected


def test_user_setup_falls_back_to_bootstrap_install(monkeypatch):
    deferred: list[str] = []

    class FakeCmds:
        @staticmethod
        def evalDeferred(callback):
            deferred.append("deferred")
            callback()
            return None

        @staticmethod
        def about(**kwargs):
            if kwargs.get("version"):
                return "2024"
            return ""

        @staticmethod
        def pluginInfo(plugin_name, query=True, loaded=True):
            _ = query, loaded
            if plugin_name == "shader_health_inspector":
                return False
            _ = plugin_name
            return False

        @staticmethod
        def loadPlugin(plugin_name, quiet=True):
            _ = plugin_name, quiet
            raise RuntimeError("plugin missing")

        @staticmethod
        def warning(message: str):
            _ = message

    fake_bootstrap = ModuleType("shader_health_inspector_bootstrap")

    def install_ui() -> None:
        deferred.append("install_ui")

    fake_bootstrap.install_ui = install_ui
    fake_bootstrap.resolve_maya_year = lambda provider: "2025"
    fake_bootstrap.PLUGIN_NAME = "shader_health_inspector"
    real_bootstrap = load_module(BOOTSTRAP_PATH, "shader_health_inspector_bootstrap_fallback_paths")
    fake_bootstrap.plugin_load_candidates = real_bootstrap.plugin_load_candidates

    fake_maya = ModuleType("maya")
    fake_maya.cmds = FakeCmds

    monkeypatch.setitem(sys.modules, "maya", fake_maya)
    monkeypatch.setitem(sys.modules, "maya.cmds", FakeCmds)
    monkeypatch.setitem(sys.modules, "shader_health_inspector_bootstrap", fake_bootstrap)

    load_module(USER_SETUP_PATH, "shader_health_user_setup_fallback")

    assert deferred == ["deferred", "install_ui"]


def test_plugin_initialize_deferred_install(monkeypatch):
    calls: list[str] = []

    class FakeBootstrap:
        @staticmethod
        def install_ui() -> None:
            calls.append("install_ui")

    class FakeCmds:
        @staticmethod
        def evalDeferred(callback):
            callback()

    class FakePlugin:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

    fake_mpx = ModuleType("OpenMayaMPx")
    fake_mpx.MFnPlugin = FakePlugin
    fake_maya = ModuleType("maya")
    fake_maya.cmds = FakeCmds

    monkeypatch.setitem(sys.modules, "shader_health_inspector_bootstrap", FakeBootstrap())
    monkeypatch.setitem(sys.modules, "maya", fake_maya)
    monkeypatch.setitem(sys.modules, "maya.cmds", FakeCmds)
    monkeypatch.setitem(sys.modules, "maya.OpenMayaMPx", fake_mpx)

    plugin = load_module(PLUGIN_PATH, "shader_health_inspector_plugin_fresh")
    plugin.initializePlugin(object())

    assert calls == ["install_ui"]


def test_plugin_uninitialize_calls_uninstall(monkeypatch):
    calls: list[str] = []

    class FakeBootstrap:
        @staticmethod
        def uninstall_ui() -> None:
            calls.append("uninstall_ui")

    class FakePlugin:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

    fake_mpx = ModuleType("OpenMayaMPx")
    fake_mpx.MFnPlugin = FakePlugin
    fake_maya = ModuleType("maya")

    monkeypatch.setitem(sys.modules, "shader_health_inspector_bootstrap", FakeBootstrap())
    monkeypatch.setitem(sys.modules, "maya", fake_maya)
    monkeypatch.setitem(sys.modules, "maya.OpenMayaMPx", fake_mpx)

    plugin = load_module(PLUGIN_PATH, "shader_health_inspector_plugin_uninit_fresh")
    plugin.uninitializePlugin(object())

    assert calls == ["uninstall_ui"]


def test_graph_fingerprint_is_deterministic_for_fixture_snapshot():
    snapshot = GraphSnapshot(
        scene_path="scene.ma",
        nodes=[
            NodeSnapshot(
                id="node:file_albedo",
                name="file_albedo",
                type_name="file",
                attrs={"colorSpace": "Raw", "fileTextureName": "albedo.exr"},
            ),
            NodeSnapshot(
                id="node:hero_mtl",
                name="hero_mtl",
                type_name="VRayMtl",
                attrs={"color": [1.0, 1.0, 1.0]},
            ),
        ],
        connections=[
            ConnectionSnapshot(
                src_node="node:file_albedo",
                src_attr="outColor",
                dst_node="node:hero_mtl",
                dst_attr="color",
            )
        ],
        materials=[
            MaterialSnapshot(
                node_id="node:hero_mtl",
                name="hero_mtl",
                type_name="VRayMtl",
                texture_nodes=["node:file_albedo"],
            )
        ],
        file_dependencies=[
            FileDependencySnapshot(
                node_id="node:file_albedo",
                attr="fileTextureName",
                raw_path="albedo.exr",
                resolved_path="P:/asset/albedo.exr",
                exists=True,
            )
        ],
    )

    enriched = enrich_snapshot(snapshot)
    material = enriched.materials[0]
    assert material.graph_fingerprint.startswith("sha256:")
    assert material.graph_fingerprint == enrich_snapshot(snapshot).materials[0].graph_fingerprint


def test_material_graph_fingerprint_uses_connection_fields():
    material = MaterialSnapshot(
        node_id="node:hero_mtl",
        name="hero_mtl",
        type_name="VRayMtl",
        texture_nodes=["node:file_albedo"],
    )
    nodes_by_id = {
        "node:file_albedo": NodeSnapshot(
            id="node:file_albedo",
            name="file_albedo",
            type_name="file",
            attrs={"fileTextureName": "albedo.exr"},
        ),
        "node:hero_mtl": NodeSnapshot(
            id="node:hero_mtl",
            name="hero_mtl",
            type_name="VRayMtl",
        ),
    }
    connections = [
        ConnectionSnapshot(
            src_node="node:file_albedo",
            src_attr="outColor",
            dst_node="node:hero_mtl",
            dst_attr="color",
        )
    ]

    first = material_graph_fingerprint(
        material,
        nodes_by_id=nodes_by_id,
        connections=connections,
        texture_paths=("P:/asset/albedo.exr",),
    )
    second = material_graph_fingerprint(
        material,
        nodes_by_id=nodes_by_id,
        connections=connections,
        texture_paths=("P:/asset/albedo.exr",),
    )

    assert first == second
    assert first.startswith("sha256:")
