import pytest

from pipeline_inspector.adapters import (
    ArnoldAdapter,
    BaseRendererAdapter,
    CommonMayaAdapter,
    RendererAdapterError,
    RendererAdapterRegistry,
    SemanticTextureSlotResolver,
    VrayAdapter,
    classify_semantic_data_kind,
)
from pipeline_inspector.core import ConnectionSnapshot, GraphSnapshot, NodeSnapshot


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
    assert weights["layeredTexture"] == 2.5
    assert adapter.expensive_node_types() == frozenset({"layeredTexture"})


def test_registry_classifies_common_maya_nodes():
    registry = RendererAdapterRegistry([CommonMayaAdapter()])
    node = NodeSnapshot(id="node:file1", name="file1", type_name="file")

    assert registry.classify_node(node) == ["texture", "file"]


def test_vray_adapter_has_expected_identity_and_rule_packs():
    adapter = VrayAdapter()

    assert adapter.id == "vray"
    assert adapter.display_name == "V-Ray"
    assert adapter.is_available() is True
    assert adapter.default_rule_packs() == ["common", "vray"]


def test_vray_adapter_supports_initial_vray_node_types():
    supported = VrayAdapter().supported_node_types()

    assert "VRayMtl" in supported
    assert "VRayBlendMtl" in supported
    assert "VRayBitmap" in supported
    assert "VRayNormalMap" in supported
    assert "VRayDisplacement" in supported
    assert "VRayLayeredTex" in supported


def test_vray_adapter_classifies_vray_nodes():
    adapter = VrayAdapter()

    assert adapter.classify_node(
        NodeSnapshot(id="node:mtl", name="mtl", type_name="VRayMtl")
    ) == ["material"]
    assert adapter.classify_node(
        NodeSnapshot(id="node:bitmap", name="bitmap", type_name="VRayBitmap")
    ) == ["texture", "file"]
    assert adapter.classify_node(
        NodeSnapshot(id="node:normal", name="normal", type_name="VRayNormalMap")
    ) == ["bump", "normal", "utility"]
    assert adapter.classify_node(
        NodeSnapshot(id="node:disp", name="disp", type_name="VRayDisplacement")
    ) == ["displacement"]
    assert adapter.classify_node(
        NodeSnapshot(id="node:unknown", name="unknown", type_name="unknownType")
    ) == []


def test_vray_adapter_exposes_texture_slot_semantics():
    semantics = VrayAdapter().texture_slot_semantics()

    assert semantics["VRayMtl.diffuseColor"] == "base_color"
    assert semantics["VRayMtl.reflectionGlossiness"] == "roughness"
    assert semantics["VRayMtl.reflectionColor"] == "specular_color"
    assert semantics["VRayMtl.metalness"] == "metalness"
    assert semantics["VRayMtl.bumpMap"] == "bump"
    assert semantics["VRayMtl.normalMap"] == "normal"
    assert semantics["VRayMtl.opacityMap"] == "opacity"
    assert semantics["VRayBlendMtl.blendAmount"] == "mask"
    assert semantics["VRayDisplacement.displacement"] == "displacement"


def test_vray_adapter_exposes_displacement_and_complexity_contract():
    adapter = VrayAdapter()

    assert adapter.displacement_slots() == ["VRayDisplacement.displacement"]

    weights = adapter.complexity_weights()
    assert weights["VRayMtl"] == 1.25
    assert weights["VRayBlendMtl"] == 3.5
    assert weights["VRayBitmap"] == 1.0
    assert weights["VRayDisplacement"] == 1.75
    assert weights["VRayLayeredTex"] == 2.5
    assert "VRayBlendMtl" in adapter.expensive_node_types()
    assert "VRayLayeredTex" in adapter.expensive_node_types()


def test_registry_classifies_vray_nodes():
    registry = RendererAdapterRegistry([CommonMayaAdapter(), VrayAdapter()])
    node = NodeSnapshot(
        id="node:vray_bitmap",
        name="vray_bitmap",
        type_name="VRayBitmap",
    )

    assert registry.classify_node(node) == ["texture", "file"]
    assert registry.ids() == ["common", "vray"]


