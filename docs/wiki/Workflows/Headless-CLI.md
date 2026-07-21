# Headless CLI

Same validation engine as the panel — for publish hooks, farm wrappers, and CI.

## Entry point

```bash
mayapy -m pipeline_inspector --help
# or system Python for snapshot-only inputs:
python -m pipeline_inspector --help
```

Scene validation **requires `mayapy`** (Maya APIs). Snapshot JSON validation can run without Maya.

## Core commands

| Command | Purpose |
| --- | --- |
| `validate` | Run rules; write JSON report |
| `manifest` | Export shader manifest (schema 1.1) |
| `diff` | Diff two reports or manifests |
| `gate` | Manifest regression gate |
| `apply-fixes` | Apply fix plan ([ADR 0004](../../adr/0004-headless-apply-fixes-policy.md)) |
| `rules validate` | Lint rule pack JSON |
| `farm-analytics` | Deadline farm QA analytics (v0.6) |

## Examples

```bash
# Validate scene
mayapy -m pipeline_inspector validate hero.ma \
  --profile-id publish_strict \
  --studio-config /pipeline/studio.json \
  --report /tmp/report.json

# Gate against baseline
mayapy -m pipeline_inspector gate hero.ma approved_manifest.json \
  --profile-id publish_strict

# Dry-run fixes
mayapy -m pipeline_inspector apply-fixes hero.ma \
  --fix-plan /tmp/plan.json --dry-run
```

## Studio config

CLI respects `PIPELINE_INSPECTOR_STUDIO_CONFIG` and `--studio-config`. User panel prefs may differ — known gap ([Capability matrix](../Reference/Capability-Matrix)).

## Full reference

→ [CLI reference](../Reference/CLI-Reference) · [`CLI_TESTING.md`](../../CLI_TESTING.md)
