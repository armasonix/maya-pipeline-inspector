"""Rule draft templates and validation for the new rule wizard."""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shader_health.core.rule_browser import load_packaged_rules_catalog
from shader_health.core.rule_loader import DEFAULT_RULE_ROOT
from shader_health.core.rule_pack_validation import (
    RuleValidationFailure,
    collect_rule_ids,
    validate_paths,
    validate_rule_object,
)
from shader_health.core.rule_schema import RULE_SCHEMA_VERSION, SEVERITIES, RuleDefinition
from shader_health.studio_config import StudioConfig

INCIDENT_RULE_SIDECAR_SCHEMA_VERSION = "1.0"

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


@dataclass(frozen=True)
class IncidentRuleExportContext:
    """Optional incident metadata stored in exported sidecar JSON."""

    source_rule_id: str = ""
    scene_path: str = ""


@dataclass(frozen=True)
class IncidentRuleDraftExportResult:
    """Outcome from exporting an incident rule draft sidecar."""

    success: bool
    path: Path | None
    message: str


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


def studio_extra_rules_folder(studio_config: StudioConfig | None) -> Path | None:
    """Return the configured studio extra_rules export folder, if any."""

    if studio_config is None:
        return None
    raw = studio_config.pipeline.extra_rules_folder.strip()
    if not raw:
        return None
    return Path(raw)


def build_incident_rule_sidecar_payload(
    draft: Mapping[str, Any],
    *,
    source_rule_id: str = "",
    scene_path: str = "",
    exported_at_utc: str | None = None,
) -> dict[str, Any]:
    """Build the incident rule sidecar JSON payload."""

    timestamp = exported_at_utc or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "schema_version": INCIDENT_RULE_SIDECAR_SCHEMA_VERSION,
        "exported_from": "incident",
        "source_rule_id": source_rule_id.strip(),
        "scene_path": scene_path.strip(),
        "exported_at_utc": timestamp,
        "rules": [dict(draft)],
    }


def incident_rule_sidecar_path(extra_rules_folder: Path, rule_id: str) -> Path:
    """Return the export path for one incident rule sidecar."""

    safe_name = rule_id.strip().replace("/", "_").replace("\\", "_") or "studio.incident.draft"
    return extra_rules_folder.expanduser() / f"{safe_name}.json"


def export_incident_rule_draft_to_studio_extra_rules(
    draft: Mapping[str, Any],
    extra_rules_folder: Path | str,
    *,
    export_context: IncidentRuleExportContext | None = None,
    known_rule_ids: Iterable[str] = (),
) -> IncidentRuleDraftExportResult:
    """Validate and export an incident rule draft sidecar to the studio extra_rules folder."""

    validation = validate_new_rule_draft(draft, known_rule_ids=known_rule_ids)
    if not validation.valid or validation.rule is None:
        message = validation.errors[0] if validation.errors else "Rule draft is invalid."
        return IncidentRuleDraftExportResult(success=False, path=None, message=message)

    folder = Path(extra_rules_folder).expanduser()
    context = export_context or IncidentRuleExportContext()
    output_path = incident_rule_sidecar_path(folder, validation.rule.id)
    payload = build_incident_rule_sidecar_payload(
        validation.rule.to_dict(),
        source_rule_id=context.source_rule_id,
        scene_path=context.scene_path,
    )

    try:
        folder.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        validate_paths([output_path])
    except (OSError, RuleValidationFailure) as exc:
        return IncidentRuleDraftExportResult(
            success=False,
            path=None,
            message=f"Could not export incident rule draft: {exc}",
        )

    resolved = output_path.resolve()
    return IncidentRuleDraftExportResult(
        success=True,
        path=resolved,
        message=f"Exported incident rule sidecar to {resolved}",
    )


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


@dataclass(frozen=True)
class IssueRuleDraftPrefill:
    """Wizard prefill derived from a failed validation issue."""

    template_id: str
    draft_input: NewRuleDraftInput


