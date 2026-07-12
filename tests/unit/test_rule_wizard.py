from __future__ import annotations

import json
from pathlib import Path

import pytest

from shader_health.core.rule_wizard import (
    RULE_TEMPLATE_ATTRIBUTE_EQUALS,
    RULE_TEMPLATE_NUMERIC_MAX,
    RULE_TEMPLATE_PATH_EXISTS,
    NewRuleDraftInput,
    build_rule_draft,
    known_rule_ids_for_authoring,
    list_rule_templates,
    validate_new_rule_draft,
    write_rule_draft_file,
)
from tests.unit.test_validate_rules_cli import make_rule, run_validator, write_rule_pack


def test_list_rule_templates_includes_mvp_starters():
    templates = list_rule_templates()

    assert len(templates) == 3
    assert {template.template_id for template in templates} == {
        "attribute_equals",
        "numeric_max",
        "path_exists",
    }


def test_build_rule_draft_from_attribute_equals_template():
    draft = build_rule_draft(
        RULE_TEMPLATE_ATTRIBUTE_EQUALS,
        NewRuleDraftInput(
            rule_id="studio.custom.colorspace.raw",
            name="Data textures must use Raw",
            message="Texture uses a color-managed color space.",
            why="Numeric data maps must stay linear.",
            severity="critical",
            attribute="colorSpace",
            expected="Raw",
        ),
    )

    assert draft["id"] == "studio.custom.colorspace.raw"
    assert draft["check"]["type"] == "attribute_equals"
    assert draft["check"]["expected"] == "Raw"


def test_validate_new_rule_draft_accepts_valid_custom_draft():
    draft = build_rule_draft(
        RULE_TEMPLATE_NUMERIC_MAX,
        NewRuleDraftInput(
            rule_id="studio.custom.graph_nodes.max",
            name="Graph node budget",
            message="Graph is too large.",
            why="Large graphs are harder to maintain.",
            severity="warning",
            attribute="graph_node_count",
            max_value=48,
        ),
    )

    result = validate_new_rule_draft(draft, known_rule_ids=())

    assert result.valid is True
    assert result.rule is not None
    assert result.rule.id == "studio.custom.graph_nodes.max"


def test_validate_new_rule_draft_rejects_duplicate_rule_id():
    draft = build_rule_draft(
        RULE_TEMPLATE_PATH_EXISTS,
        NewRuleDraftInput(
            rule_id="common.shader_complexity.graph_nodes.max",
            name="Duplicate id",
            message="Duplicate.",
            why="Duplicate.",
            severity="warning",
        ),
    )

    result = validate_new_rule_draft(
        draft,
        known_rule_ids={"common.shader_complexity.graph_nodes.max"},
    )

    assert result.valid is False
    assert result.errors
    assert "already exists" in result.errors[0]


def test_write_rule_draft_file_matches_validate_rules_cli(tmp_path: Path):
    draft = build_rule_draft(
        RULE_TEMPLATE_ATTRIBUTE_EQUALS,
        NewRuleDraftInput(
            rule_id="studio.custom.validate_rules",
            name="Validate rules draft",
            message="Test message.",
            why="Test why.",
            severity="error",
            attribute="colorSpace",
            expected="Raw",
        ),
    )
    output_path = write_rule_draft_file(tmp_path / "draft.json", draft)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["rules"][0]["id"] == "studio.custom.validate_rules"

    result = run_validator(output_path)
    assert result.returncode == 0
    assert "Validated 1 rule(s) from 1 file(s)." in result.stdout


def test_known_rule_ids_for_authoring_includes_packaged_and_extra_paths(tmp_path: Path):
    extra = tmp_path / "studio"
    write_rule_pack(extra / "custom.json", make_rule("studio.custom.extra"))

    known_ids = known_rule_ids_for_authoring(extra_rule_paths=[extra])

    assert "studio.custom.extra" in known_ids
    assert "common.shader_complexity.graph_nodes.max" in known_ids


def test_build_rule_draft_requires_rule_id():
    with pytest.raises(ValueError, match="Rule id is required"):
        build_rule_draft(
            RULE_TEMPLATE_NUMERIC_MAX,
            NewRuleDraftInput(
                rule_id="",
                name="Missing id",
                message="Message",
                why="Why",
            ),
        )
