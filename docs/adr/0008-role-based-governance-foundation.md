# ADR 0008: Role-based governance foundation

## Status

Accepted

## Date

2026-07-14

## Context

v0.6 adds studio connectors, farm submission, risky auto-fixes, and editable studio policy. Today any artist with panel access can save `pipeline_inspector_studio.json`, apply high-risk fixes, and submit farm jobs without an auditable permission model.

Production studios need a **layered** model that combines:

- studio-wide policy locks;
- tracker-assigned production roles (Ftrack / ShotGrid / Cerebro);
- per-machine user preference for self-declared role;
- safe defaults for artists.

The resolver must stay **Maya-independent** (ADR 0001) and work in headless CLI paths (ADR 0004).

## Decision

Pipeline Inspector v0.6 adopts a **four-layer role resolution stack** and a **capability matrix** enforced through `PermissionResolver` in `core/governance.py`.

### 1. Role resolution priority

Effective role is chosen from the first available layer:

| Priority | Layer | Source |
|---:|---|---|
| 1 | Studio policy | `studio.governance.enforced_role` |
| 2 | Tracker role | `PIPELINE_INSPECTOR_TRACKER_ROLE` env var mapped through `studio.governance.tracker_role_map` |
| 3 | User preference | `user.assigned_role` in `user.json` |
| 4 | Default | `technical_artist` |

### 2. Capabilities

| Capability | Technical Artist | Technical Support | Pipeline TD | Producer | Admin |
|---|---|---|---|---|---|
| `apply_safe_fixes` | yes | yes | yes | yes | yes |
| `apply_risky_fixes` | no | yes | yes | no | yes |
| `submit_farm` | yes | yes | yes | yes | yes |
| `manage_rules` | no | no | yes | no | yes |
| `edit_connectors` | no | no | yes | no | yes |
| `edit_studio_settings` | no | no | yes | no | yes |

Studio policy may add per-role denials via `studio.governance.capability_denials`. Denials subtract capabilities from the matrix; they never grant extra capabilities.

### 3. Enforcement surfaces (v0.6 foundation)

| Action | Required capability |
|---|---|
| Save Studio Config | `edit_studio_settings` and `edit_connectors` |
| Apply high-risk fixes (panel + CLI `--allow-high-risk`) | `apply_risky_fixes` |
| Submit to Farm | `submit_farm` |
| Save user preferences with `extra_rule_paths` | `manage_rules` |
| CLI `validate --extra-rules` | `manage_rules` |

Denied actions return a human-readable reason including effective role and role source.

### 4. Configuration fields

**StudioConfig** (`governance` section):

```json
{
  "governance": {
    "enforced_role": "",
    "tracker_role_map": { "Pipeline Supervisor": "pipeline_td" },
    "capability_denials": { "producer": ["submit_farm"] }
  }
}
```

**UserPreferences**:

```json
{
  "assigned_role": "technical_artist"
}
```

## Alternatives Considered

1. **Maya-only OS user mapping** — rejected; not portable to headless CLI and farm hooks.
2. **Single studio-wide capability list** — rejected; cannot express TD vs artist vs producer nuance.
3. **Per-action passwords** — rejected; poor UX and no studio rollout path.

## Consequences

### Positive

- One resolver powers panel, CLI, and future tracker-driven routing (#179).
- Studio IT can lock roles or deny capabilities without code changes.
- Unit tests can verify priority order independent of Maya.

### Negative / Tradeoffs

- User-declared roles are self-reported until tracker integration hardens layer 2.
- Studio save requires two capabilities because connectors live in the same JSON file.

## Implementation Notes

- Core module: `src/pipeline_inspector/core/governance.py`
- Panel guards: `src/pipeline_inspector/maya/ui_launcher.py`
- Basic tab exposes `assigned_role` combo bound to user preferences.

## Related

- Related issue: `#222` (plan `#176`)
- Builds on: ADR 0004, ADR 0007
