# ADR 0001: Snapshot-first core architecture

## Status

Accepted

## Date

2026-06-30

## Context

Maya Shader Health Inspector must validate material and texture problems in Maya scenes, but most validation logic should be testable without launching Maya.

Maya-dependent APIs are expensive to test, difficult to run in public CI, and sensitive to installed Maya/render plugin versions. At the same time, the project must support several execution modes:

- dockable Maya UI;
- headless mayapy validation;
- JSON/HTML report generation;
- Deadline submit preflight;
- future publish hook integration;
- pure Python unit tests.

If validation logic directly depends on Maya nodes, `maya.cmds`, Maya API objects, or UI state, the project will become hard to test, hard to maintain, and difficult for open-source contributors to extend.

## Decision

The core validation engine will be built around a snapshot-first architecture.

A Maya-dependent scanner will convert the current scene, selection, or asset into a pure Python / JSON-compatible `GraphSnapshot`. The core engine will validate only `GraphSnapshot` data and resolved rule packs.

The core engine must not import Maya modules.

Allowed in core:

- dataclasses / typed Python models;
- JSON-compatible dictionaries;
- path utilities;
- rule schema validation;
- rule evaluation;
- health scoring;
- fix planning;
- report and manifest generation.

Not allowed in core:

- `maya.cmds`;
- `maya.api.OpenMaya`;
- PySide / Qt;
- V-Ray Python APIs;
- Arnold Python APIs;
- direct Maya node handles.

The Maya layer owns scene traversal and scene mutation. The core owns validation decisions.

## Alternatives Considered

### 1. Validate directly against Maya nodes

Pros:

- faster initial scripting;
- direct access to live scene data;
- fewer data models at the beginning.

Cons:

- difficult to test in public CI;
- tightly coupled to Maya versions;
- hard to run headlessly without Maya;
- difficult to reproduce bugs from reports;
- UI and validation logic become entangled.

Rejected.

### 2. Build UI first and extract core later

Pros:

- quick visual prototype;
- easier to demo early.

Cons:

- unstable data contracts;
- core behavior shaped by UI needs instead of production validation needs;
- high risk of rewrite;
- hard to test.

Rejected.

### 3. Snapshot-first core

Pros:

- core can be tested with pytest without Maya;
- rule engine can use deterministic fixtures;
- headless, UI, reports, and Deadline integration share one validation path;
- renderer adapters can be tested with snapshot fixtures;
- production bugs can be reproduced from saved snapshots.

Cons:

- requires more upfront model design;
- scanner must maintain a stable snapshot schema;
- some live Maya state may need careful serialization.

Accepted.

## Consequences

### Positive

- Most tests can run in normal Python CI.
- Validation results are deterministic and reproducible.
- Rule packs can be validated against fixtures.
- UI is not responsible for validation logic.
- Headless validation and Maya UI behavior can remain consistent.
- Saved snapshots can be used for regression tests.

### Negative / Tradeoffs

- Initial development requires defining snapshot models early.
- Scanner implementation must be disciplined about schema stability.
- Some Maya-specific values may need normalization before entering the snapshot.
- Snapshot schema versioning becomes necessary.

## Implementation Notes

Initial core model names:

- `GraphSnapshot`
- `NodeSnapshot`
- `ConnectionSnapshot`
- `MaterialSnapshot`
- `ShadingEngineSnapshot`
- `FileDependencySnapshot`
- `ReferenceSnapshot`

Expected module location:

```text
src/shader_health/core/models.py
```

Expected fixture location:

```text
tests/fixtures/snapshots/
```

All snapshot JSON should include a schema version.

The first rule engine milestone should validate saved JSON snapshots before any Maya UI work begins.

## Related

- Issue: `#005 - Implement core snapshot models`
- Issue: `#053 - Add fixture snapshot schema documentation`
- Document: `docs/ARCHITECTURE.md`
- Document: `docs/DEVELOPMENT_PLAN.md`
