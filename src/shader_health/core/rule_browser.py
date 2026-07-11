"""Packaged rule catalog and safe session override helpers for the rule browser."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shader_health.core.rule_loader import (
    DEFAULT_RULE_ROOT,
    RuleOverride,
    build_rule_search_paths,
    load_rules_from_path,
)
from shader_health.core.rule_schema import SEVERITIES, RuleDefinition

SAFE_SEVERITIES = tuple(sorted(SEVERITIES))
THRESHOLD_PARAM_BY_CHECK_TYPE = {
    "numeric_max": "max",
    "list_length_max": "max",
    "numeric_min": "min",
}


@dataclass(frozen=True)
class RuleBrowserEntry:
    """One packaged rule shown in the rule browser."""

    rule: RuleDefinition
    source_label: str


@dataclass(frozen=True)
class EditableRuleFields:
    """Safe subset of rule fields exposed in the MVP editor."""

    rule_id: str
    enabled: bool
    severity: str
    threshold_key: str = ""
    threshold_value: int | float | None = None
    threshold_editable: bool = False


def load_packaged_rules_catalog(
    *,
    rule_root: Path = DEFAULT_RULE_ROOT,
    renderer_ids: Iterable[str] = ("common", "vray", "arnold"),
    extra_rule_paths: Iterable[Path] = (),
) -> tuple[RuleBrowserEntry, ...]:
    """Load deterministic packaged rules for browsing."""

    rules_by_id: dict[str, RuleBrowserEntry] = {}
    for path in build_rule_search_paths(rule_root, renderer_ids, extra_rule_paths):
        for rule in load_rules_from_path(path):
            rules_by_id[rule.id] = RuleBrowserEntry(
                rule=rule,
                source_label=_source_label(path, rule_root),
            )
    return tuple(entry for _, entry in sorted(rules_by_id.items()))


def effective_rule(
    entry: RuleBrowserEntry,
    session_override: RuleOverride | None,
) -> RuleDefinition:
    """Return the rule definition after applying a session override."""

    if session_override is None:
        return entry.rule
    return session_override.apply(entry.rule)


def editable_fields_for_rule(rule: RuleDefinition) -> EditableRuleFields:
    """Return the safe editable subset for one rule."""

    threshold = editable_threshold(rule)
    if threshold is None:
        threshold_key = ""
        threshold_value = None
    else:
        threshold_key, threshold_value = threshold
    return EditableRuleFields(
        rule_id=rule.id,
        enabled=bool(rule.enabled),
        severity=str(rule.severity),
        threshold_key=threshold_key or "",
        threshold_value=threshold_value,
        threshold_editable=threshold_key != "",
    )


def editable_threshold(rule: RuleDefinition) -> tuple[str, int | float] | None:
    """Return the threshold field name and value when the rule supports editing."""

    threshold_key = THRESHOLD_PARAM_BY_CHECK_TYPE.get(rule.check.type)
    if threshold_key is None:
        return None
    raw_value = rule.check.params.get(threshold_key)
    if isinstance(raw_value, bool):
        return None
    if isinstance(raw_value, int) and not isinstance(raw_value, bool):
        return threshold_key, raw_value
    if isinstance(raw_value, float):
        return threshold_key, raw_value
    return None


def build_session_override_from_edits(
    base_rule: RuleDefinition,
    *,
    enabled: bool,
    severity: str,
    threshold_key: str = "",
    threshold_value: int | float | None = None,
) -> RuleOverride | None:
    """Build a session override or return None when edits match packaged defaults."""

    normalized_severity = severity.strip().lower()
    if normalized_severity not in SEVERITIES:
        allowed = ", ".join(SAFE_SEVERITIES)
        raise ValueError(f"severity must be one of: {allowed}")

    enabled_override = enabled if enabled != base_rule.enabled else None
    severity_override = (
        normalized_severity if normalized_severity != base_rule.severity else None
    )

    check_params: dict[str, Any] | None = None
    base_threshold = editable_threshold(base_rule)
    if threshold_key and threshold_value is not None:
        if base_threshold is None or base_threshold[0] != threshold_key:
            raise ValueError(f"Rule {base_rule.id!r} does not support threshold {threshold_key!r}")
        numeric_value = _coerce_threshold_value(threshold_value)
        if numeric_value != base_threshold[1]:
            check_params = {threshold_key: numeric_value}

    if enabled_override is None and severity_override is None and check_params is None:
        return None

    return RuleOverride(
        rule_id=base_rule.id,
        enabled=enabled_override,
        severity=severity_override,
        check_params=check_params,
    )


def merge_session_rule_overrides(
    profile_overrides: Mapping[str, RuleOverride],
    session_overrides: Mapping[str, RuleOverride],
) -> dict[str, RuleOverride]:
    """Merge session overrides on top of profile overrides."""

    merged = dict(profile_overrides)
    merged.update(session_overrides)
    return merged


def _coerce_threshold_value(value: int | float) -> int | float:
    if isinstance(value, bool):
        raise ValueError("threshold must be numeric")
    if isinstance(value, int):
        if value < 0:
            raise ValueError("threshold must be zero or greater")
        return value
    if isinstance(value, float):
        if value < 0:
            raise ValueError("threshold must be zero or greater")
        return value
    raise ValueError("threshold must be numeric")


def _source_label(path: Path, rule_root: Path) -> str:
    try:
        return str(path.relative_to(rule_root))
    except ValueError:
        return str(path)
