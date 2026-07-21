# Farm tab

**Deadline 10 on-prem** integration — connection status, preflight, and job submit from Maya.

## Prerequisites

- Thinkbox **Deadline 10** Web Service reachable from artist subnet
- Studio config: `connectors.deadline` (repository, URLs, credentials)
- Scene saved to a farm-visible path

Guide: [`integrations/deadline_submit_preflight.md`](../../integrations/deadline_submit_preflight.md)

## UI sections

| Section | Purpose |
| --- | --- |
| Connection | Web Service URL, status, **Refresh Connection** |
| Scene readiness | Path, profile, last validation snapshot |
| Eligibility | Blocking issues before submit |
| Actions | **Run Farm Preflight**, **Submit to Farm** |

## Farm Check shortcut

Menu/shelf **Pipeline Inspector Farm Check**:

1. Opens **Farm** tab.
2. Runs preflight with `deadline_critical` profile alignment.

## Preflight vs Validate tab

Both use the same validation pipeline. Farm preflight emphasizes **Deadline block** flags and connector-specific packaging.

## Submit governance

Role capability **`submit_farm`** required ([Governance](Governance)). Technical Artists may be denied by studio policy.

## Analytics (TD)

Historical farm QA metrics — separate CLI (read-only):

```bash
python -m pipeline_inspector farm-analytics --help
```

→ [`integrations/deadline_farm_analytics.md`](../../integrations/deadline_farm_analytics.md)

## Workflow

→ [Farm submission](Farm-Submission)
