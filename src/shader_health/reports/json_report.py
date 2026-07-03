"""Deterministic JSON report writer for validation results."""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from shader_health.core import (
    GraphSnapshot,
    RuleResult,
    compute_health_score,
    summarize_results,
)

REPORT_SCHEMA_VERSION = "1.0"

JsonDict = dict[str, Any]
JsonValue = Any


def build_json_report(
    snapshot: GraphSnapshot,
    results: Iterable[RuleResult],
    *,
    fix_audit: Mapping[str, Any] | None = None,
) -> JsonDict:
    """Build the deterministic report payload without writing it to disk."""

    result_list = list(results)
    summary = summarize_results(result_list)
    score = compute_health_score(result_list)
    block_publish = summary.block_publish
    block_deadline = summary.block_deadline

    payload: JsonDict = {
        "block_deadline": block_deadline,
        "block_publish": block_publish,
        "blocking": {
            "any": block_publish or block_deadline,
            "deadline": block_deadline,
            "publish": block_publish,
        },
        "health_score": score.score,
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "results": [
            _json_safe(result.to_dict())
            for result in sorted(result_list, key=_result_sort_key)
        ],
        "score": score.to_dict(),
        "snapshot": _snapshot_metadata(snapshot),
        "snapshot_schema_version": snapshot.schema_version,
        "status": "failed" if summary.failed else "passed",
        "summary": summary.to_dict(),
    }
    if fix_audit is not None:
        payload["fix_audit"] = _json_safe(dict(fix_audit))
    return payload


def dumps_json_report(
    snapshot: GraphSnapshot,
    results: Iterable[RuleResult],
    *,
    indent: int | None = 2,
    fix_audit: Mapping[str, Any] | None = None,
) -> str:
    """Serialize a validation report as deterministic UTF-8 JSON text."""

    payload = build_json_report(snapshot, results, fix_audit=fix_audit)
    return json.dumps(payload, indent=indent, sort_keys=True) + "\n"


def write_json_report(
    path: str | Path,
    snapshot: GraphSnapshot,
    results: Iterable[RuleResult],
    *,
    indent: int | None = 2,
    fix_audit: Mapping[str, Any] | None = None,
) -> Path:
    """Write a deterministic validation report and return the output path."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        dumps_json_report(snapshot, results, indent=indent, fix_audit=fix_audit),
        encoding="utf-8",
    )
    return output_path


def _snapshot_metadata(snapshot: GraphSnapshot) -> JsonDict:
    return {
        "maya_version": snapshot.maya_version,
        "renderer": snapshot.renderer,
        "scan_scope": snapshot.scan_scope,
        "scene_path": snapshot.scene_path,
        "schema_version": snapshot.schema_version,
        "scanned_at_utc": snapshot.scanned_at_utc,
    }


def _result_sort_key(result: RuleResult) -> tuple[str, str, str, str, str, str]:
    return (
        result.rule_id,
        result.target_kind,
        result.target_id,
        result.node or "",
        result.plug or "",
        result.status,
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
