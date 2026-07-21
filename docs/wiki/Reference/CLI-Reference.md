# CLI reference

Entry: `mayapy -m pipeline_inspector` (scene ops) or `python -m pipeline_inspector` (snapshot JSON).

## validate

```bash
mayapy -m pipeline_inspector validate SCENE.ma \
  [--profile-id ID] \
  [--studio-config PATH] \
  [--report PATH] \
  [--selection]
```

Validates `.ma`/`.mb`, snapshot JSON, or USD asset (with optional `[usd]` extra).

## manifest

```bash
mayapy -m pipeline_inspector manifest SCENE.ma --out manifest.json
```

Shader manifest schema 1.1 — textures, fingerprints, dimensions.

## gate

```bash
mayapy -m pipeline_inspector gate SCENE.ma BASELINE.json [--profile-id ID]
```

Regression gate — non-zero exit on blocking drift.

## diff

```bash
mayapy -m pipeline_inspector diff A.json B.json [--html out.html]
```

## apply-fixes

```bash
mayapy -m pipeline_inspector apply-fixes SCENE.ma --fix-plan plan.json [--dry-run]
```

## rules validate

```bash
python -m pipeline_inspector rules validate path/to/rules/
```

## farm-analytics

```bash
python -m pipeline_inspector farm-analytics --help
```

Read-only Deadline farm QA analytics — [`deadline_farm_analytics.md`](../../integrations/deadline_farm_analytics.md).

## Exit codes

Use `--help` on each command. Publish hooks typically treat blocking validation as non-zero.

## Testing

→ [`CLI_TESTING.md`](../../CLI_TESTING.md)

## Snapshot schema

→ [`SNAPSHOT_SCHEMA.md`](../../SNAPSHOT_SCHEMA.md)
