from __future__ import annotations

from pipeline_inspector.core.rule_browser import (
    build_session_override_from_edits,
    editable_fields_for_rule,
    effective_rule,
    load_packaged_rules_catalog,
    merge_session_rule_overrides,
)
from pipeline_inspector.core.rule_loader import RuleOverride


def _catalog_entry(rule_id: str):
    catalog = load_packaged_rules_catalog()
    for entry in catalog:
        if entry.rule.id == rule_id:
            return entry
    raise AssertionError(f"Rule {rule_id!r} not found in packaged catalog")


def test_load_packaged_rules_catalog_includes_common_rules():
    catalog = load_packaged_rules_catalog()

    rule_ids = {entry.rule.id for entry in catalog}
    assert "common.shader_complexity.graph_nodes.max" in rule_ids
    assert all(entry.source_label for entry in catalog)


def test_editable_fields_for_numeric_max_rule():
    entry = _catalog_entry("common.shader_complexity.graph_nodes.max")
    fields = editable_fields_for_rule(entry.rule)

    assert fields.enabled is True
    assert fields.severity == "warning"
    assert fields.threshold_editable is True
    assert fields.threshold_key == "max"
    assert fields.threshold_value == 64


def test_build_session_override_from_edits_returns_none_when_unchanged():
    entry = _catalog_entry("common.shader_complexity.graph_nodes.max")

    override = build_session_override_from_edits(
        entry.rule,
        enabled=entry.rule.enabled,
        severity=entry.rule.severity,
        threshold_key="max",
        threshold_value=64,
    )

    assert override is None


def test_build_session_override_from_edits_captures_safe_changes():
    entry = _catalog_entry("common.shader_complexity.graph_nodes.max")

    override = build_session_override_from_edits(
        entry.rule,
        enabled=False,
        severity="error",
        threshold_key="max",
        threshold_value=32,
    )

    assert override is not None
    assert override.enabled is False
    assert override.severity == "error"
    assert override.check_params == {"max": 32}
    effective = effective_rule(entry, override)
    assert effective.enabled is False
    assert effective.severity == "error"
    assert effective.check.params["max"] == 32


def test_validate_effective_rule_uses_validate_rules_schema():
    entry = next(
        item
        for item in load_packaged_rules_catalog()
        if item.rule.id == "common.shader_complexity.graph_nodes.max"
    )
    from pipeline_inspector.core.rule_browser import validate_effective_rule
    from pipeline_inspector.core.rule_loader import RuleOverride

    rule = validate_effective_rule(
        entry,
        RuleOverride(rule_id=entry.rule.id, severity="error", check_params={"max": 32}),
    )

    assert rule.id == entry.rule.id
    assert rule.severity == "error"
    assert rule.check.params["max"] == 32


def test_merge_session_rule_overrides_layers_on_profile_overrides():
    profile_override = RuleOverride(rule_id="common.test", severity="warning")
    session_override = RuleOverride(rule_id="common.test", enabled=False)

    merged = merge_session_rule_overrides(
        {"common.test": profile_override},
        {"common.test": session_override},
    )

    assert merged["common.test"] is session_override
    assert merged["common.test"].enabled is False
