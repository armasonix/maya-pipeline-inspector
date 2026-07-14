from __future__ import annotations

import json
from pathlib import Path

from pipeline_inspector.core import (
    FileDependencySnapshot,
    GraphSnapshot,
    MaterialSnapshot,
    NodeSnapshot,
    RuleDefinition,
    ShapeSnapshot,
    ValidationEngine,
    load_rule_file,
    load_rule_stack,
)
from pipeline_inspector.core.naming_conventions import (
    format_naming_templates_text,
    name_matches_pattern,
    parse_naming_templates_text,
    resolve_object_type,
)
from pipeline_inspector.studio_config import (
    NamingTemplatesSettings,
    PipelineSettings,
    StudioConfig,
    load_studio_config,
    save_studio_config,
)

ROOT = Path(__file__).resolve().parents[2]
NAMING_RULE_PATH = ROOT / "src" / "pipeline_inspector" / "rules" / "studio" / "naming.json"
NAMING_FIXTURE_PATH = ROOT / "tests" / "fixtures" / "snapshots" / "studio_naming_patterns.json"

STUDIO_TEMPLATES = {
    "mesh": r"^geo_[A-Za-z0-9_]+$",
    "group": r"^grp_[A-Za-z0-9_]+$",
    "material": r"^mat_[A-Za-z0-9_]+$",
    "control": r"^ctrl_[A-Za-z0-9_]+$",
    "texture": r"^tex_[A-Za-z0-9_]+$",
    "shading_engine": r"^SG_[A-Za-z0-9_]+$",
    "light_source": r"^lgt_[A-Za-z0-9_]+$",
}


def load_naming_rule(rule_id: str) -> RuleDefinition:
    rules = {rule.id: rule for rule in load_rule_file(NAMING_RULE_PATH)}
    return rules[rule_id]


def load_naming_fixture() -> GraphSnapshot:
    payload = json.loads(NAMING_FIXTURE_PATH.read_text(encoding="utf-8"))
    return GraphSnapshot.from_dict(payload)


def evaluate_rule(rule_id: str, snapshot: GraphSnapshot, templates: dict[str, str] | None = None):
    return ValidationEngine(naming_templates=templates or STUDIO_TEMPLATES).validate(
        snapshot,
        [load_naming_rule(rule_id)],
    )


def test_name_matches_pattern_supports_full_match_regex():
    assert name_matches_pattern("geo_body_01", r"^geo_[A-Za-z0-9_]+$")
    assert not name_matches_pattern("body_geo_01", r"^geo_[A-Za-z0-9_]+$")


def test_parse_and_format_naming_templates_round_trip():
    text = "mesh=^geo_.+$\nmaterial=^mat_.+$"
    parsed = parse_naming_templates_text(text)
    assert parsed == {"mesh": r"^geo_.+$", "material": r"^mat_.+$"}
    assert format_naming_templates_text(parsed) == text


def test_resolve_object_type_maps_snapshot_targets():
    assert resolve_object_type(ShapeSnapshot(node_id="mesh:geo_body", name="geo_body")) == "mesh"
    assert (
        resolve_object_type(
            NodeSnapshot(
                id="node:grp_root",
                name="grp_root",
                type_name="transform",
                classification=["group"],
            )
        )
        == "group"
    )
    assert (
        resolve_object_type(
            MaterialSnapshot(
                node_id="node:mat_body",
                name="mat_body",
                type_name="standardSurface",
            )
        )
        == "material"
    )


    assert (
        resolve_object_type(
            NodeSnapshot(
                id="node:lgt_key",
                name="lgt_key",
                type_name="directionalLight",
                classification=["light"],
            )
        )
        == "light_source"
    )


def test_mesh_naming_rule_passes_for_matching_fixture_name():
    snapshot = load_naming_fixture()
    result = evaluate_rule("studio.naming.mesh.pattern", snapshot)[0]

    assert result.status == "passed"
    assert result.current_value == "geo_body"


def test_mesh_naming_rule_fails_for_invalid_fixture_name():
    snapshot = load_naming_fixture()
    invalid_shape = ShapeSnapshot(
        node_id="mesh:body_bad",
        name="body_bad",
        type_name="mesh",
    )
    snapshot = GraphSnapshot(
        scene_path=snapshot.scene_path,
        renderer=snapshot.renderer,
        shapes=[invalid_shape],
    )
    result = evaluate_rule("studio.naming.mesh.pattern", snapshot)[0]

    assert result.status == "failed"
    assert result.expected_value == STUDIO_TEMPLATES["mesh"]


