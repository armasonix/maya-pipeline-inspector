"""Rule draft templates and validation for the new rule wizard."""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shader_health.core.rule_browser import load_packaged_rules_catalog
from shader_health.core.rule_loader import DEFAULT_RULE_ROOT
from shader_health.core.rule_pack_validation import (
    RuleValidationFailure,
    collect_rule_ids,
    validate_rule_object,
)
from shader_health.core.rule_schema import RULE_SCHEMA_VERSION, SEVERITIES, RuleDefinition

RULE_TEMPLATE_ATTRIBUTE_EQUALS = "attribute_equals"
RULE_TEMPLATE_NUMERIC_MAX = "numeric_max"
RULE_TEMPLATE_PATH_EXISTS = "path_exists"

RULE_TEMPLATE_IDS = (
    RULE_TEMPLATE_ATTRIBUTE_EQUALS,
    RULE_TEMPLATE_NUMERIC_MAX,
    RULE_TEMPLATE_PATH_EXISTS,
)


@dataclass(frozen=True)
class RuleTemplateSpec:
    """One starter template for authoring a new JSON rule."""

    template_id: str
    label: str
    description: str
    scope: str
    match: dict[str, Any]
    check: dict[str, Any]
    policy: dict[str, bool]
    owner: str = "shader_td"
    renderer: tuple[str, ...] = ("common", "vray", "arnold")


@dataclass
class NewRuleDraftInput:
    """User-editable fields when creating a rule draft."""

    rule_id: str
    name: str
    message: str
    why: str
    severity: str = "warning"
    owner: str = "shader_td"
    scope: str = ""
    attribute: str = ""
    expected: str = ""
    max_value: int | float | None = None
    dependency_kind: str = "texture"
    renderer: tuple[str, ...] = ("common", "vray", "arnold")


@dataclass(frozen=True)
class RuleDraftValidationResult:
    """Outcome from validating a new rule draft."""

    valid: bool
    rule: RuleDefinition | None
    errors: tuple[str, ...]


_RULE_TEMPLATES: dict[str, RuleTemplateSpec] = {
    RULE_TEMPLATE_ATTRIBUTE_EQUALS: RuleTemplateSpec(
        template_id=RULE_TEMPLATE_ATTRIBUTE_EQUALS,
        label="Attribute equals expected value",
        description=(
            "Compare a node attribute against an expected value, for example color space "
            "or naming conventions on texture nodes."
        ),
        scope="texture_node",
        match={"node_type": ["file", "VRayBitmap", "aiImage"]},
        check={
            "type": "attribute_equals",
            "attribute": "colorSpace",
            "expected": "Raw",
        },
        policy={
            "block_publish": True,
            "block_deadline": True,
            "waiver_allowed": True,
            "auto_fix_allowed": False,
        },
    ),
    RULE_TEMPLATE_NUMERIC_MAX: RuleTemplateSpec(
        template_id=RULE_TEMPLATE_NUMERIC_MAX,
        label="Numeric maximum threshold",
        description=(
            "Fail when a numeric attribute exceeds a configured budget, for example graph "
            "node count or texture count on a material."
        ),
        scope="material",
        match={},
        check={
            "type": "numeric_max",
            "attribute": "graph_node_count",
            "max": 64,
        },
        policy={
            "block_publish": False,
            "block_deadline": False,
            "waiver_allowed": True,
            "auto_fix_allowed": False,
        },
    ),
    RULE_TEMPLATE_PATH_EXISTS: RuleTemplateSpec(
        template_id=RULE_TEMPLATE_PATH_EXISTS,
        label="File path must exist",
        description=(
            "Ensure a file dependency path resolves on disk, for example missing texture "
            "maps on file nodes."
        ),
        scope="file_dependency",
        match={"dependency_kind": "texture"},
        check={"type": "path_exists"},
        policy={
            "block_publish": True,
            "block_deadline": True,
            "waiver_allowed": False,
            "auto_fix_allowed": False,
        },
    ),
}


def list_rule_templates() -> tuple[RuleTemplateSpec, ...]:
    """Return packaged starter templates in deterministic order."""

    return tuple(_RULE_TEMPLATES[template_id] for template_id in RULE_TEMPLATE_IDS)


def get_rule_template(template_id: str) -> RuleTemplateSpec:
    normalized = template_id.strip()
    try:
        return _RULE_TEMPLATES[normalized]
    except KeyError as exc:
        allowed = ", ".join(RULE_TEMPLATE_IDS)
        message = f"Unknown rule template {template_id!r}; expected one of: {allowed}"
        raise ValueError(message) from exc


