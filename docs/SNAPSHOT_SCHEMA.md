# GraphSnapshot JSON Schema

This document describes the MVP JSON shape for `GraphSnapshot`, the renderer-agnostic data contract used by Maya Shader Health Inspector.

Status: early development. The schema is intentionally simple and will be versioned as the scanner, rule engine, reports, and manifest systems evolve.

## Purpose

`GraphSnapshot` is the boundary between Maya-dependent scanning and Maya-independent validation.

The Maya scanner converts a scene, selection, or asset into JSON-compatible snapshot data. The core validation engine consumes that snapshot without importing Maya APIs.

This keeps the following systems aligned:

- Maya scanner;
- renderer adapters;
- rule engine;
- reports;
- material manifest;
- headless validation;
- Deadline preflight;
- unit tests and fixtures.

## Top-Level Shape

```json
{
  "schema_version": "1.0",
  "scene_path": "D:/show/assets/char/demo/shading/demo_shading.ma",
  "maya_version": "2025",
  "renderer": "vray",
  "scan_scope": "scene",
  "scanned_at_utc": "2026-06-30T12:00:00Z",
  "nodes": [],
  "connections": [],
  "materials": [],
  "shading_engines": [],
  "file_dependencies": [],
  "references": []
}
```

## Required Top-Level Fields

| Field | Type | Required | Description |
|---|---|---:|---|
| `schema_version` | string | Yes | Snapshot schema version. Current MVP value: `1.0`. |
| `scene_path` | string | Yes | Source Maya scene path. Empty string is allowed for unsaved scenes. |
| `maya_version` | string | Yes | Maya version used during scan. Empty string is allowed for fixture-only snapshots. |
| `renderer` | string or null | Yes | Active renderer family if known: `common`, `vray`, `arnold`, etc. |
| `scan_scope` | string | Yes | Scan scope: `scene`, `selection`, or `asset`. |
| `scanned_at_utc` | string | Yes | UTC timestamp in ISO-like format. |
| `nodes` | array | Yes | Dependency nodes collected from shader/material graphs. |
| `connections` | array | Yes | Directed node attribute connections. |
| `materials` | array | Yes | Material-level summaries. |
| `shading_engines` | array | Yes | Shading engine assignments and shader links. |
| `file_dependencies` | array | Yes | Texture/file dependencies collected from file nodes. |
| `references` | array | Yes | Referenced scene metadata for reference-safe validation. |

All arrays may be empty.

## NodeSnapshot

Represents a Maya dependency node in renderer-agnostic form.

```json
{
  "id": "node:file_roughness",
  "name": "file_roughness",
  "full_name": "char_demo:file_roughness",
  "type_name": "file",
  "renderer_family": "common",
  "namespace": "char_demo",
  "referenced": true,
  "reference_path": "D:/show/assets/char/demo/demo_rig.ma",
  "locked": false,
  "attrs": {
    "colorSpace": "ACEScg",
    "fileTextureName": "roughness.<UDIM>.exr"
  },
  "classification": ["texture", "file"]
}
```

### NodeSnapshot Fields

| Field | Type | Required | Description |
|---|---|---:|---|
| `id` | string | Yes | Stable snapshot-local node ID. |
| `name` | string | Yes | Short node name. |
| `full_name` | string | No | Full Maya name, including namespace if present. |
| `type_name` | string | Yes | Maya node type. |
| `renderer_family` | string or null | No | Renderer family classification if known. |
| `namespace` | string or null | No | Maya namespace if present. |
| `referenced` | boolean | Yes | True if node comes from a referenced file. |
| `reference_path` | string or null | No | Source reference path if node is referenced. |
| `locked` | boolean | Yes | True if node is locked. |
| `attrs` | object | Yes | Captured attribute values relevant to validation. |
| `classification` | array[string] | Yes | Tags such as `material`, `texture`, `file`, `displacement`, `utility`. |

## ConnectionSnapshot

Represents a directed connection between two node attributes.

```json
{
  "src_node": "node:file_roughness",
  "src_attr": "outAlpha",
  "dst_node": "node:demo_mtl",
  "dst_attr": "reflectionGlossiness",
  "semantic": "roughness"
}
```

| Field | Type | Required | Description |
|---|---|---:|---|
| `src_node` | string | Yes | Source node ID. |
| `src_attr` | string | Yes | Source attribute name. |
| `dst_node` | string | Yes | Destination node ID. |
| `dst_attr` | string | Yes | Destination attribute name. |
| `semantic` | string or null | No | Semantic slot if resolved by renderer adapter. |

## MaterialSnapshot

Material-level summary used for scoring, reports, graph budget checks, and manifests.

```json
{
  "node_id": "node:demo_mtl",
  "name": "demo_mtl",
  "type_name": "VRayMtl",
  "renderer_family": "vray",
  "shading_engines": ["node:demo_sg"],
  "assigned_shapes": ["mesh:demo_body"],
  "texture_nodes": ["node:file_roughness"],
  "displacement_nodes": [],
  "graph_node_count": 2,
  "graph_depth": 1,
  "graph_fingerprint": "sha256:demo"
}
```

| Field | Type | Required | Description |
|---|---|---:|---|
| `node_id` | string | Yes | Material node ID. |
| `name` | string | Yes | Material node name. |
| `type_name` | string | Yes | Material node type. |
| `renderer_family` | string or null | No | Renderer family. |
| `shading_engines` | array[string] | Yes | Connected shading engines. |
| `assigned_shapes` | array[string] | Yes | Shapes using this material. |
| `texture_nodes` | array[string] | Yes | Texture node IDs used by this material. |
| `displacement_nodes` | array[string] | Yes | Displacement node IDs used by this material. |
| `graph_node_count` | integer | Yes | Number of nodes in material graph. |
| `graph_depth` | integer | Yes | Approximate upstream graph depth. |
| `graph_fingerprint` | string | Yes | Stable graph fingerprint if computed, otherwise empty string. |

