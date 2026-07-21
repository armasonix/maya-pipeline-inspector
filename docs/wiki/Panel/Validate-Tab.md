# Validate tab

Default tab — **scan**, **triage**, and **navigate** to problems.

## Controls

| Control | Action |
| --- | --- |
| **Workflow** | Profile: `artist_relaxed`, `publish_strict`, `deadline_critical`, `supervisor_full` |
| **Asset class** | Optional overlay: Hero / Prop / Background (resolution + geometry tiers) |
| **Validate Scene** | Full scene scan |
| **Validate Selection** | Selected DAG subset |

## Summary bar

After validation:

| Field | Meaning |
| --- | --- |
| **Health** | Heuristic 0–100 aggregate |
| **Critical / Error / Warning / Info** | Issue counts by severity |
| **Publish Block** | `YES` if publish-blocking rules failed |
| **Deadline Block** | `YES` if farm-blocking rules failed |

Blocking is profile-driven — same engine as CLI `validate`.

## Issue table

**Filters:** severity, owner, view (all/blocking/fixable), sort order.

**Columns (typical):** rule id, message, severity, node, path, owner, blocking, fixable.

## Issue details & actions

Select a row to show explanation and remediation hints.

| Button | Action |
| --- | --- |
| **Select Node** | Maya selection |
| **Hypershade** | Open graph for material |
| **Copy Path** | Clipboard — texture or node path |
| **Reveal File** | OS file browser (local paths) |

## Farm cost hint

Material complexity metadata feeds rules like `common.shader_complexity.farm_cost_score.max`. Bands: `low`, `medium`, `high`, `critical`. See [`USER_GUIDE.md` — Shader farm cost score](../../USER_GUIDE.md#shader-farm-cost-score).

## Typical loop

```text
Validate → filter Critical → select issue → fix or waiver → revalidate
```

→ [Fixes & waivers](Fixes-and-Waivers) · [Profiles](Profiles-and-Asset-Classes)