def test_arnold_adapter_has_expected_identity_and_rule_packs():
    adapter = ArnoldAdapter()

    assert adapter.id == "arnold"
    assert adapter.display_name == "Arnold"
    assert adapter.is_available() is True
    assert adapter.default_rule_packs() == ["common", "arnold"]


def test_arnold_adapter_supports_initial_arnold_node_types():
    supported = ArnoldAdapter().supported_node_types()

    assert "aiStandardSurface" in supported
    assert "aiImage" in supported
    assert "aiNormalMap" in supported
    assert "aiBump2d" in supported
    assert "aiLayerShader" in supported
    assert "aiMixShader" in supported
    assert "aiTriplanar" in supported
    assert "aiCarPaint" in supported
    assert "aiOSLShader" in supported


def test_arnold_adapter_classifies_arnold_nodes():
    adapter = ArnoldAdapter()

    assert adapter.classify_node(
        NodeSnapshot(id="node:mtl", name="mtl", type_name="aiStandardSurface")
    ) == ["material"]
    assert adapter.classify_node(
        NodeSnapshot(id="node:image", name="image", type_name="aiImage")
    ) == ["texture", "file"]
    assert adapter.classify_node(
        NodeSnapshot(id="node:normal", name="normal", type_name="aiNormalMap")
    ) == ["normal", "utility"]
    assert adapter.classify_node(
        NodeSnapshot(id="node:bump", name="bump", type_name="aiBump2d")
    ) == ["bump", "utility"]
    assert adapter.classify_node(
        NodeSnapshot(id="node:noise", name="noise", type_name="aiNoise")
    ) == ["texture", "procedural", "utility"]
    assert adapter.classify_node(
        NodeSnapshot(id="node:unknown", name="unknown", type_name="unknownType")
    ) == []


def test_arnold_adapter_exposes_texture_slot_semantics():
    semantics = ArnoldAdapter().texture_slot_semantics()

    assert semantics["aiStandardSurface.baseColor"] == "base_color"
    assert semantics["aiStandardSurface.specularRoughness"] == "roughness"
    assert semantics["aiStandardSurface.metalness"] == "metalness"
    assert semantics["aiStandardSurface.normalCamera"] == "normal"
    assert semantics["aiStandardSurface.opacity"] == "opacity"
    assert semantics["aiImage.filename"] == "texture_file"
    assert semantics["aiNormalMap.input"] == "normal"
    assert semantics["aiBump2d.bumpMap"] == "bump"
    assert semantics["aiLayerShader.mix"] == "mask"
    assert semantics["displacementShader.displacement"] == "displacement"


def test_arnold_adapter_exposes_displacement_and_complexity_contract():
    adapter = ArnoldAdapter()

    assert adapter.displacement_slots() == ["displacementShader.displacement"]

    weights = adapter.complexity_weights()
    assert weights["aiStandardSurface"] == 1.25
    assert weights["aiImage"] == 1.0
    assert weights["aiLayerShader"] == 3.0
    assert weights["aiMixShader"] == 2.5
    assert weights["aiTriplanar"] == 1.5
    assert "aiLayerShader" in adapter.expensive_node_types()
    assert "aiOSLShader" in adapter.expensive_node_types()


def test_registry_classifies_arnold_nodes():
    registry = RendererAdapterRegistry([CommonMayaAdapter(), VrayAdapter(), ArnoldAdapter()])
    node = NodeSnapshot(id="node:image", name="image", type_name="aiImage")

    assert registry.classify_node(node) == ["texture", "file"]
    assert registry.ids() == ["arnold", "common", "vray"]

def make_semantic_snapshot() -> GraphSnapshot:
    return GraphSnapshot(
        nodes=[
            NodeSnapshot(id="node:file_albedo", name="file_albedo", type_name="file"),
            NodeSnapshot(id="node:file_roughness", name="file_roughness", type_name="file"),
            NodeSnapshot(id="node:mtl", name="mtl", type_name="VRayMtl"),
        ],
        connections=[
            ConnectionSnapshot(
                src_node="node:file_albedo",
                src_attr="outColor",
                dst_node="node:mtl",
                dst_attr="diffuseColor",
            ),
            ConnectionSnapshot(
                src_node="node:file_roughness",
                src_attr="outAlpha",
                dst_node="node:mtl",
                dst_attr="reflectionGlossiness",
            ),
        ],
    )


