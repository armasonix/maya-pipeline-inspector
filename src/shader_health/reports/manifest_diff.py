"""Deterministic JSON diff for shader manifests."""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Optional

MANIFEST_DIFF_SCHEMA_VERSION = "1.0"

JsonDict = dict[str, Any]
JsonValue = Any

MATERIAL_FIELDS = (
    "name",
    "type_name",
    "renderer_family",
    "shading_engines",
    "assigned_shapes",
    "graph_fingerprint",
    "graph_node_count",
    "graph_depth",
)
TEXTURE_FIELDS = (
    "node_name",
    "type_name",
    "semantic",
    "attr",
    "raw_path",
    "resolved_path",
    "exists",
    "extension",
    "version",
    "latest_version",
    "is_udim",
    "udim_tiles",
    "missing_udim_tiles",
)


def build_manifest_diff(
    old_manifest: Mapping[str, Any],
    new_manifest: Mapping[str, Any],
) -> JsonDict:
    """Compare two shader manifests and return deterministic JSON-compatible diff."""

    old_items = _manifest_items(old_manifest)
    new_items = _manifest_items(new_manifest)
    old_keys = set(old_items)
    new_keys = set(new_items)

    new_entries = [_new_or_resolved_entry(new_items[key]) for key in sorted(new_keys - old_keys)]
    resolved_entries = [
        _new_or_resolved_entry(old_items[key]) for key in sorted(old_keys - new_keys)
    ]
    changed_entries = [
        _changed_entry(key, old_items[key], new_items[key])
        for key in sorted(old_keys.intersection(new_keys))
        if _item_changes(old_items[key], new_items[key])
    ]
    fingerprint_changes = _fingerprint_change_count(changed_entries)

    return {
        "manifest_diff_schema_version": MANIFEST_DIFF_SCHEMA_VERSION,
        "old_manifest_schema_version": old_manifest.get("manifest_schema_version"),
        "new_manifest_schema_version": new_manifest.get("manifest_schema_version"),
        "old_scene_path": old_manifest.get("scene_path"),
        "new_scene_path": new_manifest.get("scene_path"),
        "summary": {
            "new": len(new_entries),
            "resolved": len(resolved_entries),
            "changed": len(changed_entries),
            "fingerprint_changes": fingerprint_changes,
        },
        "issues": {
            "new": new_entries,
            "resolved": resolved_entries,
            "changed": changed_entries,
        },
        "regression": {
            "fingerprint_drift_detected": fingerprint_changes > 0,
            "manifest_regression_blocked": False,
        },
    }


def dumps_manifest_diff(
    old_manifest: Mapping[str, Any],
    new_manifest: Mapping[str, Any],
    *,
    indent: Optional[int] = 2,
) -> str:
    """Serialize a deterministic shader manifest diff as JSON text."""

    payload = build_manifest_diff(old_manifest, new_manifest)
    return json.dumps(payload, indent=indent, sort_keys=True) + "\n"


def write_manifest_diff(
    path: str | Path,
    old_manifest: Mapping[str, Any],
    new_manifest: Mapping[str, Any],
    *,
    indent: Optional[int] = 2,
) -> Path:
    """Write a shader manifest diff JSON file and return the output path."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        dumps_manifest_diff(old_manifest, new_manifest, indent=indent),
        encoding="utf-8",
    )
    return output_path


def _manifest_items(manifest: Mapping[str, Any]) -> dict[str, JsonDict]:
    items: dict[str, JsonDict] = {}
    for material in _list_of_mappings(manifest.get("materials")):
        material_id = _material_id(material)
        if not material_id:
            continue
        material_key = f"material:{material_id}"
        items[material_key] = {
            "kind": "material",
            "id": material_key,
            "label": str(material.get("name") or material_id),
            "fields": _selected_fields(material, MATERIAL_FIELDS),
        }
        for texture in _list_of_mappings(material.get("textures")):
            texture_id = _texture_id(material_id, texture)
            if not texture_id:
                continue
            items[texture_id] = {
                "kind": "texture",
                "id": texture_id,
                "label": str(texture.get("node_name") or texture.get("node_id") or texture_id),
                "material_id": material_id,
                "fields": _selected_fields(texture, TEXTURE_FIELDS),
            }
    return items


def _selected_fields(source: Mapping[str, Any], fields: tuple[str, ...]) -> JsonDict:
    return {field: _json_safe(source.get(field)) for field in fields}


def _item_changes(old_item: JsonDict, new_item: JsonDict) -> list[JsonDict]:
    old_fields = _fields(old_item)
    new_fields = _fields(new_item)
    changes: list[JsonDict] = []
    for field in sorted(set(old_fields).union(new_fields)):
        old_value = old_fields.get(field)
        new_value = new_fields.get(field)
        if old_value != new_value:
            changes.append({"field": field, "old": old_value, "new": new_value})
    return changes


def _changed_entry(key: str, old_item: JsonDict, new_item: JsonDict) -> JsonDict:
    entry = {
        "kind": new_item["kind"],
        "id": key,
        "label": new_item["label"],
        "changes": _item_changes(old_item, new_item),
    }
    if "material_id" in new_item:
        entry["material_id"] = new_item["material_id"]
    return entry


def _new_or_resolved_entry(item: JsonDict) -> JsonDict:
    entry = {
        "kind": item["kind"],
        "id": item["id"],
        "label": item["label"],
        "fields": item["fields"],
    }
    if "material_id" in item:
        entry["material_id"] = item["material_id"]
    return entry


def _fields(item: JsonDict) -> JsonDict:
    value = item.get("fields")
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _material_id(material: Mapping[str, Any]) -> str:
    return str(material.get("node_id") or material.get("name") or "")


def _texture_id(material_id: str, texture: Mapping[str, Any]) -> str:
    node_id = str(texture.get("node_id") or texture.get("node_name") or "")
    if not node_id:
        return ""
    attr = str(texture.get("attr") or "")
    return f"texture:{material_id}:{node_id}:{attr}"


def _list_of_mappings(value: JsonValue) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


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


def _fingerprint_change_count(changed_entries: list[JsonDict]) -> int:
    count = 0
    for entry in changed_entries:
        for change in entry.get("changes", ()):
            if isinstance(change, Mapping) and change.get("field") == "graph_fingerprint":
                count += 1
    return count
