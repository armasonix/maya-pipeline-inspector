# Reports tab

Export validation artifacts for supervisors, trackers, and CI archives.

## Export actions

| Export | Format | Typical consumer |
| --- | --- | --- |
| **JSON report** | `.json` | Pipelines, diff tools, custom dashboards |
| **HTML report** | `.html` | Human review, email, Confluence |
| **Shader manifest** | `.json` schema 1.1 | Publish baseline, regression gate |
| **Manifest diff** | JSON/HTML | Compare against approved baseline |
| **Compare approved manifest** | diff UI | Publish gate review |

Sample HTML layout: [`docs/assets/html-report.png`](../../assets/html-report.png)

## Manifest regression gate

Export manifest → later run CLI or UI **Manifest Gate**:

```bash
mayapy -m pipeline_inspector gate scene.ma baseline_manifest.json --profile-id publish_strict
```

Exit codes suitable for publish hooks — see [CLI reference](../Reference/CLI-Reference).

## Send to Tracker

When connectors are configured (Ftrack, ShotGrid, Cerebro), push markdown summary to a task/version.

→ [`integrations/tracker_publish.md`](../../integrations/tracker_publish.md)

## Report to supervisor (v0.6)

Role-based routing sends structured summaries to the correct supervisor channel ([ADR 0009](../../adr/0009-report-to-supervisor-routing-by-role.md)).

## Tips

- Run **publish_strict** before exporting manifest for publish baseline.
- Store manifests per asset version, not per arbitrary save.
- HTML reports are self-contained — no server required.
