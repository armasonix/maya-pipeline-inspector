"""Core data contracts and validation primitives."""

from shader_health.core.models import (
    SNAPSHOT_SCHEMA_VERSION,
    ConnectionSnapshot,
    FileDependencySnapshot,
    GraphSnapshot,
    ImageInfo,
    MaterialSnapshot,
    NodeSnapshot,
    ReferenceSnapshot,
    ShadingEngineSnapshot,
)
from shader_health.core.rule_schema import (
    RULE_SCHEMA_VERSION,
    RuleCheck,
    RuleDefinition,
    RuleFix,
    RuleMatch,
    RulePolicy,
    RuleSchemaError,
)

__all__ = [
    "RULE_SCHEMA_VERSION",
    "SNAPSHOT_SCHEMA_VERSION",
    "ConnectionSnapshot",
    "FileDependencySnapshot",
    "GraphSnapshot",
    "ImageInfo",
    "MaterialSnapshot",
    "NodeSnapshot",
    "ReferenceSnapshot",
    "RuleCheck",
    "RuleDefinition",
    "RuleFix",
    "RuleMatch",
    "RulePolicy",
    "RuleSchemaError",
    "ShadingEngineSnapshot",
]
