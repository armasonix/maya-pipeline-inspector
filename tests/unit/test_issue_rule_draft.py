from __future__ import annotations

from pipeline_inspector.core.rule_browser import load_packaged_rules_catalog
from pipeline_inspector.core.rule_schema import RuleResult
from pipeline_inspector.core.rule_wizard import (
    RULE_TEMPLATE_ATTRIBUTE_EQUALS,
    RULE_TEMPLATE_NUMERIC_MAX,
    RULE_TEMPLATE_PATH_EXISTS,
    build_draft_prefill_from_issue,
    build_rule_draft,
    suggested_incident_rule_id,
)


def _catalog_rule(rule_id: str):
    for entry in load_packaged_rules_catalog():
        if entry.rule.id == rule_id:
            return entry.rule
    raise AssertionError(f"Rule {rule_id!r} not found")


def test_build_draft_prefill_from_missing_texture_issue():
    rule = _catalog_rule("common.texture.missing")
    issue = RuleResult(
        rule_id=rule.id,
        severity=rule.severity,
        status="failed",
        title=rule.name,
        message=rule.message,
        why=rule.why,
        owner=rule.owner,
    )

    prefill = build_draft_prefill_from_issue(issue, rule)

    assert prefill.template_id == RULE_TEMPLATE_PATH_EXISTS
    assert prefill.draft_input.rule_id == "common.texture.missing.draft"
    assert prefill.draft_input.message == rule.message
    draft = build_rule_draft(prefill.template_id, prefill.draft_input)
    assert draft["check"]["type"] == "path_exists"


def test_build_draft_prefill_from_attribute_equals_issue():
    rule = _catalog_rule("common.texture.colorspace.data_raw")
    issue = RuleResult(
        rule_id=rule.id,
        severity=rule.severity,
        status="failed",
        title=rule.name,
        message="Data texture uses a color-managed color space.",
        why=rule.why,
        owner=rule.owner,
        expected_value="Raw",
    )

    prefill = build_draft_prefill_from_issue(issue, rule)

    assert prefill.template_id == RULE_TEMPLATE_ATTRIBUTE_EQUALS
    assert prefill.draft_input.expected == "Raw"
    assert prefill.draft_input.attribute == "colorSpace"


def test_build_draft_prefill_from_numeric_max_issue():
    rule = _catalog_rule("common.shader_complexity.graph_nodes.max")
    issue = RuleResult(
        rule_id=rule.id,
        severity=rule.severity,
        status="failed",
        title=rule.name,
        message=rule.message,
        why=rule.why,
        owner=rule.owner,
        current_value=128,
    )

    prefill = build_draft_prefill_from_issue(issue, rule)

    assert prefill.template_id == RULE_TEMPLATE_NUMERIC_MAX
    assert prefill.draft_input.attribute == "graph_node_count"
    assert prefill.draft_input.max_value == 64


def test_suggested_incident_rule_id_appends_draft_suffix_once():
    assert suggested_incident_rule_id("studio.custom.rule") == "studio.custom.rule.draft"
    assert suggested_incident_rule_id("studio.custom.rule.draft") == "studio.custom.rule.draft"
