"""Renderer adapter protocol and registry.

Renderer adapters keep renderer-specific node and plug knowledge outside the
core validation engine. The core should consume semantic information produced by
adapters instead of hardcoding V-Ray, Arnold, or future renderer behavior.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from shader_health.core import NodeSnapshot

TextureSlotSemantics = dict[str, str]
ComplexityWeights = dict[str, float]


class RendererAdapterError(ValueError):
    """Raised when renderer adapter registration or lookup fails."""


@runtime_checkable
class RendererAdapter(Protocol):
    """Protocol implemented by renderer-specific adapter classes."""

    id: str
    display_name: str

    def is_available(self) -> bool:
        """Return whether this renderer adapter can run in the current environment."""

    def supported_node_types(self) -> set[str]:
        """Return Maya node types understood by this adapter."""

    def classify_node(self, node: NodeSnapshot) -> list[str]:
        """Return semantic classification tags for a snapshot node."""

    def texture_slot_semantics(self) -> TextureSlotSemantics:
        """Map renderer-specific destination plugs to semantic texture slots."""

    def displacement_slots(self) -> list[str]:
        """Return renderer-specific displacement-related destination plugs."""

    def complexity_weights(self) -> ComplexityWeights:
        """Return per-node-type graph complexity weights."""

    def default_rule_packs(self) -> list[str]:
        """Return default rule pack identifiers for this adapter."""


@dataclass(frozen=True)
class BaseRendererAdapter:
    """Small base implementation for simple renderer adapters and tests."""

    id: str
    display_name: str

    def is_available(self) -> bool:
        return True

    def supported_node_types(self) -> set[str]:
        return set()

    def classify_node(self, node: NodeSnapshot) -> list[str]:
        del node
        return []

    def texture_slot_semantics(self) -> TextureSlotSemantics:
        return {}

    def displacement_slots(self) -> list[str]:
        return []

    def complexity_weights(self) -> ComplexityWeights:
        return {}

    def default_rule_packs(self) -> list[str]:
        return []


class RendererAdapterRegistry:
    """Deterministic in-memory registry for renderer adapters."""

    def __init__(self, adapters: Iterable[RendererAdapter] = ()) -> None:
        self._adapters: dict[str, RendererAdapter] = {}
        for adapter in adapters:
            self.register(adapter)

    def register(self, adapter: RendererAdapter, *, replace: bool = False) -> None:
        adapter_id = adapter.id.strip().lower()
        if not adapter_id:
            raise RendererAdapterError("renderer adapter id is required")

        if adapter_id in self._adapters and not replace:
            raise RendererAdapterError(f"renderer adapter already registered: {adapter_id}")

        self._adapters[adapter_id] = adapter

    def get(self, adapter_id: str) -> RendererAdapter:
        normalized_id = adapter_id.strip().lower()
        try:
            return self._adapters[normalized_id]
        except KeyError as exc:
            raise RendererAdapterError(f"unknown renderer adapter: {normalized_id}") from exc

    def ids(self) -> list[str]:
        return sorted(self._adapters)

    def adapters(self) -> list[RendererAdapter]:
        return [self._adapters[adapter_id] for adapter_id in self.ids()]

    def available_adapters(self) -> list[RendererAdapter]:
        return [adapter for adapter in self.adapters() if adapter.is_available()]

    def classify_node(self, node: NodeSnapshot) -> list[str]:
        tags: list[str] = []
        for adapter in self.available_adapters():
            if node.type_name not in adapter.supported_node_types():
                continue
            tags.extend(adapter.classify_node(node))
        return _dedupe(tags)


def _dedupe(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
