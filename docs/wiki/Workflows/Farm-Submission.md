# Farm submission

Submit renders only after **Deadline-critical** validation passes.

## Panel workflow

1. Save scene to farm-visible path.
2. Open **Farm** tab (or **Pipeline Inspector Farm Check**).
3. **Refresh Connection** — verify Deadline Web Service.
4. **Run Farm Preflight** — profile alignment `deadline_critical`.
5. Confirm **Deadline Block: NO**.
6. **Submit to Farm** (if role has `submit_farm`).

## Blocking rules

Farm profile tightens thresholds vs `artist_relaxed` — e.g. shader complexity, missing maps, local paths.

## Headless / Deadline job

Studios often wrap:

```bash
mayapy -m pipeline_inspector validate "$SCENE" --profile-id deadline_critical --report "$JSON"
```

Then Deadline pre/post job scripts — see [`deadline_submit_preflight.md`](../../integrations/deadline_submit_preflight.md).

## After submit

- Keep JSON report with job id for wrangler debug.
- Use **farm-analytics** CLI for historical failure patterns (TD).

## Related

- [Farm tab](../Panel/Farm-Tab)
- [Governance — submit_farm](../Administration/Governance)
