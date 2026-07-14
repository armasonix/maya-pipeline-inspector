# GraphSnapshot JSON Schema

This document describes the MVP JSON shape for `GraphSnapshot`, the renderer-agnostic data contract used by Maya Pipeline Inspector.

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
  "references": [],
  "shapes": []
}
```

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
| `shapes` | array | Yes | Geometry summaries for assigned or scanned shape nodes. |
| `vray_scene_metadata` | object or null | No | V-Ray scene enrichment payload when enrichment runs. |
| `arnold_scene_metadata` | object or null | No | Arnold scene enrichment payload when enrichment runs. |

All arrays may be empty.

### V-Ray scene metadata (`vray_scene_metadata`)

Attached during validation enrichment when the snapshot is prepared for rules.

```json
{
  "has_vray_plugin": true,
  "vray_plugin_node_ids": ["node:vraySettings"],
  "vray_material_count": 3,
  "has_vray_materials": true
}
```

| Field | Type | Description |
|---|---|---|
| `has_vray_plugin` | boolean | Scene contains a V-Ray settings/plugin node such as `VRaySettingsNode`. |
| `vray_plugin_node_ids` | array[string] | Node IDs for detected V-Ray plugin/settings nodes. |
| `vray_material_count` | integer | Count of V-Ray material nodes in the snapshot. |
| `has_vray_materials` | boolean | True when one or more V-Ray materials are present. |

### Arnold scene metadata (`arnold_scene_metadata`)

Attached during validation enrichment when the snapshot is prepared for rules.

```json
{
  "has_arnold_plugin": true,
  "arnold_plugin_node_ids": ["node:defaultArnoldRenderOptions"],
  "arnold_material_count": 2,
  "has_arnold_materials": true,
  "stand_in_node_ids": ["node:hero_proxyStandIn"],
  "stand_in_count": 1,
  "has_stand_ins": true
}
```

| Field | Type | Description |
|---|---|---|
| `has_arnold_plugin` | boolean | Scene contains an Arnold options/plugin node such as `aiOptions`. |
| `arnold_plugin_node_ids` | array[string] | Node IDs for detected Arnold plugin/options nodes. |
| `arnold_material_count` | integer | Count of Arnold material nodes in the snapshot. |
| `has_arnold_materials` | boolean | True when one or more Arnold materials are present. |
| `stand_in_node_ids` | array[string] | Node IDs for detected Arnold stand-in/proxy nodes (`aiStandIn`). |
| `stand_in_count` | integer | Count of Arnold stand-in nodes in the snapshot. |
| `has_stand_ins` | boolean | True when one or more Arnold stand-in nodes are present. |

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
  "graph_fingerprint": "sha256:demo",
  "graph_content_fingerprint": "sha256:content_demo"
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
| `graph_content_fingerprint` | string | Yes | Content-only fingerprint for duplicate material detection (ignores Maya node names). |
| `complexity_metadata` | object or null | No | Shader complexity profiler payload computed during enrichment. |
| `displacement_metadata` | object or null | No | Displacement risk analyzer payload computed during enrichment. |
| `vray_metadata` | object or null | No | V-Ray enrichment payload when the material is a V-Ray shader type. |
| `arnold_metadata` | object or null | No | Arnold enrichment payload when the material is an Arnold shader type. |

### Shader complexity metadata (`complexity_metadata`)

Attached during validation enrichment from upstream graph traversal and renderer adapter weights.

```json
{
  "depth_histogram": {
    "0": 1,
    "1": 1,
    "2": 1,
    "3": 2,
    "4": 1
  },
  "expensive_node_count": 1,
  "expensive_node_types": {
    "layeredTexture": 1
  },
  "farm_cost_score": 6.0,
  "farm_cost_hint": "low"
}
```

| Field | Type | Description |
|---|---|---|
| `depth_histogram` | object | Count of graph nodes at each upstream depth from the material root. |
| `expensive_node_count` | integer | Nodes whose adapter weight meets the expensive-node threshold. |
| `expensive_node_types` | object | Per node-type counts for expensive nodes. |
| `farm_cost_score` | number | Weighted render-cost estimate for the material subgraph. |
| `farm_cost_hint` | string | Cost band: `low`, `medium`, `high`, or `critical`. |

### Displacement risk metadata (`displacement_metadata`)

Attached during validation enrichment from displacement nodes, bounds, subdivision flags, and renderer-specific attrs.

```json
{
  "has_displacement": true,
  "displacement_node_ids": ["node:displacementShader1"],
  "max_amount": 12.0,
  "texture_linked": true,
  "subdivision_enabled": true,
  "bounds_min": 0.0,
  "bounds_max": 4.0,
  "bounds_span": 4.0,
  "renderer_flags": {
    "force_displacement": true,
    "subdivision_enabled": true
  },
  "force_displacement": true,
  "vector_displacement": false,
  "risk_score": 22.5,
  "risk_hint": "critical"
}
```

| Field | Type | Description |
|---|---|---|
| `has_displacement` | boolean | Material or shading engine has displacement nodes linked. |
| `displacement_node_ids` | array[string] | Displacement node IDs in the material network. |
| `max_amount` | number or null | Highest displacement amount found on linked nodes. |
| `texture_linked` | boolean | Upstream displacement texture dependency is present. |
| `subdivision_enabled` | boolean | Subdivision/displacement flags detected on the material. |
| `bounds_min` | number or null | Minimum displacement bound across linked nodes. |
| `bounds_max` | number or null | Maximum displacement bound across linked nodes. |
| `bounds_span` | number or null | `bounds_max - bounds_min` when both bounds are available. |
| `renderer_flags` | object | Renderer-specific displacement flags captured during enrichment. |
| `force_displacement` | boolean | V-Ray force-displacement flag detected. |
| `vector_displacement` | boolean | Vector displacement flag detected on the material node. |
| `risk_score` | number | Weighted displacement farm-risk estimate. |
| `risk_hint` | string | Risk band: `low`, `medium`, `high`, or `critical`. |

### V-Ray material metadata (`vray_metadata`)

Attached during validation enrichment for V-Ray material types such as `VRayMtl`.

```json
{
  "texture_count": 2,
  "displacement_linked": true,
  "subdivision_enabled": false,
  "reflection_max_depth": 8,
  "refraction_max_depth": 8,
  "limit_attrs": {
    "reflection_max_depth": 8,
    "refraction_max_depth": 8,
    "brdf": 3,
    "force_displacement": true
  }
}
```

| Field | Type | Description |
|---|---|---|
| `texture_count` | integer | Number of texture nodes linked to the material. |
| `displacement_linked` | boolean | Material has displacement nodes or a shading engine displacement shader. |
| `subdivision_enabled` | boolean | V-Ray subdivision/displacement flags detected on the material node. |
| `reflection_max_depth` | integer or null | Reflection trace depth limit when available. |
| `refraction_max_depth` | integer or null | Refraction trace depth limit when available. |
| `limit_attrs` | object | Additional normalized V-Ray limit attrs from the material node. |

### Arnold material metadata (`arnold_metadata`)

Attached during validation enrichment for Arnold material types such as `aiStandardSurface`.

```json
{
  "texture_count": 3,
  "displacement_linked": false,
  "specular_roughness": 0.35,
  "metalness": 0.0,
  "transmission_weight": 0.0,
  "transmission_depth": 8,
  "key_attrs": {
    "specular_roughness": 0.35,
    "metalness": 0.0,
    "transmission_weight": 0.0,
    "transmission_depth": 8,
    "opacity": 1.0
  }
}
```

| Field | Type | Description |
|---|---|---|
| `texture_count` | integer | Number of texture nodes linked to the material. |
| `displacement_linked` | boolean | Material has displacement nodes or a shading engine displacement shader. |
| `specular_roughness` | number or null | `specularRoughness` when available on the material node. |
| `metalness` | number or null | `metalness` when available on the material node. |
| `transmission_weight` | number or null | `transmission` weight when available on the material node. |
| `transmission_depth` | integer or null | `transmissionDepth` when available on the material node. |
| `key_attrs` | object | Additional normalized Arnold attrs from the material node. |

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
  },
  "optimized_path": "D:/show/assets/char/demo/tex/roughness_v001.<UDIM>.tx",
  "optimized_kind": "udim_tx",
  "optimized_exists": false,
  "optimized_mtime_utc": null,
  "optimized_is_stale": null,
  "optimized_udim_tiles": [1001, 1002],
  "optimized_missing_udim_tiles": [1003]
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
| `optimized_path` | string or null | No | Resolved `.tx` path (flat file or UDIM pattern). |
| `optimized_kind` | string or null | No | `tx` for single-file optimized texture; `udim_tx` for tiled UDIM `.tx`. |
| `optimized_exists` | boolean or null | No | Whether expected `.tx` file or full UDIM tile set exists. |
| `optimized_mtime_utc` | string or null | No | `.tx` mtime when a single flat `.tx` is used. |
| `optimized_is_stale` | boolean or null | No | True when source texture is newer than `.tx` (farm should re-bake). |
| `optimized_udim_tiles` | array[integer] | Yes | UDIM tile numbers with existing `.tx` files. |
| `optimized_missing_udim_tiles` | array[integer] | Yes | UDIM tiles expected from source but missing `.tx`. |

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

## ShapeSnapshot

Geometry summary for a Maya shape node (`mesh`, proxy stand-in, etc.).

```json
{
  "node_id": "mesh:body_geo",
  "name": "body_geo",
  "full_name": "|world|char_demo:body_geo",
  "type_name": "mesh",
  "transform_id": "transform:body_geo",
  "polygon_count": 6,
  "vertex_count": 8,
  "face_count": 12,
  "edge_count": 18,
  "world_bbox": {
    "min_x": -1.0,
    "min_y": -2.0,
    "min_z": -3.0,
    "max_x": 4.0,
    "max_y": 5.0,
    "max_z": 6.0
  },
  "topology_fingerprint": "sha256:8f14e45fceea167a",
  "instancing_key": "mesh:body_geo",
  "proxy_attrs": {
    "intermediateObject": false
  },
  "referenced": false,
  "namespace": "char_demo",
  "locked": false
}
```

| Field | Type | Required | Description |
|---|---|---:|---|
| `node_id` | string | Yes | Stable shape ID, typically `mesh:<short_name>`. |
| `name` | string | Yes | Short shape name. |
| `full_name` | string | No | Full Maya DAG path. |
| `type_name` | string | Yes | Maya shape type (`mesh`, `aiStandIn`, `VRayProxy`, ...). |
| `transform_id` | string | No | Parent transform ID when known. |
| `polygon_count` | integer | Yes | Polygon count from `polyEvaluate(polygon=True)`. |
| `vertex_count` | integer | Yes | Vertex count from `polyEvaluate(vertex=True)`. |
| `face_count` | integer | Yes | Face count from `polyEvaluate(face=True)`. |
| `edge_count` | integer | Yes | Edge count from `polyEvaluate(edge=True)`. |
| `world_bbox` | object or null | No | World-space axis-aligned bounds. |
| `topology_fingerprint` | string | Yes | Hash of topology counts and face-vertex signature. |
| `instancing_key` | string | Yes | Shared key for instanced copies of the same shape. |
| `proxy_attrs` | object | Yes | Proxy/custom attrs (`dso`, `fileName`, subdivision flags, ...). |
| `referenced` | boolean | Yes | True when shape comes from a referenced file. |
| `namespace` | string or null | No | Maya namespace if present. |
| `locked` | boolean | Yes | True when shape node is locked. |

Rule scopes `shape` and `geometry` evaluate against `GraphSnapshot.shapes`.

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
  "scene_path": "examples/broken_scene/pipeline_inspector_demo_broken.ma",
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

## Shader Manifest Schema

The Material Passport / Shader Manifest is a separate JSON artifact from `GraphSnapshot`. It is produced by `pipeline_inspector.reports.manifest.build_shader_manifest()` and exported from the Maya UI or headless tools.

Manifest schema is versioned independently via `manifest_schema_version`.

### Manifest schema 1.1 (v0.3)

Current manifest version:

```text
1.1
```

Migration from **1.0** is additive. Existing 1.0 manifests remain valid baselines for diff and gate workflows.

| Change | Scope | Notes |
|---|---|---|
| `manifest_schema_version` | top-level | Bumped from `1.0` to `1.1`. |
| `health_score` | top-level, optional | Integer `0..100` from validation results when `results` are passed to `build_shader_manifest()`. |
| `issues` | per-material, optional | Failed-issue summary: `failed`, `critical`, `error`, `warning`, `rule_ids`. |

Fields unchanged from 1.0 include `materials`, `textures`, `graph_fingerprint`, texture version metadata, and snapshot provenance fields (`scene_path`, `renderer`, `scan_scope`, `scanned_at_utc`).

Readers that only understand 1.0 may ignore `health_score` and per-material `issues`. Diff tooling should continue to accept 1.0 baseline manifests.

Implementation:

```text
src/pipeline_inspector/reports/manifest.py
```

## Implementation Notes

Current model implementation:

```text
src/pipeline_inspector/core/models.py
```

Current round-trip tests:

```text
tests/unit/test_snapshot_models.py
```

The core validator should consume `GraphSnapshot`, not raw Maya nodes.
