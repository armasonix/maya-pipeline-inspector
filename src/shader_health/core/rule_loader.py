"""Rule pack loading and profile override resolution."""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Optional

from shader_health.core.manifest_gate import ManifestGatePolicy
from shader_health.core.rule_schema import (
    SEVERITIES,
    RuleDefinition,
    RulePolicy,
    RuleSchemaError,
)

JsonDict = dict[str, Any]

DEFAULT_RULE_ROOT = Path(__file__).resolve().parents[1] / "rules"

_OVERRIDE_KEYS = frozenset(
    {
        "enabled",
        "severity",
        "block_publish",
        "block_deadline",
        "waiver_allowed",
        "auto_fix_allowed",
        "check",
    }
)
_POLICY_OVERRIDE_KEYS = frozenset(
    {
        "block_publish",
        "block_deadline",
        "waiver_allowed",
        "auto_fix_allowed",
    }
)


class RuleLoadError(ValueError):
    """Raised when rule packs or profiles cannot be loaded."""


@dataclass(frozen=True)
class RuleOverride:
    """Profile-level override for one rule."""

    rule_id: str
    enabled: Optional[bool] = None
    severity: Optional[str] = None
    block_publish: Optional[bool] = None
    block_deadline: Optional[bool] = None
    waiver_allowed: Optional[bool] = None
    auto_fix_allowed: Optional[bool] = None
    check_params: Optional[JsonDict] = None

    @classmethod
    def from_dict(cls, rule_id: str, data: Mapping[str, Any]) -> RuleOverride:
        unknown = sorted(set(data) - _OVERRIDE_KEYS)
        if unknown:
            raise RuleLoadError(
                f"override for {rule_id!r} has unknown field(s): {', '.join(unknown)}"
            )

        severity = data.get("severity")
        if severity is not None and severity not in SEVERITIES:
            allowed = ", ".join(sorted(SEVERITIES))
            raise RuleLoadError(
                f"override for {rule_id!r} has invalid severity; expected: {allowed}"
            )

        for key in sorted(_OVERRIDE_KEYS - {"severity", "check"}):
            value = data.get(key)
            if value is not None and not isinstance(value, bool):
                raise RuleLoadError(f"override for {rule_id!r}: {key} must be a boolean")

        raw_check = data.get("check")
        check_params = None
        if raw_check is not None:
            if not isinstance(raw_check, Mapping):
                raise RuleLoadError(f"override for {rule_id!r}: check must be an object")
            check_params = dict(raw_check)

        return cls(
            rule_id=rule_id,
            enabled=data.get("enabled"),
            severity=severity,
            block_publish=data.get("block_publish"),
            block_deadline=data.get("block_deadline"),
            waiver_allowed=data.get("waiver_allowed"),
            auto_fix_allowed=data.get("auto_fix_allowed"),
            check_params=check_params,
        )

    def apply(self, rule: RuleDefinition) -> RuleDefinition:
        policy_values = rule.policy.to_dict()
        for key in sorted(_POLICY_OVERRIDE_KEYS):
            value = getattr(self, key)
            if value is not None:
                policy_values[key] = value

        new_policy = RulePolicy.from_dict(policy_values)
        new_fix = rule.fix
        if new_fix is not None and not new_policy.auto_fix_allowed:
            new_fix = None

        new_check = rule.check
        if self.check_params:
            merged_params = dict(rule.check.params)
            merged_params.update(self.check_params)
            new_check = replace(rule.check, params=merged_params)

        updated = replace(
            rule,
            enabled=rule.enabled if self.enabled is None else self.enabled,
            severity=rule.severity if self.severity is None else self.severity,
            policy=new_policy,
            fix=new_fix,
            check=new_check,
        )
        updated.validate()
        return updated


@dataclass(frozen=True)
class ProfileDefinition:
    """Profile definition containing rule overrides."""

    id: str
    display_name: str
    rule_overrides: dict[str, RuleOverride]
    manifest_diff_policy: ManifestGatePolicy = ManifestGatePolicy()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ProfileDefinition:
        profile_id = str(data.get("id", "")).strip()
        if not profile_id:
            raise RuleLoadError("profile.id is required")

        raw_overrides = data.get("rule_overrides", {})
        if not isinstance(raw_overrides, Mapping):
            raise RuleLoadError("profile.rule_overrides must be an object")

        overrides = {
            str(rule_id): RuleOverride.from_dict(str(rule_id), _require_mapping(value, rule_id))
            for rule_id, value in raw_overrides.items()
        }
        raw_policy = data.get("manifest_diff_policy")
        policy = ManifestGatePolicy.from_mapping(
            raw_policy if isinstance(raw_policy, Mapping) else None
        )

        return cls(
            id=profile_id,
            display_name=str(data.get("display_name", profile_id)),
            rule_overrides=overrides,
            manifest_diff_policy=policy,
        )


