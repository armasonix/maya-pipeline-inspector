# Governance

Role-based capabilities (v0.6) — [ADR 0008](../../adr/0008-role-based-governance-foundation.md), supervisor routing [ADR 0009](../../adr/0009-report-to-supervisor-routing-by-role.md).

## Pipeline roles

| Role id | Typical user |
| --- | --- |
| `technical_artist` | Lookdev, lighting artists |
| `technical_support` | Support, junior TD |
| `pipeline_td` | Pipeline / tools TD |
| `admin` | Pipeline lead |

Legacy `producer` role removed — normalizes to unknown → falls back to `technical_artist` ([ADR 0009](../../adr/0009-report-to-supervisor-routing-by-role.md)).

## Capabilities

| Capability | Gates |
| --- | --- |
| `apply_risky_fixes` | High-risk fix confirmation |
| `submit_farm` | Farm tab submit |
| `edit_studio_settings` | Save studio JSON |
| `edit_connectors` | Connector credentials |
| `manage_rules` | Extra rule paths |

## Assignment

| Mode | Behavior |
| --- | --- |
| Self-reported | Artist sets **Assigned role** in Settings → Basic |
| Enforced | `governance.enforced_role` in studio JSON |
| Tracker mapping | Ftrack/Cerebro role discovery (partial) |

## Studio denials

Subtract capabilities per role:

```json
"governance": {
  "capability_denials": {
    "technical_artist": ["submit_farm"]
  }
}
```

→ [`STUDIO_OVERRIDES.md`](../../STUDIO_OVERRIDES.md)

## Supervisor routing

Report actions route to supervisor by role — panel Reports / notifications.

## UI feedback

Denied actions show reason in status banner (compliance log export — roadmap gap).

→ [Capability matrix](Capability-Matrix)
