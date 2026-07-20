"""Data-driven validation rule schema models and base rule evaluation.

The rule schema is intentionally Maya-independent. Rules describe what to match,
what to check, how severe the result is, who owns the fix, whether it blocks
production stages, and whether an optional safe fix can be planned.
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from pipeline_inspector.core.models import (
    BoundingBoxSnapshot,
    ConnectionSnapshot,
    FileDependencySnapshot,
    GraphSnapshot,
    MaterialSnapshot,
    NodeSnapshot,
    ShadingEngineSnapshot,
    ShapeSnapshot,
)
from pipeline_inspector.core.naming_conventions import (
    mesh_transform_name_from_shape,
    resolve_object_type,
)
from pipeline_inspector.core.naming_fix import texture_filename_stem

if TYPE_CHECKING:
    from pipeline_inspector.studio_config import StudioEnvironmentSettings

JsonDict = dict[str, Any]
JsonValue = Any

RULE_SCHEMA_VERSION = "1.0"

_TEXTURE_PATH_ATTRS = {
    "file": "fileTextureName",
    "VRayBitmap": "file",
    "aiImage": "filename",
    "Shader": "file",
}

SEVERITIES = frozenset({"info", "warning", "error", "critical"})
SCOPES = frozenset(
    {
        "scene",
        "node",
        "material",
        "texture_node",
        "file_dependency",
        "connection",
        "shading_engine",
        "shape",
        "geometry",
        "graph",
    }
)
FIX_RISKS = frozenset({"low", "medium", "high"})
RESULT_STATUSES = frozenset({"passed", "failed", "skipped"})

class RuleSchemaError(ValueError):
    """Raised when a rule definition is invalid."""

@dataclass(frozen=True)
class RulePolicy:
    """Production policy for a validation rule."""

    block_publish: bool = False
    block_deadline: bool = False
    waiver_allowed: bool = True
    auto_fix_allowed: bool = False

    def validate(self) -> None:
        for field_name, value in self.to_dict().items():
            if not isinstance(value, bool):
                raise RuleSchemaError(f"policy.{field_name} must be a boolean")

    def to_dict(self) -> JsonDict:
        return {
            "block_publish": self.block_publish,
            "block_deadline": self.block_deadline,
            "waiver_allowed": self.waiver_allowed,
            "auto_fix_allowed": self.auto_fix_allowed,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RulePolicy:
        policy = cls(
            block_publish=data.get("block_publish", False),
            block_deadline=data.get("block_deadline", False),
            waiver_allowed=data.get("waiver_allowed", True),
            auto_fix_allowed=data.get("auto_fix_allowed", False),
        )
        policy.validate()
        return policy

@dataclass(frozen=True)
class RuleMatch:
    """Rule target selection criteria."""

    criteria: JsonDict = field(default_factory=dict)

    def validate(self) -> None:
        if not isinstance(self.criteria, dict):
            raise RuleSchemaError("match must be an object")

    def to_dict(self) -> JsonDict:
        return dict(self.criteria)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RuleMatch:
        match = cls(criteria=dict(data))
        match.validate()
        return match

@dataclass(frozen=True)
class RuleCheck:
    """Validation operation definition."""

    type: str
    params: JsonDict = field(default_factory=dict)

    def validate(self) -> None:
        if not self.type:
            raise RuleSchemaError("check.type is required")
        if not isinstance(self.params, dict):
            raise RuleSchemaError("check params must be an object")

    def to_dict(self) -> JsonDict:
        data = dict(self.params)
        data["type"] = self.type
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RuleCheck:
        check_type = str(data.get("type", ""))
        params = dict(data)
        params.pop("type", None)
        check = cls(type=check_type, params=params)
        check.validate()
        return check

@dataclass(frozen=True)
class RuleFix:
    """Optional safe-fix definition for a rule."""

    type: str
    risk: str
    params: JsonDict = field(default_factory=dict)

    def validate(self) -> None:
        if not self.type:
            raise RuleSchemaError("fix.type is required")
        if self.risk not in FIX_RISKS:
            allowed = ", ".join(sorted(FIX_RISKS))
            raise RuleSchemaError(f"fix.risk must be one of: {allowed}")
        if not isinstance(self.params, dict):
            raise RuleSchemaError("fix params must be an object")

    def to_dict(self) -> JsonDict:
        data = dict(self.params)
        data["type"] = self.type
        data["risk"] = self.risk
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RuleFix:
        fix_type = str(data.get("type", ""))
        risk = str(data.get("risk", ""))
        params = dict(data)
        params.pop("type", None)
        params.pop("risk", None)
        fix = cls(type=fix_type, risk=risk, params=params)
        fix.validate()
        return fix

@dataclass(frozen=True)
class RuleDefinition:
    """Complete data-driven validation rule definition."""

    id: str
    name: str
    enabled: bool
    renderer: list[str]
    scope: str
    severity: str
    owner: str
    message: str
    why: str
    match: RuleMatch
    check: RuleCheck
    policy: RulePolicy
    fix: Optional[RuleFix] = None
    schema_version: str = RULE_SCHEMA_VERSION

    def validate(self) -> None:
        required_text_fields = {
            "id": self.id,
            "name": self.name,
            "scope": self.scope,
            "severity": self.severity,
            "owner": self.owner,
            "message": self.message,
            "why": self.why,
        }
        for field_name, value in required_text_fields.items():
            if not isinstance(value, str) or not value.strip():
                raise RuleSchemaError(f"{field_name} is required")

        if not isinstance(self.enabled, bool):
            raise RuleSchemaError("enabled must be a boolean")

        if not self.renderer or not all(isinstance(item, str) and item for item in self.renderer):
            raise RuleSchemaError("renderer must be a non-empty list of strings")

        if self.scope not in SCOPES:
            allowed = ", ".join(sorted(SCOPES))
            raise RuleSchemaError(f"scope must be one of: {allowed}")

        if self.severity not in SEVERITIES:
            allowed = ", ".join(sorted(SEVERITIES))
            raise RuleSchemaError(f"severity must be one of: {allowed}")

        self.match.validate()
        self.check.validate()
        self.policy.validate()
        if self.fix is not None:
            self.fix.validate()
            if not self.policy.auto_fix_allowed:
                raise RuleSchemaError("fix is defined but policy.auto_fix_allowed is false")

    def to_dict(self) -> JsonDict:
        data: JsonDict = {
            "schema_version": self.schema_version,
            "id": self.id,
            "name": self.name,
            "enabled": self.enabled,
            "renderer": list(self.renderer),
            "scope": self.scope,
            "severity": self.severity,
            "owner": self.owner,
            "message": self.message,
            "why": self.why,
            "match": self.match.to_dict(),
            "check": self.check.to_dict(),
            "policy": self.policy.to_dict(),
        }
        if self.fix is not None:
            data["fix"] = self.fix.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RuleDefinition:
        _validate_required_rule_keys(data)

        fix_data = data.get("fix")
        fix = None
        if fix_data is not None:
            fix = RuleFix.from_dict(_require_mapping(fix_data, "fix"))

        rule = cls(
            schema_version=str(data.get("schema_version", RULE_SCHEMA_VERSION)),
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            enabled=data.get("enabled", True),
            renderer=[str(item) for item in data.get("renderer", [])],
            scope=str(data.get("scope", "")),
            severity=str(data.get("severity", "")),
            owner=str(data.get("owner", "")),
            message=str(data.get("message", "")),
            why=str(data.get("why", "")),
            match=RuleMatch.from_dict(_require_mapping(data.get("match"), "match")),
            check=RuleCheck.from_dict(_require_mapping(data.get("check"), "check")),
            policy=RulePolicy.from_dict(_require_mapping(data.get("policy"), "policy")),
            fix=fix,
        )
        rule.validate()
        return rule

@dataclass(frozen=True)
class RuleResult:
    """Single validation result produced by one rule against one target."""

    rule_id: str
    severity: str
    status: str
    title: str
    message: str
    why: str
    owner: str
    target_kind: str = ""
    target_id: str = ""
    material: Optional[str] = None
    node: Optional[str] = None
    plug: Optional[str] = None
    current_value: JsonValue = None
    expected_value: JsonValue = None
    block_publish: bool = False
    block_deadline: bool = False
    auto_fix_available: bool = False
    fix_id: Optional[str] = None
    graph_trace: list[str] = field(default_factory=list)
    evidence: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "status": self.status,
            "title": self.title,
            "message": self.message,
            "why": self.why,
            "owner": self.owner,
            "target_kind": self.target_kind,
            "target_id": self.target_id,
            "material": self.material,
            "node": self.node,
            "plug": self.plug,
            "current_value": self.current_value,
            "expected_value": self.expected_value,
            "block_publish": self.block_publish,
            "block_deadline": self.block_deadline,
            "auto_fix_available": self.auto_fix_available,
            "fix_id": self.fix_id,
            "graph_trace": list(self.graph_trace),
            "evidence": dict(self.evidence),
        }

@dataclass(frozen=True)
class ValidationSummary:
    """Aggregated validation result summary.

    Severity and block policy are intentionally separate. A critical issue does
    not automatically block publish or Deadline. Blocking status is computed
    only from explicit result block flags.
    """

    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    info: int = 0
    warning: int = 0
    error: int = 0
    critical: int = 0
    block_publish: bool = False
    block_deadline: bool = False
    auto_fixable: int = 0

    def to_dict(self) -> JsonDict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "info": self.info,
            "warning": self.warning,
            "error": self.error,
            "critical": self.critical,
            "block_publish": self.block_publish,
            "block_deadline": self.block_deadline,
            "auto_fixable": self.auto_fixable,
        }

def summarize_results(results: Iterable[RuleResult]) -> ValidationSummary:
    """Compute severity counts and explicit block status from rule results."""

    total = 0
    status_counts = {"passed": 0, "failed": 0, "skipped": 0}
    severity_counts = {"info": 0, "warning": 0, "error": 0, "critical": 0}
    block_publish = False
    block_deadline = False
    auto_fixable = 0

    for result in results:
        total += 1
        if result.status in status_counts:
            status_counts[result.status] += 1
        if result.severity in severity_counts:
            severity_counts[result.severity] += 1
        block_publish = block_publish or result.block_publish
        block_deadline = block_deadline or result.block_deadline
        if result.auto_fix_available:
            auto_fixable += 1

    return ValidationSummary(
        total=total,
        passed=status_counts["passed"],
        failed=status_counts["failed"],
        skipped=status_counts["skipped"],
        info=severity_counts["info"],
        warning=severity_counts["warning"],
        error=severity_counts["error"],
        critical=severity_counts["critical"],
        block_publish=block_publish,
        block_deadline=block_deadline,
        auto_fixable=auto_fixable,
    )

@dataclass(frozen=True)
class _TargetContext:
    kind: str
    target_id: str
    obj: object
    semantic: Optional[str] = None

class ValidationEngine:
    """Evaluate rule definitions against a GraphSnapshot."""

    def __init__(
        self,
        naming_templates: Mapping[str, str] | None = None,
        studio_environment: Optional[StudioEnvironmentSettings] = None,
    ) -> None:
        self._naming_templates = dict(naming_templates or {})
        self._studio_environment = studio_environment

    def validate(
        self,
        snapshot: GraphSnapshot,
        rules: Iterable[RuleDefinition],
    ) -> list[RuleResult]:
        results: list[RuleResult] = []
        for rule in rules:
            results.extend(self._evaluate_rule(snapshot, rule))
        return results

    def _evaluate_rule(self, snapshot: GraphSnapshot, rule: RuleDefinition) -> list[RuleResult]:
        if not rule.enabled:
            return [self._skipped(rule, reason="rule_disabled")]

        targets = self._targets_for_scope(snapshot, rule.scope)
        matched = [target for target in targets if self._matches(rule.match.criteria, target)]
        if not matched:
            return [self._skipped(rule, reason="no_matching_targets")]

        return [self._evaluate_target(rule, target) for target in matched]

    def _evaluate_target(self, rule: RuleDefinition, target: _TargetContext) -> RuleResult:
        check_type = rule.check.type
        if check_type == "attribute_equals":
            return self._evaluate_attribute_equals(rule, target)
        if check_type == "attribute_in":
            return self._evaluate_attribute_in(rule, target)
        if check_type == "default_material_assignment":
            return self._evaluate_default_material_assignment(rule, target)
        if check_type == "duplicate_file_dependencies":
            return self._evaluate_duplicate_file_dependencies(rule, target)
        if check_type == "duplicate_material_fingerprints":
            return self._evaluate_duplicate_material_fingerprints(rule, target)
        if check_type == "duplicate_geometry":
            return self._evaluate_duplicate_geometry(rule, target)
        if check_type == "duplicate_geometry_scan_budget":
            return self._evaluate_duplicate_geometry_scan_budget(rule, target)
        if check_type == "duplicate_scan_budget":
            return self._evaluate_duplicate_scan_budget(rule, target)
        if check_type == "list_length_max":
            return self._evaluate_list_length_max(rule, target)
        if check_type == "list_length_min":
            return self._evaluate_list_length_min(rule, target)
        if check_type == "name_matches":
            return self._evaluate_name_matches(rule, target)
        if check_type == "numeric_max":
            return self._evaluate_numeric_max(rule, target)
        if check_type == "path_exists":
            return self._evaluate_path_exists(rule, target)
        if check_type == "path_policy":
            return self._evaluate_path_policy(rule, target)
        if check_type == "texture_version_latest":
            return self._evaluate_texture_version_latest(rule, target)
        return self._skipped(
            rule,
            target=target,
            reason=f"unsupported_check_type:{check_type}",
        )

    def _evaluate_attribute_equals(
        self,
        rule: RuleDefinition,
        target: _TargetContext,
    ) -> RuleResult:
        attribute = str(rule.check.params.get("attribute", ""))
        expected = rule.check.params.get("expected")
        current = self._read_value(target, attribute)
        status = "passed" if current == expected else "failed"
        return self._result(
            rule,
            status=status,
            target=target,
            current_value=current,
            expected_value=expected,
            plug=attribute,
        )

    def _evaluate_attribute_in(
        self,
        rule: RuleDefinition,
        target: _TargetContext,
    ) -> RuleResult:
        attribute = str(rule.check.params.get("attribute", ""))
        expected_values = rule.check.params.get("expected")
        if expected_values is None:
            expected_values = rule.check.params.get("allowed", [])
        allowed = expected_values if isinstance(expected_values, list) else [expected_values]
        current = self._read_value(target, attribute)
        status = "passed" if current in allowed else "failed"
        return self._result(
            rule,
            status=status,
            target=target,
            current_value=current,
            expected_value=allowed,
            plug=attribute,
        )

    def _evaluate_default_material_assignment(
        self,
        rule: RuleDefinition,
        target: _TargetContext,
    ) -> RuleResult:
        if not isinstance(target.obj, GraphSnapshot):
            return self._skipped(
                rule,
                target=target,
                reason="default_material_assignment_requires_graph_snapshot",
            )

        assignments = _default_material_assignments(target.obj, rule.check.params)
        status = "failed" if assignments else "passed"
        evidence = {"assignments": assignments} if assignments else {}
        return self._result(
            rule,
            status=status,
            target=target,
            current_value=len(assignments),
            expected_value=0,
            plug="shading_engines",
            evidence=evidence,
        )

    def _evaluate_duplicate_file_dependencies(
        self,
        rule: RuleDefinition,
        target: _TargetContext,
    ) -> RuleResult:
        if not isinstance(target.obj, GraphSnapshot):
            return self._skipped(
                rule,
                target=target,
                reason="duplicate_file_dependencies_requires_graph_snapshot",
            )

        groups, scan_truncated = _duplicate_file_dependency_groups(
            target.obj,
            max_dependencies=_as_optional_int(rule.check.params.get("max_file_dependencies")),
        )
        status = "failed" if groups else "passed"
        evidence: JsonDict = {"duplicate_groups": groups} if groups else {}
        if scan_truncated:
            evidence["file_dependency_scan_truncated"] = True
            evidence["file_dependency_count"] = len(target.obj.file_dependencies)
            evidence["max_file_dependencies"] = rule.check.params.get("max_file_dependencies")
        return self._result(
            rule,
            status=status,
            target=target,
            current_value=len(groups),
            expected_value=0,
            plug="file_dependencies",
            evidence=evidence,
        )

    def _evaluate_duplicate_material_fingerprints(
        self,
        rule: RuleDefinition,
        target: _TargetContext,
    ) -> RuleResult:
        if not isinstance(target.obj, GraphSnapshot):
            return self._skipped(
                rule,
                target=target,
                reason="duplicate_material_fingerprints_requires_graph_snapshot",
            )

        groups, scan_truncated, material_count, scanned_count = (
            _duplicate_material_fingerprint_groups(
                target.obj,
                rule.check.params,
            )
        )
        status = "failed" if groups else "passed"
        evidence: JsonDict = {"duplicate_groups": groups} if groups else {}
        evidence.update(
            {
                "material_count": material_count,
                "scanned_material_count": scanned_count,
            }
        )
        if scan_truncated:
            evidence["material_scan_truncated"] = True
            evidence["max_materials"] = rule.check.params.get("max_materials")
        return self._result(
            rule,
            status=status,
            target=target,
            current_value=len(groups),
            expected_value=0,
            plug="materials",
            evidence=evidence,
        )

    def _evaluate_duplicate_geometry(
        self,
        rule: RuleDefinition,
        target: _TargetContext,
    ) -> RuleResult:
        if not isinstance(target.obj, GraphSnapshot):
            return self._skipped(
                rule,
                target=target,
                reason="duplicate_geometry_requires_graph_snapshot",
            )

        groups, scan_truncated, shape_count, scanned_count = _duplicate_geometry_groups(
            target.obj,
            rule.check.params,
        )
        status = "failed" if groups else "passed"
        evidence: JsonDict = {"duplicate_groups": groups} if groups else {}
        evidence.update(
            {
                "shape_count": shape_count,
                "scanned_shape_count": scanned_count,
            }
        )
        if scan_truncated:
            evidence["geometry_scan_truncated"] = True
            evidence["max_shapes"] = rule.check.params.get("max_shapes")
        return self._result(
            rule,
            status=status,
            target=target,
            current_value=len(groups),
            expected_value=0,
            plug="shapes",
            evidence=evidence,
        )

    def _evaluate_duplicate_geometry_scan_budget(
        self,
        rule: RuleDefinition,
        target: _TargetContext,
    ) -> RuleResult:
        if not isinstance(target.obj, GraphSnapshot):
            return self._skipped(
                rule,
                target=target,
                reason="duplicate_geometry_scan_budget_requires_graph_snapshot",
            )

        max_shapes = _as_optional_int(rule.check.params.get("max_shapes"))
        shape_count = len(target.obj.shapes)
        exceeded = max_shapes is not None and max_shapes > 0 and shape_count > max_shapes
        status = "failed" if exceeded else "passed"
        evidence = {
            "shape_count": shape_count,
            "max_shapes": max_shapes,
        }
        if exceeded:
            evidence["geometry_scan_truncated"] = True
        return self._result(
            rule,
            status=status,
            target=target,
            current_value=shape_count,
            expected_value=max_shapes or 0,
            plug="duplicate_geometry_scan_budget",
            evidence=evidence,
        )

    def _evaluate_duplicate_scan_budget(
        self,
        rule: RuleDefinition,
        target: _TargetContext,
    ) -> RuleResult:
        if not isinstance(target.obj, GraphSnapshot):
            return self._skipped(
                rule,
                target=target,
                reason="duplicate_scan_budget_requires_graph_snapshot",
            )

        max_materials = _as_optional_int(rule.check.params.get("max_materials"))
        max_file_dependencies = _as_optional_int(rule.check.params.get("max_file_dependencies"))
        material_count = len(target.obj.materials)
        file_dependency_count = len(target.obj.file_dependencies)
        material_exceeded = (
            max_materials is not None and max_materials > 0 and material_count > max_materials
        )
        file_dependency_exceeded = (
            max_file_dependencies is not None
            and max_file_dependencies > 0
            and file_dependency_count > max_file_dependencies
        )
        exceeded = material_exceeded or file_dependency_exceeded
        status = "failed" if exceeded else "passed"
        evidence = {
            "material_count": material_count,
            "file_dependency_count": file_dependency_count,
        }
        if max_materials is not None:
            evidence["max_materials"] = max_materials
        if max_file_dependencies is not None:
            evidence["max_file_dependencies"] = max_file_dependencies
        if material_exceeded:
            evidence["material_scan_truncated"] = True
        if file_dependency_exceeded:
            evidence["file_dependency_scan_truncated"] = True
        return self._result(
            rule,
            status=status,
            target=target,
            current_value=max(material_count, file_dependency_count),
            expected_value=max(max_materials or 0, max_file_dependencies or 0),
            plug="duplicate_scan_budget",
            evidence=evidence,
        )

    def _evaluate_list_length_max(
        self,
        rule: RuleDefinition,
        target: _TargetContext,
    ) -> RuleResult:
        attribute = str(rule.check.params.get("attribute", ""))
        maximum = rule.check.params.get("max")
        current = self._read_value(target, attribute)
        maximum_number = _as_float(maximum)
        if not isinstance(current, list) or maximum_number is None:
            return self._skipped(
                rule,
                target=target,
                reason="list_length_max_requires_list_and_numeric_max",
            )

        current_length = len(current)
        status = "passed" if current_length <= maximum_number else "failed"
        return self._result(
            rule,
            status=status,
            target=target,
            current_value=current_length,
            expected_value=maximum,
            plug=attribute,
            evidence={"max": maximum_number},
        )

    def _evaluate_list_length_min(
        self,
        rule: RuleDefinition,
        target: _TargetContext,
    ) -> RuleResult:
        attribute = str(rule.check.params.get("attribute", ""))
        minimum = rule.check.params.get("min")
        current = self._read_value(target, attribute)
        minimum_number = _as_float(minimum)
        if not isinstance(current, list) or minimum_number is None:
            return self._skipped(
                rule,
                target=target,
                reason="list_length_min_requires_list_and_numeric_min",
            )

        current_length = len(current)
        status = "passed" if current_length >= minimum_number else "failed"
        return self._result(
            rule,
            status=status,
            target=target,
            current_value=current_length,
            expected_value=minimum,
            plug=attribute,
            evidence={"min": minimum_number},
        )

    def _evaluate_name_matches(
        self,
        rule: RuleDefinition,
        target: _TargetContext,
    ) -> RuleResult:
        pattern = self._resolve_naming_pattern(rule)
        if not pattern:
            return self._skipped(
                rule,
                target=target,
                reason="naming_template_not_configured",
            )

        try:
            compiled = re.compile(pattern)
        except re.error:
            return self._skipped(
                rule,
                target=target,
                reason="invalid_naming_pattern",
            )

        name_field = str(rule.check.params.get("name_field", "name"))
        object_type = rule.check.params.get("object_type") or rule.match.criteria.get(
            "object_type"
        )
        plug = name_field
        if object_type == "texture":
            texture_path = self._texture_file_path(target)
            if texture_path:
                current = texture_filename_stem(texture_path)
                plug = self._texture_path_attr(target) or "fileTextureName"
            else:
                current = self._read_value(target, name_field)
        else:
            current = self._read_value(target, name_field)
            if object_type in {"mesh", "camera"} and isinstance(target.obj, ShapeSnapshot):
                current = mesh_transform_name_from_shape(target.obj)
        if not isinstance(current, str) or not current.strip():
            return self._skipped(
                rule,
                target=target,
                reason="missing_name",
            )

        status = "passed" if compiled.fullmatch(current) else "failed"
        return self._result(
            rule,
            status=status,
            target=target,
            current_value=current,
            expected_value=pattern,
            plug=plug,
        )

    def _resolve_naming_pattern(self, rule: RuleDefinition) -> Optional[str]:
        params = rule.check.params
        inline_pattern = params.get("pattern")
        if inline_pattern is not None:
            normalized = str(inline_pattern).strip()
            return normalized or None

        object_type = params.get("object_type") or params.get("template_key")
        if object_type is None:
            return None
        return self._naming_templates.get(str(object_type))

    def _texture_file_path(self, target: _TargetContext) -> Optional[str]:
        if not isinstance(target.obj, NodeSnapshot):
            return None
        attr = self._texture_path_attr(target)
        if not attr:
            return None
        value = target.obj.attrs.get(attr)
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    def _texture_path_attr(self, target: _TargetContext) -> Optional[str]:
        if not isinstance(target.obj, NodeSnapshot):
            return None
        return _TEXTURE_PATH_ATTRS.get(target.obj.type_name, "fileTextureName")

    def _evaluate_numeric_max(
        self,
        rule: RuleDefinition,
        target: _TargetContext,
    ) -> RuleResult:
        attribute = str(rule.check.params.get("attribute", ""))
        maximum = rule.check.params.get("max")
        current = self._read_value(target, attribute)
        current_number = _as_float(current)
        maximum_number = _as_float(maximum)
        if current_number is None or maximum_number is None:
            return self._skipped(
                rule,
                target=target,
                reason="numeric_max_requires_numeric_values",
            )

        status = "passed" if current_number <= maximum_number else "failed"
        return self._result(
            rule,
            status=status,
            target=target,
            current_value=current,
            expected_value=maximum,
            plug=attribute,
            evidence={"max": maximum_number},
        )

    def _evaluate_path_exists(self, rule: RuleDefinition, target: _TargetContext) -> RuleResult:
        if not isinstance(target.obj, FileDependencySnapshot):
            return self._skipped(
                rule,
                target=target,
                reason="path_exists_requires_file_dependency",
            )

        status = "passed" if target.obj.exists else "failed"
        return self._result(
            rule,
            status=status,
            target=target,
            current_value=target.obj.resolved_path or target.obj.raw_path,
            expected_value="existing file",
            plug=target.obj.attr,
        )

    def _evaluate_path_policy(self, rule: RuleDefinition, target: _TargetContext) -> RuleResult:
        if not isinstance(target.obj, FileDependencySnapshot):
            return self._skipped(
                rule,
                target=target,
                reason="path_policy_requires_file_dependency",
            )

        violations = _path_policy_violations(
            target.obj,
            rule.check.params,
            studio_environment=self._studio_environment,
        )
        status = "failed" if violations else "passed"
        evidence = {"violations": violations} if violations else {}
        return self._result(
            rule,
            status=status,
            target=target,
            current_value=target.obj.resolved_path or target.obj.raw_path,
            expected_value="path policy compliant",
            plug=target.obj.attr,
            evidence=evidence,
        )

    def _evaluate_texture_version_latest(
        self,
        rule: RuleDefinition,
        target: _TargetContext,
    ) -> RuleResult:
        if not isinstance(target.obj, FileDependencySnapshot):
            return self._skipped(
                rule,
                target=target,
                reason="texture_version_latest_requires_file_dependency",
            )

        current_version = target.obj.version
        latest_version = target.obj.latest_version
        if not current_version or not latest_version:
            return self._skipped(
                rule,
                target=target,
                reason="texture_version_latest_requires_version_metadata",
            )

        status = "passed" if current_version == latest_version else "failed"
        return self._result(
            rule,
            status=status,
            target=target,
            current_value=current_version,
            expected_value=latest_version,
            plug="version",
            evidence={"latest_version": latest_version},
        )

    def _targets_for_scope(self, snapshot: GraphSnapshot, scope: str) -> list[_TargetContext]:
        if scope in {"node", "texture_node"}:
            return [_TargetContext("node", node.id, node) for node in snapshot.nodes]
        if scope == "material":
            return [
                _TargetContext("material", item.node_id, item)
                for item in snapshot.materials
            ]
        if scope == "file_dependency":
            node_semantics = _node_semantics_by_id(snapshot)
            return [
                _TargetContext(
                    "file_dependency",
                    item.node_id,
                    item,
                    node_semantics.get(item.node_id),
                )
                for item in snapshot.file_dependencies
            ]
        if scope == "connection":
            return [
                _TargetContext(
                    "connection",
                    f"{item.src_node}->{item.dst_node}",
                    item,
                    item.semantic,
                )
                for item in snapshot.connections
            ]
        if scope == "shading_engine":
            return [
                _TargetContext("shading_engine", item.node_id, item)
                for item in snapshot.shading_engines
            ]
        if scope in {"shape", "geometry"}:
            return [
                _TargetContext("shape", item.node_id, item)
                for item in snapshot.shapes
            ]
        if scope in {"scene", "graph"}:
            return [_TargetContext(scope, snapshot.scene_path, snapshot)]
        return []

    def _matches(self, criteria: Mapping[str, Any], target: _TargetContext) -> bool:
        for key, expected in criteria.items():
            current = self._read_match_value(target, key)
            if not self._value_matches(current, expected):
                return False
        return True

    def _value_matches(self, current: Any, expected: Any) -> bool:
        if isinstance(expected, list):
            if isinstance(current, list):
                return bool(set(current).intersection(expected))
            return current in expected
        if isinstance(current, list):
            return expected in current
        return current == expected

    def _read_match_value(self, target: _TargetContext, key: str) -> Any:
        if key == "node_type":
            return self._read_value(target, "type_name")
        if key == "object_type":
            return resolve_object_type(target.obj)
        if key == "semantic_slot":
            return target.semantic or self._read_value(target, "semantic_slot")
        if key == "dependency_kind" and isinstance(target.obj, FileDependencySnapshot):
            return "texture"
        if key == "usd_prim" and isinstance(target.obj, FileDependencySnapshot):
            return str(target.obj.node_id).startswith("prim:")
        return self._read_value(target, key)

    def _read_value(self, target: _TargetContext, key: str) -> Any:
        obj = target.obj
        if isinstance(obj, NodeSnapshot) and "." not in key and key in obj.attrs:
            return obj.attrs[key]
        if isinstance(obj, GraphSnapshot) and key == "renderer_family":
            return obj.renderer
        if "." in key:
            return _read_nested_value(obj, key)
        if hasattr(obj, key):
            return getattr(obj, key)
        return None

    def _skipped(
        self,
        rule: RuleDefinition,
        *,
        reason: str,
        target: Optional[_TargetContext] = None,
    ) -> RuleResult:
        evidence = {"reason": reason}
        return self._result(rule, status="skipped", target=target, evidence=evidence)

    def _result(
        self,
        rule: RuleDefinition,
        *,
        status: str,
        target: Optional[_TargetContext] = None,
        current_value: JsonValue = None,
        expected_value: JsonValue = None,
        plug: Optional[str] = None,
        evidence: Optional[Mapping[str, Any]] = None,
    ) -> RuleResult:
        is_failed = status == "failed"
        target_kind = target.kind if target else ""
        target_id = target.target_id if target else ""
        node_name = self._node_name(target) if target else None
        return RuleResult(
            rule_id=rule.id,
            severity=rule.severity,
            status=status,
            title=rule.name,
            message=rule.message,
            why=rule.why,
            owner=rule.owner,
            target_kind=target_kind,
            target_id=target_id,
            node=node_name,
            plug=plug,
            current_value=current_value,
            expected_value=expected_value,
            block_publish=rule.policy.block_publish if is_failed else False,
            block_deadline=rule.policy.block_deadline if is_failed else False,
            auto_fix_available=bool(rule.fix and is_failed and rule.policy.auto_fix_allowed),
            fix_id=rule.fix.type if rule.fix and is_failed else None,
            evidence=dict(evidence or {}),
        )

    def _node_name(self, target: Optional[_TargetContext]) -> Optional[str]:
        if target is None:
            return None
        obj = target.obj
        if isinstance(obj, (NodeSnapshot, MaterialSnapshot, ShadingEngineSnapshot, ShapeSnapshot)):
            if isinstance(obj, NodeSnapshot) and str(obj.id).startswith("prim:"):
                return obj.full_name or obj.id.removeprefix("prim:")
            if isinstance(obj, MaterialSnapshot) and str(obj.node_id).startswith("prim:"):
                return obj.full_name or obj.node_id.removeprefix("prim:")
            return obj.name
        if isinstance(obj, FileDependencySnapshot):
            return obj.node_id.removeprefix("prim:") or obj.node_id
        if isinstance(obj, ConnectionSnapshot):
            return obj.dst_node
        return None

_REQUIRED_RULE_KEYS = frozenset(
    {
        "id",
        "name",
        "enabled",
        "renderer",
        "scope",
        "severity",
        "owner",
        "message",
        "why",
        "match",
        "check",
        "policy",
    }
)

def _node_semantics_by_id(snapshot: GraphSnapshot) -> dict[str, str]:
    semantics: dict[str, str] = {}
    for node in snapshot.nodes:
        semantic = node.attrs.get("semantic_slot")
        if isinstance(semantic, str) and semantic:
            semantics[node.id] = semantic
    return semantics

def _default_material_assignments(
    snapshot: GraphSnapshot,
    params: Mapping[str, Any],
) -> list[JsonDict]:
    default_materials = _normalized_identifier_set(
        params.get("default_materials", ["lambert1", "node:lambert1"])
    )
    default_engines = _normalized_identifier_set(
        params.get("default_shading_engines", ["initialShadingGroup"])
    )

    assignments: list[JsonDict] = []
    for engine in snapshot.shading_engines:
        if not engine.members:
            continue
        is_default_material = _matches_identifier(engine.surface_shader, default_materials)
        is_default_engine = _matches_identifier(engine.name, default_engines)
        is_default_engine = is_default_engine or _matches_identifier(
            engine.node_id,
            default_engines,
        )
        if is_default_material or is_default_engine:
            assignments.append(
                {
                    "shading_engine": engine.node_id,
                    "surface_shader": engine.surface_shader,
                    "members": list(engine.members),
                    "count": len(engine.members),
                }
            )
    return assignments

def _duplicate_file_dependency_groups(
    snapshot: GraphSnapshot,
    *,
    max_dependencies: Optional[int] = None,
) -> tuple[list[JsonDict], bool]:
    dependencies = snapshot.file_dependencies
    scan_truncated = False
    if (
        max_dependencies is not None
        and max_dependencies > 0
        and len(dependencies) > max_dependencies
    ):
        dependencies = sorted(dependencies, key=lambda item: item.node_id)[:max_dependencies]
        scan_truncated = True

    grouped: dict[str, list[FileDependencySnapshot]] = {}
    for dependency in dependencies:
        key = _duplicate_file_dependency_key(dependency)
        if key:
            grouped.setdefault(key, []).append(dependency)

    groups: list[JsonDict] = []
    for path, path_dependencies in sorted(grouped.items()):
        node_ids = sorted({dependency.node_id for dependency in path_dependencies})
        if len(node_ids) > 1:
            groups.append(
                {
                    "path": path,
                    "node_ids": node_ids,
                    "count": len(node_ids),
                }
            )
    return groups, scan_truncated

def _duplicate_material_fingerprint_groups(
    snapshot: GraphSnapshot,
    params: Mapping[str, Any],
) -> tuple[list[JsonDict], bool, int, int]:
    max_materials = _as_optional_int(params.get("max_materials"))
    min_group_size = _as_optional_int(params.get("min_group_size")) or 2
    materials = sorted(snapshot.materials, key=lambda item: item.node_id)
    material_count = len(materials)
    scan_truncated = False
    if max_materials is not None and max_materials > 0 and material_count > max_materials:
        materials = materials[:max_materials]
        scan_truncated = True

    grouped: dict[str, list[MaterialSnapshot]] = {}
    for material in materials:
        fingerprint = material.graph_content_fingerprint
        if not fingerprint:
            continue
        grouped.setdefault(fingerprint, []).append(material)

    groups: list[JsonDict] = []
    for fingerprint, duplicates in sorted(grouped.items()):
        material_ids = sorted({item.node_id for item in duplicates})
        if len(material_ids) < min_group_size:
            continue
        groups.append(
            {
                "fingerprint": fingerprint,
                "material_ids": material_ids,
                "material_names": sorted({item.name for item in duplicates}),
                "count": len(material_ids),
            }
        )
    return groups, scan_truncated, material_count, len(materials)

_PROXY_GEOMETRY_TYPES = frozenset({"aiStandIn", "VRayProxy"})
_PROXY_FILE_ATTRS = ("dso", "fileName", "filename", "vrmesh")


def _duplicate_geometry_groups(
    snapshot: GraphSnapshot,
    params: Mapping[str, Any],
) -> tuple[list[JsonDict], bool, int, int]:
    max_shapes = _as_optional_int(params.get("max_shapes"))
    min_group_size = _as_optional_int(params.get("min_group_size")) or 2
    bbox_precision = _as_optional_int(params.get("bbox_precision")) or 3
    match_attributes = _as_string_list(params.get("match_attributes"))
    include_referenced = bool(params.get("include_referenced", False))

    shapes = sorted(snapshot.shapes, key=lambda item: item.node_id)
    shape_count = len(shapes)
    scan_truncated = False
    if max_shapes is not None and max_shapes > 0 and shape_count > max_shapes:
        shapes = shapes[:max_shapes]
        scan_truncated = True

    grouped: dict[str, list[ShapeSnapshot]] = {}
    for shape in shapes:
        if not include_referenced and shape.referenced:
            continue
        if shape.proxy_attrs.get("intermediateObject") is True:
            continue
        geometry_key = _duplicate_geometry_key(
            shape,
            match_attributes=match_attributes,
            bbox_precision=bbox_precision,
        )
        if not geometry_key:
            continue
        grouped.setdefault(geometry_key, []).append(shape)

    groups: list[JsonDict] = []
    for geometry_key, duplicates in sorted(grouped.items()):
        if _is_intentional_geometry_instance_group(duplicates):
            continue
        shape_ids = sorted({item.node_id for item in duplicates})
        if len(shape_ids) < min_group_size:
            continue
        sample = duplicates[0]
        groups.append(
            {
                "geometry_key": geometry_key,
                "topology_fingerprint": sample.topology_fingerprint,
                "bbox": _bbox_payload(sample.world_bbox),
                "shape_ids": shape_ids,
                "shape_names": sorted({item.name for item in duplicates}),
                "instancing_keys": sorted({item.instancing_key for item in duplicates}),
                "count": len(shape_ids),
            }
        )
    return groups, scan_truncated, shape_count, len(shapes)


def _duplicate_geometry_key(
    shape: ShapeSnapshot,
    *,
    match_attributes: list[str],
    bbox_precision: int,
) -> str:
    if shape.type_name in _PROXY_GEOMETRY_TYPES:
        proxy_value = _proxy_geometry_source(shape)
        if proxy_value:
            return f"proxy:{shape.type_name}:{proxy_value}"
        return f"proxy:{shape.type_name}:{shape.node_id}"

    topology = shape.topology_fingerprint.strip()
    if not topology:
        return ""

    bbox_signature = _bbox_signature(shape.world_bbox, precision=bbox_precision)
    attribute_signature = _geometry_attribute_signature(shape.proxy_attrs, match_attributes)
    return f"mesh:{topology}|{bbox_signature}|{attribute_signature}"


def _proxy_geometry_source(shape: ShapeSnapshot) -> str:
    for attr_name in _PROXY_FILE_ATTRS:
        value = shape.proxy_attrs.get(attr_name)
        if value:
            return str(value)
    return ""


def _geometry_attribute_signature(
    proxy_attrs: Mapping[str, Any],
    match_attributes: list[str],
) -> str:
    if not match_attributes:
        return ""
    parts: list[str] = []
    for attr_name in sorted(match_attributes):
        value = proxy_attrs.get(attr_name)
        if value is not None:
            parts.append(f"{attr_name}={value}")
    return ";".join(parts)


def _bbox_signature(bbox: Optional[BoundingBoxSnapshot], *, precision: int) -> str:
    if bbox is None:
        return "none"
    fmt = f"{{:.{precision}f}}"
    return "|".join(
        [
            fmt.format(bbox.min_x),
            fmt.format(bbox.min_y),
            fmt.format(bbox.min_z),
            fmt.format(bbox.max_x),
            fmt.format(bbox.max_y),
            fmt.format(bbox.max_z),
        ]
    )


def _bbox_payload(bbox: Optional[BoundingBoxSnapshot]) -> Optional[JsonDict]:
    if bbox is None:
        return None
    return bbox.to_dict()


def _is_intentional_geometry_instance_group(shapes: list[ShapeSnapshot]) -> bool:
    if len(shapes) < 2:
        return False
    instancing_keys = {shape.instancing_key for shape in shapes if shape.instancing_key}
    return len(instancing_keys) == 1


def _duplicate_file_dependency_key(dependency: FileDependencySnapshot) -> str:
    path = dependency.resolved_path or dependency.raw_path
    return _normalize_path(path) if path else ""

def _normalized_identifier_set(value: Any) -> set[str]:
    identifiers: set[str] = set()
    for item in _as_string_list(value):
        identifiers.update(_identifier_candidates(item))
    return identifiers

def _matches_identifier(value: Optional[str], identifiers: set[str]) -> bool:
    return bool(_identifier_candidates(value).intersection(identifiers))

def _identifier_candidates(value: Optional[str]) -> set[str]:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return set()
    return {normalized, normalized.rsplit(":", 1)[-1]}

def _read_nested_value(obj: object, key: str) -> Any:
    current: Any = obj
    for part in key.split("."):
        if current is None:
            return None
        if isinstance(current, NodeSnapshot) and part in current.attrs:
            return current.attrs[part]
        if hasattr(current, part):
            current = getattr(current, part)
        else:
            return None
    return current

def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]

def _as_float(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _as_optional_int(value: Any) -> Optional[int]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def _path_policy_violations(
    dependency: FileDependencySnapshot,
    params: Mapping[str, Any],
    *,
    studio_environment: Optional[StudioEnvironmentSettings] = None,
) -> list[str]:
    authored_paths = [dependency.raw_path] if dependency.raw_path else []
    paths = _dependency_paths(dependency)
    disallowed = params.get("disallow", [])
    if not isinstance(disallowed, list):
        disallowed = [disallowed]

    violations: list[str] = []
    for policy in disallowed:
        policy_name = str(policy)
        if policy_name == "local_drive":
            local_drive_hit = False
            resolved = str(dependency.resolved_path or dependency.raw_path or "")
            for path in authored_paths:
                if not _is_local_drive_path(path):
                    continue
                local_drive_hit = True
                break
            if local_drive_hit:
                violations.append("local_drive")
        elif policy_name == "user_home" and any(
            _is_user_home_path(path) for path in authored_paths
        ):
            violations.append("user_home")
        elif policy_name == "desktop" and any(
            _has_path_segment(path, "desktop") for path in authored_paths
        ):
            violations.append("desktop")
        elif policy_name == "downloads" and any(
            _has_path_segment(path, "downloads") for path in authored_paths
        ):
            violations.append("downloads")
        elif policy_name == "temp" and any(
            _is_temp_path(path) for path in authored_paths
        ):
            violations.append("temp")

    allowed_prefixes = params.get("allowed_prefixes", [])
    if allowed_prefixes:
        prefix_list = (
            allowed_prefixes if isinstance(allowed_prefixes, list) else [allowed_prefixes]
        )
        raw_path = str(dependency.raw_path or "")
        resolved_path = str(dependency.resolved_path or raw_path)
        from pipeline_inspector.util.paths import texture_path_policy_compliant

        if not texture_path_policy_compliant(
            raw_path,
            resolved_path,
            prefix_list,
            studio_environment,
        ):
            violations.append("outside_project_root")

    # #region agent log
    if violations or "${" in str(dependency.raw_path or "") or _is_local_drive_path(
        str(dependency.raw_path or "")
    ):
        from pipeline_inspector.util.debug_log import write_debug_log

        write_debug_log(
            "rule_schema._path_policy_violations",
            "File dependency path policy",
            {
                "target_id": str(dependency.node_id or "")[:120],
                "attr": str(dependency.attr or ""),
                "raw_path": str(dependency.raw_path or "")[:160],
                "violations": "|".join(violations) or "none",
                "usd_prim": str(str(dependency.node_id or "").startswith("prim:")),
            },
            hypothesis_id="H37",
        )
    # #endregion

    return violations

def _dependency_paths(dependency: FileDependencySnapshot) -> list[str]:
    return [
        path
        for path in (dependency.raw_path, dependency.resolved_path or "")
        if path
    ]

def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip().rstrip("/").lower()

def _is_local_drive_path(path: str) -> bool:
    normalized = path.replace("\\", "/").strip()
    return len(normalized) >= 3 and normalized[1] == ":" and normalized[2] == "/"

def _is_user_home_path(path: str) -> bool:
    normalized = _normalize_path(path)
    return (
        normalized.startswith("~/")
        or normalized.startswith("/users/")
        or normalized.startswith("/home/")
        or _starts_with_drive_user_path(normalized)
    )

def _starts_with_drive_user_path(path: str) -> bool:
    return len(path) >= 9 and path[1:9] == ":/users/"

def _has_path_segment(path: str, segment: str) -> bool:
    parts = [part for part in _normalize_path(path).split("/") if part]
    return segment.lower() in parts

def _is_temp_path(path: str) -> bool:
    normalized = _normalize_path(path)
    return (
        _has_path_segment(normalized, "temp")
        or _has_path_segment(normalized, "tmp")
        or "/appdata/local/temp/" in f"/{normalized}/"
    )

def _matches_allowed_prefix(paths: list[str], allowed_prefixes: Any) -> bool:
    prefixes = allowed_prefixes if isinstance(allowed_prefixes, list) else [allowed_prefixes]
    normalized_prefixes = [_normalize_path(str(prefix)) for prefix in prefixes if str(prefix)]
    if not normalized_prefixes:
        return True

    normalized_paths = [_normalize_path(path) for path in paths]
    for path in normalized_paths:
        if any(path == prefix or path.startswith(f"{prefix}/") for prefix in normalized_prefixes):
            return True
    return False

def _validate_required_rule_keys(data: Mapping[str, Any]) -> None:
    missing = sorted(key for key in _REQUIRED_RULE_KEYS if key not in data)
    if missing:
        joined = ", ".join(missing)
        raise RuleSchemaError(f"rule is missing required field(s): {joined}")

def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuleSchemaError(f"{label} must be an object")
    return value
