# ADR 0003: Safe-fix and reference-safety policy

## Status

Accepted

## Date

2026-06-30

## Context

Maya Pipeline Inspector will eventually offer safe auto-fixes for common material QA issues such as wrong color space, unsafe paths, outdated texture links, and low-risk attribute corrections.

However, scene mutation in production Maya scenes is dangerous. Maya scenes often contain referenced assets, locked nodes, render-layer or namespace complexity, and shot-level overrides. A validator that silently edits scene data can damage production files, introduce unintended reference edits, or make Technical Artists distrust the tool.

The project must support production-safe workflows for several user groups:

- Technical Artists who need quick fixes;
- Shader TDs who need repeatable material policy;
- Pipeline TDs who need headless/publish safety;
- Render Supervisors who need control over risky exceptions.

The tool should help users fix problems, but it must never behave like an uncontrolled scene mutator.

## Decision

Maya Pipeline Inspector will be non-destructive by default.

All automatic fixes must go through a Safe Auto-Fix Queue. Fixes must be previewable, explainable, risk-rated, and blocked for referenced or locked nodes unless the active profile explicitly allows that behavior.

The default policy is:

- validation may inspect referenced nodes;
- validation may report issues inside referenced assets;
- validation must not modify referenced nodes by default;
- validation must not modify locked nodes by default;
- no fix may run silently;
- all Maya scene fixes must be undoable where possible;
- high-risk fixes require explicit confirmation;
- risky fixes may require supervisor approval depending on profile.

## Fix Categories

MVP fix categories:

| Fix Type | Example | Default Risk | Default Behavior |
|---|---|---:|---|
| `set_attr` | `file.colorSpace = Raw` | Low | Allowed for local unlocked nodes |
| `relink_path` | relink texture to latest version | Medium | Preview required |
| `normalize_path` | convert local path to project variable | Medium | Preview required |
| `disable_feature` | disable displacement | High | Confirmation required |
| `cleanup_orphan` | delete unused shader network | High | Preview-only in MVP |

## Required Fix Metadata

Every fix action must include:

- fix ID;
- rule ID;
- title;
- risk level;
- target node;
- target attribute if applicable;
- before value;
- after value;
- explanation;
- whether the node is referenced;
- whether the node is locked;
- whether reference edit would be required;
- whether undo is supported;
- whether supervisor approval is required.

## Alternatives Considered

### 1. No auto-fixes

Pros:

- safest possible implementation;
- validator cannot damage scenes;
- simpler first release.

Cons:

- lower value for Technical Artists;
- repetitive manual fixes remain costly;
- tool becomes diagnostic only.

Rejected as a long-term policy, but some risky fixes remain report-only.

### 2. Apply safe fixes immediately

Pros:

- fast user workflow;
- simpler UI;
- attractive for simple fixes like colorSpace changes.

Cons:

- user may not understand what changed;
- undo/reference behavior can be unclear;
- mistakes reduce trust;
- not acceptable for production scenes.

Rejected.

### 3. Safe Auto-Fix Queue with reference protection

Pros:

- users can preview changes;
- fixes are explainable;
- referenced/locked nodes are protected;
- risk is visible;
- production profiles can control permissions;
- audit/report integration is possible.

Cons:

- more implementation work;
- requires fix planner and UI queue;
- some fixes will require additional policy handling.

Accepted.

## Consequences

### Positive

- The tool remains trustworthy in production scenes.
- Technical Artists can still use convenient low-risk fixes.
- Supervisors can control risky changes through profile policy.
- Referenced assets are protected from accidental shot-level mutation.
- Fixes can be reported, audited, and tested.

### Negative / Tradeoffs

- Safe-fix implementation takes longer.
- UI must include a fix queue and explanation panel.
- Some users may want one-click fixes but will need to confirm changes.
- Headless mode must carefully separate validation from mutation.

## Implementation Notes

Expected core modules:

```text
src/pipeline_inspector/core/fix_plan.py
src/pipeline_inspector/core/waivers.py
```

Expected Maya modules:

```text
src/pipeline_inspector/maya/fix_applier.py
src/pipeline_inspector/maya/reference_safety.py
```

Expected UI behavior:

```text
Issue selected -> available fix shown -> before/after displayed -> user confirms -> fix applied inside undo chunk -> revalidate
```

Maya fix application should use undo chunks where possible.

Referenced node default behavior:

```text
Scan: allowed
Report: allowed
Fix: blocked by default
Waive: profile-dependent
```

Headless behavior:

- default headless validation must not mutate scenes;
- a future explicit `--apply-fixes` mode may exist, but only with strict policy and clear output;
- Deadline preflight must validate and block, not silently fix.

## Related

- Issue: `#040 - Implement fix planner`
- Issue: `#041 - Implement Maya fix applier with undo chunk`
- Issue: `#042 - Implement Safe Auto-Fix Queue UI`
- Issue: `#043 - Implement waiver sidecar system`
- Issue: `#015 - Implement reference-safe metadata collection`
- Document: `docs/ARCHITECTURE.md`
- Document: `docs/USER_GUIDE.md`
- Document: `docs/RULE_AUTHORING.md`
