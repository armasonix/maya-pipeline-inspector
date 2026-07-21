# Overview

**Maya Pipeline Inspector** (`maya-pipeline-inspector`) validates shading networks, texture dependencies, renderer-specific material settings, displacement, paths, geometry budgets, and workstation readiness **inside Maya** or **headlessly** via the same rule engine.

## Who it is for

| Role | Primary need |
| --- | --- |
| **Technical Artist** | Fast red/yellow/green status, select broken nodes, safe fixes |
| **Shader TD** | Enforce material rules, tune profiles, author rule packs |
| **Pipeline TD** | Headless gates, studio config, Deadline hooks, CI |
| **Render supervisor** | Blocking status, waivers, HTML/JSON reports, farm safety |

## Core ideas

1. **Snapshot-first** — Maya (or USD) produces a `GraphSnapshot`; rules run without live scene mutation ([ADR 0001](../../adr/0001-snapshot-first-core.md)).
2. **Data-driven rules** — JSON rule packs for Common, V-Ray, Arnold, USD health; studio overlays.
3. **GUI-first** — Panel is the daily surface; CLI mirrors validation ([ADR 0005](../../adr/0005-gui-first-product-philosophy.md)).
4. **Safe fixes** — Auto-fix queue with reference protection, high-risk gates, audit trail ([ADR 0003](../../adr/0003-safe-fix-reference-safety-policy.md)).
5. **Studio extensibility** — Profiles, waivers, connectors, governance without forking core code.

## What it is not

- Not a full publish/AMS replacement
- Not measured render-time prediction (farm cost score is heuristic)
- Not AWS Deadline Cloud integration (on-prem Deadline 10 is supported)
- Not texture freshness from a publish database (filesystem sibling scan only)

See [FAQ — known limitations](../FAQ-and-Troubleshooting#known-limitations).

## Version & support matrix

| Item | Status |
| --- | --- |
| **Shipped release** | v0.6.0 (2026-07-21) |
| **Maya tested** | 2024, 2025 |
| **Maya best effort** | 2026 |
| **Renderer packs** | Common, V-Ray, Arnold (+ USD health rules) |
| **License** | MIT |

## Next steps

→ [Installation](Installation) · [5-minute quick start](Quick-Start-5-Minutes) · [Panel overview](Panel-Overview)
