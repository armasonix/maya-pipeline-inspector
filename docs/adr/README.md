# Architecture Decision Records

This folder contains Architecture Decision Records (ADRs) for Maya Shader Health Inspector.

ADRs document important technical decisions that shape the project architecture. They explain what was decided, why it was decided, what alternatives were considered, and what consequences the decision has.

## Why ADRs Exist

Maya Shader Health Inspector is intended to become a production-ready, open-source Maya material QA framework. The project has several architectural constraints:

- the core validation engine must remain testable without Maya;
- renderer-specific behavior must stay outside the core;
- scene mutation must be safe, explicit, undoable, and reference-aware;
- rule packs and profiles must be data-driven;
- UI, headless validation, reports, and Deadline integration should share the same validation core;
- the Maya dockable panel is the primary product surface; CLI and farm hooks are integration surfaces (ADR 0005).

ADRs help keep these decisions visible as the codebase grows.

## ADR Index

| ADR | Title | Status |
|---|---|---|
| 0001 | Snapshot-first core architecture | Accepted |
| 0002 | Renderer adapter boundary | Accepted |
| 0003 | Safe-fix and reference-safety policy | Accepted |
| 0004 | Headless apply-fixes policy | Accepted |
| 0005 | GUI-first product philosophy | Accepted |

## Status Values

Use one of these values:

- `Proposed` — decision is still under discussion.
- `Accepted` — decision is active and should guide implementation.
- `Superseded` — decision was replaced by a later ADR.
- `Rejected` — decision was considered but not adopted.

## Creating a New ADR

1. Copy `ADR_TEMPLATE.md`.
2. Name the new file using the next number:

```text
0004-short-decision-title.md
```

3. Keep the decision focused on one topic.
4. Link related issues or pull requests if available.
5. Update this README index.

## Rule of Thumb

Create an ADR when a decision changes how contributors should design code, write rules, handle safety, structure data, or integrate with Maya/renderers/pipeline tools.
