# ADR 0005: GUI-first product philosophy

## Status

Accepted

## Date

2026-07-07

## Context

v0.3 delivered a functional Maya dockable panel, headless CLI, manifest gates, apply-fixes automation, and a Deadline preflight example. Pipeline TDs can integrate Pipeline Inspector without opening Maya, and the shared `validation_pipeline` keeps UI and headless results aligned.

In practice, the primary daily users are Technical Artists and Shader TDs working inside Maya. They validate scenes during lookdev, triage issues before publish, and need fast, low-friction access to blocking state (`block_publish`, `block_deadline`) without reading JSON reports or running terminal commands. v0.4 expands farm submission (Deadline 10 on-prem), native plugin bootstrap, and UX improvements — all of which must land in the panel first or alongside headless delivery.

Without an explicit product philosophy, new features risk shipping as CLI-only utilities or scattered panel buttons. That pattern slows Technical Artist adoption, increases support burden on pipeline TDs, and creates GUI/headless drift over time.

## Decision

Maya Pipeline Inspector adopts a **GUI-first product philosophy** for v0.4 and subsequent releases:

1. **GUI first** — Every new pipeline-facing feature must ship with a Maya panel affordance before (or in the same milestone as) CLI-only delivery. Headless and farm wrappers remain required, but they are secondary surfaces that call the same modules the panel uses.
2. **Speed** — Default Technical Artist flows should reach an actionable result in **three clicks or fewer** from an open panel: for example, open panel → Validate Scene → select or fix an issue. Farm preflight and submit paths follow the same constraint once the Farm tab ships (M26).
3. **Clarity** — Publish and Deadline blocking state must be visible in the panel summary without opening exported JSON. Health score, severity counts, and `block_publish` / `block_deadline` chips belong in persistent UI chrome, not only in report files.
4. **Delight** — Routine safe actions should not spam confirmation modals. Use consistent spacing, tooltips, non-blocking progress feedback, and deferred UI updates (existing Maya-safe patterns) so validation feels responsive during long scans.
5. **Parity** — The Maya panel and headless entrypoints must call `pipeline_inspector.maya.validation_pipeline` (and future `integrations/deadline` helpers) — never duplicate validation or preflight decision logic in UI-only code paths.

### Architectural layering

The dockable panel is the **primary product surface**. CLI, JSON/HTML reports, manifest export, apply-fixes, and Deadline hooks are **integration surfaces** that reuse the same core pipeline:

```text
Technical Artist / TD (primary)
  -> Maya dockable UI (tabs: Validate, Waivers, Fixes, Reports, Farm)
  -> ui_launcher callbacks
  -> validation_pipeline / integrations.deadline
  -> shared core (snapshot, rules, scoring, fix plan)

Pipeline automation (secondary)
  -> CLI / mayapy / Deadline job
  -> same validation_pipeline / integrations.deadline
  -> same reports and exit codes
```

### Non-goals for v0.4

The following are explicitly out of scope for this ADR and the v0.4.0 milestone:

- Rewriting the rule engine in C++ (native `.mll` remains a thin bootstrap per ADR 0006).
- AWS Deadline Cloud integration.
- Full visual redesign or a new QSS theme system.
- Replacing JSON rule authoring with a rule editor UI (roadmap v0.5+).

## Alternatives Considered

### 1. CLI-first / pipeline-first delivery

Pros:

- Faster for pipeline TDs to script and gate publish;
- no Qt/Maya UI testing burden for new features;
- aligns with headless farm and CI workflows.

Cons:

- Technical Artists defer to TDs for routine validate/fix flows;
- blocking state hidden in terminal output or JSON;
- GUI lags behind CLI, increasing parity bugs.

Rejected as the default product stance. CLI remains first-class but not primary.

### 2. Equal weight UI and CLI (no declared primary surface)

Pros:

- avoids perceived bias toward Technical Artists;
- both surfaces evolve in parallel.

Cons:

- no clear acceptance criterion when schedules conflict;
- duplicate affordances (panel buttons vs subcommands) without a tie-breaker;
- UX audit and Wave 1 improvements lack a governing principle.

Rejected.

### 3. GUI-first with mandatory panel affordance (accepted)

Pros:

- Technical Artists get farm, manifest, and fix workflows without leaving Maya;
- pipeline modules stay shared — panel is a thin controller;
- M22 UX audit and M28 Wave 1 have explicit P0 criteria (action bar, triage speed, farm status).

Cons:

- every feature needs UI design and mocked Qt tests;
- some studio-only automation may never need a button (acceptable — expose via CLI, document in integration guides).

Accepted.

## Consequences

### Positive

- v0.4 Farm tab, shelf shortcuts, and Deadline guides have a clear mandate before REST submit APIs are considered complete.
- UX audit (#092) and Wave 1 (#108–#109) can gate scope on P0 panel improvements rather than open-ended polish.
- Contributors know where to add new behavior: extend `validation_pipeline` or `integrations/`, then wire `ui_launcher` / `main_window`.
- Technical Artists see blocking state and farm eligibility without pipeline TD intervention.

### Negative / Tradeoffs

- Features that are purely batch-oriented still need a minimal panel status or link (for example, “last farm preflight” on the Farm tab) even when Technical Artists rarely click it.
- GUI work adds milestone time versus CLI-only shipping; parallel tracks (M24 native plugin, M25 Deadline core) must still reserve UI wiring in M26.
- “Three clicks” is a design guideline, not a hard automated test — manual checklist and UX audit capture compliance.

## Implementation Notes

Expected documentation and code touchpoints for v0.4:

```text
docs/adr/0005-gui-first-product-philosophy.md   # this ADR
docs/ARCHITECTURE.md                            # product surface diagram, status
docs/USER_GUIDE.md                              # Technical Artist-facing principles
docs/MAYA_UX_AUDIT_v0.4.md                      # friction inventory (#092)
src/pipeline_inspector/maya/ui_launcher.py           # panel callbacks (no duplicated validation)
src/pipeline_inspector/ui/main_window.py             # tabs, summary chrome, Farm tab (#101)
src/pipeline_inspector/maya/validation_pipeline.py   # single enrichment + validation path
src/pipeline_inspector/integrations/deadline/        # shared farm preflight/submit (#098–#100)
```

When adding a feature, use this checklist:

1. Does the panel expose the action or state? If not, add it or document why the feature is automation-only.
2. Does UI code call `validation_pipeline` (or the integration module), not reimplement checks?
3. Are `block_publish` and `block_deadline` visible in the summary after validate?
4. Are safe actions confirmable in one step; risky actions still gated per ADR 0003/0004?

## Related

- Issue: `#091 - ADR 0005 GUI-first product philosophy` (GitHub #119)
- Issue: `#092 - Maya UI/UX audit report + prioritized backlog` (GitHub #120)
- ADR: `0001-snapshot-first-core.md`
- ADR: `0003-safe-fix-reference-safety-policy.md`
- ADR: `0004-headless-apply-fixes-policy.md`
- ADR: `0006-native-mll-plugin-strategy.md`
- Document: `docs/ARCHITECTURE.md`
- Document: `docs/USER_GUIDE.md`
- Document: `docs/MAYA_UX_AUDIT_v0.4.md` (planned, #092)
- Document: `docs/V0_4_DEVELOPMENT_PLAN.md` (planned)
