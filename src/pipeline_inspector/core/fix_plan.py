"""Safe auto-fix planning for validation results."""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Optional

from pipeline_inspector.core.models import (
    GraphSnapshot,
    MaterialSnapshot,
    NodeSnapshot,
    ShapeSnapshot,
)
from pipeline_inspector.core.naming_fix import (
    propose_naming_fix,
    propose_texture_file_path_fix,
    texture_filename_stem,
)
from pipeline_inspector.core.rule_schema import RuleDefinition, RuleResult
from pipeline_inspector.studio_config import StudioEnvironmentSettings
from pipeline_inspector.util.paths import (
    effective_studio_normalize_target,
    normalize_path_to_studio_tokens,
    replace_path_prefix,
    studio_environment_is_configured,
    studio_normalize_prefixes,
)

JsonDict = dict[str, Any]
JsonValue = Any

_REFERENCE_BLOCK_REASON = "target_referenced"
_LOCKED_BLOCK_REASON = "target_locked"
HIGH_RISK_BLOCK_REASON = "high_risk_requires_explicit_confirmation"
INVALID_NORMALIZE_PATH_REASON = "invalid_normalize_path"
TEXTURE_FILE_MISSING_BLOCK_REASON = "texture_file_missing"
UNPLANNABLE_EXPECTED_VALUES = frozenset(
    {
        "path policy compliant",
        "existing file",
    }
)
_VERSION_TOKEN_RE = re.compile(r"(?i)v(?P<version>\d+)")
UNDO_SUPPORTED_FIX_TYPES = frozenset(
    {
        "set_attr",
        "relink_path",
        "normalize_path",
        "disable_feature",
        "rename_node",
        "set_default_prim",
    }
)
NAMING_FIX_TYPE = "rename_node"
TEXTURE_FILE_FIX_TYPE = "rename_texture_file"

