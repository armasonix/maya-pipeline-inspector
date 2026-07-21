# Studio configuration

Deploy facility-wide policy with **`pipeline_inspector_studio.json`** (schema **2.0**).

## Discovery order

1. `PIPELINE_INSPECTOR_STUDIO_CONFIG` env var (absolute path)
2. `~/.pipeline_inspector/pipeline_inspector_studio.json`
3. `~/pipeline_inspector_studio.json`

CLI override: `--studio-config /path/to/file.json`

## Rollout pattern

```powershell
# Facility launcher
$env:PIPELINE_INSPECTOR_STUDIO_CONFIG = "\\pipeline\config\pipeline_inspector_studio.json"
& "C:\Program Files\Autodesk\Maya2025\bin\maya.exe"
```

Deploy same file to Deadline workers for headless parity.

## Schema sections (2.0)

| Section | Purpose |
| --- | --- |
| `studio_name` | Display label |
| `pipeline` | Rule paths, defaults, toggles |
| `studio_environment` | Texture/asset/cache/render roots |
| `connectors` | Deadline, trackers, notifications |
| `bug_report` | Relay URL, metadata |
| `readiness.checks` | Machine probes |
| `governance` | Role enforcement, capability denials |
| `updates` | Auto-update pins |

Legacy 1.0 files migrate on save.

## Secrets

Never commit tokens or relay API keys. Use env substitution or secure share ACLs.

Full reference: [`STUDIO_OVERRIDES.md`](../../STUDIO_OVERRIDES.md)

## Panel editing

TDs with write access: Settings → Studio / Connectors → **Save Studio Config**. Banner shows loaded path.

## Related

- [Settings hub](../Panel/Settings-Hub)
- [Governance](Governance)
- [`MAYA_INSTALL.md` — Studio config rollout](../../MAYA_INSTALL.md)
