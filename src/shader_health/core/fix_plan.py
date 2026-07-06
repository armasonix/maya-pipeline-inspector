"""Safe auto-fix planning for validation results."""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from shader_health.core.models import GraphSnapshot, MaterialSnapshot, NodeSnapshot
from shader_health.core.rule_schema import RuleDefinition, RuleResult

JsonDict = dict[str, Any]
JsonValue = Any

_REFERENCE_BLOCK_REASON = "target_referenced"
_LOCKED_BLOCK_REASON = "target_locked"
HIGH_RISK_BLOCK_REASON = "high_risk_requires_explicit_confirmation"
INVALID_NORMALIZE_PATH_REASON = "invalid_normalize_path"
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
    }
)


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


def build_fix_plan(
    results: Iterable[RuleResult],
    rules: Iterable[RuleDefinition],
    snapshot: GraphSnapshot,
) -> FixPlan:
    """Build a non-mutating fix plan from failed validation results."""

    rules_by_id = {rule.id: rule for rule in rules}
    node_index = _NodeIndex(snapshot)
    actions: list[FixAction] = []

    for result in results:
        if result.status != "failed":
            continue
        rule = rules_by_id.get(result.rule_id)
        if rule is None or rule.fix is None:
            continue
        actions.append(_build_action(result, rule, node_index))

    return FixPlan(actions=tuple(actions))


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
        )
        if normalized is not None:
            return normalized
    if fix_type == "disable_feature":
        if "value" in fix_params:
            return fix_params["value"]
        return False
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


def _block_reasons(node: Optional[NodeSnapshot], risk: str) -> list[str]:
    reasons: list[str] = []
    if node is not None and node.locked:
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


def _fix_id(result: RuleResult, fix_type: str) -> str:
    target = result.target_id or result.node or "scene"
    return f"{result.rule_id}:{target}:{fix_type}"


def replace_path_prefix(path: str, old_prefix: str, new_prefix: str) -> Optional[str]:
    """Replace a path prefix, preserving the remainder of the path."""

    path_norm = path.replace("\\", "/")
    old_norm = old_prefix.replace("\\", "/").rstrip("/")
    new_norm = new_prefix.replace("\\", "/").rstrip("/")
    if not path_norm or not old_norm or not new_norm:
        return None

    if path_norm.lower() == old_norm.lower():
        return new_norm

    old_with_sep = f"{old_norm}/"
    if path_norm.lower().startswith(old_with_sep.lower()):
        suffix = path_norm[len(old_norm) :]
        return new_norm + suffix
    return None


def resolve_normalize_path_value(
    before_path: str,
    fix_params: Mapping[str, Any],
    *,
    planned_after: JsonValue = None,
    scene_path: str = "",
) -> Optional[str]:
    """Resolve the target path for a normalize_path fix."""

    explicit_path = fix_params.get("path")
    if isinstance(explicit_path, str) and explicit_path.strip():
        return explicit_path.strip()

    replace_from = fix_params.get("replace_from")
    replace_to = fix_params.get("replace_to")
    if replace_from and replace_to:
        normalized = replace_path_prefix(before_path, str(replace_from), str(replace_to))
        if normalized is not None:
            return normalized

    if replace_to:
        project_root = project_root_from_scene(
            str(fix_params.get("scene_path") or scene_path or "")
        )
        if project_root:
            normalized = replace_path_prefix(before_path, project_root, str(replace_to))
            if normalized is not None:
                return normalized
        basename_target = _normalize_to_asset_root_basename(before_path, str(replace_to))
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
        if (parent / "src" / "shader_health").is_dir():
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


class _NodeIndex:
    def __init__(self, snapshot: GraphSnapshot) -> None:
        self.scene_path = snapshot.scene_path or ""
        self._by_key: dict[str, NodeSnapshot] = {}
        self._dependency_paths: dict[str, str] = {}
        for node in snapshot.nodes:
            self._add(node.id, node)
            self._add(node.name, node)
            self._add(node.full_name, node)
        for material in snapshot.materials:
            self._add_material(material)
        for dependency in snapshot.file_dependencies:
            self._dependency_paths[dependency.node_id] = (
                dependency.raw_path or dependency.resolved_path or ""
            )

    def file_dependency_path(self, target_id: str) -> Optional[str]:
        path = self._dependency_paths.get(str(target_id or ""), "").strip()
        return path or None

    def find(self, result: RuleResult) -> Optional[NodeSnapshot]:
        for key in (result.target_id, result.node):
            node = self._by_key.get(str(key or ""))
            if node is not None:
                return node
        return None

    def _add(self, key: str, node: NodeSnapshot) -> None:
        if key:
            self._by_key.setdefault(key, node)

    def _add_material(self, material: MaterialSnapshot) -> None:
        node = self._by_key.get(material.node_id)
        if node is not None:
            self._add(material.name, node)
