import pytest

from shader_health.adapters import (
    BaseRendererAdapter,
    CommonMayaAdapter,
    RendererAdapterError,
    RendererAdapterRegistry,
)
from shader_health.core import NodeSnapshot


class FakeAdapter(BaseRendererAdapter):
    def supported_node_types(self) -> set[str]:
        return {"file", "fakeMaterial"}

    def classify_node(self, node: NodeSnapshot) -> list[str]:
        if node.type_name == "file":
            return ["texture", "file"]
        if node.type_name == "fakeMaterial":
            return ["material", "material"]
        return []

    def texture_slot_semantics(self) -> dict[str, str]:
        return {
            "fakeMaterial.baseColor": "base_color",
            "fakeMaterial.roughness": "roughness",
        }

    def displacement_slots(self) -> list[str]:
        return ["fakeMaterial.displacement"]

    def complexity_weights(self) -> dict[str, float]:
        return {"fakeMaterial": 2.0, "file": 1.0}

    def default_rule_packs(self) -> list[str]:
        return ["common", "fake"]


class UnavailableAdapter(FakeAdapter):
    def is_available(self) -> bool:
        return False


def test_base_renderer_adapter_defaults_are_safe_empty_values():
    adapter = BaseRendererAdapter(id="base", display_name="Base")
    node = NodeSnapshot(id="node:file1", name="file1", type_name="file")

    assert adapter.is_available() is True
    assert adapter.supported_node_types() == set()
    assert adapter.classify_node(node) == []
    assert adapter.texture_slot_semantics() == {}
    assert adapter.displacement_slots() == []
    assert adapter.complexity_weights() == {}
    assert adapter.default_rule_packs() == []


def test_registry_registers_and_returns_adapters_by_normalized_id():
    adapter = FakeAdapter(id="Fake", display_name="Fake Renderer")
    registry = RendererAdapterRegistry([adapter])

    assert registry.ids() == ["fake"]
    assert registry.get("fake") is adapter
    assert registry.get("FAKE") is adapter
    assert registry.adapters() == [adapter]


def test_registry_rejects_empty_adapter_id():
    registry = RendererAdapterRegistry()
    adapter = FakeAdapter(id=" ", display_name="Invalid")

    with pytest.raises(RendererAdapterError, match="adapter id is required"):
        registry.register(adapter)


def test_registry_rejects_duplicate_adapter_id_unless_replace_is_true():
    registry = RendererAdapterRegistry()
    first = FakeAdapter(id="fake", display_name="Fake One")
    second = FakeAdapter(id="fake", display_name="Fake Two")

    registry.register(first)
    with pytest.raises(RendererAdapterError, match="already registered"):
        registry.register(second)

    registry.register(second, replace=True)
    assert registry.get("fake") is second


def test_registry_unknown_adapter_raises_actionable_error():
    registry = RendererAdapterRegistry()

    with pytest.raises(RendererAdapterError, match="unknown renderer adapter: missing"):
        registry.get("missing")


def test_registry_filters_unavailable_adapters():
    available = FakeAdapter(id="available", display_name="Available")
    unavailable = UnavailableAdapter(id="unavailable", display_name="Unavailable")
    registry = RendererAdapterRegistry([available, unavailable])

    assert registry.available_adapters() == [available]


def test_registry_classifies_node_with_available_matching_adapter():
    available = FakeAdapter(id="fake", display_name="Fake")
    unavailable = UnavailableAdapter(id="offline", display_name="Offline")
    registry = RendererAdapterRegistry([available, unavailable])
    node = NodeSnapshot(id="node:mat", name="mat", type_name="fakeMaterial")

    assert registry.classify_node(node) == ["material"]


def test_fake_adapter_exposes_renderer_semantics_contract():
    adapter = FakeAdapter(id="fake", display_name="Fake")

    assert adapter.texture_slot_semantics()["fakeMaterial.roughness"] == "roughness"
    assert adapter.displacement_slots() == ["fakeMaterial.displacement"]
    assert adapter.complexity_weights()["fakeMaterial"] == 2.0
    assert adapter.default_rule_packs() == ["common", "fake"]

def test_common_maya_adapter_has_expected_identity_and_rule_pack():
    adapter = CommonMayaAdapter()

    assert adapter.id == "common"
    assert adapter.display_name == "Common Maya"
    assert adapter.is_available() is True
    assert adapter.default_rule_packs() == ["common"]


def test_common_maya_adapter_supports_core_maya_node_types():
    adapter = CommonMayaAdapter()

    supported = adapter.supported_node_types()

    assert "file" in supported
    assert "shadingEngine" in supported
    assert "lambert" in supported
    assert "standardSurface" in supported
    assert "displacementShader" in supported
    assert "bump2d" in supported
    assert "place2dTexture" in supported


def test_common_maya_adapter_classifies_common_nodes():
    adapter = CommonMayaAdapter()

    assert adapter.classify_node(
        NodeSnapshot(id="node:file1", name="file1", type_name="file")
    ) == ["texture", "file"]
    assert adapter.classify_node(
        NodeSnapshot(id="node:sg", name="sg", type_name="shadingEngine")
    ) == ["shading_engine"]
    assert adapter.classify_node(
        NodeSnapshot(id="node:mat", name="mat", type_name="standardSurface")
    ) == ["material"]
    assert adapter.classify_node(
        NodeSnapshot(id="node:disp", name="disp", type_name="displacementShader")
    ) == ["displacement"]
    assert adapter.classify_node(
        NodeSnapshot(id="node:bump", name="bump", type_name="bump2d")
    ) == ["bump", "utility"]
    assert adapter.classify_node(
        NodeSnapshot(id="node:place", name="place", type_name="place2dTexture")
    ) == ["placement", "utility"]
    assert adapter.classify_node(
        NodeSnapshot(id="node:unknown", name="unknown", type_name="unknownType")
    ) == []


def test_common_maya_adapter_exposes_texture_slot_semantics():
    semantics = CommonMayaAdapter().texture_slot_semantics()

    assert semantics["lambert.color"] == "base_color"
    assert semantics["standardSurface.baseColor"] == "base_color"
    assert semantics["standardSurface.specularRoughness"] == "roughness"
    assert semantics["standardSurface.metalness"] == "metalness"
    assert semantics["standardSurface.normalCamera"] == "normal"
    assert semantics["standardSurface.opacity"] == "opacity"
    assert semantics["displacementShader.displacement"] == "displacement"
    assert semantics["bump2d.bumpValue"] == "bump"


def test_common_maya_adapter_exposes_displacement_and_complexity_contract():
    adapter = CommonMayaAdapter()

    assert adapter.displacement_slots() == ["displacementShader.displacement"]

    weights = adapter.complexity_weights()
    assert weights["shadingEngine"] == 0.25
    assert weights["file"] == 1.0
    assert weights["standardSurface"] == 1.0
    assert weights["displacementShader"] == 1.25
    assert weights["layeredTexture"] == 2.0


def test_registry_classifies_common_maya_nodes():
    registry = RendererAdapterRegistry([CommonMayaAdapter()])
    node = NodeSnapshot(id="node:file1", name="file1", type_name="file")

    assert registry.classify_node(node) == ["texture", "file"]