_CHECK_TYPE_TO_TEMPLATE = {
    "attribute_equals": RULE_TEMPLATE_ATTRIBUTE_EQUALS,
    "numeric_max": RULE_TEMPLATE_NUMERIC_MAX,
    "list_length_max": RULE_TEMPLATE_NUMERIC_MAX,
    "path_exists": RULE_TEMPLATE_PATH_EXISTS,
}


def template_id_for_check_type(check_type: str) -> str:
    normalized = check_type.strip()
    return _CHECK_TYPE_TO_TEMPLATE.get(normalized, RULE_TEMPLATE_ATTRIBUTE_EQUALS)


def template_id_for_rule_id(rule_id: str) -> str:
    lowered = rule_id.lower()
    if "missing" in lowered or ".path" in lowered:
        return RULE_TEMPLATE_PATH_EXISTS
    if ".max" in lowered or "complexity" in lowered or "resolution" in lowered:
        return RULE_TEMPLATE_NUMERIC_MAX
    if "colorspace" in lowered:
        return RULE_TEMPLATE_ATTRIBUTE_EQUALS
    return RULE_TEMPLATE_ATTRIBUTE_EQUALS


def suggested_incident_rule_id(source_rule_id: str) -> str:
    base = source_rule_id.strip() or "studio.incident.unknown"
    if base.endswith(".draft"):
        return base
    return f"{base}.draft"


def build_draft_prefill_from_issue(
    issue: Any,
    rule: RuleDefinition | None = None,
) -> IssueRuleDraftPrefill:
    """Build a new-rule wizard prefill from a failed issue and optional source rule."""

    rule_id = str(getattr(issue, "rule_id", "") or "")
    template_id = template_id_for_rule_id(rule_id)
    if rule is not None:
        template_id = template_id_for_check_type(rule.check.type)

    message = str(getattr(issue, "message", "") or "")
    why = str(getattr(issue, "why", "") or "")
    severity = str(getattr(issue, "severity", "") or "warning")
    owner = str(getattr(issue, "owner", "") or "shader_td")
    name = str(getattr(issue, "title", "") or message or rule_id)

    attribute = ""
    expected = ""
    max_value: int | float | None = None
    dependency_kind = "texture"
    scope = ""
    renderer: tuple[str, ...] = ("common", "vray", "arnold")

    if rule is not None:
        name = rule.name or name
        message = message or rule.message
        why = why or rule.why
        severity = severity or rule.severity
        owner = owner or rule.owner
        scope = rule.scope
        renderer = tuple(rule.renderer)
        check = rule.check
        if check.type == "attribute_equals":
            attribute = str(check.params.get("attribute", ""))
            expected_value = check.params.get("expected")
            if expected_value is not None:
                expected = str(expected_value)
            elif issue.expected_value is not None:
                expected = str(issue.expected_value)
        elif check.type in {"numeric_max", "list_length_max"}:
            attribute = str(check.params.get("attribute", ""))
            raw_max = check.params.get("max")
            if isinstance(raw_max, (int, float)) and not isinstance(raw_max, bool):
                max_value = raw_max
        elif check.type == "path_exists":
            dependency_kind = str(rule.match.to_dict().get("dependency_kind", "texture"))
    else:
        plug = str(getattr(issue, "plug", "") or "")
        if plug:
            attribute = plug
        if issue.expected_value is not None:
            expected = str(issue.expected_value)
        current = issue.current_value
        if (
            template_id == RULE_TEMPLATE_NUMERIC_MAX
            and isinstance(current, (int, float))
            and not isinstance(current, bool)
        ):
            max_value = current

    return IssueRuleDraftPrefill(
        template_id=template_id,
        draft_input=NewRuleDraftInput(
            rule_id=suggested_incident_rule_id(rule_id),
            name=name,
            message=message,
            why=why,
            severity=severity,
            owner=owner,
            scope=scope,
            attribute=attribute,
            expected=expected,
            max_value=max_value,
            dependency_kind=dependency_kind,
            renderer=renderer,
        ),
    )
