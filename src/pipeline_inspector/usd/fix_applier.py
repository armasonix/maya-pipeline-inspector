"""Apply safe fixes to OpenUSD assets."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Optional

from pipeline_inspector.core.fix_plan import FixAction, resolve_normalize_path_value
from pipeline_inspector.studio_config import StudioEnvironmentSettings

UNSUPPORTED_FIX_REASON = "unsupported_fix_type"
INVALID_TARGET_REASON = "invalid_usd_target"
RENAME_FAILED_REASON = "rename_failed"
SET_DEFAULT_PRIM_FIX_TYPE = "set_default_prim"
SET_ATTR_FIX_TYPE = "set_attr"
RENAME_NODE_FIX_TYPE = "rename_node"
RENAME_TEXTURE_FILE_FIX_TYPE = "rename_texture_file"
SUPPORTED_FIX_TYPES = frozenset(
    {
        "relink_path",
        "normalize_path",
        SET_DEFAULT_PRIM_FIX_TYPE,
        SET_ATTR_FIX_TYPE,
        RENAME_NODE_FIX_TYPE,
        RENAME_TEXTURE_FILE_FIX_TYPE,
    }
)


@dataclass(frozen=True)
class AppliedUsdFixRecord:
    fix_id: str
    fix_type: str
    target_id: str
    target_attr: Optional[str]
    before_value: Any
    after_value: Any
    succeeded: bool
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        target_node = str(self.target_id or "")
        if target_node.startswith("prim:"):
            target_node = target_node.removeprefix("prim:")
        rule_id = self.fix_id.rsplit(":", 1)[0] if self.fix_id else ""
        return {
            "fix_id": self.fix_id,
            "rule_id": rule_id,
            "fix_type": self.fix_type,
            "target_node": target_node,
            "target_attr": self.target_attr,
            "before_value": self.before_value,
            "after_value": self.after_value,
            "applied": self.succeeded,
            "blocked": self.message == "blocked",
            "message": self.message,
            "block_reasons": [],
        }


def apply_usd_fix_actions(
    usd_path: Path | str,
    actions: list[FixAction],
    *,
    stage: Any = None,
    studio_environment: Optional[StudioEnvironmentSettings] = None,
) -> list[AppliedUsdFixRecord]:
    """Apply planned fixes to a USD asset on disk or an already-open stage."""

    Usd, UsdShade, Sdf = _import_usd_modules()
    path = Path(usd_path).resolve()
    opened_stage = stage
    if opened_stage is None:
        opened_stage = Usd.Stage.Open(str(path))
    if opened_stage is None:
        raise RuntimeError(f"Unable to open USD stage: {path}")

    records = _apply_usd_fix_actions_to_stage(
        opened_stage,
        actions,
        anchor_dir=path.parent,
        studio_environment=studio_environment,
        Usd=Usd,
        UsdShade=UsdShade,
        Sdf=Sdf,
    )
    opened_stage.GetRootLayer().Save()
    return records


def _apply_usd_fix_actions_to_stage(
    stage: Any,
    actions: list[FixAction],
    *,
    anchor_dir: Path,
    studio_environment: Optional[StudioEnvironmentSettings],
    Usd: Any,
    UsdShade: Any,
    Sdf: Any,
) -> list[AppliedUsdFixRecord]:
    records: list[AppliedUsdFixRecord] = []
    for action in actions:
        if action.blocked:
            records.append(
                AppliedUsdFixRecord(
                    fix_id=action.fix_id,
                    fix_type=action.fix_type,
                    target_id=action.target_id,
                    target_attr=action.target_attr,
                    before_value=action.before_value,
                    after_value=action.after_value,
                    succeeded=False,
                    message="blocked",
                )
            )
            continue
        if action.fix_type not in SUPPORTED_FIX_TYPES:
            records.append(
                AppliedUsdFixRecord(
                    fix_id=action.fix_id,
                    fix_type=action.fix_type,
                    target_id=action.target_id,
                    target_attr=action.target_attr,
                    before_value=action.before_value,
                    after_value=action.after_value,
                    succeeded=False,
                    message=UNSUPPORTED_FIX_REASON,
                )
            )
            continue
        if action.fix_type == SET_DEFAULT_PRIM_FIX_TYPE:
            records.append(_apply_set_default_prim(stage, action, Usd=Usd))
            continue
        if action.fix_type == SET_ATTR_FIX_TYPE:
            records.append(_apply_set_attr(stage, action, UsdShade=UsdShade))
            continue
        if action.fix_type == RENAME_NODE_FIX_TYPE:
            record = _apply_rename_node(stage, action)
            records.append(record)
            _debug_usd_fix_log(record, hypothesis_id="H10")
            continue
        if action.fix_type == RENAME_TEXTURE_FILE_FIX_TYPE:
            record = _apply_rename_texture_file(
                stage,
                action,
                anchor_dir=anchor_dir,
                studio_environment=studio_environment,
                UsdShade=UsdShade,
                Sdf=Sdf,
            )
            records.append(record)
            _debug_usd_fix_log(record, hypothesis_id="H10")
            continue
        if action.fix_type in {"relink_path", "normalize_path"}:
            records.append(
                _apply_shader_asset_path(
                    stage,
                    action,
                    anchor_dir=anchor_dir,
                    studio_environment=studio_environment,
                    UsdShade=UsdShade,
                    Sdf=Sdf,
                )
            )
    return records


def _apply_set_default_prim(stage: Any, action: FixAction, *, Usd: Any) -> AppliedUsdFixRecord:
    prim_path = str(action.after_value or action.params.get("prim_path") or "")
    prim = stage.GetPrimAtPath(prim_path)
    if not prim or not prim.IsValid():
        return AppliedUsdFixRecord(
            fix_id=action.fix_id,
            fix_type=action.fix_type,
            target_id=action.target_id,
            target_attr=action.target_attr,
            before_value=action.before_value,
            after_value=action.after_value,
            succeeded=False,
            message=INVALID_TARGET_REASON,
        )
    stage.SetDefaultPrim(prim)
    return AppliedUsdFixRecord(
        fix_id=action.fix_id,
        fix_type=action.fix_type,
        target_id=action.target_id,
        target_attr=action.target_attr,
        before_value=action.before_value,
        after_value=prim_path,
        succeeded=True,
    )


def _apply_set_attr(stage: Any, action: FixAction, *, UsdShade: Any) -> AppliedUsdFixRecord:
    prim_path = _resolve_usd_prim_path(stage, action)
    prim = stage.GetPrimAtPath(prim_path)
    if not prim or not prim.IsA(UsdShade.Shader):
        return AppliedUsdFixRecord(
            fix_id=action.fix_id,
            fix_type=action.fix_type,
            target_id=action.target_id,
            target_attr=action.target_attr,
            before_value=action.before_value,
            after_value=action.after_value,
            succeeded=False,
            message=INVALID_TARGET_REASON,
        )
    shader = UsdShade.Shader(prim)
    attribute = str(action.target_attr or action.params.get("attribute") or "")
    after_value = action.after_value
    if attribute == "colorSpace":
        if _set_shader_colorspace(shader, str(after_value)):
            return AppliedUsdFixRecord(
                fix_id=action.fix_id,
                fix_type=action.fix_type,
                target_id=action.target_id,
                target_attr=attribute,
                before_value=action.before_value,
                after_value=after_value,
                succeeded=True,
            )
    return AppliedUsdFixRecord(
        fix_id=action.fix_id,
        fix_type=action.fix_type,
        target_id=action.target_id,
        target_attr=action.target_attr,
        before_value=action.before_value,
        after_value=action.after_value,
        succeeded=False,
        message=UNSUPPORTED_FIX_REASON,
    )


def _set_shader_colorspace(shader: Any, value: str) -> bool:
    file_input = shader.GetInput("file")
    if file_input:
        attr = file_input.GetAttr()
        if attr is not None and hasattr(attr, "SetColorSpace"):
            attr.SetColorSpace(value)
            return True
    for input_name, normalized in (
        ("sourceColorSpace", value.casefold()),
        ("rgb_color_space", value.casefold()),
    ):
        input_attr = shader.GetInput(input_name)
        if input_attr:
            input_attr.Set(normalized)
            return True
    color_space = shader.GetInput("color_space")
    if color_space and value == "Raw":
        color_space.Set(0)
        return True
    if color_space and value == "sRGB":
        color_space.Set(1)
        return True
    return False


def _apply_shader_asset_path(
    stage: Any,
    action: FixAction,
    *,
    anchor_dir: Path,
    studio_environment: Optional[StudioEnvironmentSettings],
    UsdShade: Any,
    Sdf: Any,
) -> AppliedUsdFixRecord:
    prim_path = _resolve_usd_prim_path(stage, action)
    prim = stage.GetPrimAtPath(prim_path)
    if not prim or not prim.IsA(UsdShade.Shader):
        return _failed_record(action, message=INVALID_TARGET_REASON)
    shader = UsdShade.Shader(prim)
    input_name = _resolve_shader_input_name(shader, str(action.target_attr or "file"))
    input_attr = shader.GetInput(input_name)
    if not input_attr:
        return AppliedUsdFixRecord(
            fix_id=action.fix_id,
            fix_type=action.fix_type,
            target_id=action.target_id,
            target_attr=action.target_attr,
            before_value=action.before_value,
            after_value=action.after_value,
            succeeded=False,
            message=INVALID_TARGET_REASON,
        )
    before_path = str(action.before_value or "")
    after_path = str(action.after_value or "")
    if action.fix_type == "normalize_path" and studio_environment is not None:
        normalized = resolve_normalize_path_value(
            before_path,
            action.params,
            studio_environment=studio_environment,
        )
        if normalized is not None:
            after_path = normalized
    input_attr.Set(Sdf.AssetPath(after_path))
    return AppliedUsdFixRecord(
        fix_id=action.fix_id,
        fix_type=action.fix_type,
        target_id=action.target_id,
        target_attr=action.target_attr,
        before_value=before_path,
        after_value=after_path,
        succeeded=True,
    )


def _apply_rename_node(stage: Any, action: FixAction) -> AppliedUsdFixRecord:
    old_path = _resolve_usd_prim_path(stage, action)
    new_name = _rename_target_name(action.after_value)
    if not old_path or not new_name:
        return _failed_record(action, message=INVALID_TARGET_REASON)

    moved, new_path, error = _move_prim_path(stage, old_path, new_name)
    if not moved:
        return _failed_record(action, message=error or RENAME_FAILED_REASON)

    return AppliedUsdFixRecord(
        fix_id=action.fix_id,
        fix_type=action.fix_type,
        target_id=action.target_id,
        target_attr=action.target_attr,
        before_value=action.before_value,
        after_value=new_path,
        succeeded=True,
    )


def _apply_rename_texture_file(
    stage: Any,
    action: FixAction,
    *,
    anchor_dir: Path,
    studio_environment: Optional[StudioEnvironmentSettings],
    UsdShade: Any,
    Sdf: Any,
) -> AppliedUsdFixRecord:
    from pipeline_inspector.maya.fix_applier import (
        INVALID_TEXTURE_FILE_RENAME_REASON,
        _is_path_string_value,
        _rename_texture_files_on_disk,
    )

    raw_before = action.before_value
    raw_after = action.after_value
    if not _is_path_string_value(raw_before) or not _is_path_string_value(raw_after):
        return _failed_record(action, message=INVALID_TEXTURE_FILE_RENAME_REASON)

    resolved_before = str(action.params.get("resolved_before") or raw_before)
    is_udim = bool(action.params.get("is_udim"))
    rename_error = _rename_texture_files_on_disk(
        resolved_before,
        str(raw_before),
        str(raw_after),
        is_udim=is_udim,
    )
    if rename_error:
        return _failed_record(action, message=str(rename_error))

    path_record = _apply_shader_asset_path(
        stage,
        replace(action, after_value=str(raw_after).strip()),
        anchor_dir=anchor_dir,
        studio_environment=studio_environment,
        UsdShade=UsdShade,
        Sdf=Sdf,
    )
    if not path_record.succeeded:
        return path_record

    node_after = action.params.get("node_name_after")
    if isinstance(node_after, str) and node_after.strip():
        prim_path = path_record.after_value if isinstance(path_record.after_value, str) else ""
        resolved_path = _resolve_usd_prim_path(stage, action)
        rename_record = _apply_rename_node(
            stage,
            replace(
                action,
                fix_type=RENAME_NODE_FIX_TYPE,
                target_id=f"prim:{resolved_path}",
                target_node=resolved_path,
                before_value=_prim_short_name(resolved_path),
                after_value=node_after.strip(),
                params={
                    **action.params,
                    "resolved_prim_path": resolved_path,
                },
            ),
        )
        if not rename_record.succeeded:
            return rename_record
        return AppliedUsdFixRecord(
            fix_id=action.fix_id,
            fix_type=action.fix_type,
            target_id=action.target_id,
            target_attr=action.target_attr,
            before_value=action.before_value,
            after_value=rename_record.after_value,
            succeeded=True,
            message="Texture file and USD prim renamed.",
        )

    return path_record


def _move_prim_path(
    stage: Any,
    old_path: str,
    new_name: str,
) -> tuple[bool, str, str]:
    from pxr import Sdf

    old = Sdf.Path(old_path)
    if old.name == new_name:
        return True, old_path, ""

    new_path = str(old.GetParentPath().AppendChild(new_name))
    old_prim = stage.GetPrimAtPath(old_path)
    if not old_prim or not old_prim.IsValid():
        return False, "", INVALID_TARGET_REASON

    new_prim = stage.GetPrimAtPath(new_path)
    if new_prim and new_prim.IsValid():
        return False, "", RENAME_FAILED_REASON

    layer = stage.GetEditTarget().GetLayer()
    if layer is None:
        layer = stage.GetRootLayer()
    spec = layer.GetPrimAtPath(old)
    if spec is None and layer is not stage.GetRootLayer():
        layer = stage.GetRootLayer()
        spec = layer.GetPrimAtPath(old)
    if spec is None:
        return False, "", INVALID_TARGET_REASON

    try:
        spec.name = new_name
        return True, new_path, ""
    except Exception:  # noqa: BLE001
        return False, "", RENAME_FAILED_REASON


def _resolve_shader_input_name(shader: Any, target_attr: str) -> str:
    normalized = str(target_attr or "").strip()
    candidates = [normalized] if normalized else []
    if normalized == "fileTextureName":
        candidates.extend(["file", "asset:file", "inputs:file"])
    elif normalized == "file":
        candidates.extend(["fileTextureName"])
    for candidate in candidates:
        if candidate and shader.GetInput(candidate):
            return candidate
    return normalized or "file"


def _prim_short_name(prim_path: str) -> str:
    token = str(prim_path or "").strip().strip("/")
    if not token:
        return ""
    return token.rsplit("/", 1)[-1]


def _failed_record(action: FixAction, *, message: str) -> AppliedUsdFixRecord:
    return AppliedUsdFixRecord(
        fix_id=action.fix_id,
        fix_type=action.fix_type,
        target_id=action.target_id,
        target_attr=action.target_attr,
        before_value=action.before_value,
        after_value=action.after_value,
        succeeded=False,
        message=message,
    )


def _debug_usd_fix_log(record: AppliedUsdFixRecord, *, hypothesis_id: str) -> None:
    if record.fix_type not in {RENAME_NODE_FIX_TYPE, RENAME_TEXTURE_FILE_FIX_TYPE}:
        return
    try:
        log_path = Path(__file__).resolve().parents[2] / "debug-618f4f.log"
        payload = {
            "sessionId": "618f4f",
            "timestamp": int(time.time() * 1000),
            "location": "usd.fix_applier.apply_usd_fix_actions",
            "message": "USD rename fix applied",
            "data": {
                "fix_type": record.fix_type,
                "target_id": record.target_id,
                "succeeded": str(record.succeeded),
                "message": record.message,
                "after_value": str(record.after_value or ""),
                "runId": "post-fix",
            },
            "hypothesisId": hypothesis_id,
        }
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
    except OSError:
        return


def _prim_path_from_target(target_id: str) -> str:
    if target_id.startswith("prim:"):
        return target_id.removeprefix("prim:")
    return target_id


def _normalize_usd_prim_path(raw_path: str) -> str:
    token = str(raw_path or "").strip()
    if not token:
        return ""
    if token.startswith("prim:"):
        token = token.removeprefix("prim:")
    token = token.replace("\\", "/").strip()
    if not token.startswith("/"):
        token = f"/{token.lstrip('/')}"
    return token


def _rename_target_name(value: Any) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    if "/" in token:
        return _prim_short_name(token)
    return token


def _texture_prim_path_score(prim_path: str) -> int:
    normalized = str(prim_path or "").casefold()
    if "bitmap" in normalized:
        return 100
    if "/vray/" in normalized:
        return 80
    if "usdpreviewsurface" in normalized or "usduvtexture" in normalized:
        return 60
    return 10


def _resolve_usd_prim_path(stage: Any, action: FixAction) -> str:
    candidates: list[str] = []
    seen: set[str] = set()

    def _add(raw: Any) -> None:
        normalized = _normalize_usd_prim_path(str(raw or ""))
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        candidates.append(normalized)

    resolved = action.params.get("resolved_prim_path")
    if isinstance(resolved, str):
        _add(resolved)
    _add(action.target_node)
    _add(_prim_path_from_target(action.target_id))

    for candidate in candidates:
        prim = stage.GetPrimAtPath(candidate)
        if prim and prim.IsValid():
            _debug_resolve_log(action, candidate, source="direct")
            return candidate

    search_name = _prim_short_name(_prim_path_from_target(action.target_id))
    if not search_name:
        return candidates[0] if candidates else ""

    matches = [
        str(prim.GetPath())
        for prim in stage.Traverse()
        if str(prim.GetName()) == search_name
    ]
    if len(matches) == 1:
        _debug_resolve_log(action, matches[0], source="unique_name")
        return matches[0]
    if len(matches) > 1:
        best_match = max(matches, key=_texture_prim_path_score)
        _debug_resolve_log(action, best_match, source="scored_name", match_count=len(matches))
        return best_match

    _debug_resolve_log(action, candidates[0] if candidates else "", source="fallback")
    return candidates[0] if candidates else ""


def _debug_resolve_log(
    action: FixAction,
    resolved_path: str,
    *,
    source: str,
    match_count: int = 0,
) -> None:
    if action.fix_type not in {RENAME_NODE_FIX_TYPE, RENAME_TEXTURE_FILE_FIX_TYPE}:
        return
    try:
        log_path = Path(__file__).resolve().parents[2] / "debug-618f4f.log"
        payload = {
            "sessionId": "618f4f",
            "timestamp": int(time.time() * 1000),
            "location": "usd.fix_applier._resolve_usd_prim_path",
            "message": "Resolved USD prim path for fix",
            "data": {
                "fix_type": action.fix_type,
                "target_id": action.target_id,
                "target_node": str(action.target_node or ""),
                "resolved_path": resolved_path,
                "source": source,
                "match_count": str(match_count),
            },
            "hypothesisId": "H11",
        }
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
    except OSError:
        return


def _import_usd_modules() -> tuple[Any, Any, Any]:
    try:
        from pxr import Sdf, Usd, UsdShade
    except ImportError as exc:
        raise RuntimeError(
            "USD fix application requires OpenUSD Python bindings (pip install usd-core)."
        ) from exc
    return Usd, UsdShade, Sdf
