# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-07-08

**Maya Shader Health Inspector v0.4 — GUI-First Farm Integration & Render Risk Depth**

Extends v0.3 with Deadline 10 on-prem integration (core package + Farm tab), native `.mll` plugin Phase 1, Maya integration CI activation, expanded render-risk rules, and UX Wave 1 (settings screen, studio config, Connectors).

### Added

#### Product philosophy and UX audit (M22)

- [ADR 0005](docs/adr/0005-gui-first-product-philosophy.md) — GUI-first product philosophy for artist-facing workflows.
- [`docs/MAYA_UX_AUDIT_v0.4.md`](docs/MAYA_UX_AUDIT_v0.4.md) — friction inventory and prioritized Wave 1 backlog.

#### Maya integration CI (M23)

- Self-hosted Maya CI smoke path: `tools/ci/resolve_mayapy.py`, `tools/ci/maya_integration_checks.py`.
- GitHub Actions `workflow_dispatch` job validates scene export, manifest 1.1, gate, and Deadline preflight smoke steps.

#### Native Maya plugin Phase 1 (M24)

- [ADR 0006](docs/adr/0006-native-mll-plugin-strategy.md) — thin C++ `.mll` delegates to Python; `.py` plug-in fallback retained.
- CMake scaffolding under `native/`; versioned plug-in output paths in `.gitignore`.

#### Deadline 10 integration core (M25)

- Package `shader_health.integrations.deadline`: `DeadlineConfig`, `DeadlineClient`, preflight, eligibility gate, CommandScript submit API.
- [`docs/integrations/deadline_submit_preflight.md`](docs/integrations/deadline_submit_preflight.md) — studio guide (Web Service, pool/group, GUI + headless).
- Example scripts: `examples/deadline/submit_preflight.py`, `submit_to_farm.py`, `shader_health_deadline_validate.py`.

#### Deadline GUI & Farm tab (M26)

- **Farm** tab: connection lamp (Online/Offline), scene readiness, eligibility, preflight and submit actions.
- Menu + shelf **Shader Health Farm Check** — opens Farm tab and runs `deadline_critical` preflight.

#### Render risk & optimization depth (M27)

- Displacement enrichment and expanded displacement-risk rules with fixture coverage.
- Optimized texture / `.tx` derivative rules (`common.texture.optimized.*`) with snapshot enrichment.
- Duplicate material / duplicate texture detection rules and integration fixtures.

#### UX Wave 1 & studio settings (M28)

- Settings screen (gear icon): **Basic / Advanced / Connectors / Studio** tabs with persistent panel header.
- Studio config file `shader_health_studio.json`: **Require .tx** pipeline toggle; **Thinkbox Deadline** connector with **Remote Farm** ON/OFF.
- Connectors ↔ Farm tab linkage: disabled connector forces Farm **Offline** and disables farm actions.
- Issue Details layout polish (splitter persistence, borderless scroll, stable panel width).
- Issue triage: double-click row selects node; fix queue and export action wiring tests expanded.

### Changed

- Demo scene report/manifest samples refreshed for v0.4 rule packs (committed HTML/JSON/manifest only).
- Farm tab status messaging distinguishes integration disabled vs Web Service unreachable.

### Fixed

- Removed accidental commit of local demo artifacts (fix audit sidecar, `*_fixed.ma`, manifest diff exports, Deadline command aux files).
- Removed temporary debug-session logging from settings UI and CI helper scripts.

### Known limitations (v0.4)

- Native `.mll` binaries are built locally or attached to releases; repository ships CMake scaffolding and Python fallback only.
- Deadline connector settings are Maya UI / studio JSON today — headless `shader_health validate` does not yet accept `--studio-config`.
- Public CI still requires a self-hosted runner with `mayapy` for Maya integration smoke.
- Rule authoring remains JSON-only (no rule editor UI).

### Install

Same as v0.3 — see [`docs/MAYA_INSTALL.md`](docs/MAYA_INSTALL.md) and [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md).

**Planning for v0.5+:** [DEVELOPMENT_PLAN.md §27](docs/DEVELOPMENT_PLAN.md).

## [0.3.0] - 2026-07-07

