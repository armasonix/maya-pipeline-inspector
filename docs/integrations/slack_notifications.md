# Slack notifications

Shader Health Inspector can post validation summaries to Slack using **incoming webhooks** with **severity routing**:

- **Publish block** events route to `connectors.slack.publish_webhook_url`
- **Deadline block** events route to `connectors.slack.deadline_webhook_url`

Both routes share the same Block Kit payload shape and the same `notify_on` event model used by Telegram and Discord.

## Studio config

```json
{
  "connectors": {
    "slack": {
      "enabled": true,
      "publish_webhook_url": "https://hooks.slack.com/services/.../publish",
      "deadline_webhook_url": "https://hooks.slack.com/services/.../deadline",
      "notify_on": ["block_publish", "block_deadline"],
      "include_report_link": true
    }
  },
  "studio_environment": {
    "render_root": "\\\\farm\\render"
  }
}
```

| Field | Purpose |
|---|---|
| `enabled` | Master toggle for Slack notifications |
| `publish_webhook_url` | Incoming webhook for publish-blocking validations |
| `deadline_webhook_url` | Incoming webhook for Deadline-blocking validations |
| `notify_on` | Same block events as other notification connectors |
| `include_report_link` | Append an optional report path built from `render_root` |

Webhook URLs are treated as secrets in the Settings UI (password echo) and should live in the studio config file deployed by pipeline TDs.

## Channel routing

Routing happens per matched block event:

1. Validation computes `block_publish` / `block_deadline` from failed rule results.
2. `notify_on` filters which events may fire.
3. Each active event posts to its routed webhook URL.

If only one webhook is configured, only the matching route can send. A publish block does not fall back to the Deadline webhook.

## Rich blocks payload

Messages use Slack Block Kit via `integrations/slack/blocks.py`:

- Header with matched block labels
- Section fields for scene, profile, scope, and health score
- Issue counts (critical / error / warning / info)
- Optional report link section when enabled

## Optional report link

When `include_report_link` is true and `studio_environment.render_root` is set, Shader Health builds:

```
{render_root}/{scene_stem}_shader_health_report.json
```

Example:

- Scene: `\\farm\assets\hero\hero.ma`
- `render_root`: `\\farm\render`
- Link: `\\farm\render\hero_shader_health_report.json`

The link is informational. Studios typically mirror or publish JSON reports to that location from their own export or farm pipeline.

## Settings UI

Open **Settings → Connectors → Slack** in the Maya panel:

1. Enable notifications.
2. Paste the publish and Deadline incoming webhook URLs.
3. Choose which block events should notify.
4. Toggle **Include report link from render_root** when report paths should appear in Slack messages.

## Package layout

```
src/shader_health/integrations/slack/
  config.py    # SlackConfig
  client.py    # SlackClient (incoming webhook POST)
  blocks.py    # Block Kit formatter + routing helpers
```

Runtime wiring from validation events is handled separately from this connector package (see Milestone 34 notification dispatcher work).

## Security notes

- Use incoming webhooks only; OAuth Slack apps are out of scope for v0.5.
- Do not commit webhook URLs to git. Store them in `shader_health_studio.json` on a controlled network share.
- Treat webhook responses as untrusted network data.
