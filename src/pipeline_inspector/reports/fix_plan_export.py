"""Deterministic fix plan export writer."""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pipeline_inspector.core.fix_plan import FixAction, FixPlan
from pipeline_inspector.core.models import GraphSnapshot

FIX_PLAN_SCHEMA_VERSION = "1.0"

JsonDict = dict[str, Any]
JsonValue = Any

def build_fix_plan_export(
    fix_plan: FixPlan,
    *,
    snapshot: GraphSnapshot,
    profile_id: str,
) -> JsonDict:
    """Build a deterministic fix plan export payload without writing it to disk."""

    actions = tuple(
        sorted(fix_plan.actions, key=_action_sort_key)
    )
    safe_count = sum(1 for action in actions if not action.blocked)
    blocked_count = sum(1 for action in actions if action.blocked)
    return {
        "actions": [_json_safe(action.to_dict()) for action in actions],
        "blocked_count": blocked_count,
        "fix_plan_schema_version": FIX_PLAN_SCHEMA_VERSION,
        "profile_id": profile_id,
        "safe_count": safe_count,
        "scan_scope": snapshot.scan_scope,
        "scene_path": snapshot.scene_path,
        "total": len(actions),
    }

def dumps_fix_plan_export(
    fix_plan: FixPlan,
    *,
    snapshot: GraphSnapshot,
    profile_id: str,
    indent: int | None = 2,
) -> str:
    """Serialize a fix plan export as deterministic UTF-8 JSON text."""

    payload = build_fix_plan_export(fix_plan, snapshot=snapshot, profile_id=profile_id)
    return json.dumps(payload, indent=indent, sort_keys=True) + "\n"

def write_fix_plan_export(
    path: str | Path,
    fix_plan: FixPlan,
    *,
    snapshot: GraphSnapshot,
    profile_id: str,
    indent: int | None = 2,
) -> Path:
    """Write a deterministic fix plan export and return the output path."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        dumps_fix_plan_export(
            fix_plan,
            snapshot=snapshot,
            profile_id=profile_id,
            indent=indent,
        ),
        encoding="utf-8",
    )
    return output_path

def _action_sort_key(action: FixAction) -> tuple[str, str, str, str]:
    return (
        action.fix_id,
        action.rule_id,
        action.target_id,
        action.fix_type,
    )

def _json_safe(value: JsonValue) -> JsonValue:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
