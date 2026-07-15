# Tracker publish and report attachment

Send to Tracker publishes a validation summary to the first enabled task tracker
(Ftrack, ShotGrid, or Cerebro). Issue #223 adds enriched Markdown notes and optional
HTML report attachments.

## Note content

Every publish path builds a `TrackerReportBundle` from the validation run:

- **Markdown note** — readable issue list via `reports/markdown_report.py`
- **HTML report** — self-contained report written to a temp file, or reused from
  `report_path` when the UI already exported HTML

If Markdown generation fails upstream, connectors fall back to the legacy plain-text
summary (`format_validation_publish_summary`).

## Attachment behavior by tracker

| Tracker | HTML attachment | Fallback | Optional actions |
| --- | --- | --- | --- |
| Ftrack | Task **Component** via `upload_component` batch action | Markdown note only; `attachment_error` in metadata | Set task status (`task_status_name`) |
| ShotGrid | Note **Attachment** via `/upload/Attachment/{note_id}` | Markdown note only; `attachment_error` in metadata | — |
| Cerebro | Not supported (no upload API in connector) | Markdown note plus `**Attached report path:**` when a local HTML path is known | Optional pause status on publish |

Capability flags live in `integrations/trackers/capabilities.py`.

## Publish metadata

Successful publishes may include:

- `note_id` — created note reference
- `component_id` — Ftrack HTML component id
- `attachment_id` — ShotGrid attachment id
- `attachment_error` — non-fatal HTML upload failure
- `task_status` — Ftrack/Cerebro status side effect

The Reports tab status line (`format_tracker_publish_status`) mentions HTML attachment
success or a non-fatal upload failure.

## Manual verification

1. Enable one tracker in Settings → Connectors.
2. Run validation and click **Send to Tracker**.
3. Confirm the task/note shows the Markdown summary.
4. On Ftrack/ShotGrid, confirm the HTML report is attached when upload succeeds.
