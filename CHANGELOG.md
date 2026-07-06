# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Improved

- Texture version freshness (`common.texture.version.latest`): clearer edge-case handling for multiple folder siblings, single-version folders, and missing `v###` tokens; added pass/fail snapshot fixtures and documented filesystem-only detection in [USER_GUIDE.md](docs/USER_GUIDE.md).

### Added

- Publish preflight hook example ([`examples/publish/submit_preflight.py`](examples/publish/submit_preflight.py)) and integration guide ([`docs/integrations/publish_submit_preflight.md`](docs/integrations/publish_submit_preflight.md)).
- Maya install guide ([`docs/MAYA_INSTALL.md`](docs/MAYA_INSTALL.md)) for `MAYA_MODULE_PATH`, editable `pip`, and menu/shelf bootstrap.
- Studio overrides guide ([`docs/STUDIO_OVERRIDES.md`](docs/STUDIO_OVERRIDES.md)) with worked `examples/studio/` rule pack and profile sample.
- Optional Maya integration GitHub Actions workflow ([`.github/workflows/maya-integration.yml`](.github/workflows/maya-integration.yml), `workflow_dispatch` only).

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

[0.1.0]: https://github.com/armasonix/maya-shader-health-inspector/releases/tag/v0.1.0
