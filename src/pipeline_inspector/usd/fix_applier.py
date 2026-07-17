"""Apply safe fixes to OpenUSD assets."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from pipeline_inspector.core.fix_plan import FixAction, resolve_normalize_path_value
from pipeline_inspector.studio_config import StudioEnvironmentSettings

UNSUPPORTED_FIX_REASON = "unsupported_fix_type"
INVALID_TARGET_REASON = "invalid_usd_target"
SET_DEFAULT_PRIM_FIX_TYPE = "set_default_prim"
SET_ATTR_FIX_TYPE = "set_attr"
SUPPORTED_FIX_TYPES = frozenset(
    {
        "relink_path",
        "normalize_path",
        SET_DEFAULT_PRIM_FIX_TYPE,
        SET_ATTR_FIX_TYPE,
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


def apply_usd_fix_actions(
    usd_path: Path | str,
    actions: list[FixAction],
    *,
    studio_environment: Optional[StudioEnvironmentSettings] = None,
) -> list[AppliedUsdFixRecord]:
    """Apply planned fixes to a USD asset on disk."""

    Usd, UsdShade, Sdf = _import_usd_modules()
    path = Path(usd_path).resolve()
    stage = Usd.Stage.Open(str(path))
    if stage is None:
        raise RuntimeError(f"Unable to open USD stage: {path}")

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
        if action.fix_type in {"relink_path", "normalize_path"}:
            records.append(
                _apply_shader_asset_path(
                    stage,
                    action,
                    anchor_dir=path.parent,
                    studio_environment=studio_environment,
                    UsdShade=UsdShade,
                    Sdf=Sdf,
                )
            )
    stage.GetRootLayer().Save()
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
    prim_path = _prim_path_from_target(action.target_id)
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
    prim_path = _prim_path_from_target(action.target_id)
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
    input_name = str(action.target_attr or "file")
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


def _prim_path_from_target(target_id: str) -> str:
    if target_id.startswith("prim:"):
        return target_id.removeprefix("prim:")
    return target_id


def _import_usd_modules() -> tuple[Any, Any, Any]:
    try:
        from pxr import Sdf, Usd, UsdShade
    except ImportError as exc:
        raise RuntimeError(
            "USD fix application requires OpenUSD Python bindings (pip install usd-core)."
        ) from exc
    return Usd, UsdShade, Sdf
