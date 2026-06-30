# Rule Authoring Guide

Maya Shader Health Inspector is intended to be data-driven. Most validation behavior should be defined in JSON rule packs rather than hardcoded directly into the core validator.

Status: early development. The schema below is the target MVP shape and may change while the core engine is implemented.

## Rule Authoring Goals

Rules should be:

- readable by Technical Artists, Shader TDs, and Pipeline TDs;
- stable across renderer adapter changes;
- explainable to artists;
- testable with snapshot fixtures;
- configurable by profile;
- safe when they define auto-fixes.

## Rule Philosophy

A rule must not only say that something is wrong. It must explain:

1. what failed;
2. why it matters in production;
3. what value or state is expected;
4. who owns the fix;
5. whether it blocks publish or Deadline;
6. whether a safe auto-fix is available.

## Minimal Rule Example

```json
{
  "id": "common.texture.missing",
  "name": "Texture file must exist",
  "enabled": true,
  "renderer": ["common", "vray", "arnold"],
  "scope": "file_dependency",
  "severity": "critical",
  "owner": "shader_td",
  "message": "Texture file is missing.",
  "why": "Missing textures usually render black, flat, or incorrect on the farm and can waste render resources.",
  "match": {
    "dependency_kind": "texture"
  },
  "check": {
    "type": "path_exists"
  },
  "policy": {
    "block_publish": true,
    "block_deadline": true,
    "waiver_allowed": false,
    "auto_fix_allowed": false
  }
}
```

## Color Space Rule Example

```json
{
  "id": "common.texture.colorspace.data_raw",
  "name": "Data textures must use Raw color space",
  "enabled": true,
  "renderer": ["common", "vray", "arnold"],
  "scope": "texture_node",
  "severity": "critical",
  "owner": "shader_td",
  "message": "Data texture uses a color-managed color space.",
  "why": "Roughness, masks, normal, bump, and displacement maps store numeric data. Color transforms can change those numeric values and alter the rendered material.",
  "match": {
    "semantic_slot": ["roughness", "metalness", "normal", "bump", "displacement", "mask"],
    "node_type": ["file", "VRayBitmap", "aiImage"]
  },
  "check": {
    "type": "attribute_equals",
    "attribute": "colorSpace",
    "expected": "Raw"
  },
  "policy": {
    "block_publish": true,
    "block_deadline": true,
    "waiver_allowed": true,
    "auto_fix_allowed": true
  },
  "fix": {
    "type": "set_attr",
    "attribute": "colorSpace",
    "value": "Raw",
    "risk": "low"
  }
}
```

## Required Fields

Every production rule should include:

| Field | Purpose |
|---|---|
| `id` | Stable unique rule ID. Must not be renamed casually. |
| `name` | Human-readable rule name. |
| `enabled` | Default enabled state. |
| `renderer` | Renderer families where the rule can run. |
| `scope` | Target domain: node, material, file dependency, graph, scene. |
| `severity` | User-facing importance: info, warning, error, critical. |
| `owner` | Expected fix owner: artist, texture_artist, shader_td, pipeline_td, supervisor. |
| `message` | Short issue text. |
| `why` | Explanation shown in UI/report. |
| `match` | Target selection criteria. |
| `check` | Validation operation. |
| `policy` | Block, waiver, and auto-fix behavior. |

## Severity vs Block Policy

Severity and blocking must stay separate.

Example:

```json
"severity": "warning",
"policy": {
  "block_publish": false,
  "block_deadline": false
}
```

A warning may still block in a strict profile, but that should happen through profile overrides, not by assuming every warning blocks.

## Recommended Severity Meaning

| Severity | Meaning |
|---|---|
| `info` | Useful cleanup or visibility, not a failure. |
| `warning` | Should be reviewed, usually not blocking. |
| `error` | Should be fixed before publish, may block depending on profile. |
| `critical` | High risk, usually blocks publish or farm submission. |

## Owners

Suggested owner values:

- `artist`
- `texture_artist`
- `shader_td`
- `pipeline_td`
- `render_supervisor`
- `supervisor`

Ownership helps the UI and reports group issues by responsibility.

## Match Section

The `match` section selects objects from the snapshot.

Possible target concepts:

- node type;
- renderer family;
- semantic slot;
- material type;
- texture extension;
- path pattern;
- asset class;
- referenced/locked status;
- graph metric.

Example:

```json
"match": {
  "node_type": ["file", "aiImage"],
  "semantic_slot": ["roughness", "mask"],
  "referenced": false
}
```

## Check Types for MVP

Initial check types:

| Check Type | Purpose |
|---|---|
| `attribute_equals` | Attribute must equal expected value. |
| `attribute_in` | Attribute must be in allowed list. |
| `path_exists` | File path must exist. |
| `path_policy` | Path must follow studio/profile policy. |
| `udim_complete` | UDIM tile set must be complete. |
| `texture_version_latest` | Texture version should be latest according to naming policy. |
| `color_space_by_semantic` | Color/data slot should use correct color management. |
| `graph_budget` | Material graph must stay within complexity limits. |
| `displacement_risk` | Displacement setup must stay within safe thresholds. |
| `optimized_texture_freshness` | Optimized texture must exist and be newer than source. |
| `orphan_network` | Unassigned/dead shader network detection. |

## Policy Section

Policy controls production behavior.

```json
"policy": {
  "block_publish": true,
  "block_deadline": false,
  "waiver_allowed": true,
  "auto_fix_allowed": false
}
```

Rules should be conservative by default. Profiles may override policy for artist, publish, deadline, supervisor, or CI modes.

## Auto-Fix Section

Auto-fix is optional and must be safe by design.

Allowed MVP fix types:

| Fix Type | Example | Risk |
|---|---|---|
| `set_attr` | `file.colorSpace = Raw` | low |
| `relink_path` | relink v001 texture to v003 | medium |
| `normalize_path` | convert local path to project variable | medium |
| `disable_feature` | disable risky displacement | high |
| `cleanup_orphan` | delete unused network | high, preview-only |

Example:

```json
"fix": {
  "type": "set_attr",
  "attribute": "colorSpace",
  "value": "Raw",
  "risk": "low"
}
```

Auto-fixes must not run silently. The UI must show before value, after value, reason, risk, target node, and reference/lock status.

## Profile Overrides

Profiles can adjust rule behavior without editing base rules.

Example:

```json
{
  "id": "deadline_critical",
  "rule_overrides": {
    "common.texture.missing": {
      "enabled": true,
      "severity": "critical",
      "block_deadline": true
    },
    "common.shader.orphan_network": {
      "enabled": false
    }
  }
}
```

## Rule ID Naming

Use stable hierarchical IDs:

```text
common.texture.missing
common.texture.path.local_drive
common.texture.colorspace.data_raw
common.udim.missing_tile
vray.displacement.high_amount
arnold.texture.tx_missing
```

Rules should not be renamed once released. If behavior changes significantly, create a new rule ID or document migration.

## Testing Rules

Every rule should have:

- at least one passing fixture;
- at least one failing fixture;
- expected severity;
- expected block flags;
- expected message/why fields;
- expected fix availability if applicable.

Rules should be validated by a CLI tool before release:

```bash
python tools/validate_rules.py
```

## Open-Source Safety

Do not commit proprietary studio rules, production paths, client names, real asset names, or internal server locations. Use sanitized demo data and generic examples.