def test_semantic_resolver_uses_connection_destination_for_vray_slots():
    resolver = SemanticTextureSlotResolver(RendererAdapterRegistry([VrayAdapter()]))

    results = resolver.resolve_all(make_semantic_snapshot())

    assert [item.status for item in results] == ["resolved", "resolved"]
    assert [item.semantic for item in results] == ["base_color", "roughness"]
    assert [item.data_kind for item in results] == ["color", "data"]
    assert results[0].adapter_id == "vray"
    assert results[0].is_resolved is True


def test_semantic_resolver_marks_unknown_when_no_mapping_exists():
    snapshot = GraphSnapshot(
        nodes=[
            NodeSnapshot(id="node:file1", name="file1", type_name="file"),
            NodeSnapshot(id="node:mtl", name="mtl", type_name="VRayMtl"),
        ],
        connections=[
            ConnectionSnapshot(
                src_node="node:file1",
                src_attr="outColor",
                dst_node="node:mtl",
                dst_attr="notMapped",
            )
        ],
    )
    resolver = SemanticTextureSlotResolver(RendererAdapterRegistry([VrayAdapter()]))

    result = resolver.resolve_all(snapshot)[0]

    assert result.status == "unknown"
    assert result.semantic == "unknown"
    assert result.data_kind == "unknown"
    assert "no semantic mapping" in result.reason


def test_semantic_resolver_marks_missing_destination_node_as_unknown():
    snapshot = GraphSnapshot(
        nodes=[NodeSnapshot(id="node:file1", name="file1", type_name="file")],
        connections=[
            ConnectionSnapshot(
                src_node="node:file1",
                src_attr="outColor",
                dst_node="node:missing",
                dst_attr="diffuseColor",
            )
        ],
    )
    resolver = SemanticTextureSlotResolver(RendererAdapterRegistry([VrayAdapter()]))

    result = resolver.resolve_all(snapshot)[0]

    assert result.status == "unknown"
    assert result.semantic == "unknown"
    assert "destination node not found" in result.reason


class ColorOnlyAdapter(BaseRendererAdapter):
    def texture_slot_semantics(self) -> dict[str, str]:
        return {"fakeMaterial.input": "base_color"}


class DataOnlyAdapter(BaseRendererAdapter):
    def texture_slot_semantics(self) -> dict[str, str]:
        return {"fakeMaterial.input": "roughness"}


def test_semantic_resolver_marks_ambiguous_slots_as_unknown():
    snapshot = GraphSnapshot(
        nodes=[
            NodeSnapshot(id="node:file1", name="file1", type_name="file"),
            NodeSnapshot(id="node:fake", name="fake", type_name="fakeMaterial"),
        ],
        connections=[
            ConnectionSnapshot(
                src_node="node:file1",
                src_attr="outColor",
                dst_node="node:fake",
                dst_attr="input",
            )
        ],
    )
    registry = RendererAdapterRegistry(
        [
            ColorOnlyAdapter(id="color", display_name="Color"),
            DataOnlyAdapter(id="data", display_name="Data"),
        ]
    )
    resolver = SemanticTextureSlotResolver(registry)

    result = resolver.resolve_all(snapshot)[0]

    assert result.status == "ambiguous"
    assert result.semantic == "unknown"
    assert result.data_kind == "unknown"
    assert "ambiguous semantic mapping" in result.reason


def test_semantic_resolver_can_apply_semantics_to_snapshot_connections():
    resolver = SemanticTextureSlotResolver(RendererAdapterRegistry([VrayAdapter()]))

    updated = resolver.apply_to_snapshot(make_semantic_snapshot())

    assert [item.semantic for item in updated.connections] == ["base_color", "roughness"]
    assert make_semantic_snapshot().connections[0].semantic is None


def test_semantic_data_kind_classification():
    assert classify_semantic_data_kind("base_color") == "color"
    assert classify_semantic_data_kind("emission") == "color"
    assert classify_semantic_data_kind("roughness") == "data"
    assert classify_semantic_data_kind("normal") == "data"
    assert classify_semantic_data_kind("material") == "material"
    assert classify_semantic_data_kind("custom") == "unknown"

