# How rules work

Pipeline Inspector is **data-driven**: JSON rules + profiles evaluate a **`GraphSnapshot`**, not live DG mutations per rule.

## Pipeline

```text
Maya scene  →  scanner  →  GraphSnapshot  →  enrich  →  rule engine  →  issues
```

1. **Scanner** collects materials, file dependencies, shapes, connections.
2. **Enrichment** adds derived fields (UDIM, max_dimension, complexity, geometry stats).
3. **Rule engine** loads enabled rules for active **profile** + studio overlays.
4. **Issues** carry severity, owner, blocking flags, fix metadata.

Architecture: [ADR 0001 — Snapshot-first core](../../adr/0001-snapshot-first-core.md) · [`ARCHITECTURE.md`](../../ARCHITECTURE.md)

## Rule packs

| Pack | Location | Focus |
| --- | --- | --- |
| Common | `src/pipeline_inspector/rules/common/` | Textures, paths, UDIM, complexity, geometry |
| V-Ray | `rules/vray/` | V-Ray material policies |
| Arnold | `rules/arnold/` | Arnold material policies |
| USD health | optional `usd` extra | USD asset checks |

Studios add paths via Settings → Advanced or `pipeline_inspector_studio.json`.

## Rule structure (conceptual)

| Field | Role |
| --- | --- |
| `id` | Stable identifier (`common.texture.missing`) |
| `severity` | critical / error / warning / info |
| `check` | Predicate on snapshot fields |
| `fix` | Optional safe fix template |
| `blocking` | Publish / Deadline block flags per profile |

Schema details: [`RULE_AUTHORING.md`](../../RULE_AUTHORING.md) · [`SNAPSHOT_SCHEMA.md`](../../SNAPSHOT_SCHEMA.md)

## Renderer adapters

Renderer-specific node lists and cost weights live in **adapters** — rules stay portable ([ADR 0002](../../adr/0002-renderer-adapter-boundary.md)).

## Next

→ [Profiles & asset class](Profiles-and-Asset-Classes) · [Authoring rules](Authoring-Rules)