**Maya Shader Health Inspector v0.3 — Pipeline Automation & Manifest Depth**

Extends v0.2 with manifest schema 1.1, graph fingerprinting, manifest regression gates, headless `apply-fixes`, texture resolution budgets by asset class, and Maya plugin dual-install.

### Added

#### Plugin and install (M15)

- Python MPx plugin stub (`shader_health_inspector.py`) with dual install path (plugin + module bootstrap).
- [`docs/MAYA_INSTALL.md`](docs/MAYA_INSTALL.md) — Plug-in Manager vs module-only policy and `autoLoad` studio guidance.

#### Manifest fingerprint and schema 1.1 (M16)

- Material graph fingerprint algorithm for deterministic passport hashing.
- `build_shader_manifest()` extended for schema **1.1** (`manifest_schema_version`, fingerprints, enrichment metadata).
- Manifest schema 1.1 migration notes in [`docs/SNAPSHOT_SCHEMA.md`](docs/SNAPSHOT_SCHEMA.md).
- Manifest diff fingerprint regression hints in diff reports.

#### Manifest gates and preflight (M17)

- Profile `manifest_diff_policy` overrides per workflow profile.
- `shader_health gate` CLI and `validate --baseline-manifest` regression evaluation.
- Publish preflight optional manifest gate in [`examples/publish/submit_preflight.py`](examples/publish/submit_preflight.py).

#### Headless apply-fixes (M18)

- [ADR 0004](docs/adr/0004-headless-apply-fixes-policy.md) — headless apply-fixes policy.
- `shader_health apply-fixes` subcommand with `--dry-run`, `--confirm-risky`, and supervisor policy flags.
- Fix apply audit integration and documented exit codes.

#### Texture resolution budgets (M19)

- Texture dimension metadata enrichment (including lightweight OpenEXR header probe).
- Resolution budget rules: `asset_class_hero`, `asset_class_prop`, `asset_class_background` profile overlays.
- Asset class dropdown in Maya UI; `--asset-class-id` on headless `validate`, `gate`, `manifest`, and `apply-fixes`.

#### Pipeline UX and automation polish (M20)

- **Compare to Approved Manifest** UI shortcut (sidecar-first, no file picker).
- `shader_health manifest` headless CLI subcommand.
- Maya CI manifest export + gate smoke in [`.github/workflows/maya-integration.yml`](.github/workflows/maya-integration.yml) (`workflow_dispatch`).
- Maya UI: **Publish Preflight**, **Manifest Gate**, tabbed panel layout polish.
- [`docs/CLI_TESTING.md`](docs/CLI_TESTING.md) and [`tools/compare_parity.py`](tools/compare_parity.py) for GUI↔CLI parity smoke.
- `shader_health.util.paths` — `normalize_cli_path()` / `resolve_cli_path()` for Git Bash MSYS paths on Windows.
- Headless demo scene: `examples/broken_scene/shader_health_demo_broken_headless.ma`.

### Fixed

- `mayapy` scene commands call `maya.standalone.initialize()` before `cmds.file` (fixes `maya.cmds has no attribute 'file'`).
- `ci_headless` accepted as standalone pipeline profile in `compose_profiles()`.
- GUI Export Shader Manifest uses shared `build_shader_manifest()` path (schema 1.1 parity with CLI).

### Known limitations (v0.3)

- Texture resolution probing is filesystem/header-based (no render-farm TX cache integration).
- `cleanup_orphan` auto-delete remains preview-only per ADR 0003.
- Public CI runs without Maya; optional `workflow_dispatch` Maya job only.
- Rule authoring remains JSON-only (no rule editor UI).

### Install

Same as v0.2 — see [`docs/MAYA_INSTALL.md`](docs/MAYA_INSTALL.md) and [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md).

**Planning for v0.4+:** [DEVELOPMENT_PLAN.md §27](docs/DEVELOPMENT_PLAN.md), [V0_3_DEVELOPMENT_PLAN.md](docs/V0_3_DEVELOPMENT_PLAN.md) (completed).

## [0.2.0] - 2026-07-06

**Maya Shader Health Inspector v0.2 — Production Hardening & Studio Readiness**