## ShadingEngineSnapshot

Represents assignment and shader links for a Maya shading engine.

```json
{
  "node_id": "node:demo_sg",
  "name": "demo_sg",
  "surface_shader": "node:demo_mtl",
  "displacement_shader": null,
  "volume_shader": null,
  "members": ["mesh:demo_body"]
}
```

## FileDependencySnapshot

Represents a texture or renderer file dependency.

```json
{
  "node_id": "node:file_roughness",
  "attr": "fileTextureName",
  "raw_path": "$ASSET_ROOT/tex/roughness_v001.<UDIM>.exr",
  "resolved_path": "D:/show/assets/char/demo/tex/roughness_v001.<UDIM>.exr",
  "exists": true,
  "is_sequence": false,
  "is_udim": true,
  "udim_tiles": [1001, 1002],
  "missing_udim_tiles": [1003],
  "extension": ".exr",
  "version": "001",
  "latest_version": "003",
  "mtime_utc": "2026-06-30T11:00:00Z",
  "size_bytes": 1024,
  "image_info": {
    "width": 4096,
    "height": 4096,
    "channels": 1,
    "bit_depth": "16f",
    "color_space": null,
    "compression": null
  }
}
```

| Field | Type | Required | Description |
|---|---|---:|---|
| `node_id` | string | Yes | File/texture node ID. |
| `attr` | string | Yes | Attribute holding the path. |
| `raw_path` | string | Yes | Original unresolved path from Maya. |
| `resolved_path` | string or null | No | Resolved absolute path if available. |
| `exists` | boolean | Yes | Whether resolved file or pattern exists. |
| `is_sequence` | boolean | Yes | True if sequence pattern detected. |
| `is_udim` | boolean | Yes | True if UDIM pattern detected. |
| `udim_tiles` | array[integer] | Yes | Existing UDIM tiles if known. |
| `missing_udim_tiles` | array[integer] | Yes | Missing UDIM tiles if expected set is known. |
| `extension` | string or null | No | File extension. |
| `version` | string or null | No | Current parsed version token. |
| `latest_version` | string or null | No | Latest detected version token. |
| `mtime_utc` | string or null | No | Last modification time if known. |
| `size_bytes` | integer or null | No | File size if known. |
| `image_info` | object or null | No | Optional image metadata. |

## ImageInfo

Optional image metadata. This may be unavailable in fast/deadline-critical profiles.

```json
{
  "width": 4096,
  "height": 4096,
  "channels": 3,
  "bit_depth": "16f",
  "color_space": "ACEScg",
  "compression": "zip"
}
```

## ReferenceSnapshot

Referenced scene metadata used for reference-safe validation and fix blocking.

```json
{
  "namespace": "char_demo",
  "path": "D:/show/assets/char/demo/demo_rig.ma",
  "loaded": true,
  "locked": false,
  "node_ids": ["node:file_roughness"]
}
```

## Fixture Example

Snapshot fixtures should live under:

```text
tests/fixtures/snapshots/
```

Recommended fixture naming:

```text
vray_wrong_colorspace.json
common_missing_texture.json
arnold_missing_tx.json
common_udim_missing_tile.json
```

A minimal fixture should include:

```json
{
  "schema_version": "1.0",
  "scene_path": "examples/broken_scene/shader_health_demo_broken.ma",
  "maya_version": "2025",
  "renderer": "vray",
  "scan_scope": "scene",
  "scanned_at_utc": "2026-06-30T12:00:00Z",
  "nodes": [
    {
      "id": "node:file_roughness",
      "name": "file_roughness",
      "full_name": "file_roughness",
      "type_name": "file",
      "renderer_family": "common",
      "namespace": null,
      "referenced": false,
      "reference_path": null,
      "locked": false,
      "attrs": {
        "colorSpace": "ACEScg",
        "fileTextureName": "roughness.<UDIM>.exr"
      },
      "classification": ["texture", "file"]
    }
  ],
  "connections": [],
  "materials": [],
  "shading_engines": [],
  "file_dependencies": [],
  "references": []
}
```

## Required vs Optional Policy

For stable schema contracts, all top-level keys should always be present.

Nested fields should also be present when possible. Optional values should use `null`, empty strings, empty arrays, or empty objects instead of removing keys.

Recommended defaults:

| Missing Data | Preferred Value |
|---|---|
| unknown string | `""` or `null`, depending on field semantics |
| unknown list | `[]` |
| unknown object | `{}` |
| unknown boolean | `false` unless true is safer, e.g. `loaded` defaults to true |
| unknown number | `0` or `null`, depending on field semantics |

## Schema Versioning Policy

Current version:

```text
1.0
```

Versioning rules:

- additive optional fields may keep the same major version;
- removing fields requires a new major version;
- changing field meaning requires a new major version;
- changing enum values should be documented and tested;
- report, manifest, rule, and snapshot schemas should be versioned separately;
- fixtures should pin their `schema_version` explicitly.

Future migrations should provide compatibility loaders where practical.

## Implementation Notes

Current model implementation:

```text
src/shader_health/core/models.py
```

Current round-trip tests:

```text
tests/unit/test_snapshot_models.py
```

The core validator should consume `GraphSnapshot`, not raw Maya nodes.
