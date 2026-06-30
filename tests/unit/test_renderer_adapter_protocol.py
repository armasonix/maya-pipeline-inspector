import pytest

from shader_health.adapters import (
    BaseRendererAdapter,
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
