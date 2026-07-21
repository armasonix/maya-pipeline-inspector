# ADR 0009: Report-to-supervisor routing by role

## Status

Accepted

## Date

2026-07-14

## Context

ADR 0008 introduced `PermissionResolver` with a tracker-role layer stubbed via
`PIPELINE_INSPECTOR_TRACKER_ROLE`. Studios need validation and readiness reports
routed to the correct supervisor channel based on the reporter's effective pipeline
role, with real Ftrack and Cerebro role discovery.

## Decision

1. **Remove `producer`** from the pipeline role matrix. Legacy `assigned_role:
   producer` normalizes to unknown and falls back to `technical_artist`.

2. **Tracker role resolution** (priority):
   - `PIPELINE_INSPECTOR_TRACKER_ROLE` env var
   - Ftrack `SecurityRole` names for `PIPELINE_INSPECTOR_TRACKER_USER` /
     `user.tracker_username` / OS username
   - Cerebro group names from the connected API session
   - Mapped through `studio.governance.tracker_role_map`

3. **Supervisor routing** via `studio.governance.supervisor_routes`:
   - Key: reporter pipeline role (`technical_artist`, …)
   - Value: `supervisor_label`, `telegram_chat_id`, optional Discord/Slack webhooks

4. **Integration points**:
   - `dispatch_validation_notifications(..., supervisor_route=...)`
   - Readiness tab **Send report to Supervisor**
   - Settings → Studio → Governance & supervisor routing UI

## Consequences

- Technical Artists route block reports to Lead TD without manual chat selection.
- Ftrack/Cerebro connectors now participate in governance, not only publish.
- Producer role removed; use `technical_artist` or studio-specific tracker maps.

## Related

- Issue #225 (plan #179)
- Builds on ADR 0008
