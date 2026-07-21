# Rule Authoring Guide

Maya Pipeline Inspector is intended to be data-driven. Most validation behavior should be defined in JSON rule packs rather than hardcoded directly into the core validator.

Status: early development for the JSON schema; the Maya **incident-to-rule** UI workflow is available from v0.5 (see [Incident-to-Rule Workflow](#incident-to-rule-workflow-maya-ui)).

## Rule Authoring Goals

Rules should be:

- readable by Technical Artists, Shader TDs, and Pipeline TDs;
- stable across renderer adapter changes;
- explainable to Technical Artists;
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
| `owner` | Expected fix owner (JSON value): `artist` (Technical Artist), `texture_artist`, `shader_td`, `pipeline_td`, `supervisor`. |
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
| `duplicate_geometry` | Scene-level duplicate mesh detection by topology, bounds, and optional proxy attrs. |

### `duplicate_geometry`

Graph-scoped check that groups `ShapeSnapshot` entries by geometry fingerprint:

- **Meshes:** `topology_fingerprint` + rounded `world_bbox` + optional `match_attributes` from `proxy_attrs`
- **Proxy / stand-in shapes (`aiStandIn`, `VRayProxy`):** proxy source attrs such as `dso` or `fileName`

Intentional Maya instance groups are ignored when every shape in a duplicate group shares the same `instancing_key`. Intermediate meshes (`proxy_attrs.intermediateObject = true`) and referenced shapes (unless `include_referenced: true`) are skipped.

Example rule:

```json
"check": {
  "type": "duplicate_geometry",
  "max_shapes": 500,
  "min_group_size": 2,
  "bbox_precision": 3,
  "match_attributes": ["displaySmoothMesh"]
}
```

Failed results include `evidence.duplicate_groups[]` with `shape_ids`, `topology_fingerprint`, `bbox`, and `instancing_keys`. Pair with `duplicate_geometry_scan_budget` when scenes may exceed the scan cap.

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

Rules should be conservative by default. Profiles may override policy for lookdev (`artist_relaxed`), publish, deadline, supervisor, or CI modes.

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

For studio deployment patterns (`--extra-rules`, custom profile folders, and UI pipeline hooks), see [STUDIO_OVERRIDES.md](STUDIO_OVERRIDES.md).

## Incident-to-Rule Workflow (Maya UI)

Pipeline TDs and shader TDs can turn a failed validation issue into a JSON rule draft inside Maya, validate it with the same checks as `tools/validate_rules.py`, and export a studio sidecar for review.

Related docs:

- [STUDIO_OVERRIDES.md](STUDIO_OVERRIDES.md) — `--extra-rules`, `extra_rule_paths`, and studio config rollout
- [USER_GUIDE.md](USER_GUIDE.md) — Validate tab, profiles, and issue details
- [MAYA_INSTALL.md](MAYA_INSTALL.md) — loading the dockable panel in Maya

### When to use

Use the incident-to-rule workflow when:

- a production failure exposes a gap not covered by packaged rules;
- a show needs a stricter or show-specific check derived from a real scene;
- you want to prototype a rule from live issue context before opening a PR to the studio rule pack.

Prefer **Rule Editor** session overrides first when you only need a temporary severity, threshold, or enabled change for the current Maya session. Author a new rule when the behavior should ship to the facility rule stack.

### Prerequisites

| Setting | Where | Purpose |
| --- | --- | --- |
| `pipeline.extra_rules_folder` | Settings → **Studio Policy** (from `pipeline_inspector_studio.json`) | Target folder for **Export to Studio extra_rules** |
| `extra_rule_paths` | Settings → **Advanced** → Extra rule roots (stored in `user.json`) | Local rule packs layered at validation time; default save path when no studio folder is set |
| Validation run | Validate tab | Populates the issue list and keeps source rule definitions available for prefill |

Facility rollout example for the export folder inside `pipeline_inspector_studio.json`:

```json
{
  "schema_version": "2.0",
  "studio_name": "Example Studio",
  "pipeline": {
    "extra_rules_folder": "//studio/share/pipeline_inspector/extra_rules"
  }
}
```

### Workflow A — from a failed issue

1. Open the dockable panel and run **Validate Scene** (or selection / publish preflight as needed).
2. Select one **failed** issue in the Validate table.
3. In issue details, click **Create Rule Draft**.
4. The **New Rule** wizard opens with prefill from the issue:
   - template chosen from the source check type (`attribute_equals`, `numeric_max`, or `path_exists`);
   - `message`, `why`, `severity`, and `owner` copied from the issue (and source rule when loaded);
   - suggested rule id `{source_rule_id}.draft` (for example `common.texture.missing.draft`).
5. Edit fields as needed. Choose **Validate** — the draft must pass schema checks and must not duplicate an id already loaded from packaged rules or extra rule roots.
6. Persist the draft using one of:
   - **Save** — writes `{"rules": [<rule>]}` to the output path shown in the form (defaults to the studio extra_rules folder or first extra rule root when configured);
   - **Export to Studio extra_rules** — enabled when `pipeline.extra_rules_folder` is set; writes an incident sidecar (see below) after validation.
7. Hand off to pipeline review: merge into the show rule pack, run `python tools/validate_rules.py`, deploy to the same paths your launchers pass to `--extra-rules` / `extra_rule_paths`.

If no issue is selected, **Create Rule Draft** shows a status message asking you to select a failed issue first.

### Workflow B — blank rule from template

Settings → **Advanced** → **New Rule…** opens the same wizard without issue prefill. Pick one of the starter templates, fill in ids and copy, validate, then save or export.

### Rule Editor (session overrides)

Settings → **Advanced** → **Open Rule Editor…** browses the loaded rule catalog (packaged rules plus configured extra rule roots). TDs can edit the safe subset for the **current Maya session** only:

- enabled
- severity
- numeric threshold (when the rule exposes one)

**Apply** / **Save** runs the same validation path as `tools/validate_rules.py` before writing session overrides. Overrides apply on the next validation run in that session; they are not written to disk and do not replace studio rule packs.

### Starter templates (wizard)

| Template | Typical use |
| --- | --- |
| `attribute_equals` | Color space, naming, or other attribute must match an expected value |
| `numeric_max` | Resolution, complexity, or other numeric ceiling |
| `path_exists` | Missing texture or other file dependency on disk |

Templates seed `scope`, `match`, `check`, and default `policy`. Adjust copy, severity, and owner before validating.

### Incident sidecar JSON

**Export to Studio extra_rules** writes one file per rule id:

```text
{extra_rules_folder}/{rule_id}.json
```

Example payload:

```json
{
  "schema_version": "1.0",
  "exported_from": "incident",
  "source_rule_id": "common.texture.missing",
  "scene_path": "//show/scenes/hero/shot010.ma",
  "exported_at_utc": "2026-07-11T09:00:00+00:00",
  "rules": [
    {
      "id": "common.texture.missing.draft",
      "name": "Texture file must exist",
      "enabled": true,
      "renderer": ["common", "vray", "arnold"],
      "scope": "file_dependency",
      "severity": "critical",
      "owner": "shader_td",
      "message": "Texture file is missing.",
      "why": "Missing textures usually render black or incorrect on the farm.",
      "match": { "dependency_kind": "texture" },
      "check": { "type": "path_exists" },
      "policy": {
        "block_publish": true,
        "block_deadline": true,
        "waiver_allowed": false,
        "auto_fix_allowed": false
      }
    }
  ]
}
```

Metadata fields (`source_rule_id`, `scene_path`, `exported_at_utc`) support TD review and audit. The authoritative rule body is still the object inside `rules[]`; promote it into your show pack using the normal pack layout documented in [STUDIO_OVERRIDES.md](STUDIO_OVERRIDES.md).

### Pipeline handoff checklist

1. Review the sidecar or saved draft in version control (no client names, real production paths, or secrets in open-source examples).
2. Rename or finalize the rule id before release — avoid shipping `.draft` suffixes to Technical Artists.
3. Run `python tools/validate_rules.py` (and profile override checks if the rule is referenced in a studio profile).
4. Deploy the JSON into the facility `extra_rules` tree or show rule pack loaded by `--extra-rules` / `extra_rule_paths`.
5. Confirm Maya and headless CLI use the same extra rule paths so validation matches TD review.

### Current limitations

- The wizard covers MVP templates only; advanced checks still require hand-authored JSON.
- **Create Rule Draft** prefill works best when the source rule definition was loaded during validation.
- Session overrides from Rule Editor do not persist across Maya restarts.
- **Export to Studio extra_rules** requires `pipeline.extra_rules_folder`; otherwise use **Save** to a path under your local extra rule roots.

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
