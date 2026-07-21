# Settings hub

Open via **gear** icon on the panel. Multi-page overlay for user prefs, studio policy, and connectors ([ADR 0007](../../adr/0007-settings-and-connectors-architecture.md)).

## Pages

| Page | Audience | Contents |
| --- | --- | --- |
| **Basic** | Artist | Theme, assigned role, check-for-updates on startup |
| **Advanced** | TD | Extra rule paths, debug toggles |
| **Studio Environment** | TD | Texture/asset/cache/render roots, variable aliases |
| **Studio** | TD | Pipeline toggles, manifest policy, readiness checks |
| **Connectors** | TD | Deadline, notifications, trackers |
| **Bug Report** | All | Relay URL, diagnostics bundle |
| **Support** | All | Links, version info |

## Config files

| File | Scope |
| --- | --- |
| `pipeline_inspector_studio.json` | Facility-wide — deploy via env var |
| `~/.pipeline_inspector/user.json` | Per-user preferences |

Discovery order: [`MAYA_INSTALL.md` — Studio config rollout](../../MAYA_INSTALL.md)

## Save actions

- **Save User Config** — local preferences.
- **Save Studio Config** — requires `edit_studio_settings` capability.

Status banner shows which studio file is loaded.

## Connectors overview

| Connector | Doc |
| --- | --- |
| Deadline 10 | [Farm tab](Farm-Tab) |
| Telegram / Discord / Slack | [`STUDIO_OVERRIDES.md`](../../STUDIO_OVERRIDES.md) |
| Ftrack / ShotGrid / Cerebro | [`tracker_publish.md`](../../integrations/tracker_publish.md) |
| Bug report relay | [`bug_report_relay.md`](../../integrations/bug_report_relay.md) |

→ [Studio config](../Administration/Studio-Config) · [Governance](../Administration/Governance)