Extends v0.1 with production-grade safe fixes, V-Ray/Arnold policy packs, supervisor change review, pipeline integration docs, and waiver/fix UX polish.

### Added

#### Safe fixes and audit

- `relink_path`, `normalize_path`, and `disable_feature` fix appliers with undo-chunk apply.
- Fix apply audit log (`*.shader_health_fix_audit.json`) with JSON round-trip tests.
- **Export Fix Plan** from Maya UI and headless CLI.
- Rule packs expose `normalize_path` / `relink_path` / `disable_feature` fixes (not only `set_attr`).

#### Renderer policy packs

- V-Ray and Arnold snapshot enrichment (`vray_metadata`, `arnold_metadata`, scene plugin detection).
- Production policy rules: plugin missing, displacement review, texture budget, trace depth (V-Ray and Arnold packs).
- Renderer policy fixture tests in `tests/fixtures/snapshots/`.

#### Change review and manifests

- HTML manifest diff report template.
- `shader_health diff` CLI subcommand.
- **Export Manifest Diff** from Maya UI (baseline picker + JSON/HTML output).

#### Pipeline integration and studio docs

- Publish preflight hook example ([`examples/publish/submit_preflight.py`](examples/publish/submit_preflight.py)) and [integration guide](docs/integrations/publish_submit_preflight.md).
- Maya install guide ([`docs/MAYA_INSTALL.md`](docs/MAYA_INSTALL.md)).
- Studio overrides guide ([`docs/STUDIO_OVERRIDES.md`](docs/STUDIO_OVERRIDES.md)) with `examples/studio/` sample pack.
- Optional Maya integration GitHub Actions workflow (`.github/workflows/maya-integration.yml`, `workflow_dispatch` only).
- Manual Maya verification checklist ([`docs/MAYA_V02_MANUAL_CHECKLIST.md`](docs/MAYA_V02_MANUAL_CHECKLIST.md)).

#### Maya UI (v0.2)

- Waiver manager UI with sidecar revoke and expiry display.
- High-risk fix confirmation: per-fix dialog for strict profiles, batch confirm for `supervisor_full`.
- Safe Auto-Fix Queue **Select** toggle buttons (replacing YES/NO cells).
- Issue filters on one horizontal row; Issue Details show reference-safety status.
- Referenced-node fixes apply in the current scene as Maya reference edits (when not locked).

### Changed

- `normalize_path` resolves local checkout paths via detected project root (`src/shader_health/`) and maps standalone user paths to `${ASSET_ROOT}/textures/<filename>`.
- Fix queue apply matches actions by `fix_id`; blocked selections show explicit description messages.
- Reconciled long-term roadmap in [DEVELOPMENT_PLAN.md §27](docs/DEVELOPMENT_PLAN.md); Milestones 10–14 indexed in §26.

### Improved

- Texture version freshness (`common.texture.version.latest`): edge cases for sibling folders, single-version folders, and missing `v###` tokens; pass/fail fixtures and USER_GUIDE documentation.

### Known limitations (v0.2)

- Texture version detection remains filesystem-based (no publish DB / AMS integration).
- Public CI runs without Maya; optional `workflow_dispatch` Maya job only.
- Missing texture files cannot be auto-relinked without a known target path.
- Rule authoring remains JSON-only (no rule editor UI).

### Install

Same as v0.1 — see [`docs/MAYA_INSTALL.md`](docs/MAYA_INSTALL.md) and [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md).

**Planning for v0.3+:** [DEVELOPMENT_PLAN.md §27](docs/DEVELOPMENT_PLAN.md), [V0_2_DEVELOPMENT_PLAN.md](docs/V0_2_DEVELOPMENT_PLAN.md) (completed).

## [0.1.0] - 2026-07-03

**Maya Shader Health Inspector v0.1 — Texture & Shader Preflight MVP**

First public proof-of-concept release. Validates material and texture health in Maya before publish or render-farm submission, with a snapshot-first architecture shared by the dockable UI and headless CLI.

### Added

#### Core validation

