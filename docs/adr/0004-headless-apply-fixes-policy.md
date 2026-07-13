# ADR 0004: Headless apply-fixes policy

## Status

Accepted

## Date

2026-07-06

## Context

v0.2 shipped preview-only fix planning and Maya UI apply with undo chunks. Studios can validate scenes headlessly (`pipeline_inspector validate`), export fix plans, and gate publish or farm submission without opening the dockable panel.

Pipeline automation increasingly needs a headless `pipeline_inspector apply-fixes` path for supervised batch repair, but scene mutation from batch jobs carries higher risk than validation-only preflight. ADR 0003 established that headless validation must not mutate scenes by default and that referenced nodes, locked nodes, and high-risk fixes require explicit policy.

The project must define how headless apply differs from UI apply while reusing the same fix planner, `FixAction` metadata, Maya fix applier, and fix audit sidecar.

## Decision

Maya Pipeline Inspector will add an explicit headless `pipeline_inspector apply-fixes` subcommand that mutates scenes only when callers opt in with clear inputs and policy flags.

The headless apply policy is:

1. **Mutation is explicit** — callers must pass a Maya scene path and either `--fix-plan` (deterministic export from a prior validated run) or rely on inline re-validation planning inside the command. There is no silent auto-fix during `validate`.
2. **Dry-run is first-class** — `--dry-run` prints the would-apply action set and optional apply report JSON without opening Maya undo chunks or mutating the scene.
3. **Reference safety inherits ADR 0003** — referenced targets remain blocked unless `--allow-referenced` is set.
4. **High-risk fixes require explicit opt-in** — `--allow-high-risk` is required for actions flagged `requires_supervisor` (for example `disable_feature`).
5. **Audit is mandatory on real apply** — successful non-dry-run sessions append to `{scene_stem}.pipeline_inspector_fix_audit.json` beside the scene via the existing fix audit sidecar helpers.
6. **Undo stays Maya-local** — headless apply opens one undo chunk per invocation (`Pipeline Inspector Apply Fixes`). Batch pipelines must not assume cross-scene undo.
7. **Non-goals for v0.3** — `cleanup_orphan` auto-delete remains preview-only per ADR 0003.

### Exit codes

Headless `apply-fixes` aligns with `pipeline_inspector validate` where practical:

| Code | Meaning |
| --- | --- |
| `0` | Applied successfully, or dry-run planned with no runtime failure |
| `1` | Blocked apply (policy blocked all actionable fixes, or publish-style block) |
| `3` | Runtime failure (Maya API error, missing scene, apply error) |
| `4` | Configuration error (invalid fix plan, profile, or rule load failure) |

Dry-run returns `0` when planning succeeds even if every action would be blocked; callers inspect the apply report JSON for `blocked_count` and per-action `block_reasons`.

## Alternatives Considered

### 1. Headless validation only (no apply subcommand)

Pros:

- safest default for farm and publish wrappers;
- no new mutation surface in CI or batch jobs.

Cons:

- studios must manually open Maya to apply repeatable low-risk fixes;
- fix-plan exports become diagnostic-only artifacts.

Rejected for v0.3 pipeline automation goals, but `validate` remains non-mutating.

### 2. Auto-apply safe fixes during `validate`

Pros:

- single command for “fix and report”;
- attractive for one-shot cleanup scripts.

Cons:

- violates ADR 0003 non-destructive default;
- publish and Deadline preflight could mutate scenes unexpectedly;
- harder to audit who approved which fixes.

Rejected.

### 3. Explicit `apply-fixes` subcommand with policy flags

Pros:

- separates validation from mutation;
- reuses UI fix applier, planner, and audit sidecar;
- supports `validate` → `apply-fixes --dry-run` → supervisor-approved `apply-fixes` chains;
- studios can document who may pass `--allow-referenced` and `--allow-high-risk`.

Cons:

- requires mayapy (not plain Python) for scene mutation;
- additional CLI surface and documentation burden.

Accepted.

## Consequences

### Positive

- Publish and repair wrappers can chain validation, dry-run preview, and supervised apply with deterministic fix-plan JSON.
- Fix audit sidecars provide a studio-visible history beside the scene file.
- Policy flags mirror UI Safe Auto-Fix Queue constraints for referenced and high-risk actions.

### Negative / Tradeoffs

- Farm jobs must not treat headless apply as a substitute for artist review on high-risk fixes.
- Studios must govern `--allow-referenced` and `--allow-high-risk` usage in pipeline docs.
- Headless apply requires Maya; snapshot-only CI cannot exercise real scene mutation without mayapy integration tests.

## Implementation Notes

Expected CLI surface (Milestone 18, issues #081–#083):

```text
pipeline_inspector apply-fixes scene.ma [--fix-plan plan.json] [--dry-run]
  [--profile publish_strict] [--fix-ids FIX_ID ...]
  [--allow-referenced] [--allow-high-risk] [--report apply_report.json]
```

Expected modules:

```text
src/pipeline_inspector/cli.py                  # apply-fixes subcommand
src/pipeline_inspector/maya/fix_applier.py     # apply_fix_actions()
src/pipeline_inspector/maya/validation_pipeline.py  # persist_fix_apply_audit()
src/pipeline_inspector/core/fix_plan.py        # FixPlan / FixAction
src/pipeline_inspector/core/fix_audit.py       # fix audit sidecar schema
```

Recommended studio workflow:

```text
1. pipeline_inspector validate scene.ma --report report.json --export-fix-plan plan.json
2. pipeline_inspector apply-fixes scene.ma --fix-plan plan.json --dry-run --report dry_run.json
3. Supervisor reviews dry_run.json and fix audit policy.
4. pipeline_inspector apply-fixes scene.ma --fix-plan plan.json --report apply.json
5. Fix audit appended to scene.pipeline_inspector_fix_audit.json
```

Farm jobs should prefer fix-plan JSON produced by an earlier validated run rather than re-planning inside unattended apply jobs.

## Related

- Issue: `#080 - ADR 0004 headless apply-fixes policy`
- Issue: `#081 - pipeline_inspector apply-fixes subcommand`
- Issue: `#082 - apply-fixes policy flags`
- Issue: `#083 - fix_audit integration and exit codes`
- ADR: `0003-safe-fix-reference-safety-policy.md`
- Document: `docs/USER_GUIDE.md`
- Document: `docs/V0_3_DEVELOPMENT_PLAN.md`
