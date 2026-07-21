# Maya Pipeline Inspector — Development Plan

> **Shipped:** v0.1.0 (2026-07-03) · v0.2.0 (2026-07-06) · v0.3.0 (2026-07-07) · v0.4.0 (2026-07-08) · v0.5.0 (2026-07-12) · **v0.6.0 (2026-07-21)**  
> **Next:** v0.7+ — deepen shipped subsystems (see [§14 Roadmap](#14-roadmap--strengthen-and-extend))  
> **Cycle plans:** [V0_6_DEVELOPMENT_PLAN.md](V0_6_DEVELOPMENT_PLAN.md) · [V0_5_DEVELOPMENT_PLAN.md](V0_5_DEVELOPMENT_PLAN.md) · [V0_3_DEVELOPMENT_PLAN.md](V0_3_DEVELOPMENT_PLAN.md) · [V0_2_DEVELOPMENT_PLAN.md](V0_2_DEVELOPMENT_PLAN.md)

**Project type:** Open-source Maya plug-in / pipeline QA framework (MIT)  
**Primary users:** Technical Artist, Shader TD, Pipeline TD, Render Supervisor  
**Primary DCC:** Autodesk Maya 2024–2026 (2023− untested)  
**Renderer rule packs:** Common Maya, V-Ray, Arnold (+ USD health rules for USD assets)  
**Core principle:** Snapshot-first validation, renderer adapters, data-driven JSON rules, safe fixes, GUI-first product surface ([ADR 0005](adr/0005-gui-first-product-philosophy.md))

**Companion docs:** [Wiki Home](wiki/Home.md) · [ARCHITECTURE.md](ARCHITECTURE.md) · [USER_GUIDE.md](USER_GUIDE.md) · [STUDIO_OVERRIDES.md](STUDIO_OVERRIDES.md) · [RULE_AUTHORING.md](RULE_AUTHORING.md) · [CHANGELOG.md](../CHANGELOG.md)

---

## How to read this document

| Section | Purpose |
| --- | --- |
| §1–§5 | Problem, goals, users, principles — stable product intent |
| §6–§7 | **Current reality** — what ships in v0.6.0 and known gaps |
| §8–§12 | Architecture and subsystem reference (implementation truth) |
| §13 | Release history and links to per-cycle GitHub plans |
| §14 | **Future work** — extend and harden existing functionality, not restart MVP |
| §15–§17 | Quality bar, risks, release discipline |
| Appendix | Historical milestone index (v0.1 bootstrap); technical deep-dives retained for rule/schema authors |

This plan **does not** describe a pre-release MVP anymore. v0.6.0 is a public MIT release with 1306+ automated tests, studio settings hub, farm integration, governance foundation, and geometry/readiness subsystems. Remaining gaps are documented honestly in [USER_GUIDE — Known limitations](USER_GUIDE.md#known-limitations--gaps).

---

## 1. Executive Summary

**Maya Pipeline Inspector** is a production-oriented **material and scene QA framework** for Maya. It scans shading networks, texture dependencies, renderer-specific material settings, displacement, UDIM sets, path policies, shader complexity, **geometry budgets**, and studio readiness **before** publish or Deadline submission.

The tool answers:

> Can this asset or shot be safely published or submitted to the render farm — and if not, what is broken, who owns the fix, how dangerous is it, and can it be fixed safely?

**What exists today (v0.6.0):**

- Pure-Python **core validator** testable without Maya (~1306 pytest cases).
- **Maya dockable panel** — Validate, Waivers, Reports, Readiness, Farm, Settings.
- **Headless CLI** — validate, manifest, gate, diff, apply-fixes, rules validate, farm-analytics.
- **Safe auto-fix queue** with reference protection, high-risk gates, fix audit trail.
- **Studio + user configuration** ([ADR 0007](adr/0007-settings-and-connectors-architecture.md)).
- **Connectors** — Telegram, Discord, Slack; Ftrack, ShotGrid, Cerebro; Bug Report relay; GitHub auto-update.
- **Deadline 10 on-prem** — Farm tab submit, preflight, farm analytics CLI.
- **Role governance** ([ADR 0008](adr/0008-role-based-governance-foundation.md)) and supervisor routing ([ADR 0009](adr/0009-report-to-supervisor-routing-by-role.md)).
- **Rule authoring MVP** — browser, wizard, incident-to-rule export.
- **Demo scenes** — `examples/vray_policy/`, `examples/arnold_policy/`.

**What we are building toward:** a **stable, extensible open-source QA layer** studios can adopt and extend — not a closed one-off checker. Future work **extends** validation domains, headless parity, connector reliability, and adapter coverage rather than replacing the architecture.

---

## 2. Production Problem

Feature animation and VFX productions accumulate hundreds of materials across characters, environments, props, FX, and shot overrides. Failures that reach the farm or comp are expensive:

| Failure class | Typical cost |
| --- | --- |
| Missing / stale textures | Black maps, rerenders, comp hold |
| Wrong color space on data maps | Wrong look, silent numeric drift |
| Broken UDIM sets | Tile gaps, partial renders |
| Local / user paths | Farm path failures |
| Displacement risk | Long frames, memory spikes |
| Shader graph complexity | Farm cost overrun |
| Duplicate materials / textures | Scene bloat, inconsistent look |
| **Geometry over budget (v0.6)** | Farm time, viewport pain |
| **Duplicate meshes (v0.6)** | Accidental double geometry |
| Renderer plugin mismatch | Blank or default shaders |
| Workstation not ready (v0.6) | Wasted publish/submit cycles |

Pipeline Inspector moves detection **left** — into the Technical Artist session and publish preflight — with explainable rules, waivers, reports, and optional safe fixes.

---

## 3. Product Goals and Scope Boundaries

### 3.1 Core goals (ongoing)

1. Detect material and scene QA failures before render time.
2. Keep validation **data-driven, explainable, and testable** without Maya for the core.
3. Support Common Maya, V-Ray, and Arnold through **renderer adapters**; extend via new packs.
4. Provide a fast **dockable Maya panel** as the primary surface ([ADR 0005](adr/0005-gui-first-product-philosophy.md)).
5. Provide **headless** validation for publish hooks, CI, and farm preflight.
6. Apply **safe auto-fixes** with preview, undo, reference protection, audit, and governance gates.
7. Produce JSON/HTML reports, manifests, diffs, and farm analytics for supervisors and TDs.
8. Remain **open-source and studio-extensible** (extra rules, profiles, connectors, relay).

### 3.2 In scope — deepen, don't restart

These are **shipped or partially shipped**; roadmap work **hardens and extends** them:

- Validation pipeline, rule schema, profiles, waivers, fix plan.
- Settings hub, studio config 2.0, user preferences, connectors registry.
- Farm tab + Deadline package + farm analytics CLI.
- Machine Readiness probes and Readiness tab.
- Geometry rules and `ShapeSnapshot` enrichment.
- PermissionResolver, capability matrix, supervisor routing.
- Rule browser / wizard / incident-to-rule workflow.
- Native `.mll` Phase 1 + Python plug-in fallback ([ADR 0006](adr/0006-native-mll-plugin-strategy.md)).

### 3.3 Out of scope (explicit non-goals)

- Full material conversion between renderers.
- Replacing ShotGrid, Ftrack, or Cerebro as production trackers.
- Real-time always-on scene monitoring.
- Renderer performance simulation or dollar-cost farm billing.
- Complete USD/MaterialX authoring tool (inspection/validation only).
- Automatic deletion of material networks without explicit user action.
- AWS Deadline Cloud as a drop-in replacement for on-prem Deadline 10 docs (separate integration track).

---

## 4. Target Users and Value

### 4.1 Technical Artist / Lookdev

**Needs:** fast self-QA, jump to bad nodes, understand rule rationale, safe fixes, avoid rejected publishes.

**Shipped value:** Validate Scene/Selection, issue details with graph trace, Safe Auto-Fix Queue, waivers, profiles (`artist_relaxed`, `publish_strict`), policy demo scenes.

**Next:** clearer compact UI, selection-scoped geometry budgets, guided fix workflows.

### 4.2 Shader TD

**Needs:** enforceable rule packs, studio overrides, incident-to-rule loop, manifest regression.

**Shipped value:** JSON rule packs, `pipeline_inspector rules validate`, rule editor MVP, studio `extra_rules`, V-Ray/Arnold policy packs, manifest diff + gate.

**Next:** richer rule editor, publish-DB texture freshness, weighted scoring profiles.

### 4.3 Render Supervisor

**Needs:** blocking summary, HTML reports, farm block visibility, team routing.

**Shipped value:** Health score, `block_publish` / `block_deadline`, HTML/JSON export, farm analytics CLI, role-based supervisor notifications ([ADR 0009](adr/0009-report-to-supervisor-routing-by-role.md)).

**Next:** trend dashboards from farm JSONL history, readiness escalation policies.

### 4.4 Pipeline TD

**Needs:** headless hooks, studio JSON, CI gates, Deadline integration, governance.

**Shipped value:** CLI validate/gate/apply-fixes, `--studio-config`, Maya CI smoke scripts, Farm tab submit, Readiness probe config, `PermissionResolver`, public bug-report relay spec.

**Next:** headless user-prefs parity, governance audit export, AWS Deadline Cloud analytics adapter.

---

## 5. Product Principles

1. **Snapshot-first.** Maya API → `GraphSnapshot` → pure validator → UI/CLI/reports share one pipeline.
2. **Renderer boundary.** Core rules stay renderer-agnostic; adapters supply enrichment and packs.
3. **Explain every issue.** `why`, owner, evidence, and fix preview are first-class.
4. **Safe mutation.** Reference-safe defaults; high-risk fixes gated by profile + governance.
5. **GUI-first, not GUI-only.** Panel is primary; CLI/farm/CI use the same modules ([ADR 0005](adr/0005-gui-first-product-philosophy.md)).
6. **Studio override without fork.** Profiles, extra rules, studio JSON, waivers — not core patches.
7. **Testable core.** 1306+ unit/fixture tests; Maya integration optional on self-hosted runners.
8. **Open extensibility.** Connectors registry, readiness probes, rule packs, ADRs for cross-cutting decisions.
9. **Honest limitations.** Gaps documented in USER_GUIDE; no false “production-complete” claims.

---

## 6. Shipped Capability Matrix (v0.6.0)

Legend: **Shipped** · **Partial** (works with documented gaps) · **Gap** (not implemented)

### 6.1 Validation engine

| Capability | Status | Notes |
| --- | --- | --- |
| GraphSnapshot model | Shipped | Materials, files, shapes, connections, enrichment fields |
| JSON rule engine + profiles | Shipped | Common, V-Ray, Arnold, USD health, studio naming |
| Asset-class overlays | Shipped | hero / prop / background polycount tiers |
| Geometry polycount rules | Shipped | `geometry_polycount.json`, scan scope aware |
| Duplicate geometry rules | Shipped | Scan budget + truncated evidence on large scenes |
| Texture path / missing / UDIM | Shipped | Core preflight domain |
| Color space / displacement / complexity | Shipped | Common + renderer packs |
| Texture freshness | Partial | Filesystem sibling versions only — no publish DB |
| Optimized `.tx` / tiled textures | Shipped | Detect/report; no maketx generation |
| Duplicate materials/textures | Shipped | |
| Health score | Shipped | Heuristic aggregate — not measured render cost |
| Waivers (sidecar JSON) | Shipped | Waiver manager UI |
| Manifest v1.1 + fingerprint | Shipped | |
| Manifest diff + regression gate | Shipped | CLI `gate`, UI compare shortcuts |
| USD asset validation path | Partial | Snapshot + rules; not full MaterialX authoring |

### 6.2 Safe fixes

| Capability | Status | Notes |
| --- | --- | --- |
| Fix types: set_attr, relink_path, normalize_path, disable_feature | Shipped | |
| Fix plan export (UI + CLI) | Shipped | |
| Headless apply-fixes | Shipped | [ADR 0004](adr/0004-headless-apply-fixes-policy.md) |
| Fix apply audit JSON | Shipped | |
| Reference / lock protection | Shipped | |
| High-risk confirmation + governance gate | Shipped | `PermissionResolver` |
| Texture / path rename fixes | Partial | Rule-dependent |

### 6.3 Maya panel

| Tab / area | Status | Notes |
| --- | --- | --- |
| Validate (scene / selection) | Shipped | Async job, filters, issue details, graph trace |
| Safe Auto-Fix Queue | Shipped | |
| Waivers | Shipped | |
| Reports (JSON/HTML/manifest/tracker) | Shipped | Send to Tracker |
| Readiness | Shipped | v0.6 — probe engine, Maya-only |
| Farm | Shipped | Deadline 10 on-prem submit + preflight |
| Settings hub | Shipped | Basic, Advanced, Studio Environment, Studio, Connectors, Bug Report, Support |
| Themes (Classic / Dark) | Shipped | User prefs |
| Check for Updates | Shipped | Module-path install + rollback |
| Rule browser / wizard | Partial | MVP — complex JSON still hand-edited |
| Native `.mll` bootstrap | Partial | Build locally; Python fallback always available |

### 6.4 Headless CLI

| Command | Status | Notes |
| --- | --- | --- |
| `validate` | Shipped | Scene, snapshot JSON, USD; `--studio-config` |
| `manifest` | Shipped | |
| `diff` | Shipped | JSON + HTML diff |
| `gate` | Shipped | Baseline manifest regression |
| `apply-fixes` | Shipped | `--dry-run`, governance flags |
| `rules validate` | Shipped | Rule pack QA |
| `farm-analytics` | Shipped | v0.6 — JSON/HTML/JSONL history |
| User preferences in CLI | Gap | Studio config only — panel may differ |
| Readiness CLI | Gap | Probes are Maya-session only |

### 6.5 Integrations

| Integration | Status | Notes |
| --- | --- | --- |
| Deadline 10 Web Service | Shipped | Config, client, Farm tab, preflight examples |
| Farm analytics tiers A–D | Shipped | See [deadline_farm_analytics.md](integrations/deadline_farm_analytics.md) |
| Telegram / Discord / Slack | Shipped | Dispatcher + Settings UI |
| Ftrack / ShotGrid / Cerebro publish | Shipped | Markdown notes; Cerebro no HTML upload |
| Tracker role discovery (Ftrack/Cerebro) | Shipped | Governance mapping |
| Bug Report HTTPS relay | Shipped | Public + studio private relay spec |
| GitHub Releases auto-update | Shipped | Zip asset contract |
| AWS Deadline Cloud | Gap | Separate from on-prem guide |
| Publish-database texture freshness | Gap | Planned extension |

### 6.6 Governance (v0.6)

| Capability | Status | Notes |
| --- | --- | --- |
| PermissionResolver + capability matrix | Shipped | [ADR 0008](adr/0008-role-based-governance-foundation.md) |
| Supervisor routing by role | Shipped | [ADR 0009](adr/0009-report-to-supervisor-routing-by-role.md) |
| Settings governance UI | Shipped | |
| Self-reported user role | Partial | Unless `governance.enforced_role` |
| Compliance audit log export | Gap | Deny reasons in UI only |

---

## 7. Product Surfaces and Workflows

### 7.1 Primary surface — dockable panel

```text
Pipeline Inspector panel
├── Validate      — scan, triage, fix queue, export
├── Waivers       — sidecar waiver manager
├── Reports       — JSON/HTML/manifest, Send to Tracker
├── Readiness     — workstation probes (v0.6)
├── Farm          — Deadline check + submit
└── Settings      — gear overlay: Basic, Advanced, Studio Environment,
                    Studio policy, Connectors, Bug Report, Support
```

All validation paths call `maya.validation_pipeline` → core engine. Widgets do not fork rule evaluation ([ARCHITECTURE.md](ARCHITECTURE.md)).

### 7.2 Integration surfaces

```text
mayapy / CLI  ──► validation_pipeline ──► core
Deadline hook / Farm tab ──► integrations.deadline ──► validation_pipeline
farm-analytics CLI ──► integrations.deadline (read-only analytics)
Notifications ──► integrations.notify.dispatcher
Trackers ──► integrations.{ftrack,shotgrid,cerebro}
Bug Report ──► integrations.bug_report.relay_client
```

### 7.3 Headless vs panel parity (honest matrix)

| Concern | Panel | Headless CLI |
| --- | :---: | :---: |
| Studio config | ✓ | ✓ (`--studio-config`, env) |
| User preferences | ✓ | ✗ |
| Role / governance resolution | ✓ | Partial |
| Validate / gate / apply-fixes | ✓ | ✓ |
| Readiness probes | ✓ | ✗ |
| Connectors (notify/tracker) | ✓ | Partial (scripted) |
| Rule session overrides | ✓ (non-persistent) | ✗ |

Closing this matrix is a **primary v0.7 theme** (see §14.2).

---

## 8. Architecture Overview

High-level data flow (unchanged strategic design, now fully implemented):

```text
Maya scene / USD asset
  → scanner + snapshot_enrichment
  → GraphSnapshot
  → renderer adapter resolution
  → rule pack + profile + asset class
  → core validator + waivers
  → RuleResult list + health score + fix plan
  → panel / CLI / reports / Deadline / notifications
```

**Layer map:**

| Layer | Location | Role |
| --- | --- | --- |
| Core | `src/pipeline_inspector/core/` | Models, rules, validator, scoring, fix plan, governance, manifest |
| Maya | `src/pipeline_inspector/maya/` | Scanner, enrichment, validation_pipeline, fix_applier, ui_launcher |
| UI | `src/pipeline_inspector/ui/` | Panel, Settings, Readiness, Farm, update wizard |
| Integrations | `src/pipeline_inspector/integrations/` | Deadline, notify, trackers, bug report, update, readiness |
| Adapters | `src/pipeline_inspector/adapters/` | common_maya, vray, arnold |
| USD | `src/pipeline_inspector/usd/` | USD scan/enrichment/fix path (partial) |

Full diagrams, ADR index, and package layout: [ARCHITECTURE.md](ARCHITECTURE.md).

---

## 9. Core Subsystems (current implementation)

### 9.1 Validation pipeline

Entry points: `run_validation_for_user` (panel), CLI `validate`, Farm preflight, manifest export context.

Pipeline stages: scan → enrich → load rules (packaged + studio extra + session) → evaluate → apply waivers → score → fix plan → persist session state on panel content.

**Scan scopes:** `scene`, `selection` — affect geometry and duplicate scans.

### 9.2 Rules and profiles

**Packaged rule roots:**

```text
src/pipeline_inspector/rules/
├── common/          # texture, UDIM, paths, complexity, geometry, duplicates, …
├── vray/            # renderer_health, …
├── arnold/          # renderer_health, …
├── usd/             # usd_health
├── studio/          # naming (studio overlay example)
└── profiles/        # publish_strict, deadline_critical, ci_headless, asset_class_*, …
```

Authoring guide: [RULE_AUTHORING.md](RULE_AUTHORING.md). CLI QA: `pipeline_inspector rules validate`.

### 9.3 Manifest, diff, and gates

- Manifest schema **1.1** with graph fingerprint.
- `pipeline_inspector gate` for publish/CI regression against approved baseline.
- UI: Compare to Approved Manifest; CLI: `diff` with HTML output.

### 9.4 Settings and connectors ([ADR 0007](adr/0007-settings-and-connectors-architecture.md))

Two-layer config:

| Layer | File | Loaded in |
| --- | --- | --- |
| Studio | `pipeline_inspector_studio.json` | Panel + headless |
| User | `pipeline_inspector_user.json` | Panel only |

Connectors registry wires Deadline, notify channels, trackers, bug report, updates. Deploy guide: [STUDIO_OVERRIDES.md](STUDIO_OVERRIDES.md).

### 9.5 Geometry QA (v0.6)

- `ShapeSnapshot` on `GraphSnapshot`; Maya scanner fills polycount / mesh identity.
- Rules: `geometry_polycount.json`, `duplicate_geometry.json`.
- Profiles: `asset_class_hero`, `asset_class_prop`, `asset_class_background`.
- Large-scene duplicate scan honors budget with explicit truncation evidence.

### 9.6 Machine Readiness (v0.6)

- Config: `studio_config.readiness.checks`.
- Engine: `integrations/readiness/engine.py` + injectable probes.
- UI: Readiness tab; optional notify escalation.
- Does **not** mutate scenes.

### 9.7 Role governance (v0.6)

- `core/governance.py` — `PermissionResolver`, capability matrix.
- Gates: risky fixes, farm submit, extra rules, studio settings save, connector edit.
- Tracker role mapping: env + Ftrack/Cerebro discovery + `tracker_role_map`.
- Supervisor routes: `supervisor_routes` per reporter role.

### 9.8 Deadline and farm intelligence

- **Operational:** Farm tab, job submit, preflight CommandScript examples.
- **Analytics (v0.6):** `farm-analytics` CLI — throughput, failure rate, pool utilization, tier A–D breakdowns, optional JSONL history.
- Guide: [deadline_farm_analytics.md](integrations/deadline_farm_analytics.md).

### 9.9 Notifications and trackers

- Dispatcher routes validation/readiness/farm events to enabled connectors.
- Reports tab **Send to Tracker** publishes summary + optional HTML attachment (tracker-dependent).
- Slack thread context enrichment from tracker metadata (v0.5+).

### 9.10 Rule authoring and incident workflow

- Rule browser + safe field editor; New Rule Wizard from templates.
- Issue details → create rule draft → export to studio `extra_rules`.
- Session rule overrides from editor **do not persist** across restarts (known gap).

### 9.11 Auto-update

- GitHub Releases client; semver compare; module-path install with rollback backup.
- Expects release asset `maya-pipeline-inspector-<version>.zip`.
- Guide: [auto_update.md](integrations/auto_update.md).

---

## 10. Data Model and Rule Schema (reference)

Detailed field lists remain stable; see [ARCHITECTURE.md](ARCHITECTURE.md) and `core/models.py`, `core/rule_schema.py`.

**Key types:** `GraphSnapshot`, `NodeSnapshot`, `ShapeSnapshot`, `MaterialSnapshot`, `FileDependencySnapshot`, `RuleResult`, `FixAction`, `HealthScore`, manifest types, readiness probe results.

**Rule concepts:** severity, `block_publish`, `block_deadline`, owner, `why`, evidence dict, fix descriptor, scope (`material`, `geometry`, …), check types registered in `rule_schema.py`.

Rule types in active production packs include: missing texture, path policy, UDIM integrity, color space, displacement risk, shader complexity, optimized texture, duplicate material/texture, renderer health, geometry polycount, duplicate geometry, naming (studio).

---

## 11. Renderer Adapters

| Adapter | Status | Enrichment / rules |
| --- | --- | --- |
| `common_maya` | Shipped | Baseline material/file graph |
| `vray` | Shipped | V-Ray scene + material policy pack |
| `arnold` | Shipped | Arnold scene + material policy pack |
| USD | Partial | USD scan path + `usd_health` rules |
| RenderMan | Gap | Future adapter |
| Redshift | Gap | Future adapter |

Adapter boundary: [ADR 0002](adr/0002-renderer-adapter-boundary.md). Contribution: [CONTRIBUTING.md](../CONTRIBUTING.md#renderer-adapter-contribution-guidelines).

---

## 12. Testing Strategy

### 12.1 Test pyramid (current)

```text
Unit + snapshot fixtures (no Maya): ~95%  — 1306+ tests, default CI
Maya integration smoke:              ~4%   — self-hosted runner, optional
Manual Maya release checklist:       ~1%   — V0_6_RELEASE.md, MAYA_V02_MANUAL_CHECKLIST
```

### 12.2 What CI runs today

- `pytest tests` on GitHub Actions (Linux/Windows).
- `ruff`, `mypy` on `src/pipeline_inspector`.
- Snapshot validation CLI smoke on fixture JSON.
- Maya integration workflow: `workflow_dispatch` on self-hosted runner with `mayapy`.

### 12.3 Fixture layout

```text
tests/fixtures/snapshots/   # GraphSnapshot JSON + expectation sidecars
examples/vray_policy/       # Live Maya demo + checked-in HTML reports
examples/arnold_policy/     # Live Maya demo + checked-in HTML reports
```

### 12.4 Definition of done (feature)

A feature is **done** when:

- core/model/schema updated if needed;
- unit tests + fixture coverage added;
- panel **or** CLI exposes the behavior on the shared pipeline;
- reports include new issue types;
- severity/block policy configurable via profiles;
- reference-safe / governance behavior verified;
- USER_GUIDE or integration doc updated;
- known limitations not hidden.

---

## 13. Release History and Cycle Plans

| Tag | Date | Theme | Plan doc |
| --- | --- | --- | --- |
| v0.1.0 | 2026-07-03 | Core MVP / public POC | [Appendix A](#appendix-a--historical-github-milestones-v01-bootstrap) (M0–M8) |
| v0.2.0 | 2026-07-06 | Safe fixes, renderer packs, manifest diff | [V0_2_DEVELOPMENT_PLAN.md](V0_2_DEVELOPMENT_PLAN.md) |
| v0.3.0 | 2026-07-07 | Manifest gates, headless apply-fixes | [V0_3_DEVELOPMENT_PLAN.md](V0_3_DEVELOPMENT_PLAN.md) |
| v0.4.0 | 2026-07-08 | GUI-first, Deadline Farm tab, native `.mll` Phase 1 | [V0_4_RELEASE.md](V0_4_RELEASE.md) |
| v0.5.0 | 2026-07-12 | Settings hub, connectors, rule authoring, auto-update | [V0_5_DEVELOPMENT_PLAN.md](V0_5_DEVELOPMENT_PLAN.md) |
| **v0.6.0** | **2026-07-21** | **Geometry, Readiness, governance, farm analytics, MIT public release** | [V0_6_DEVELOPMENT_PLAN.md](V0_6_DEVELOPMENT_PLAN.md) |

Release playbook (tag, GitHub Release, zip asset): [V0_6_RELEASE.md](V0_6_RELEASE.md).

---

## 14. Roadmap — Strengthen and Extend

Future work **builds on shipped subsystems**. We do not replan MVP from scratch.

### 14.1 Guiding themes (v0.7 → v1.0)

1. **Parity** — headless CLI matches panel for prefs, governance, and readiness where safe.
2. **Depth** — geometry, USD, farm analytics, scoring, and adapters gain production-grade edge cases.
3. **Reliability** — connectors, probes, and governance auditable and observable.
4. **Stability** — semver for rule schema and adapter API; v1.0 doc + API freeze candidacy.

### 14.2 v0.7 — Headless parity and governance hardening

**Goal:** Pipeline TDs get the same policy enforcement in CI/farm scripts as Technical Artists see in the panel.

| Workstream | Extend |
| --- | --- |
| CLI user prefs | Load `pipeline_inspector_user.json` optionally in headless; document precedence vs studio |
| Governance in CLI | Unified `PermissionResolver` path for `apply-fixes`, `--extra-rules`, farm submit scripts |
| Governance audit | Export deny/allow decisions to JSONL for supervisor review |
| Readiness headless | `pipeline_inspector readiness` subcommand with injectable probes for farm worker images |
| Connector delivery status | Surface last notify/tracker errors in Settings + Reports status |
| Rule editor persistence | Optional save session overrides to user or studio draft path |

**Exit criteria:** documented parity matrix (§7.3) with no red rows for governance; 1400+ tests; ADR update if CLI prefs change security model.

### 14.3 v0.8 — Geometry, USD, and validation depth

**Goal:** Expand scene QA beyond materials without breaking snapshot-first design.

| Workstream | Extend |
| --- | --- |
| Geometry | Per-LODG group budgets; instancing-aware duplicate detection; render stats enrichment |
| USD / MaterialX | Full USD stage validation path; MaterialX binding checks; navigation parity in panel |
| Scan performance | Incremental scan cache (fingerprint-based invalidation) for large scenes |
| Scoring | Weighted health score profiles; separate farm-cost score tuning |
| Texture freshness | Optional publish-database / tracker API hook (studio plugin interface) |
| Adapters | RenderMan adapter spike; Redshift adapter spike behind feature flag |

**Exit criteria:** USD fixture suite in CI; cache hit/miss tests; hero-asset geometry regression fixture.

### 14.4 v0.9 — Farm intelligence and connector reliability

**Goal:** Supervisors and wranglers run Pipeline Inspector as an operational layer, not only preflight.

| Workstream | Extend |
| --- | --- |
| Farm analytics | Scheduled JSONL aggregation; shot/pass trend HTML dashboard template |
| Deadline Cloud | Read-only analytics adapter parallel to on-prem Web Service |
| Farm tab | Post-submit job monitor polish; validation job result HTML attach to notify |
| Trackers | Richer publish payloads; retry/backoff; connector health self-test in Readiness |
| Notifications | Template library per event type; webhook signing options |
| Bug report | Rate-limit telemetry; studio relay HA notes |

**Exit criteria:** farm analytics history example in `examples/`; connector health probes in default studio template.

### 14.5 v1.0 — Stable public framework

**Goal:** Studio-ready **open-source QA framework** with explicit stability promises.

| Workstream | Deliver |
| --- | --- |
| API stability | Document semver for rule schema, manifest schema, connector config |
| Adapter API | Formal adapter protocol doc + conformance test kit |
| Documentation | Certified doc set: install, studio deploy, every connector, every CLI command |
| Demo package | Curated demo scenes + expected issue counts in CI fixture form where possible |
| Release discipline | Signed tags, attached `.mll` matrix, migration notes between minors |
| Community | Contributor onboarding, example rule packs, early-adopter list in COMMUNITY.md |

**Exit criteria:** v1.0.0 tag; no P0 gaps in USER_GUIDE limitations for declared supported workflows; 1500+ tests.

### 14.6 Longer horizon (post–v1.0)

- Lookdev regression thumbnails tied to manifest fingerprint.
- Optional maketx / texture optimization fixes (opt-in, studio-driven).
- Cross-DCC snapshot interchange (read-only inspection, not authoring).
- Background incremental validation on scene idle (explicit opt-in; ADR required).

---

## 15. Technical Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Maya scan cost on huge scenes | Slow panel | Selection scope, geometry/duplicate budgets, incremental cache (v0.8) |
| Headless/panel policy drift | CI false confidence | v0.7 parity program; document matrix §7.3 |
| Connector secrets in studio JSON | Leak | ADR 0007 patterns; env substitution; never log tokens |
| Governance self-report bypass | Wrong farm submit | `enforced_role`, tracker role map, studio policy review |
| Rule schema drift | Studio pack breaks | `rules validate` in CI; semver in v1.0 |
| False positives erode trust | Waivers abuse | Evidence fields, waiver manager, supervisor profiles |
| Native `.mll` vs Python drift | Version mismatch | Single `version.py`; CMake sync at release |

---

## 16. Release Checklist (summary)

Full steps: [V0_6_RELEASE.md](V0_6_RELEASE.md).

1. `pytest` / `ruff` / `mypy` green.
2. Version bump in `version.py`, `pyproject.toml`, `test_import.py`, fallback plug-in, native CMake.
3. CHANGELOG + README + this plan §13/§14 review.
4. Maya manual smoke (policy demo scene, Readiness, Farm, governance).
5. Merge `dev` → `main`; annotated tag `v0.6.x`; GitHub Release + zip asset.

---

## 17. README and Positioning

Public README states:

- **Open-source MIT** material/scene QA for Maya pipelines.
- **v0.6.0 shipped** with honest MVP-quality caveats for connectors and governance.
- Community paths: [COMMUNITY.md](../COMMUNITY.md), CONTRIBUTING, issue templates.

Narrative: *scan → diagnose → explain → fix safely → report → block bad submissions* — implemented end-to-end, with documented gaps rather than aspirational bullet lists.

---

## Appendix A — Historical GitHub Milestones (v0.1 bootstrap)

The original v0.1 implementation plan (Milestones 0–8, Issues #1–#48) bootstrapped the repository. Detailed issue acceptance criteria live in git history and early milestones; **do not use** that checklist for current work.

| Milestone | Theme |
| --- | --- |
| M0 | Project bootstrap |
| M1 | Core validation engine |
| M2 | Maya scanner |
| M3 | Renderer adapters |
| M4 | Production rules MVP |
| M5 | Reports and manifest |
| M6 | Maya UI MVP |
| M7 | Safe fixes, waivers, integration |
| M8 | Demo and v0.1 release |

v0.2–v0.6 delivery is tracked in per-cycle plan documents (§13).

---

## Appendix B — Technical deep-dives (rule authors)

The following topics retain detailed specifications useful when authoring rules or extending the engine. Implementation status is **shipped** unless marked Partial/Gap in §6.

### B.1 Validation domains (summary)

| Domain | Module / rules | Status |
| --- | --- | --- |
| Texture path policy | `common/texture_paths.json` | Shipped |
| Texture freshness | `common/texture_freshness.json` | Partial |
| UDIM integrity | `common/udim_integrity.json` | Shipped |
| Color space | `common/color_space.json` | Shipped |
| Displacement risk | `common/displacement_common.json` + renderer packs | Shipped |
| Shader complexity | `common/shader_complexity.json` | Shipped |
| Optimized textures | `common/optimized_textures.json` | Shipped |
| Duplicate materials/textures | `common/duplicate_*.json` | Shipped |
| Geometry polycount | `common/geometry_polycount.json` | Shipped |
| Duplicate geometry | `common/duplicate_geometry.json` | Shipped |
| Renderer health | `vray/`, `arnold/` packs | Shipped |

### B.2 Preflight profiles

Packaged profiles include: `artist_relaxed`, `publish_strict`, `deadline_critical`, `supervisor_full`, `ci_headless`, asset-class overlays. Profiles control enabled rules, severities, block flags, and manifest diff policy — not separate code paths.

### B.3 Safe fix types

`set_attr`, `relink_path`, `normalize_path`, `disable_feature` — applied through `fix_applier` with undo chunks, reference checks, and fix audit JSON. High-risk fixes require capability + confirmation.

### B.4 External references

- Maya Python API 2.0 — DAG/DG traversal, plugs, function sets.
- Maya `workspaceControl` — dockable panel hosting.
- OpenImageIO — texture metadata where available.
- V-Ray / Arnold for Maya — node and color management specifics.
- Deadline 10 Web Service — farm submit and analytics GET endpoints.

---

*Last updated for v0.6.0 release prep (#186 / #232).*
