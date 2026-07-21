"""Navigate to USD prims inside a Maya scene via UFE."""
from __future__ import annotations

import importlib
from typing import Any, Optional

from pipeline_inspector.core.models import GraphSnapshot
from pipeline_inspector.maya.navigation import (
    NavigationActionResult,
    _hypershade_panel_name,
    _result,
)
from pipeline_inspector.usd.enrichment import usd_material_name_from_prim_path


def is_usd_prim_target(*, target_id: str = "", node_name: str = "") -> bool:
    """Return whether the navigation target refers to a USD stage prim."""

    if str(target_id).startswith("prim:") or str(node_name).startswith("prim:"):
        return True
    if _looks_like_usd_prim_path(str(node_name)) or _looks_like_usd_prim_path(
        str(target_id).removeprefix("prim:")
    ):
        return True
    return _looks_like_maya_usd_reference_target(target_id=target_id, node_name=node_name)


def _looks_like_maya_usd_reference_target(*, target_id: str = "", node_name: str = "") -> bool:
    token = str(target_id or node_name or "").strip()
    if not token.startswith("node:"):
        return False
    body = token.removeprefix("node:")
    return ":" in body and not body.startswith("/")


def resolve_usd_prim_path(
    *,
    target_id: str = "",
    node_name: str = "",
    material_name: str = "",
    snapshot: Optional[GraphSnapshot] = None,
    cmds: Optional[Any] = None,
) -> str:
    """Resolve a USD prim path from issue navigation fields."""

    for candidate in (target_id, node_name, material_name):
        prim_path = _prim_path_from_token(candidate)
        if prim_path:
            return prim_path

    if snapshot is not None:
        if material_name:
            for material in snapshot.materials:
                if material.name == material_name or material.full_name == material_name:
                    resolved = _prim_path_from_token(material.node_id) or str(
                        material.full_name or ""
                    )
                    if resolved:
                        return resolved

        if node_name:
            for node in snapshot.nodes:
                if not str(node.id).startswith("prim:"):
                    continue
                prim_path = _prim_path_from_token(node.id)
                if node.name == node_name or node.full_name == node_name or prim_path == node_name:
                    return prim_path or str(node.full_name or "")

    if cmds is not None:
        discovered = find_usd_prim_for_issue(
            target_id=target_id,
            node_name=node_name,
            material_name=material_name,
            cmds=cmds,
        )
        if discovered:
            return discovered

    return ""


def find_usd_prim_for_issue(
    *,
    target_id: str = "",
    node_name: str = "",
    material_name: str = "",
    cmds: Optional[Any] = None,
) -> str:
    """Locate a USD prim path on proxy stages using Maya-style node identifiers."""

    maya_cmds = cmds or _maya_cmds()
    proxy_shapes = maya_cmds.ls(type="mayaUsdProxyShape", long=True) or []
    if not proxy_shapes:
        return ""

    search_tokens = _usd_search_tokens(target_id, node_name, material_name)
    if not search_tokens:
        return ""

    for shape in proxy_shapes:
        stage = _get_proxy_stage(shape, maya_cmds)
        if stage is None:
            continue
        match = _match_prim_on_stage(stage, search_tokens)
        if match:
            return match

    return ""


def _usd_search_tokens(target_id: str, node_name: str, material_name: str) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()

    def _add(value: str) -> None:
        normalized = str(value or "").strip()
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        tokens.append(normalized)

    for raw in (material_name, node_name, target_id):
        if not raw:
            continue
        if str(raw).startswith("node:"):
            raw = str(raw).removeprefix("node:")
        if ":" in str(raw):
            _add(str(raw).rsplit(":", 1)[-1])
        _add(str(raw))
        for part in str(raw).split("_"):
            if part:
                _add(part)
        parts = str(raw).split("_")
        for index in range(len(parts)):
            suffix = "_".join(parts[index:])
            if suffix:
                _add(suffix)

    return tokens


def _match_prim_on_stage(stage: Any, search_tokens: list[str]) -> str:
    best_match = ""
    best_score = 0
    for prim in stage.Traverse():
        prim_path = str(prim.GetPath())
        prim_name = str(prim.GetName())
        for token in search_tokens:
            score = 0
            if prim_name == token:
                score = 100
            elif prim_name.endswith(token) or token.endswith(prim_name):
                score = 80
            elif token in prim_path:
                score = 60
            elif token in prim_name:
                score = 40
            if score > best_score:
                best_score = score
                best_match = prim_path
    return best_match if best_score >= 40 else ""


