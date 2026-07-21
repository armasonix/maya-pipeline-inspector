# Integrations index

Pipeline Inspector connects to farm, trackers, chat, and update infrastructure. Each integration is **optional** — core validation works offline.

## Render farm

| Integration | Status | Doc |
| --- | --- | --- |
| **Deadline 10 on-prem** | Shipped | [`deadline_submit_preflight.md`](../../integrations/deadline_submit_preflight.md) |
| Farm analytics CLI | Shipped | [`deadline_farm_analytics.md`](../../integrations/deadline_farm_analytics.md) |
| AWS Deadline Cloud | Not shipped | — |

Wiki: [Farm tab](Farm-Tab) · [Farm submission](Farm-Submission)

## Publish & preflight

| Integration | Doc |
| --- | --- |
| Publish submit preflight | [`publish_submit_preflight.md`](../../integrations/publish_submit_preflight.md) |

Wiki: [Publish preflight](Publish-Preflight)

## Trackers

| Integration | Doc |
| --- | --- |
| Ftrack, ShotGrid, Cerebro | [`tracker_publish.md`](../../integrations/tracker_publish.md) |

Panel: **Reports → Send to Tracker**

## Notifications

| Channel | Doc |
| --- | --- |
| Slack | [`slack_notifications.md`](../../integrations/slack_notifications.md) |
| Telegram, Discord | [`STUDIO_OVERRIDES.md`](../../STUDIO_OVERRIDES.md) |

Configure in Settings → Connectors.

## Bug report relay

HTTPS relay for in-panel **Bug Report** — [`bug_report_relay.md`](../../integrations/bug_report_relay.md)

## Auto-update

GitHub Releases zip + in-app wizard — [`auto_update.md`](../../integrations/auto_update.md)

Wiki: [Updates & releases](Updates-and-Releases)

## Architecture

Connectors registry: [ADR 0007 — Settings and connectors architecture](../../adr/0007-settings-and-connectors-architecture.md)

Settings UI: [Settings hub](Settings-Hub)
