# Contributing to Maya Shader Health Inspector

Thank you for your interest in contributing to Maya Shader Health Inspector.

This project is an open-source, production-oriented Maya material QA framework. Contributions are welcome, but they must preserve the project's core principles: production safety, data-driven validation, explainable results, testable core logic, and clean renderer boundaries.

## Project Status

The project is currently in early development. The architecture is being built from the pure Python validation core outward:

```text
Snapshot model -> rule engine -> rule packs -> Maya scanner -> adapters -> reports -> UI -> safe fixes -> headless -> Deadline -> demo -> release
```

Before opening a large pull request, check the current GitHub issues and milestones.

## Development Setup

### Requirements

- Python 3.9+
- Git
- Autodesk Maya is optional for pure Python core development

### Install in Editable Mode

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Alternative:

```bash
python -m pip install -r requirements-dev.txt
```

### Run Checks

```bash
python -m pytest tests -v
python -m ruff check src tests
python -m mypy src
git diff --check
```

All checks should pass before opening a pull request.

## Branch Workflow

Recommended workflow:

```text
main       stable milestone state
dev        active integration branch
feature/*  optional branch for larger tasks
```

Small focused changes may go directly into `dev`. Larger features should use a feature branch and then merge into `dev`.

Use clear commit messages:

```text
chore: add repository hygiene files
feat: implement core snapshot models
test: add rule loader override tests
docs: add rule authoring guide
fix: prevent referenced node mutation
```

When relevant, reference issues:

```text
Refs #12
Closes #12
```

## Pull Request Expectations

A pull request should:

- target the correct branch, usually `dev`;
- focus on one issue or one coherent feature;
- include tests for code changes;
- update documentation when behavior changes;
- avoid unrelated formatting churn;
- keep Maya-dependent changes separated from pure core changes when practical;
- describe validation performed locally.

Recommended PR checklist:

```text
[ ] Tests pass
[ ] Ruff passes
[ ] mypy passes
[ ] git diff --check passes
[ ] Docs updated if needed
[ ] No production assets, secrets, client data, or private paths included
```

## Code Contribution Rules

### Keep the Core Maya-Independent

The core validation engine should operate on plain Python models and JSON-compatible snapshot data. Do not import `maya.cmds`, Maya API modules, PySide, V-Ray, or Arnold APIs from core modules.

Maya-dependent code belongs under:

```text
src/shader_health/maya/
```

UI code belongs under:

```text
src/shader_health/ui/
```

Renderer-specific code belongs under:

```text
src/shader_health/adapters/
```

### Prefer Data-Driven Rules

Validation behavior should usually live in JSON rule packs rather than hardcoded Python checks.

Rules should include:

- stable rule ID;
- severity;
- owner;
- message;
- `why` explanation;
- match criteria;
- check definition;
- block policy;
- optional safe fix definition.

See:

```text
docs/RULE_AUTHORING.md
```

### Keep Renderer Boundaries Clean

Renderer adapters should classify renderer-specific nodes and plug semantics. The core engine should not hardcode V-Ray or Arnold node knowledge.

Initial adapters:

- Common Maya;
- V-Ray;
- Arnold.

Future adapters may include:

- RenderMan;
- Redshift;
- USD / MaterialX inspection.

### Safe Fixes Must Be Explicit

Scene mutation is dangerous in production. Any auto-fix must be:

- previewable;
- explainable;
- undoable where possible;
- reference-aware;
- locked-node aware;
- blocked by default for referenced nodes unless profile explicitly allows it.

No silent scene mutation is allowed.

## Rule Contribution Guidelines

When adding a rule:

1. Add or update the rule JSON.
2. Add a passing fixture.
3. Add a failing fixture.
4. Add tests for severity, block flags, owner, message, and `why`.
5. Add fix tests if the rule defines an auto-fix.
6. Update documentation if the rule introduces a new check type.

Rule IDs should be stable and hierarchical:

```text
common.texture.missing
common.texture.path.local_drive
common.texture.colorspace.data_raw
common.udim.missing_tile
vray.displacement.high_amount
arnold.texture.tx_missing
```

