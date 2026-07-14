"""Studio naming-template helpers and object-type resolution for validation."""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Optional

from pipeline_inspector.core.models import (
    MaterialSnapshot,
    NodeSnapshot,
    ShadingEngineSnapshot,
    ShapeSnapshot,
)

NAMING_OBJECT_TYPES: tuple[str, ...] = (
    "mesh",
    "group",
    "material",
    "control",
    "texture",
    "shading_engine",
)


def format_naming_templates_text(templates: Mapping[str, str]) -> str:
    """Serialize configured naming templates for the studio settings editor."""

    lines: list[str] = []
    for object_type in NAMING_OBJECT_TYPES:
        pattern = str(templates.get(object_type, "") or "").strip()
        if pattern:
            lines.append(f"{object_type}={pattern}")
    return "\n".join(lines)


def parse_naming_templates_text(text: str) -> dict[str, str]:
    """Parse `object_type=regex` lines from the studio settings editor."""

    templates: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        object_type, _, pattern = line.partition("=")
        normalized_type = object_type.strip()
        normalized_pattern = pattern.strip()
        if normalized_type in NAMING_OBJECT_TYPES and normalized_pattern:
            templates[normalized_type] = normalized_pattern
    return templates


def normalize_naming_templates(raw: Mapping[str, Any] | None) -> dict[str, str]:
    """Keep only supported object types with non-empty regex patterns."""

    if not raw:
        return {}
    templates: dict[str, str] = {}
    for object_type in NAMING_OBJECT_TYPES:
        value = raw.get(object_type)
        if value is None:
            continue
        pattern = str(value).strip()
        if pattern:
            templates[object_type] = pattern
    return templates


def resolve_object_type(target_obj: object) -> Optional[str]:
    """Map a validation target snapshot to a studio naming object type."""

    if isinstance(target_obj, MaterialSnapshot):
        return "material"
    if isinstance(target_obj, ShadingEngineSnapshot):
        return "shading_engine"
    if isinstance(target_obj, ShapeSnapshot):
        type_name = target_obj.type_name.lower()
        if type_name == "nurbscurve":
            return "control"
        if type_name in {"mesh", "nurbssurface", "subdiv", "aistandin", "vrayproxy"}:
            return "mesh"
        return None
    if isinstance(target_obj, NodeSnapshot):
        if "group" in target_obj.classification:
            return "group"
        if "control" in target_obj.classification:
            return "control"
        if "material" in target_obj.classification:
            return "material"
        if "texture" in target_obj.classification or "file" in target_obj.classification:
            return "texture"
        type_name = target_obj.type_name.lower()
        if type_name == "transform":
            return "group"
        if type_name == "nurbscurve":
            return "control"
        if type_name in {"file", "vraybitmap", "aiimage"}:
            return "texture"
    return None


def compile_naming_pattern(pattern: str) -> re.Pattern[str]:
    """Compile a naming regex used by the `name_matches` check."""

    return re.compile(str(pattern))


def name_matches_pattern(name: str, pattern: str) -> bool:
    """Return whether the full node name matches the naming regex."""

    return bool(compile_naming_pattern(pattern).fullmatch(name))
