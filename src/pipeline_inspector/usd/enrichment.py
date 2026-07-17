"""USD snapshot enrichment for validation and fix planning."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Optional

from pipeline_inspector.adapters.base import RendererAdapterRegistry, UsdAdapter
from pipeline_inspector.adapters.semantic import SemanticTextureSlotResolver
from pipeline_inspector.core.models import (
    FileDependencySnapshot,
    GraphSnapshot,
    UsdStageMetadata,
)
from pipeline_inspector.studio_config import StudioEnvironmentSettings
from pipeline_inspector.usd.scanner import is_usd_path
from pipeline_inspector.util.paths import resolve_studio_path

_USD_RENDERER_ID = "usd"
_USD_EXTENSIONS = {".usd", ".usda", ".usdc"}


def is_usd_snapshot(snapshot: GraphSnapshot) -> bool:
    if snapshot.renderer == _USD_RENDERER_ID:
        return True
    return is_usd_path(snapshot.scene_path)


def prepare_usd_snapshot_for_validation(
    snapshot: GraphSnapshot,
    *,
    studio_environment: Optional[StudioEnvironmentSettings] = None,
) -> GraphSnapshot:
    """Normalize USD asset snapshots before rule evaluation."""

    enriched = replace(snapshot, renderer=_USD_RENDERER_ID)
    enriched = _resolve_file_dependency_paths(enriched, studio_environment=studio_environment)
    enriched = _ensure_usd_stage_metadata(enriched)
    resolver = SemanticTextureSlotResolver(_usd_adapter_registry())
    return resolver.apply_to_snapshot(enriched)


def _resolve_file_dependency_paths(
    snapshot: GraphSnapshot,
    *,
    studio_environment: Optional[StudioEnvironmentSettings],
) -> GraphSnapshot:
    if not snapshot.file_dependencies:
        return snapshot
    resolved_dependencies: list[FileDependencySnapshot] = []
    anchor = Path(snapshot.scene_path).parent if snapshot.scene_path else Path.cwd()
    for dependency in snapshot.file_dependencies:
        raw_path = dependency.raw_path
        resolved_path = dependency.resolved_path or raw_path
        if studio_environment is not None:
            resolved_path = resolve_studio_path(raw_path, studio_environment) or resolved_path
        candidate = Path(resolved_path)
        if not candidate.is_absolute():
            candidate = (anchor / candidate).resolve()
        resolved_dependencies.append(
            replace(
                dependency,
                resolved_path=str(candidate),
                exists=candidate.exists(),
                extension=candidate.suffix.lower() or dependency.extension,
            )
        )
    return replace(snapshot, file_dependencies=resolved_dependencies)


def _ensure_usd_stage_metadata(snapshot: GraphSnapshot) -> GraphSnapshot:
    if snapshot.usd_stage_metadata is not None:
        return snapshot
    return replace(
        snapshot,
        usd_stage_metadata=UsdStageMetadata(
            root_layer=snapshot.scene_path,
            has_default_prim=False,
        ),
    )


def _usd_adapter_registry() -> RendererAdapterRegistry:
    return RendererAdapterRegistry([UsdAdapter()])
