# Profiles & asset classes

**Profiles** select which rules run and how blocking behaves. **Asset class** overlays resolution and geometry budgets.

## Workflow profiles (Maya UI)

| Profile | Use case |
| --- | --- |
| `artist_relaxed` | Daily lookdev — fewer complexity warnings |
| `publish_strict` | Publish gate — blocking enabled |
| `deadline_critical` | Farm preflight — tightest material/path checks |
| `supervisor_full` | Review — may allow batch risky-fix confirm |

Headless-only example: `ci_headless` — not shown in UI dropdown.

## Asset class overlays

| Class | Texture max edge | Geometry tier |
| --- | --- | --- |
| None | Rules disabled | Default scan |
| `asset_class_hero` | 4096px | Hero polycount budget |
| `asset_class_prop` | 2048px | Prop budget |
| `asset_class_background` | 1024px | Background budget |

Selected class merges onto active workflow profile during validation.

## Health score

Heuristic aggregate — **not** render time. Use severity counts and blocking flags for gates.

## Studio overrides

`pipeline_inspector_studio.json` can:

- Enable/disable rule ids
- Override thresholds
- Add rule search paths
- Set default profile per pipeline mode

→ [`STUDIO_OVERRIDES.md`](../../STUDIO_OVERRIDES.md)

## Waivers interaction

Waivers suppress specific rule/node/path combinations per sidecar policy — blocking may clear while issue remains visible as waived.

→ [Fixes & waivers](../Panel/Fixes-and-Waivers)
