"""Data-driven validation rule schema models.

The rule schema is intentionally Maya-independent. Rules describe what to match,
what to check, how severe the result is, who owns the fix, whether it blocks
production stages, and whether an optional safe fix can be planned.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Optional

JsonDict = dict[str, Any]

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


def _validate_required_rule_keys(data: Mapping[str, Any]) -> None:
    missing = sorted(key for key in _REQUIRED_RULE_KEYS if key not in data)
    if missing:
        joined = ", ".join(missing)
        raise RuleSchemaError(f"rule is missing required field(s): {joined}")


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuleSchemaError(f"{label} must be an object")
    return value
