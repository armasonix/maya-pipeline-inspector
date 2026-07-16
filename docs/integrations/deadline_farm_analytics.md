# Deadline farm analytics collection

Studio guide for collecting Deadline 10 on-prem farm analytics through the Web Service REST API.

## Overview

Pipeline Inspector can read job, statistics, and pool/worker state from the Deadline Web Service and derive:

- throughput (completed jobs per hour)
- failure rate
- average render time
- pool utilization

Extended tiers add:

- **Tier A — operations:** queue wait, wall clock, render efficiency, task error rate, pending/suspended backlog, pool/group/plugin/user breakdowns, top failed jobs
- **Tier B — frame economics:** median/p95 sec/frame, failed/completed frame counts, slowest frames (from `/api/tasks`)
- **Tier C — shot intelligence:** beauty/matte/other pass mix from job naming, rerender watchlist by shot key, validation-linked job count
- **Tier D — history:** optional JSONL append via `--history-path` for longer rerender trend analysis

## Shot and pass naming conventions

Shot keys default to `show_seq###_sh###` tokens found in `JobName`, `BatchName`, `Comment`, or `ExtraInfo0-2`.

Pass labels default to:

| Label | Tokens |
| --- | --- |
| `beauty` | `beauty`, `master`, `rgb`, `beauty_pass` |
| `matte` | `matte`, `holdout`, `mask`, `matte_pass` |
| `other` | everything else |

Override shot extraction with `--shot-key-pattern` when your studio uses a different template.

## Required Web Service permissions

Analytics collection is **read-only**. The Web Service user only needs successful `GET` access to:

| Endpoint | Purpose |
| --- | --- |
| `/api/jobs?States=...` | Job counts by state |
| `/api/jobs?JobID=...&Statistics=true` | Per-job render statistics |
| `/api/tasks?JobID=...` | Per-frame/task render samples |
| `/api/pools` | Pool names |
| `/api/pools?Pool=...` | Workers assigned to a pool |
| `/api/slaves?Data=info` | Worker rendering state |

No `POST`, `PUT`, or `DELETE` permissions are required for analytics.

If authentication is enabled on the Web Service, configure the same credentials your studio already uses for Farm tab connectivity. See [deadline_submit_preflight.md](deadline_submit_preflight.md).

## Headless usage

### CLI

```bash
python -m pipeline_inspector farm-analytics --json
python -m pipeline_inspector farm-analytics --pool lookdev --window-hours 12
python -m pipeline_inspector farm-analytics --html D:/reports/farm_summary.html --history-path D:/reports/farm_history.jsonl
```

### Example script

```bash
python examples/deadline/farm_analytics.py --json
```

### Python API

```python
from pipeline_inspector.integrations.deadline import DeadlineClient, DeadlineConfig, collect_farm_analytics

client = DeadlineClient(DeadlineConfig.from_env())
report = collect_farm_analytics(client, pool_filter="lookdev")
print(report.metrics.failure_rate)
```

### Maya panel hook

```python
from pipeline_inspector.maya.farm_actions import collect_farm_analytics_report

report = collect_farm_analytics_report(pool_filter="lookdev")
```

## Management HTML report

Pipeline Inspector can turn the same analytics payload into a self-contained HTML report with KPI cards and embedded SVG charts. The layout reuses the validation report stylesheet for a consistent studio look.

Report flow:

1. **Key Metrics** — numeric KPI cards
2. **Farm KPI Dashboard** — donut, gauge, and bar charts for immediate visual farm health
3. **Detail sections** — operations, frame, and shot tables for follow-up

### Reports tab

Open the **Reports** tab and click **Export Farm HTML Report**. The panel collects live analytics from the Deadline Web Service and writes `reports/farm/{scene}_deadline_farm_report.html` next to the open scene.

### Organized output layout

Default exports are grouped under a `reports/` folder beside the scene:

| Folder | Artifacts |
| --- | --- |
| `reports/validation/` | JSON/HTML validation reports |
| `reports/manifests/` | shader manifest + manifest diff JSON/HTML |
| `reports/fix_plans/` | fix plan JSON exports |
| `reports/farm/` | farm validation JSON + farm HTML report |

Legacy flat files directly beside the scene are still recognized as approved manifest sidecars when present.

### CLI

```bash
python -m pipeline_inspector farm-analytics --html D:/reports/farm_summary.html
python -m pipeline_inspector farm-analytics --html D:/reports/farm_summary.html --json
```

### Example script

```bash
python examples/deadline/farm_analytics.py --html D:/reports/farm_summary.html
```

### Python API

```python
from pipeline_inspector.maya.farm_actions import export_farm_html_report

result = export_farm_html_report(path="D:/reports/farm_summary.html", pool_filter="lookdev")
print(result.path)
```

A deterministic sample report for docs and screenshots lives at `tests/fixtures/deadline_farm_report_sample.html`.

## Metric notes

- **Throughput** uses completed-job completion timestamps when available. If jobs do not expose completion dates, the collector falls back to the completed-job count divided by the window and marks the result as estimated.
- **Failure rate** is `failed / (completed + failed)` for jobs in the queried states.
- **Average render time** samples up to 25 completed jobs and reads `Statistics=true` payloads.
- **Pool utilization** is `rendering_workers / workers_in_pool` using worker info records.
- **Frame economics** samples completed jobs (default 10) and reads `/api/tasks` for per-frame render times.
- **Rerender watchlist** groups jobs by shot key; entries with 2+ submits appear in the HTML report.
- **History JSONL** stores full serialized snapshots for nightly ETL or supervisor trend review.

## Related docs

- [deadline_submit_preflight.md](deadline_submit_preflight.md) — Web Service setup and Farm tab connectivity