Do not rename released rule IDs casually. If behavior changes significantly, create a new rule ID or document migration.

## Renderer Adapter Contribution Guidelines

When adding or changing a renderer adapter:

- keep adapter logic isolated from the core engine;
- add snapshot fixtures for the renderer graph patterns;
- classify semantic texture slots through connection destinations;
- document unsupported or ambiguous node behavior;
- add tests for adapter registration and semantic mapping;
- do not require the renderer plugin to be installed for pure unit tests.

Renderer plugin availability should be handled gracefully.

## Testing Strategy

Default public CI should not require Maya. Most tests should run as pure Python tests using snapshot fixtures.

Use pure Python tests for:

- models;
- rule schema;
- rule loader;
- profile overrides;
- validator behavior;
- scoring;
- path utilities;
- UDIM parsing;
- report generation;
- manifest and diff logic;
- fix planning.

Maya integration tests should be optional/local unless a Maya runner is explicitly available:

```bash
mayapy -m pytest tests/integration -v
```

Maintainers can run the optional Maya workflow [`.github/workflows/maya-integration.yml`](.github/workflows/maya-integration.yml) on a self-hosted runner labeled `maya` (manual dispatch, weekly schedule, or same-repo PR). See [`docs/MAYA_INSTALL.md`](docs/MAYA_INSTALL.md).

### Native Maya plug-in (optional)

The thin C++ bootstrap is built with CMake against a licensed Maya devkit. Pure Python contributors can skip this step — the `.py` plug-in fallback remains supported.

```powershell
.\tools\build_native_plugin.ps1 -MayaVersion 2025
```

Details: [`native/README.md`](native/README.md), [ADR 0006](docs/adr/0006-native-mll-plugin-strategy.md).

## Documentation Contributions

Documentation should be practical and production-oriented.

Useful documentation contributions include:

- rule authoring examples;
- renderer adapter notes;
- UI workflow explanations;
- Deadline integration examples;
- safe-fix policy details;
- sanitized demo scene documentation;
- troubleshooting guides.

## Open-Source Safety and Data Privacy

Do not commit or publish:

- proprietary studio scenes;
- client names or confidential show names;
- real production assets;
- internal server paths;
- private texture paths;
- API tokens or secrets;
- screenshots containing confidential data;
- unlicensed textures, models, or HDRIs.

Use sanitized examples and demo assets only.

Bad examples:

```text
//studio-server/project/client_show/asset/hero_character/...
C:/Users/artist/Desktop/client_final_texture.exr
```

Good examples:

```text
$ASSET_ROOT/char/demo_hero/tex/body_albedo_v001.<UDIM>.exr
examples/broken_scene/textures/dress_roughness_v001.1001.exr
```

## Issue Guidelines

Good issues include:

- clear problem statement;
- expected behavior;
- current behavior if known;
- affected profile/rule/renderer;
- reproduction steps or fixture idea;
- acceptance criteria.

For rule requests, include:

- rule purpose;
- affected renderer/material type;
- example graph or snapshot shape;
- severity suggestion;
- block policy suggestion;
- safe-fix possibility;
- why the rule matters in production.

## Coding Style

Use clear, typed, boring Python. Prefer explicit data models and small functions over clever abstractions.

Guidelines:

- keep modules focused;
- avoid global mutable state;
- avoid hidden Maya side effects;
- prefer deterministic JSON output;
- keep rule/result IDs stable;
- write tests with clear fixture names;
- make errors actionable.

## Definition of Done

A code feature is done when:

- implementation is complete;
- tests are added;
- docs are updated if needed;
- reports/headless behavior are considered;
- safety behavior is explicit;
- CI passes.

A validation rule is done when:

- the rule is data-driven;
- message and `why` are present;
- severity and block policy are explicit;
- owner is assigned;
- tests cover pass/fail behavior;
- auto-fix, if any, is safe and documented.

## Questions

Use GitHub issues for design questions, rule requests, renderer support requests, and bug reports.