def select_usd_prim(
    prim_path: str,
    *,
    cmds: Optional[Any] = None,
) -> NavigationActionResult:
    """Select a USD prim through the Maya USD proxy UFE path."""

    target = str(prim_path or "").strip()
    if not target:
        return _result("select_node", "", False, "USD prim path is empty.")

    maya_cmds = cmds or _maya_cmds()
    proxy_shapes = maya_cmds.ls(type="mayaUsdProxyShape", long=True) or []
    if not proxy_shapes:
        return _result(
            "select_node",
            target,
            False,
            "No mayaUsdProxyShape found in the current scene.",
        )

    normalized = _normalize_prim_path(target)
    shape, ufe_path = _resolve_proxy_ufe_path(normalized, proxy_shapes, maya_cmds)
    if shape is None or not ufe_path:
        return _result(
            "select_node",
            normalized,
            False,
            f"Unable to locate USD prim {normalized} on any proxy stage.",
        )

    if _select_ufe_path(ufe_path, maya_cmds):
        return _result(
            "select_node",
            ufe_path,
            True,
            f"USD prim selected: {normalized}",
        )

    return _result(
        "select_node",
        ufe_path,
        False,
        f"Unable to select USD prim {normalized}.",
    )


def resolve_usd_material_scope_prim(
    prim_path: str,
    *,
    material_name: str = "",
) -> str:
    """Return the USD Material scope prim for a shader/texture prim path."""

    normalized = _normalize_prim_path(prim_path)
    if not normalized:
        return ""

    parts = [part for part in normalized.strip("/").split("/") if part]
    expected_material = str(material_name or "").strip().strip("/").split("/")[-1]
    for index, part in enumerate(parts):
        if part != "mtl" or index + 1 >= len(parts):
            continue
        material_part = parts[index + 1]
        if expected_material and material_part != expected_material:
            continue
        return f"/{'/'.join(parts[: index + 2])}"

    if expected_material:
        for index, part in enumerate(parts):
            if part == "mtl" and index + 1 < len(parts):
                return f"/{'/'.join(parts[: index + 2])}"

    material_from_path = usd_material_name_from_prim_path(normalized)
    if material_from_path:
        for index, part in enumerate(parts):
            if part == "mtl" and index + 1 < len(parts) and parts[index + 1] == material_from_path:
                return f"/{'/'.join(parts[: index + 2])}"

    return normalized


def open_usd_shader_view(
    prim_path: str,
    *,
    material_name: str = "",
    cmds: Optional[Any] = None,
    mel: Optional[Any] = None,
) -> NavigationActionResult:
    """Select a USD shader prim and open Hypershade plus Attribute Editor."""

    maya_cmds = cmds or _maya_cmds()
    requested_prim = _normalize_prim_path(prim_path)
    material_prim = resolve_usd_material_scope_prim(
        prim_path,
        material_name=material_name,
    )

    selection = select_usd_prim(requested_prim, cmds=maya_cmds)
    selected_prim = requested_prim
    if not selection.succeeded and material_prim and material_prim != requested_prim:
        selection = select_usd_prim(material_prim, cmds=maya_cmds)
        selected_prim = material_prim

    if not selection.succeeded:
        return NavigationActionResult(
            action="open_in_hypershade",
            target=prim_path,
            succeeded=False,
            message=selection.message,
        )

    maya_mel = mel or _maya_mel()
    opened_panels = _open_usd_material_panels(maya_cmds, maya_mel)
    _focus_usd_hypershade_graph(maya_cmds, maya_mel)
    panels_label = ", ".join(opened_panels) if opened_panels else "selection"
    return _result(
        "open_in_hypershade",
        selected_prim,
        True,
        (
            f"USD material selected: {selected_prim}. "
            f"Opened {panels_label}. "
            "Use Attribute Editor for USD material properties."
        ),
    )


def _open_usd_material_panels(cmds: Any, mel: Any) -> list[str]:
    opened: list[str] = []
    if _open_hypershade_window(cmds, mel):
        opened.append("Hypershade")
    if _open_attribute_editor_window(cmds, mel):
        opened.append("Attribute Editor")
    return opened


def _focus_usd_hypershade_graph(cmds: Any, mel: Any) -> bool:
    """Refresh Hypershade graph layout for the current UFE USD selection."""

    panel_name = _hypershade_panel_name(cmds) or "hyperShadePanel1"
    graph_command = f'hyperShadePanelGraphCommand("{panel_name}", "showUpAndDownstream")'

    def _apply_io_connections_view() -> None:
        mel.eval(graph_command)

    eval_deferred = getattr(cmds, "evalDeferred", None)
    if eval_deferred is not None:
        eval_deferred(_apply_io_connections_view)
    else:
        _apply_io_connections_view()
    return True