def build_rule_draft(
    template_id: str,
    draft: NewRuleDraftInput,
) -> dict[str, Any]:
    """Build a JSON-ready rule draft from one template and user input."""

    template = get_rule_template(template_id)
    normalized_severity = draft.severity.strip().lower()
    if normalized_severity not in SEVERITIES:
        allowed = ", ".join(sorted(SEVERITIES))
        raise ValueError(f"severity must be one of: {allowed}")

    rule_id = draft.rule_id.strip()
    if not rule_id:
        raise ValueError("Rule id is required.")

    check = dict(template.check)
    match = dict(template.match)
    if template_id == RULE_TEMPLATE_ATTRIBUTE_EQUALS:
        attribute = draft.attribute.strip() or str(check.get("attribute", ""))
        expected = draft.expected.strip() or str(check.get("expected", ""))
        if not attribute:
            raise ValueError("Attribute name is required for this template.")
        if not expected:
            raise ValueError("Expected value is required for this template.")
        check["attribute"] = attribute
        check["expected"] = expected
    elif template_id == RULE_TEMPLATE_NUMERIC_MAX:
        attribute = draft.attribute.strip() or str(check.get("attribute", ""))
        if not attribute:
            raise ValueError("Attribute name is required for this template.")
        max_value = draft.max_value if draft.max_value is not None else check.get("max")
        if max_value is None:
            raise ValueError("Maximum threshold is required for this template.")
        check["attribute"] = attribute
        check["max"] = max_value
    elif template_id == RULE_TEMPLATE_PATH_EXISTS:
        dependency_kind = draft.dependency_kind.strip() or str(match.get("dependency_kind", ""))
        if not dependency_kind:
            raise ValueError("Dependency kind is required for this template.")
        match["dependency_kind"] = dependency_kind

    return {
        "schema_version": RULE_SCHEMA_VERSION,
        "id": rule_id,
        "name": draft.name.strip() or rule_id,
        "enabled": True,
        "renderer": list(draft.renderer or template.renderer),
        "scope": (draft.scope.strip() or template.scope),
        "severity": normalized_severity,
        "owner": draft.owner.strip() or template.owner,
        "message": draft.message.strip() or "Validation rule failed.",
        "why": draft.why.strip() or "Explain why this rule matters in production.",
        "match": match,
        "check": check,
        "policy": dict(template.policy),
    }


def known_rule_ids_for_authoring(
    *,
    rule_root: Path = DEFAULT_RULE_ROOT,
    extra_rule_paths: Iterable[Path] = (),
) -> frozenset[str]:
    """Collect existing rule ids from packaged rules and configured extra paths."""

    catalog_ids = {
        entry.rule.id for entry in load_packaged_rules_catalog(
            rule_root=rule_root,
            extra_rule_paths=extra_rule_paths,
        )
    }
    extra_paths = [path for path in extra_rule_paths if str(path).strip()]
    if not extra_paths:
        return frozenset(catalog_ids)
    return frozenset(catalog_ids | collect_rule_ids(extra_paths))


def validate_new_rule_draft(
    draft: Mapping[str, Any],
    *,
    known_rule_ids: Iterable[str] = (),
) -> RuleDraftValidationResult:
    """Validate a draft using the same schema checks as validate_rules.py."""

    errors: list[str] = []
    rule: RuleDefinition | None = None
    try:
        rule = validate_rule_object(draft)
    except RuleValidationFailure as exc:
        return RuleDraftValidationResult(valid=False, rule=None, errors=(str(exc),))

    known_ids = frozenset(known_rule_ids)
    if rule.id in known_ids:
        errors.append(f"Rule id {rule.id!r} already exists in the loaded rule catalog.")

    return RuleDraftValidationResult(
        valid=not errors,
        rule=rule,
        errors=tuple(errors),
    )


def write_rule_draft_file(path: Path, draft: Mapping[str, Any]) -> Path:
    """Write one rule draft to a JSON pack file."""

    normalized = path.expanduser()
    normalized.parent.mkdir(parents=True, exist_ok=True)
    payload = {"rules": [dict(draft)]}
    normalized.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return normalized.resolve()


def default_draft_input_for_template(template_id: str) -> NewRuleDraftInput:
    """Return starter form values for one template."""

    template = get_rule_template(template_id)
    attribute = str(template.check.get("attribute", ""))
    expected = str(template.check.get("expected", ""))
    max_value = template.check.get("max")
    dependency_kind = str(template.match.get("dependency_kind", "texture"))
    numeric_max = max_value if isinstance(max_value, (int, float)) and not isinstance(
        max_value, bool
    ) else None
    return NewRuleDraftInput(
        rule_id="studio.custom.example_rule",
        name="Custom validation rule",
        message="Describe the failure shown to artists.",
        why="Explain why this check matters before publish or farm submission.",
        severity="warning",
        owner=template.owner,
        scope=template.scope,
        attribute=attribute,
        expected=expected,
        max_value=numeric_max,
        dependency_kind=dependency_kind,
        renderer=template.renderer,
    )


def template_field_labels(template_id: str) -> Sequence[tuple[str, str]]:
    """Return template-specific field labels for the wizard form."""

    if template_id == RULE_TEMPLATE_ATTRIBUTE_EQUALS:
        return (("attribute", "Attribute"), ("expected", "Expected value"))
    if template_id == RULE_TEMPLATE_NUMERIC_MAX:
        return (("attribute", "Attribute"), ("max_value", "Maximum"))
    if template_id == RULE_TEMPLATE_PATH_EXISTS:
        return (("dependency_kind", "Dependency kind"),)
    return ()