def test_material_naming_rule_passes_and_fails_from_fixture():
    snapshot = load_naming_fixture()
    passed = evaluate_rule("studio.naming.material.pattern", snapshot)[0]
    assert passed.status == "passed"

    invalid_material = MaterialSnapshot(
        node_id="node:shader_body",
        name="shader_body",
        type_name="standardSurface",
    )
    failed_snapshot = GraphSnapshot(
        scene_path=snapshot.scene_path,
        renderer=snapshot.renderer,
        materials=[invalid_material],
    )
    failed = evaluate_rule("studio.naming.material.pattern", failed_snapshot)[0]
    assert failed.status == "failed"


def test_group_and_control_naming_rules_use_node_scope():
    snapshot = load_naming_fixture()

    group_result = evaluate_rule("studio.naming.group.pattern", snapshot)[0]
    control_result = evaluate_rule("studio.naming.control.pattern", snapshot)[0]

    assert group_result.status == "passed"
    assert control_result.status == "passed"


def test_texture_naming_rule_validates_texture_file_stem():
    snapshot = load_naming_fixture()
    node = snapshot.nodes[2]
    snapshot = GraphSnapshot(
        scene_path=snapshot.scene_path,
        renderer=snapshot.renderer,
        nodes=(
            NodeSnapshot(
                id=node.id,
                name=node.name,
                full_name=node.full_name,
                type_name=node.type_name,
                classification=node.classification,
                attrs={"fileTextureName": "D:/show/tex/albedo_wrong.exr"},
            ),
        ),
        file_dependencies=(
            FileDependencySnapshot(
                node_id=node.id,
                attr="fileTextureName",
                raw_path="D:/show/tex/albedo_wrong.exr",
                resolved_path="D:/show/tex/albedo_wrong.exr",
                exists=True,
            ),
        ),
    )
    result = evaluate_rule("studio.naming.texture.pattern", snapshot)[0]

    assert result.status == "failed"
    assert result.current_value == "albedo_wrong"


def test_texture_and_shading_engine_naming_rules_pass_from_fixture():
    snapshot = load_naming_fixture()
    texture_node = snapshot.nodes[2]
    snapshot = GraphSnapshot(
        scene_path=snapshot.scene_path,
        renderer=snapshot.renderer,
        nodes=(
            NodeSnapshot(
                id=texture_node.id,
                name=texture_node.name,
                full_name=texture_node.full_name,
                type_name=texture_node.type_name,
                classification=texture_node.classification,
                attrs={"fileTextureName": "D:/show/tex/tex_albedo.exr"},
            ),
            *snapshot.nodes[:2],
            *snapshot.nodes[3:],
        ),
        materials=snapshot.materials,
        shading_engines=snapshot.shading_engines,
        shapes=snapshot.shapes,
        file_dependencies=(
            FileDependencySnapshot(
                node_id=texture_node.id,
                attr="fileTextureName",
                raw_path="D:/show/tex/tex_albedo.exr",
                resolved_path="D:/show/tex/tex_albedo.exr",
                exists=True,
            ),
        ),
    )

    texture_result = evaluate_rule("studio.naming.texture.pattern", snapshot)[0]
    shading_result = evaluate_rule("studio.naming.shading_engine.pattern", snapshot)[0]

    assert texture_result.status == "passed"
    assert shading_result.status == "passed"


def test_name_matches_skips_when_studio_template_missing():
    snapshot = load_naming_fixture()
    result = ValidationEngine(naming_templates={}).validate(
        snapshot,
        [load_naming_rule("studio.naming.mesh.pattern")],
    )[0]

    assert result.status == "skipped"
    assert result.evidence["reason"] == "naming_template_not_configured"


def test_rule_stack_loads_studio_naming_rules():
    rules = load_rule_stack(renderer_ids=("common",))
    rule_ids = {rule.id for rule in rules}

    assert "studio.naming.mesh.pattern" in rule_ids
    assert "studio.naming.material.pattern" in rule_ids


def test_studio_config_round_trips_naming_templates(tmp_path: Path):
    config = StudioConfig(
        pipeline=PipelineSettings(
            naming_templates=NamingTemplatesSettings(templates=STUDIO_TEMPLATES)
        )
    )
    path = tmp_path / "pipeline_inspector_studio.json"
    save_studio_config(path, config)
    loaded = load_studio_config(path)

    assert loaded.pipeline.naming_templates.templates == STUDIO_TEMPLATES