def load_profile(path: Path) -> ProfileDefinition:
    payload = _load_json(path)
    return ProfileDefinition.from_dict(_require_mapping(payload, path))


def load_rule_file(path: Path) -> list[RuleDefinition]:
    payload = _load_json(path)
    rules: list[RuleDefinition] = []
    for index, raw_rule in enumerate(_iter_rule_objects(payload, path), start=1):
        try:
            rules.append(RuleDefinition.from_dict(raw_rule))
        except RuleSchemaError as exc:
            raise RuleLoadError(f"{path}: rule #{index}: {exc}") from exc
    return rules


def load_rules_from_path(path: Path) -> list[RuleDefinition]:
    if path.is_file():
        return load_rule_file(path)
    if path.is_dir():
        rules: list[RuleDefinition] = []
        for rule_file in sorted(path.rglob("*.json")):
            rules.extend(load_rule_file(rule_file))
        return rules
    raise RuleLoadError(f"Rule path does not exist: {path}")


def build_rule_search_paths(
    rule_root: Path = DEFAULT_RULE_ROOT,
    renderer_ids: Iterable[str] = (),
    extra_rule_paths: Iterable[Path] = (),
) -> list[Path]:
    """Return deterministic rule search paths: common, renderers, extras."""

    paths: list[Path] = []
    common_path = rule_root / "common"
    if common_path.exists():
        paths.append(common_path)

    seen_renderers = {"common"}
    for renderer_id in renderer_ids:
        renderer = renderer_id.strip().lower()
        if not renderer or renderer in seen_renderers:
            continue
        seen_renderers.add(renderer)
        renderer_path = rule_root / renderer
        if renderer_path.exists():
            paths.append(renderer_path)

    paths.extend(sorted(extra_rule_paths))
    return paths


def load_rule_stack(
    rule_root: Path = DEFAULT_RULE_ROOT,
    renderer_ids: Iterable[str] = (),
    profile_path: Optional[Path] = None,
    profile: Optional[ProfileDefinition] = None,
    extra_rule_paths: Iterable[Path] = (),
) -> list[RuleDefinition]:
    """Load common + renderer + extra rules and apply optional profile overrides."""

    if profile_path is not None and profile is not None:
        raise RuleLoadError("Provide either profile_path or profile, not both.")

    rules_by_id: dict[str, RuleDefinition] = {}
    for path in build_rule_search_paths(rule_root, renderer_ids, extra_rule_paths):
        for rule in load_rules_from_path(path):
            rules_by_id[rule.id] = rule

    rules = list(rules_by_id.values())
    if profile is not None:
        return apply_profile_overrides(rules, profile)
    if profile_path is None:
        return rules

    return apply_profile_overrides(rules, load_profile(profile_path))


def apply_profile_overrides(
    rules: Iterable[RuleDefinition],
    profile: ProfileDefinition,
) -> list[RuleDefinition]:
    resolved: list[RuleDefinition] = []
    for rule in rules:
        override = profile.rule_overrides.get(rule.id)
        resolved.append(rule if override is None else override.apply(rule))
    return resolved


def validate_profile_overrides(
    profile: ProfileDefinition,
    rules_by_id: Mapping[str, RuleDefinition],
) -> None:
    unknown = sorted(set(profile.rule_overrides) - set(rules_by_id))
    if unknown:
        raise RuleLoadError(
            f"profile {profile.id!r} references unknown rule(s): {', '.join(unknown)}"
        )


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuleLoadError(f"{path}: invalid JSON: {exc}") from exc
    except OSError as exc:
        raise RuleLoadError(f"{path}: cannot read file: {exc}") from exc


def _iter_rule_objects(payload: Any, path: Path) -> list[Mapping[str, Any]]:
    if isinstance(payload, Mapping):
        if "rules" not in payload:
            return [_require_mapping(payload, path)]

        raw_rules = payload["rules"]
        if not isinstance(raw_rules, list):
            raise RuleLoadError(f"{path}: 'rules' must be a list")
        return [_require_mapping(item, path) for item in raw_rules]

    if isinstance(payload, list):
        return [_require_mapping(item, path) for item in payload]

    raise RuleLoadError(f"{path}: root must be an object, a list, or an object with 'rules'")


def _require_mapping(value: Any, label: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuleLoadError(f"{label}: expected object")
    return value
