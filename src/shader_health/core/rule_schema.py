"""Data-driven validation rule schema models and base rule evaluation.

The rule schema is intentionally Maya-independent. Rules describe what to match,
what to check, how severe the result is, who owns the fix, whether it blocks
production stages, and whether an optional safe fix can be planned.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Optional

from shader_health.core.models import (
    ConnectionSnapshot,
    FileDependencySnapshot,
    GraphSnapshot,
    MaterialSnapshot,
    NodeSnapshot,
    ShadingEngineSnapshot,
)

JsonDict = dict[str, Any]
JsonValue = Any

RULE_SCHEMA_VERSION = "1.0"

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
        if check_type == "path_exists":
            return self._evaluate_path_exists(rule, target)
        if check_type == "path_policy":
            return self._evaluate_path_policy(rule, target)
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

        violations = _path_policy_violations(target.obj, rule.check.params)
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

    def _targets_for_scope(self, snapshot: GraphSnapshot, scope: str) -> list[_TargetContext]:
        if scope in {"node", "texture_node"}:
            return [_TargetContext("node", node.id, node) for node in snapshot.nodes]
        if scope == "material":
            return [
                _TargetContext("material", item.node_id, item)
                for item in snapshot.materials
            ]
        if scope == "file_dependency":
            return [
                _TargetContext("file_dependency", item.node_id, item)
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
        if key == "semantic_slot":
            return target.semantic or self._read_value(target, "semantic_slot")
        if key == "dependency_kind" and isinstance(target.obj, FileDependencySnapshot):
            return "texture"
        return self._read_value(target, key)

    def _read_value(self, target: _TargetContext, key: str) -> Any:
        obj = target.obj
        if isinstance(obj, NodeSnapshot) and key in obj.attrs:
            return obj.attrs[key]
        if isinstance(obj, GraphSnapshot) and key == "renderer_family":
            return obj.renderer
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
        if isinstance(obj, (NodeSnapshot, MaterialSnapshot, ShadingEngineSnapshot)):
            return obj.name
        if isinstance(obj, FileDependencySnapshot):
            return obj.node_id
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


def _path_policy_violations(
    dependency: FileDependencySnapshot,
    params: Mapping[str, Any],
) -> list[str]:
    paths = _dependency_paths(dependency)
    disallowed = params.get("disallow", [])
    if not isinstance(disallowed, list):
        disallowed = [disallowed]

    violations: list[str] = []
    for policy in disallowed:
        policy_name = str(policy)
        if policy_name == "local_drive" and any(_is_local_drive_path(path) for path in paths):
            violations.append("local_drive")
        elif policy_name == "user_home" and any(_is_user_home_path(path) for path in paths):
            violations.append("user_home")
        elif policy_name == "desktop" and any(_has_path_segment(path, "desktop") for path in paths):
            violations.append("desktop")
        elif policy_name == "downloads" and any(_has_path_segment(path, "downloads") for path in paths):
            violations.append("downloads")
        elif policy_name == "temp" and any(_is_temp_path(path) for path in paths):
            violations.append("temp")

    allowed_prefixes = params.get("allowed_prefixes", [])
    if allowed_prefixes and not _matches_allowed_prefix(paths, allowed_prefixes):
        violations.append("outside_project_root")

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
