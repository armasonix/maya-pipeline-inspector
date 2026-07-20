"""Scan OpenUSD assets into the shared GraphSnapshot contract."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline_inspector.core.models import (
    FileDependencySnapshot,
    GraphSnapshot,
    MaterialSnapshot,
    NodeSnapshot,
    ShapeSnapshot,
    UsdStageMetadata,
)

_USD_EXTENSIONS = {".usd", ".usda", ".usdc"}


def scan_usd_stage(
    usd_path: Path | str,
    *,
    scan_scope: str = "asset",
) -> GraphSnapshot:
    """Open a USD stage and convert it into a GraphSnapshot."""

    path = Path(usd_path).resolve()
    Usd, UsdGeom, UsdShade, Sdf = _import_usd_modules()
    stage = Usd.Stage.Open(str(path))
    if stage is None:
        raise RuntimeError(f"Unable to open USD stage: {path}")

    nodes: list[NodeSnapshot] = []
    materials: list[MaterialSnapshot] = []
    shapes: list[ShapeSnapshot] = []
    file_dependencies: list[FileDependencySnapshot] = []
    unbound_mesh_paths: list[str] = []
    suggested_default_prim = ""

    for prim in stage.Traverse():
        prim_path = str(prim.GetPath())
        type_name = prim.GetTypeName()
        node_id = _prim_node_id(prim_path)
        attrs: dict[str, Any] = {"prim_path": prim_path}
        if prim.IsA(UsdShade.Shader):
            shader = UsdShade.Shader(prim)
            attrs.update(_shader_node_attrs(shader=shader, prim_name=prim.GetName(), Sdf=Sdf))
        nodes.append(
            NodeSnapshot(
                id=node_id,
                name=prim.GetName(),
                full_name=prim_path,
                type_name=type_name or "Xform",
                renderer_family="usd",
                attrs=attrs,
            )
        )

        if prim.IsA(UsdGeom.Mesh):
            mesh = UsdGeom.Mesh(prim)
            shapes.append(
                ShapeSnapshot(
                    node_id=node_id,
                    name=prim.GetName(),
                    full_name=prim_path,
                    type_name="Mesh",
                    polygon_count=_mesh_face_count(mesh),
                )
            )
            binding = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()[0]
            if not binding:
                unbound_mesh_paths.append(prim_path)

        if prim.IsA(UsdShade.Material):
            materials.append(
                MaterialSnapshot(
                    node_id=node_id,
                    name=prim.GetName(),
                    full_name=prim_path,
                    type_name="Material",
                    renderer_family="usd",
                    texture_nodes=[],
                    displacement_nodes=[],
                )
            )

        if prim.IsA(UsdShade.Shader):
            file_dependencies.extend(
                _shader_file_dependencies(
                    shader=UsdShade.Shader(prim),
                    node_id=node_id,
                    stage_path=path,
                    Sdf=Sdf,
                )
            )

    file_dependencies = _dedupe_texture_file_dependencies(file_dependencies)

    default_prim_path = ""
    has_default_prim = stage.HasDefaultPrim()
    if has_default_prim:
        default_prim_path = str(stage.GetDefaultPrim().GetPath())
    for child in stage.GetPseudoRoot().GetChildren():
        suggested_default_prim = str(child.GetPath())
        break

    opening_errors = _read_opening_errors(stage)
    missing_reference_paths = _missing_reference_paths(stage, path.parent, Sdf=Sdf)

    metadata = UsdStageMetadata(
        root_layer=str(stage.GetRootLayer().realPath or path),
        default_prim=default_prim_path,
        has_default_prim=has_default_prim,
        suggested_default_prim=suggested_default_prim,
        prim_count=len(nodes),
        mesh_count=len(shapes),
        material_count=len(materials),
        unbound_mesh_count=len(unbound_mesh_paths),
        unbound_mesh_paths=unbound_mesh_paths,
        missing_reference_count=len(missing_reference_paths),
        missing_reference_paths=missing_reference_paths,
        payload_count=len(stage.GetUsedLayers()),
        opening_error_count=len(opening_errors),
        opening_errors=opening_errors,
    )

    return GraphSnapshot(
        scene_path=str(path),
        maya_version="",
        renderer="usd",
        scan_scope=scan_scope,
        scanned_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        nodes=nodes,
        materials=materials,
        shapes=shapes,
        file_dependencies=file_dependencies,
        usd_stage_metadata=metadata,
    )


def is_usd_path(path: Path | str) -> bool:
    return Path(path).suffix.casefold() in _USD_EXTENSIONS


def _import_usd_modules() -> tuple[Any, Any, Any, Any]:
    try:
        from pxr import Sdf, Usd, UsdGeom, UsdShade
    except ImportError as exc:
        raise RuntimeError(
            "USD scanning requires OpenUSD Python bindings (pip install usd-core)."
        ) from exc
    return Usd, UsdGeom, UsdShade, Sdf


def _prim_node_id(prim_path: str) -> str:
    return f"prim:{prim_path}"


def _mesh_face_count(mesh: Any) -> int:
    counts = mesh.GetFaceVertexCountsAttr().Get() or []
    return int(len(counts))


def _shader_node_attrs(*, shader: Any, prim_name: str, Sdf: Any) -> dict[str, Any]:
    info_id = _shader_info_id(shader)
    semantic_slot = _infer_semantic_slot(prim_name, info_id)
    color_space = _read_shader_colorspace(shader, Sdf=Sdf)
    file_path = _read_shader_file_path(shader, Sdf=Sdf)
    attrs: dict[str, Any] = {}
    if info_id:
        attrs["info_id"] = info_id
    if semantic_slot:
        attrs["semantic_slot"] = semantic_slot
    if color_space:
        attrs["colorSpace"] = color_space
    if file_path:
        attrs["file"] = file_path
    return attrs


def _read_shader_file_path(shader: Any, *, Sdf: Any) -> str:
    for input_name in _texture_path_input_names(shader):
        file_input = shader.GetInput(input_name)
        if not file_input:
            continue
        value = file_input.Get()
        if value is None:
            continue
        if isinstance(value, Sdf.AssetPath):
            path = str(value.path or "")
        else:
            path = str(value).strip()
        if path:
            return path
    return ""


def _infer_semantic_slot(prim_name: str, info_id: str) -> str:
    lowered = prim_name.casefold()
    for hint, semantic in _SEMANTIC_HINTS:
        if hint in lowered:
            return semantic
    info_lower = info_id.casefold()
    if "roughness" in info_lower:
        return "roughness"
    if "normal" in info_lower:
        return "normal"
    if "bitmap" in info_lower or "uvtexture" in info_lower:
        return "base_color"
    return ""


def _read_shader_colorspace(shader: Any, *, Sdf: Any) -> str:
    for key in ("sourceColorSpace", "rgb_color_space"):
        value = _shader_input_scalar(shader, key)
        if value:
            return _normalize_colorspace(str(value))
    file_input = shader.GetInput("file")
    if file_input:
        attr = file_input.GetAttr()
        if attr is not None and hasattr(attr, "GetColorSpace"):
            colorspace = attr.GetColorSpace()
            if colorspace:
                return _normalize_colorspace(str(colorspace))
    color_space = _shader_input_scalar(shader, "color_space")
    if color_space is not None:
        return _normalize_vray_colorspace_enum(int(color_space))
    return ""


def _shader_input_scalar(shader: Any, name: str) -> Any:
    input_attr = shader.GetInput(name)
    if not input_attr:
        return None
    return input_attr.Get()


def _shader_info_id(shader: Any) -> str:
    prim = shader.GetPrim() if hasattr(shader, "GetPrim") else None
    if prim is not None:
        attr = prim.GetAttribute("info:id")
        if attr and attr.IsValid():
            value = attr.Get()
            if value is not None:
                return str(value)
    info_input = shader.GetInput("info:id")
    if info_input:
        value = info_input.Get()
        if value is not None:
            return str(value)
    return ""


def _is_arnold_image_shader(shader: Any) -> bool:
    return _shader_info_id(shader).casefold() == "arnold:image"


def _texture_path_input_names(shader: Any) -> tuple[str, ...]:
    if _is_arnold_image_shader(shader):
        return ("filename", "file")
    return ("file", "filename")


def _normalize_colorspace(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        return ""
    if normalized.casefold() == "raw":
        return "Raw"
    if normalized.casefold() in {"srgb", "s_rgb"}:
        return "sRGB"
    if normalized.casefold() == "acescg":
        return "ACEScg"
    return normalized


def _normalize_vray_colorspace_enum(value: int) -> str:
    if value == 0:
        return "Raw"
    if value == 1:
        return "sRGB"
    return str(value)


_SEMANTIC_HINTS = (
    ("albedo", "base_color"),
    ("diffuse", "base_color"),
    ("basecolor", "base_color"),
    ("roughness", "roughness"),
    ("normal", "normal"),
    ("bump", "bump"),
    ("opacity", "opacity"),
    ("displacement", "displacement"),
    ("metalness", "metalness"),
    ("metallic", "metalness"),
)


def _shader_file_dependencies(
    *,
    shader: Any,
    node_id: str,
    stage_path: Path,
    Sdf: Any,
) -> list[FileDependencySnapshot]:
    dependencies: list[FileDependencySnapshot] = []
    input_names = _texture_path_input_names(shader)
    if _is_arnold_image_shader(shader):
        filename_input = shader.GetInput("filename")
        if filename_input is not None:
            filename_value = filename_input.Get()
            if (
                filename_value is not None
                and isinstance(filename_value, Sdf.AssetPath)
                and str(filename_value.path or "").strip()
            ):
                input_names = ("filename",)
    for input_name in input_names:
        input_attr = shader.GetInput(input_name)
        if input_attr is None:
            continue
        value = input_attr.Get()
        if value is None or not isinstance(value, Sdf.AssetPath):
            continue
        raw_path = str(value.path or "")
        if not raw_path:
            continue
        resolved = _resolve_asset_path(raw_path, stage_path.parent)
        dependencies.append(
            FileDependencySnapshot(
                node_id=node_id,
                attr=str(input_attr.GetBaseName()),
                raw_path=raw_path,
                resolved_path=str(resolved) if resolved is not None else raw_path,
                exists=bool(resolved and resolved.exists()),
                extension=resolved.suffix.lower() if resolved is not None else None,
            )
        )
    return dependencies


def _dedupe_texture_file_dependencies(
    dependencies: list[FileDependencySnapshot],
) -> list[FileDependencySnapshot]:
    grouped: dict[tuple[str, str], FileDependencySnapshot] = {}
    for dependency in dependencies:
        prim_path = dependency.node_id.removeprefix("prim:")
        material_key = _material_key_from_prim_path(prim_path)
        path_key = _normalize_texture_path_key(dependency.raw_path)
        key = (material_key, path_key)
        current = grouped.get(key)
        if current is None or _prefer_texture_dependency(dependency, current):
            grouped[key] = dependency
    return list(grouped.values())


def _material_key_from_prim_path(prim_path: str) -> str:
    parts = str(prim_path or "").strip("/").split("/")
    for index, part in enumerate(parts):
        if part == "mtl" and index + 1 < len(parts):
            return parts[index + 1]
    return prim_path


def _normalize_texture_path_key(raw_path: str) -> str:
    return str(raw_path or "").strip().replace("\\", "/").casefold()


def _prefer_texture_dependency(
    candidate: FileDependencySnapshot,
    incumbent: FileDependencySnapshot,
) -> bool:
    candidate_score = _texture_dependency_score(candidate.node_id)
    incumbent_score = _texture_dependency_score(incumbent.node_id)
    if candidate_score != incumbent_score:
        return candidate_score > incumbent_score
    if candidate.attr == "filename" and incumbent.attr == "file":
        return True
    if incumbent.attr == "filename" and candidate.attr == "file":
        return False
    return False


def _texture_dependency_score(node_id: str) -> int:
    prim_path = str(node_id).removeprefix("prim:").casefold()
    if "bitmap" in prim_path:
        return 100
    if "/vray/" in prim_path:
        return 80
    if "usdpreviewsurface" in prim_path or "usduvtexture" in prim_path:
        return 20
    return 50


def _resolve_asset_path(raw_path: str, anchor_dir: Path) -> Path | None:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return (anchor_dir / candidate).resolve()


def _read_opening_errors(stage: Any) -> list[str]:
    get_opening_errors = getattr(stage, "GetOpeningErrors", None)
    if get_opening_errors is None:
        return []
    try:
        return [str(item) for item in get_opening_errors()]
    except Exception:  # noqa: BLE001 - older Maya USD builds expose partial APIs
        return []


def _missing_reference_paths(stage: Any, anchor_dir: Path, *, Sdf: Any) -> list[str]:
    missing: list[str] = []
    for layer in stage.GetUsedLayers():
        identifier = str(layer.identifier or "")
        if not identifier or identifier.startswith("anon:"):
            continue
        resolved = _resolve_asset_path(identifier, anchor_dir)
        if resolved is None or not resolved.exists():
            missing.append(identifier)
    return missing
