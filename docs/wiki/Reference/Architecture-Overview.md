# Architecture overview

High-level system design — full detail in [`ARCHITECTURE.md`](../../ARCHITECTURE.md).

## Layers

```text
┌─────────────────────────────────────────────────────────┐
│  Maya UI (Qt panel, menus, shelf)                        │
├─────────────────────────────────────────────────────────┤
│  maya.* — scanner, validation_pipeline, commands       │
├─────────────────────────────────────────────────────────┤
│  pipeline_inspector core — models, rules, validator    │
├─────────────────────────────────────────────────────────┤
│  integrations — deadline, notify, trackers, update       │
└─────────────────────────────────────────────────────────┘
```

## Snapshot-first core

Maya is a **producer** of `GraphSnapshot`. The validator is pure Python and runs in CI without Maya for fixture tests ([ADR 0001](../../adr/0001-snapshot-first-core.md)).

## Renderer adapters

Isolate V-Ray / Arnold node semantics from common rules ([ADR 0002](../../adr/0002-renderer-adapter-boundary.md)).

## Configuration

Studio JSON + user JSON + env vars ([ADR 0007](../../adr/0007-settings-and-connectors-architecture.md)).

## Native plug-in

Optional `.mll` with Python fallback ([ADR 0006](../../adr/0006-native-mll-plugin-strategy.md)).

## ADR index

→ [`adr/README.md`](../../adr/README.md)

## Development plan

Roadmap & subsystem map: [`DEVELOPMENT_PLAN.md`](../../DEVELOPMENT_PLAN.md)