@dataclass(frozen=True)
class FixAction:
    """Previewable, non-mutating safe-fix action produced by the planner."""

    fix_id: str
    rule_id: str
    title: str
    fix_type: str
    risk: str
    target_kind: str
    target_id: str
    target_node: str
    target_attr: Optional[str] = None
    before_value: JsonValue = None
    after_value: JsonValue = None
    explanation: str = ""
    referenced: bool = False
    locked: bool = False
    reference_path: Optional[str] = None
    requires_reference_edit: bool = False
    requires_supervisor: bool = False
    undo_supported: bool = True
    blocked: bool = False
    block_reasons: list[str] = field(default_factory=list)
    params: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        """Return a deterministic JSON-compatible representation."""

        return {
            "fix_id": self.fix_id,
            "rule_id": self.rule_id,
            "title": self.title,
            "fix_type": self.fix_type,
            "risk": self.risk,
            "target_kind": self.target_kind,
            "target_id": self.target_id,
            "target_node": self.target_node,
            "target_attr": self.target_attr,
            "before_value": self.before_value,
            "after_value": self.after_value,
            "explanation": self.explanation,
            "referenced": self.referenced,
            "locked": self.locked,
            "reference_path": self.reference_path,
            "requires_reference_edit": self.requires_reference_edit,
            "requires_supervisor": self.requires_supervisor,
            "undo_supported": self.undo_supported,
            "blocked": self.blocked,
            "block_reasons": list(self.block_reasons),
            "params": dict(self.params),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> FixAction:
        block_reasons = data.get("block_reasons", [])
        params = data.get("params", {})
        return cls(
            fix_id=str(data.get("fix_id", "")),
            rule_id=str(data.get("rule_id", "")),
            title=str(data.get("title", "")),
            fix_type=str(data.get("fix_type", "")),
            risk=str(data.get("risk", "")),
            target_kind=str(data.get("target_kind", "")),
            target_id=str(data.get("target_id", "")),
            target_node=str(data.get("target_node", "")),
            target_attr=data.get("target_attr"),
            before_value=data.get("before_value"),
            after_value=data.get("after_value"),
            explanation=str(data.get("explanation", "")),
            referenced=bool(data.get("referenced", False)),
            locked=bool(data.get("locked", False)),
            reference_path=data.get("reference_path"),
            requires_reference_edit=bool(data.get("requires_reference_edit", False)),
            requires_supervisor=bool(data.get("requires_supervisor", False)),
            undo_supported=bool(data.get("undo_supported", True)),
            blocked=bool(data.get("blocked", False)),
            block_reasons=list(block_reasons) if isinstance(block_reasons, list) else [],
            params=dict(params) if isinstance(params, Mapping) else {},
        )

@dataclass(frozen=True)
class FixPlan:
    """Collection of planned fix actions."""

    actions: tuple[FixAction, ...] = ()

    @property
    def total(self) -> int:
        return len(self.actions)

    @property
    def safe_count(self) -> int:
        return sum(1 for action in self.actions if not action.blocked)

    @property
    def blocked_count(self) -> int:
        return sum(1 for action in self.actions if action.blocked)

    def to_dict(self) -> JsonDict:
        """Return a deterministic JSON-compatible representation."""

        return {
            "total": self.total,
            "safe_count": self.safe_count,
            "blocked_count": self.blocked_count,
            "actions": [action.to_dict() for action in self.actions],
        }

def fix_plan_from_export(data: Mapping[str, Any]) -> FixPlan:
    """Load a fix plan from a deterministic export JSON payload."""

    raw_actions = data.get("actions", [])
    if not isinstance(raw_actions, list):
        raise ValueError("fix plan export actions must be a list")
    actions = tuple(
        FixAction.from_dict(item) for item in raw_actions if isinstance(item, Mapping)
    )
    return FixPlan(actions=actions)

def build_fix_plan(
    results: Iterable[RuleResult],
    rules: Iterable[RuleDefinition],
    snapshot: GraphSnapshot,
    *,
    studio_environment: Optional[StudioEnvironmentSettings] = None,
) -> FixPlan:
    """Build a non-mutating fix plan from failed validation results."""

    rules_by_id = {rule.id: rule for rule in rules}
    node_index = _NodeIndex(snapshot, studio_environment=studio_environment)
    actions: list[FixAction] = []

    for result in results:
        if result.status != "failed":
            continue
        rule = rules_by_id.get(result.rule_id)
        if rule is None:
            continue
        if rule.fix is not None:
            actions.append(_build_action(result, rule, node_index))
            continue
        naming_action = _build_naming_action(result, rule, node_index)
        if naming_action is not None:
            actions.append(naming_action)

    return FixPlan(actions=tuple(actions))


def apply_fix_availability(
    results: Iterable[RuleResult],
    fix_plan: FixPlan,
) -> list[RuleResult]:
    """Mark validation results auto-fixable when the fix planner produced an action."""

    available_keys = {
        (action.rule_id, action.target_id)
        for action in fix_plan.actions
        if not action.blocked
    }
    enriched: list[RuleResult] = []
    for result in results:
        key = (result.rule_id, result.target_id)
        if key not in available_keys:
            enriched.append(result)
            continue
        fix_id = next(
            (
                action.fix_id
                for action in fix_plan.actions
                if action.rule_id == result.rule_id
                and action.target_id == result.target_id
                and not action.blocked
            ),
            None,
        )
        enriched.append(
            replace(
                result,
                auto_fix_available=True,
                fix_id=fix_id or result.fix_id,
            )
        )
    return enriched

def _build_naming_action(
    result: RuleResult,
    rule: RuleDefinition,
    node_index: _NodeIndex,
) -> Optional[FixAction]:
    if rule.check.type != "name_matches" or not rule.policy.auto_fix_allowed:
        return None
    pattern = result.expected_value
    current_name = result.current_value
    if not isinstance(pattern, str) or not pattern.strip():
        return None
    if not isinstance(current_name, str) or not current_name.strip():
        return None

    object_type = rule.check.params.get("object_type") or rule.match.criteria.get(
        "object_type"
    )
    if object_type == "texture":
        return _build_texture_file_naming_action(result, rule, node_index, pattern)

    rename_target = _resolve_naming_rename_target(
        result,
        node_index,
        pattern=pattern,
        current_name=current_name,
        object_type=str(object_type or ""),
    )
    if rename_target is None:
        return None
    target_node, rename_before, proposed_name = rename_target
    if not proposed_name or proposed_name == rename_before:
        return None

    node = node_index.find(result)
    shape = (
        node_index.find_shape(result)
        if str(object_type or "") == "mesh"
        else None
    )
    ref_source = shape if shape is not None else node
    referenced = bool(ref_source.referenced) if ref_source is not None else False
    locked = bool(ref_source.locked) if ref_source is not None else False
    if shape is not None and str(object_type or "") == "mesh":
        transform = node_index.find_by_id(shape.transform_id)
        if transform is not None:
            locked = locked or bool(transform.locked)
    reference_path = (
        getattr(ref_source, "reference_path", None) if ref_source is not None else None
    )
    block_reasons = _block_reasons(
        ref_source,
        "low",
        fix_type=NAMING_FIX_TYPE,
    )
    target_id, target_node, action_params = _usd_prim_fix_fields(
        result,
        node,
        target_node=target_node,
        base_params={"pattern": pattern, "object_type": object_type},
    )

    return FixAction(
        fix_id=_fix_id(result, NAMING_FIX_TYPE),
        rule_id=rule.id,
        title=f"{rule.name}: rename",
        fix_type=NAMING_FIX_TYPE,
        risk="low",
        target_kind=result.target_kind,
        target_id=target_id,
        target_node=target_node,
        before_value=rename_before,
        after_value=proposed_name,
        explanation=result.why or rule.why,
        referenced=referenced,
        locked=locked,
        reference_path=reference_path,
        requires_reference_edit=referenced,
        requires_supervisor=False,
        undo_supported=True,
        blocked=bool(hard_block_reasons(block_reasons)),
        block_reasons=block_reasons,
        params=action_params,
    )


def _find_transform_for_shape(
    shape: ShapeSnapshot,
    node_index: _NodeIndex,
) -> Optional[tuple[str, str]]:
    """Return (target_node, transform_short_name) for a mesh shape snapshot."""

    transform = node_index.find_by_id(shape.transform_id)
    if transform is not None and transform.type_name in ("", "transform"):
        transform_name = transform.name or _short_dag_name(transform.full_name)
        target_node = transform.full_name or transform.name
        if transform_name and target_node:
            return target_node, transform_name

    if shape.full_name and "|" in shape.full_name:
        parent_path = shape.full_name.rsplit("|", 1)[0]
        parent_name = _short_dag_name(parent_path)
        if parent_name:
            return parent_path, parent_name

    transform_name = _transform_short_name_from_id(shape.transform_id)
    if transform_name:
        return transform_name, transform_name

    inferred_name = _infer_transform_name_from_shape_name(shape.name)
    if inferred_name:
        return inferred_name, inferred_name
    return None


def _transform_short_name_from_id(transform_id: str) -> str:
    token = str(transform_id or "").strip()
    if token.startswith("transform:"):
        return token.split(":", 1)[1]
    return ""


def _infer_transform_name_from_shape_name(shape_name: str) -> str:
    normalized = str(shape_name or "").strip()
    if not normalized:
        return ""
    match = re.search(r"Shape\d*$", normalized)
    if match:
        return normalized[: match.start()]
    return normalized


def _resolve_naming_rename_target(
    result: RuleResult,
    node_index: _NodeIndex,
    *,
    pattern: str,
    current_name: str,
    object_type: str,
) -> Optional[tuple[str, str, str]]:
    """Resolve DAG target and before/after names for a naming rename fix."""

    node = node_index.find(result)
    default_target = _target_node_name(result, node)
    if object_type == "mesh":
        shape = node_index.find_shape(result)
        if shape is not None:
            transform_target = _find_transform_for_shape(shape, node_index)
            if transform_target is not None:
                target_node, transform_name = transform_target
                proposed = propose_naming_fix(transform_name, pattern)
                if proposed and proposed != transform_name:
                    return target_node, transform_name, proposed

    proposed_name = propose_naming_fix(current_name, pattern)
    if not proposed_name or proposed_name == current_name:
        return None
    return default_target, current_name, proposed_name


def _short_dag_name(name: str) -> str:
    normalized = str(name or "").strip()
    if not normalized:
        return ""
    return normalized.split("|")[-1].split(":")[-1]


def _build_texture_file_naming_action(
    result: RuleResult,
    rule: RuleDefinition,
    node_index: _NodeIndex,
    pattern: str,
) -> Optional[FixAction]:
    dependency = node_index.file_dependency(result.target_id)
    raw_path = dependency.raw_path if dependency is not None else None
    if not raw_path:
        return None

    proposed_path = propose_texture_file_path_fix(raw_path, pattern)
    if not proposed_path or proposed_path == raw_path:
        return None

    proposed_node = propose_naming_fix(texture_filename_stem(raw_path), pattern)
    if not proposed_node:
        proposed_node = propose_naming_fix(str(result.node or ""), pattern)
    if not proposed_node:
        return None

    node = node_index.find(result)
    target_node = _target_node_name(result, node)
    block_reasons = _block_reasons(node, "low")
    if dependency is not None and not dependency.exists:
        block_reasons.append(TEXTURE_FILE_MISSING_BLOCK_REASON)
    if dependency is not None and dependency.is_udim and not dependency.exists:
        block_reasons.append(TEXTURE_FILE_MISSING_BLOCK_REASON)

    target_id, target_node, action_params = _usd_prim_fix_fields(
        result,
        node,
        target_node=target_node,
        base_params={
            "pattern": pattern,
            "node_name_before": result.node or texture_filename_stem(raw_path),
            "node_name_after": proposed_node,
            "resolved_before": dependency.resolved_path if dependency else raw_path,
            "is_udim": bool(dependency.is_udim) if dependency else False,
        },
    )

    return FixAction(
        fix_id=_fix_id(result, TEXTURE_FILE_FIX_TYPE),
        rule_id=rule.id,
        title=f"{rule.name}: rename texture file",
        fix_type=TEXTURE_FILE_FIX_TYPE,
        risk="medium",
        target_kind=result.target_kind,
        target_id=target_id,
        target_node=target_node,
        target_attr=dependency.attr if dependency else "fileTextureName",
        before_value=raw_path,
        after_value=proposed_path,
        explanation=(
            "Renames the texture file on disk, updates the file node path, "
            "and aligns the Maya file node name with the studio template."
        ),
        referenced=bool(node.referenced) if node else False,
        locked=bool(node.locked) if node else False,
        reference_path=node.reference_path if node else None,
        requires_reference_edit=bool(node.referenced) if node else False,
        requires_supervisor=False,
        undo_supported=False,
        blocked=bool(hard_block_reasons(block_reasons)),
        block_reasons=block_reasons,
        params=action_params,
    )


def _build_action(
    result: RuleResult,
    rule: RuleDefinition,
    node_index: _NodeIndex,
) -> FixAction:
    assert rule.fix is not None
    node = node_index.find(result)
    target_node = _target_node_name(result, node)
    target_attr = _target_attr(result, rule.fix.params)
    fix_type = rule.fix.type
    before_value = _before_value(result, node_index, fix_type)
    after_value = _after_value(
        result,
        rule.fix.params,
        fix_type,
        node_index=node_index,
    )
    block_reasons = _block_reasons(node, rule.fix.risk)
    if fix_type == "normalize_path" and not _is_plannable_normalize(
        before_value,
        after_value,
    ):
        block_reasons.append(INVALID_NORMALIZE_PATH_REASON)
    if fix_type == "relink_path" and not _is_plannable_path_value(after_value):
        block_reasons.append(INVALID_NORMALIZE_PATH_REASON)

    params = dict(rule.fix.to_dict())
    if node_index.scene_path:
        params["scene_path"] = node_index.scene_path
    if (
        node_index.studio_environment is not None
        and studio_environment_is_configured(node_index.studio_environment)
    ):
        params["studio_environment"] = node_index.studio_environment.to_dict()

    return FixAction(
        fix_id=_fix_id(result, rule.fix.type),
        rule_id=rule.id,
        title=f"{rule.name}: {rule.fix.type}",
        fix_type=rule.fix.type,
        risk=rule.fix.risk,
        target_kind=result.target_kind,
        target_id=result.target_id,
        target_node=target_node,
        target_attr=target_attr,
        before_value=before_value,
        after_value=after_value,
        explanation=result.why or rule.why,
        referenced=bool(node.referenced) if node else False,
        locked=bool(node.locked) if node else False,
        reference_path=node.reference_path if node else None,
        requires_reference_edit=bool(node.referenced) if node else False,
        requires_supervisor=rule.fix.risk == "high",
        undo_supported=rule.fix.type in UNDO_SUPPORTED_FIX_TYPES,
        blocked=bool(hard_block_reasons(block_reasons)),
        block_reasons=block_reasons,
        params=params,
    )

def _target_attr(result: RuleResult, fix_params: Mapping[str, Any]) -> Optional[str]:
    attr = fix_params.get("attribute")
    if attr:
        return str(attr)
    return result.plug

def _before_value(
    result: RuleResult,
    node_index: _NodeIndex,
    fix_type: str,
) -> JsonValue:
    if fix_type in {"relink_path", "normalize_path"}:
        dependency_path = node_index.file_dependency_path(result.target_id)
        if dependency_path:
            return dependency_path
    return result.current_value

def _after_value(
    result: RuleResult,
    fix_params: Mapping[str, Any],
    fix_type: str,
    *,
    node_index: Optional[_NodeIndex] = None,
) -> JsonValue:
    if fix_type == "relink_path":
        explicit_path = fix_params.get("path")
        if isinstance(explicit_path, str) and explicit_path.strip():
            return explicit_path.strip()
        dependency_path = (
            node_index.file_dependency_path(result.target_id) if node_index is not None else None
        )
        if dependency_path and result.current_value and result.expected_value:
            relinked = swap_texture_version_in_path(
                dependency_path,
                str(result.current_value),
                str(result.expected_value),
            )
            if relinked is not None:
                return relinked
    if fix_type == "normalize_path":
        dependency_path = (
            node_index.file_dependency_path(result.target_id) if node_index is not None else None
        )
        before_path = str(dependency_path or result.current_value or "")
        normalized = resolve_normalize_path_value(
            before_path,
            fix_params,
            scene_path=node_index.scene_path if node_index is not None else "",
            studio_environment=(
                node_index.studio_environment if node_index is not None else None
            ),
        )
        if normalized is not None:
            return normalized
    if fix_type == "disable_feature":
        if "value" in fix_params:
            return fix_params["value"]
        return False
    if fix_type == "set_default_prim":
        value_from = fix_params.get("value_from")
        if isinstance(value_from, str) and node_index is not None:
            nested = _read_snapshot_value(node_index.snapshot, value_from)
            if nested:
                return nested
    if "value" in fix_params:
        return fix_params["value"]
    if "path" in fix_params:
        return fix_params["path"]
    return result.expected_value

def swap_texture_version_in_path(
    path: str,
    current_version: str,
    latest_version: str,
) -> Optional[str]:
    """Replace the first v### token in a texture path with the latest version."""

    current_digits = current_version.lstrip("vV")
    latest_digits = latest_version.lstrip("vV")
    if not current_digits.isdigit() or not latest_digits.isdigit():
        return None

    match = _VERSION_TOKEN_RE.search(path)
    if match is None or match.group("version") != current_digits:
        return None

    width = len(match.group("version"))
    replacement = f"v{int(latest_digits):0{width}d}"
    start, end = match.span()
    return path[:start] + replacement + path[end:]

def _block_reasons(
    node: NodeSnapshot | ShapeSnapshot | None,
    risk: str,
    *,
    fix_type: Optional[str] = None,
) -> list[str]:
    reasons: list[str] = []
    referenced = bool(node.referenced) if node is not None else False
    skip_reference_lock = referenced and fix_type == NAMING_FIX_TYPE
    if node is not None and node.locked and not skip_reference_lock:
        reasons.append(_LOCKED_BLOCK_REASON)
    if risk == "high":
        reasons.append(HIGH_RISK_BLOCK_REASON)
    return reasons

def hard_block_reasons(block_reasons: Iterable[str]) -> list[str]:
    """Return block reasons that prevent application without override flags."""

    return [reason for reason in block_reasons if reason != HIGH_RISK_BLOCK_REASON]

def _target_node_name(result: RuleResult, node: Optional[NodeSnapshot]) -> str:
    if node is not None:
        return node.full_name or node.name or node.id
    return result.node or result.target_id


def _usd_prim_fix_fields(
    result: RuleResult,
    node: Optional[NodeSnapshot],
    *,
    target_node: str,
    base_params: dict[str, Any],
) -> tuple[str, str, dict[str, Any]]:
    """Prefer full USD prim paths in fix actions when the snapshot provides them."""

    params = dict(base_params)
    target_id = result.target_id
    resolved_target_node = target_node
    if node is None or not str(node.id).startswith("prim:"):
        return target_id, resolved_target_node, params

    prim_path = str(node.full_name or node.id.removeprefix("prim:")).strip()
    if prim_path and not prim_path.startswith("/"):
        prim_path = f"/{prim_path.lstrip('/')}"
    if prim_path:
        params["resolved_prim_path"] = prim_path
        target_id = f"prim:{prim_path}"
        resolved_target_node = prim_path
    return target_id, resolved_target_node, params

def _fix_id(result: RuleResult, fix_type: str) -> str:
    target = result.target_id or result.node or "scene"
    return f"{result.rule_id}:{target}:{fix_type}"

def resolve_normalize_path_value(
    before_path: str,
    fix_params: Mapping[str, Any],
    *,
    planned_after: JsonValue = None,
    scene_path: str = "",
    studio_environment: Optional[StudioEnvironmentSettings] = None,
) -> Optional[str]:
    """Resolve the target path for a normalize_path fix."""

    explicit_path = fix_params.get("path")
    if isinstance(explicit_path, str) and explicit_path.strip():
        return explicit_path.strip()

    if studio_environment is not None:
        tokenized = normalize_path_to_studio_tokens(before_path, studio_environment)
        if tokenized is not None:
            return tokenized

    replace_from = fix_params.get("replace_from")
    replace_to = fix_params.get("replace_to")
    effective_replace_to = (
        effective_studio_normalize_target(str(replace_to), studio_environment)
        if replace_to
        else ""
    )
    if replace_from and replace_to:
        normalized = replace_path_prefix(
            before_path,
            str(replace_from),
            effective_replace_to or str(replace_to),
        )
        if normalized is not None:
            return normalized

    if effective_replace_to or replace_to:
        target_replace_to = effective_replace_to or str(replace_to)
        if studio_environment is not None:
            for root, token in studio_normalize_prefixes(studio_environment):
                normalized = replace_path_prefix(before_path, root, token)
                if normalized is not None:
                    return normalized
        project_root = project_root_from_scene(
            str(fix_params.get("scene_path") or scene_path or "")
        )
        if project_root:
            normalized = replace_path_prefix(before_path, project_root, target_replace_to)
            if normalized is not None:
                return normalized
        basename_target = _normalize_to_asset_root_basename(before_path, target_replace_to)
        if basename_target is not None:
            return basename_target

    if isinstance(planned_after, str) and planned_after.strip():
        return planned_after.strip()
    return None

def project_root_from_scene(scene_path: str) -> Optional[str]:
    """Best-effort project root for local path normalization."""

    if not scene_path.strip():
        return None
    scene = Path(scene_path).resolve()
    for parent in (scene.parent, *scene.parents):
        if (parent / "src" / "pipeline_inspector").is_dir():
            return str(parent).replace("\\", "/")
    return str(scene.parent).replace("\\", "/")

def _normalize_to_asset_root_basename(before_path: str, replace_to: str) -> Optional[str]:
    """Map standalone local paths to ${ASSET_ROOT}/textures/<filename>."""

    normalized_path = before_path.replace("\\", "/").strip()
    if not normalized_path:
        return None
    filename = Path(normalized_path).name
    if not filename:
        return None
    asset_root = replace_to.replace("\\", "/").rstrip("/")
    if not asset_root:
        return None
    return f"{asset_root}/textures/{filename}"

def _is_plannable_path_value(value: JsonValue) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip()
    if not normalized:
        return False
    return normalized.casefold() not in UNPLANNABLE_EXPECTED_VALUES

def _is_plannable_normalize(before_value: JsonValue, after_value: JsonValue) -> bool:
    if not _is_plannable_path_value(after_value):
        return False
    return str(before_value or "").strip() != str(after_value or "").strip()


@dataclass(frozen=True)
class _FileDependencyRef:
    raw_path: str
    resolved_path: str
    attr: str
    is_udim: bool
    exists: bool


class _NodeIndex:
    def __init__(
        self,
        snapshot: GraphSnapshot,
        *,
        studio_environment: Optional[StudioEnvironmentSettings] = None,
    ) -> None:
        self.scene_path = snapshot.scene_path or ""
        self.snapshot = snapshot
        self.studio_environment = studio_environment
        self._by_key: dict[str, NodeSnapshot] = {}
        self._shapes_by_id: dict[str, ShapeSnapshot] = {}
        self._file_dependencies: dict[str, _FileDependencyRef] = {}
        for node in snapshot.nodes:
            self._add(node.id, node)
            self._add(node.name, node)
            self._add(node.full_name, node)
            if node.type_name == "transform":
                self._add(f"transform:{node.name}", node)
        for material in snapshot.materials:
            self._add_material(material)
            self._add(
                material.node_id,
                NodeSnapshot(id=material.node_id, name=material.name, full_name=material.name),
            )
            self._add(material.name, NodeSnapshot(id=material.node_id, name=material.name))
        for shading_engine in snapshot.shading_engines:
            self._add(
                shading_engine.node_id,
                NodeSnapshot(
                    id=shading_engine.node_id,
                    name=shading_engine.name,
                    full_name=shading_engine.name,
                ),
            )
            self._add(
                shading_engine.name,
                NodeSnapshot(id=shading_engine.node_id, name=shading_engine.name),
            )
        for shape in snapshot.shapes:
            self._shapes_by_id[shape.node_id] = shape
            shape_node = NodeSnapshot(
                id=shape.node_id,
                name=shape.name,
                full_name=shape.full_name or shape.name,
                referenced=shape.referenced,
                locked=shape.locked,
            )
            self._add(shape.node_id, shape_node)
            self._add(shape.name, shape_node)
            if shape.full_name:
                self._add(shape.full_name, shape_node)
        for dependency in snapshot.file_dependencies:
            raw_path = dependency.raw_path or dependency.resolved_path or ""
            resolved_path = dependency.resolved_path or dependency.raw_path or ""
            self._file_dependencies[dependency.node_id] = _FileDependencyRef(
                raw_path=raw_path,
                resolved_path=resolved_path,
                attr=dependency.attr,
                is_udim=dependency.is_udim,
                exists=dependency.exists,
            )

    def file_dependency(self, target_id: str) -> Optional[_FileDependencyRef]:
        return self._file_dependencies.get(str(target_id or ""))

    def file_dependency_path(self, target_id: str) -> Optional[str]:
        dependency = self.file_dependency(target_id)
        if dependency is None:
            return None
        path = dependency.raw_path.strip()
        return path or None

    def find(self, result: RuleResult) -> Optional[NodeSnapshot]:
        for key in (result.target_id, result.node):
            node = self._by_key.get(str(key or ""))
            if node is not None:
                return node
        return None

    def find_shape(self, result: RuleResult) -> Optional[ShapeSnapshot]:
        return self._shapes_by_id.get(str(result.target_id or ""))

    def find_by_id(self, node_id: str) -> Optional[NodeSnapshot]:
        normalized = str(node_id or "").strip()
        if not normalized:
            return None
        return self._by_key.get(normalized)

    def _add(self, key: str, node: NodeSnapshot) -> None:
        if key:
            self._by_key.setdefault(key, node)

    def _add_material(self, material: MaterialSnapshot) -> None:
        node = self._by_key.get(material.node_id)
        if node is not None:
            self._add(material.name, node)


def _read_snapshot_value(snapshot: GraphSnapshot, dotted_path: str) -> Any:
    from pipeline_inspector.core.rule_schema import _read_nested_value

    return _read_nested_value(snapshot, dotted_path)
