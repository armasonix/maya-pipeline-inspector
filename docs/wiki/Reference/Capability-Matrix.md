# Capability matrix (v0.6.0)

Condensed from [`DEVELOPMENT_PLAN.md` §6](../../DEVELOPMENT_PLAN.md#6-shipped-capability-matrix-v060). Legend: **Shipped** · **Partial** · **Gap**

## Validation engine

| Capability | Status |
| --- | --- |
| GraphSnapshot + JSON rules | Shipped |
| Common / V-Ray / Arnold / USD health packs | Shipped |
| Geometry polycount + duplicate scan | Shipped |
| Texture missing, path, UDIM, color space | Shipped |
| Texture freshness | Partial — filesystem only |
| Health score | Shipped — heuristic |

## Maya panel

| Tab | Status |
| --- | --- |
| Validate, Waivers, Fixes, Reports | Shipped |
| Readiness, Farm, Settings hub | Shipped |
| Rule browser / wizard | Partial |
| Native `.mll` | Partial — build locally |

## Headless CLI

| Command | Status |
| --- | --- |
| validate, manifest, diff, gate, apply-fixes | Shipped |
| rules validate, farm-analytics | Shipped |
| Readiness CLI | Gap |
| CLI user prefs parity | Gap |

## Integrations

| Integration | Status |
| --- | --- |
| Deadline 10, notifications, trackers, bug relay | Shipped |
| GitHub Release auto-update | Shipped |
| AWS Deadline Cloud | Gap |

## Governance

| Capability | Status |
| --- | --- |
| PermissionResolver + routing | Shipped |
| Self-reported roles | Partial |
| Compliance audit export | Gap |

Full tables: [`DEVELOPMENT_PLAN.md` §6–§6.6](../../DEVELOPMENT_PLAN.md#6-shipped-capability-matrix-v060)
