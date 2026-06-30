# Maya Shader Health Inspector

Production-oriented material QA framework for Autodesk Maya pipelines.

**Status:** early development / architecture phase  
**Primary DCC:** Autodesk Maya  
**Initial renderer targets:** Common Maya, V-Ray, Arnold  
**Future renderer targets:** RenderMan, Redshift, USD / MaterialX

Maya Shader Health Inspector is designed to detect material and texture problems before assets reach publish, lighting, or Deadline render submission. It focuses on repeatable, data-driven QA for shader graphs, texture dependencies, color management, UDIM sets, displacement risk, path policy, renderer compatibility, and farm-preflight safety.

The tool answers one practical production question:

> Can this asset or shot be safely published or submitted to the render farm, and if not, what is broken, who owns the fix, how dangerous is it, and can it be fixed safely?

## Why this exists

Feature animation and VFX productions can accumulate hundreds of unique materials across characters, props, environments, crowds, and shot-level overrides. Common failures include:

- missing texture files;
- stale texture versions;
- wrong color space on data maps;
- broken UDIM tile sets;
- local artist paths that render farm machines cannot access;
- risky displacement settings;
- overly complex shader graphs;
- duplicate or orphan material networks;
- renderer plugin/version mismatch;
- referenced assets that cannot be safely modified in a shot scene.

These problems are often discovered too late: during farm submission, overnight rendering, lighting review, or final image QA. The goal of this project is to move material failure detection earlier in the pipeline.

## Core principles

- Data-driven validation rules.
- Renderer-agnostic core with renderer-specific adapters.
- Testable pure Python validation engine independent of Maya UI.
- Safe fixes only: previewable, undoable, and reference-aware.
- Explainable results: every issue must describe what is wrong, why it matters, and what should be done.
- Headless validation for publish systems, CI, and Deadline preflight.
- Dockable Maya UI for artists, Shader TDs, and supervisors.

## Planned MVP scope

The first MVP focuses on texture and shader preflight:

- GraphSnapshot model for Maya material networks.
- JSON rule schema and rule loader.
- Common Maya, V-Ray, and Arnold adapter foundation.
- Missing texture and path policy validation.
- UDIM integrity checks.
- Semantic texture slot detection.
- Color space validation for color vs data maps.
- Displacement risk checks.
- Basic shader complexity scoring.
- Material Health Score.
- JSON / HTML reports.
- Headless validation command.
- Dockable Maya panel.
- Deadline submit preflight example.

## Repository status

Development is currently driven from `docs/DEVELOPMENT_PLAN.md` and GitHub issues/milestones.

The project is intentionally being built in this order:

```text
Snapshot model -> rule engine -> rule packs -> Maya scanner -> adapters -> reports -> UI -> safe fixes -> headless -> Deadline -> demo -> release
```

This keeps the validation core testable before the Maya UI and renderer integrations are added.

## Development

Development setup will be added as part of the packaging milestone.

For now, the package source lives under:

```text
src/shader_health/
```

## License

MIT License. See `LICENSE`.