- `GraphSnapshot` data model and Maya scene scanner.
- JSON rule schema, rule loader, and pure-Python validation engine.
- Snapshot enrichment (semantic texture slots, UDIM metadata, material index).
- Material health score and severity summary with publish/deadline block flags.
- Packaged rule packs: Common Maya, V-Ray, and Arnold (basic info-audit rules).
- Five validation profiles: `artist_relaxed`, `publish_strict`, `deadline_critical`, `supervisor_full`, `ci_headless`.
- Waiver sidecar support (`*.shader_health_waivers.json`).

#### Checks (v0.1)

- Missing texture files and unsafe/local path policy.
- Stale texture version naming.
- Broken UDIM tile sets.
- Wrong color space on data maps (with safe auto-fix where allowed).
- Displacement risk and shader graph complexity budgets.
- Duplicate textures and orphan/default material network hygiene.

#### Maya UI

- Dockable **Shader Health Inspector** panel (menu + shelf entry).
- **Validate Scene** and **Validate Selection** with profile dropdown.
- Issue table with severity, owner, and blocking/auto-fix filters.
- Issue details: what/why/current/expected, graph trace, waive action.
- Navigation: **Select Node**, **Open in Hypershade** (input/output connections), **Copy Path**, **Reveal File**.
- **Safe Auto-Fix Queue** with YES/NO selection, preview, and undoable apply.
- Scene reset when opening or creating a new scene.

#### Reports and pipeline integration

- Deterministic JSON validation reports.
- Self-contained HTML reports (full-width layout, collapsible severity groups).
- Shader manifest export and manifest diff tooling.
- Headless CLI: `python -m shader_health validate …`
- Deadline submit preflight example (`examples/deadline/`).

#### Demo and documentation

- Broken demo scene: `examples/broken_scene/shader_health_demo_broken.ma`
- Sample JSON/HTML/manifest artifacts in the demo folder.
- README with UI, HTML report, and safe-fix GIF captures.
- User guide, architecture notes, rule authoring guide, snapshot schema, ADRs.

#### Testing and CI

- Unit test suite for rules, engine, reports, Maya UI wiring (mocked), and fix planning.
- Integration tests for the shared validation pipeline, headless CLI, and renderer rule packs.
- GitHub Actions: pytest (Python 3.9–3.13), Ruff, mypy, and `tools/validate_rules.py`.

### Known limitations (v0.1)

- V-Ray and Arnold coverage is MVP-level (info-audit rules), not full renderer policy packs.
- Public CI runs without Autodesk Maya; Maya behavior is validated locally.
- No rule authoring UI; rules are JSON-only.
- No background incremental scan cache.

### Install

```bash
git clone https://github.com/armasonix/maya-shader-health-inspector.git
cd maya-shader-health-inspector
python -m pip install -e ".[dev]"
```

In Maya, add the repo to `MAYA_MODULE_PATH` or install the package into the Maya Python environment. See [`docs/MAYA_INSTALL.md`](docs/MAYA_INSTALL.md) for the full guide.

Quick manual session setup:

```python
from shader_health.maya.commands import install_ui, show_ui
install_ui()
show_ui()
```

See [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) for the full workflow.

**Next release planning:** [docs/V0_2_DEVELOPMENT_PLAN.md](docs/V0_2_DEVELOPMENT_PLAN.md) (Milestones 10–14, Issues #049–#070).

### Headless example

```bash
python -m shader_health validate examples/broken_scene/shader_health_demo_broken.ma \
  --input-kind scene \
  --profile-id publish_strict \
  --report report.json
```

(Scene validation requires `mayapy` / Maya Python.)

### Links

- Demo scene: [`examples/broken_scene/README.md`](examples/broken_scene/README.md)
- User guide: [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md)
- Architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Deadline preflight: [`docs/integrations/deadline_submit_preflight.md`](docs/integrations/deadline_submit_preflight.md)

[0.4.0]: https://github.com/armasonix/maya-shader-health-inspector/releases/tag/v0.4.0
[0.3.0]: https://github.com/armasonix/maya-shader-health-inspector/releases/tag/v0.3.0
[0.2.0]: https://github.com/armasonix/maya-shader-health-inspector/releases/tag/v0.2.0
[0.1.0]: https://github.com/armasonix/maya-shader-health-inspector/releases/tag/v0.1.0