def _open_attribute_editor_window(cmds: Any, mel: Any) -> bool:
    try:
        mel.eval("openAEWindow")
        return True
    except Exception:  # noqa: BLE001
        pass
    attribute_editor = getattr(cmds, "AttributeEditor", None)
    if attribute_editor is not None:
        try:
            attribute_editor()
            return True
        except Exception:  # noqa: BLE001
            pass
    return False


def _open_hypershade_window(cmds: Any, mel: Any) -> bool:
    hypershade_window = getattr(cmds, "HypershadeWindow", None)
    if hypershade_window is not None:
        try:
            hypershade_window()
            return True
        except Exception:  # noqa: BLE001
            pass
    try:
        mel.eval("HypershadeWindow")
        return True
    except Exception:  # noqa: BLE001
        return False


def _normalize_prim_path(prim_path: str) -> str:
    normalized = str(prim_path or "").strip()
    if not normalized:
        return ""
    return normalized if normalized.startswith("/") else f"/{normalized}"


def _resolve_proxy_ufe_path(
    prim_path: str,
    proxy_shapes: list[str],
    cmds: Any,
) -> tuple[Optional[str], str]:
    for shape in proxy_shapes:
        if not _proxy_contains_prim(shape, prim_path, cmds):
            continue
        return shape, f"{shape},{prim_path}"
    if proxy_shapes:
        return proxy_shapes[0], f"{proxy_shapes[0]},{prim_path}"
    return None, ""


def _proxy_contains_prim(shape: str, prim_path: str, cmds: Any) -> bool:
    stage = _get_proxy_stage(shape, cmds)
    if stage is None:
        return False
    prim = stage.GetPrimAtPath(prim_path)
    return bool(prim and prim.IsValid())


def _get_proxy_stage(shape: str, cmds: Any) -> Any:
    try:
        maya_usd_ufe = importlib.import_module("mayaUsd.ufe")
        get_stage = getattr(maya_usd_ufe, "getStage", None)
        if get_stage is not None:
            return get_stage(shape)
    except Exception:  # noqa: BLE001
        pass

    try:
        maya_usd_lib = importlib.import_module("mayaUsd.lib")
        get_prim = getattr(maya_usd_lib, "GetPrim", None)
        if get_prim is not None:
            prim = get_prim(shape)
            if prim is not None:
                return prim.GetStage()
    except Exception:  # noqa: BLE001
        pass

    return None


def _select_ufe_path(ufe_path: str, cmds: Any) -> bool:
    try:
        cmds.select(ufe_path, replace=True)
        if _selection_matches(ufe_path, cmds):
            return True
    except Exception:  # noqa: BLE001
        pass

    return bool(_replace_ufe_selection(ufe_path) and _selection_matches(ufe_path, cmds))


def _selection_matches(ufe_path: str, cmds: Any) -> bool:
    selected = cmds.ls(sl=True, ufe=True) or []
    if not selected:
        return False
    prim_suffix = ufe_path.split(",", 1)[-1]
    return any(
        item == ufe_path or item.endswith(prim_suffix) or prim_suffix in item
        for item in selected
    )


def _looks_like_usd_prim_path(value: str) -> bool:
    token = str(value or "").strip()
    return token.startswith("/") and token.count("/") >= 1


def _prim_path_from_token(value: str) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    if token.startswith("prim:"):
        return _normalize_prim_path(token.removeprefix("prim:"))
    if token.startswith("/"):
        return token
    return ""


def _replace_ufe_selection(ufe_path: str) -> bool:
    try:
        ufe = importlib.import_module("ufe")
        path = ufe.Path(ufe.PathString(ufe_path))
        ufe.GlobalSelection.get().replaceWith(ufe.PathSelection([path]))
        return True
    except Exception:  # noqa: BLE001 - UFE import/selection varies by Maya build
        pass

    try:
        maya_usd_ufe = importlib.import_module("mayaUsd.ufe")
        select = getattr(maya_usd_ufe, "select", None)
        if select is not None:
            select(ufe_path)
            return True
    except Exception:  # noqa: BLE001
        pass

    return False


def _maya_cmds() -> Any:
    return importlib.import_module("maya.cmds")


def _maya_mel() -> Any:
    return importlib.import_module("maya.mel")
