# Deadline farm analytics collection

Studio guide for collecting Deadline 10 on-prem farm analytics through the Web Service REST API.

## Overview

Pipeline Inspector can read job, statistics, and pool/worker state from the Deadline Web Service and derive:

- throughput (completed jobs per hour)
- failure rate
- average render time
- pool utilization

## Required Web Service permissions

Analytics collection is **read-only**. The Web Service user only needs successful `GET` access to:

| Endpoint | Purpose |
| --- | --- |
| `/api/jobs?States=...` | Job counts by state |
| `/api/jobs?JobID=...&Statistics=true` | Per-job render statistics |
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

## Metric notes

- **Throughput** uses completed-job completion timestamps when available. If jobs do not expose completion dates, the collector falls back to the completed-job count divided by the window and marks the result as estimated.
- **Failure rate** is `failed / (completed + failed)` for jobs in the queried states.
- **Average render time** samples up to 25 completed jobs and reads `Statistics=true` payloads.
- **Pool utilization** is `rendering_workers / workers_in_pool` using worker info records.

## Related docs

- [deadline_submit_preflight.md](deadline_submit_preflight.md) — Web Service setup and Farm tab connectivity
