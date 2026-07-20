"""Collapse duplicate USD/Maya validation hits to one canonical prim per material slot."""
from __future__ import annotations

import re
from collections import defaultdict

from pipeline_inspector.core.models import GraphSnapshot, NodeSnapshot
from pipeline_inspector.core.rule_schema import RuleResult
from pipeline_inspector.usd.enrichment import usd_material_name_from_prim_path

_COLORSPACE_RULE_PREFIX = "common.texture.colorspace."
_MATERIAL_FROM_FLATTENED = re.compile(
    r"_mtl_([^_/]+(?:_[^_/]+)?)(?:_[Vv][Rr]ay|_[Uu]sd|_|$)",
    re.IGNORECASE,
)
_TEXTURE_SUFFIX_RE = re.compile(r"(?:_place2dtexture\d*|_bitmap|_tex)$", re.IGNORECASE)
_MTL_SEGMENT_RE = re.compile(r"_[Mm][Tt][Ll]_")

def dedupe_validation_results(
    snapshot: GraphSnapshot,
    results: list[RuleResult],
) -> list[RuleResult]:
    """Keep one canonical colorspace issue per material semantic slot on merged USD scenes."""

    if not any(str(node.id).startswith("prim:") for node in snapshot.nodes):
        return results

    nodes_by_id = {node.id: node for node in snapshot.nodes}
    groups: dict[tuple[str, str, str], list[RuleResult]] = defaultdict(list)
    for result in results:
        if result.status != "failed" or not result.rule_id.startswith(_COLORSPACE_RULE_PREFIX):
            continue
        groups[_colorspace_group_key(result, nodes_by_id)].append(result)

    if not groups:
        return results

    keep_ids: set[tuple[str, str]] = set()
    for group_results in groups.values():
        winner = max(group_results, key=lambda item: _colorspace_node_score(item, nodes_by_id))
        keep_ids.add((winner.rule_id, winner.target_id))

    deduped: list[RuleResult] = []
    dropped = 0
    for result in results:
        if (
            result.status == "failed"
            and result.rule_id.startswith(_COLORSPACE_RULE_PREFIX)
            and (result.rule_id, result.target_id) not in keep_ids
        ):
            dropped += 1
            continue
        deduped.append(result)
    if dropped:
        kept_targets = sorted(target_id for rule_id, target_id in keep_ids)
        _debug_dedupe_log(
            dropped=dropped,
            kept=len(keep_ids),
            groups=len(groups),
            kept_targets="|".join(kept_targets),
        )
    return deduped


def _debug_dedupe_log(*, dropped: int, kept: int, groups: int, kept_targets: str = "") -> None:
    from pipeline_inspector.util.debug_log import write_debug_log

    write_debug_log(
        "usd_validation_dedupe.dedupe_validation_results",
        "Colorspace results deduped",
        {
            "dropped": str(dropped),
            "kept": str(kept),
            "groups": str(groups),
            "kept_targets": kept_targets,
        },
        hypothesis_id="H8",
    )


def _colorspace_group_key(
    result: RuleResult,
    nodes_by_id: dict[str, NodeSnapshot],
) -> tuple[str, str, str]:
    node = nodes_by_id.get(result.target_id)
    material = _resolve_material_for_result(result, node)
    texture_key = _resolve_texture_identity(result, node)
    return (result.rule_id, material, texture_key)


def _resolve_texture_identity(
    result: RuleResult,
    node: NodeSnapshot | None,
) -> str:
    candidates: list[str] = []
    if node is not None:
        candidates.extend(
            [
                str(node.full_name or ""),
                str(node.name or ""),
            ]
        )
    candidates.extend(
        [
            str(result.node or ""),
            str(result.target_id or ""),
        ]
    )
    for candidate in candidates:
        normalized = _normalize_texture_identity(candidate)
        if normalized:
            return normalized
    if node is not None:
        semantic = str(node.attrs.get("semantic_slot") or "").strip()
        if semantic:
            return semantic
    return ""


def _normalize_texture_identity(text: str) -> str:
    normalized = str(text or "").strip()
    if not normalized:
        return ""
    segment = normalized.replace("\\", "/").rsplit("/", 1)[-1]
    segment = segment.removeprefix("node:").removeprefix("char_usd_asset:").removeprefix("prim:")
    if _MTL_SEGMENT_RE.search(segment):
        segment = _MTL_SEGMENT_RE.split(segment)[-1]
    while True:
        stripped = _TEXTURE_SUFFIX_RE.sub("", segment)
        if stripped == segment:
            break
        segment = stripped
    segment = re.sub(r"_place2dtexture\d*$", "", segment, flags=re.IGNORECASE)
    segment = re.sub(r"_bitmap$", "", segment, flags=re.IGNORECASE)
    segment = re.sub(r"_tex$", "", segment, flags=re.IGNORECASE)
    return segment.casefold()


def _resolve_material_for_result(
    result: RuleResult,
    node: NodeSnapshot | None,
) -> str:
    if node is not None and str(node.id).startswith("prim:"):
        prim_path = node.full_name or node.id.removeprefix("prim:")
        material = usd_material_name_from_prim_path(prim_path)
        if material:
            return material

    for token in (result.target_id, result.node or ""):
        if not token:
            continue
        normalized = str(token).removeprefix("node:").removeprefix("char_usd_asset:")
        match = _MATERIAL_FROM_FLATTENED.search(normalized)
        if match:
            return match.group(1)
        material = usd_material_name_from_prim_path(normalized)
        if material:
            return material
    return str(result.material or "")


def _colorspace_node_score(
    result: RuleResult,
    nodes_by_id: dict[str, NodeSnapshot],
) -> int:
    target_id = str(result.target_id or "")
    node_name = str(result.node or "")
    if target_id.startswith("node:") and not target_id.startswith("prim:"):
        return 0

    prim_path = target_id.removeprefix("prim:") if target_id.startswith("prim:") else node_name
    lowered = prim_path.casefold()
    if "/usdpreviewsurface/" in lowered and "bitmap" not in lowered and (
        "place2dtexture" not in lowered
    ):
        return 100
    if "place2dtexture" in lowered:
        return 25
    if "bitmap" in lowered:
        return 20
    if "/vray/" in lowered:
        return 30
    node = nodes_by_id.get(result.target_id)
    if node is not None and node.type_name == "Shader":
        return 40
    return 10
