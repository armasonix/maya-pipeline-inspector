# Studio custom rules and profile overrides

This guide explains how studios extend Maya Shader Health Inspector with show-specific rule packs and profile JSON without forking the core validator. It also documents how to roll out the studio-wide settings file `shader_health_studio.json` via `SHADER_HEALTH_STUDIO_CONFIG`.

Use it together with:

- [MAYA_INSTALL.md](MAYA_INSTALL.md) — loading the tool inside Maya and setting `SHADER_HEALTH_STUDIO_CONFIG` in facility launchers
- [adr/0007-settings-and-connectors-architecture.md](adr/0007-settings-and-connectors-architecture.md) — studio vs user config split and schema 2.0
- [RULE_AUTHORING.md](RULE_AUTHORING.md) — rule schema, check types, and policy fields
- [adr/0002-renderer-adapter-boundary.md](adr/0002-renderer-adapter-boundary.md) — where renderer-specific logic belongs

## Studio config file (`shader_health_studio.json`)

Studios roll out pipeline policy, network paths, and connector settings through a single JSON file. That file is separate from the custom rule packs and profile overrides covered later in this guide.

| Concern | File | Rollout mechanism |
| --- | --- | --- |
| Studio-wide policy | `shader_health_studio.json` | `SHADER_HEALTH_STUDIO_CONFIG` env var (recommended) |
| Per-machine UI prefs | `~/.shader_health/user.json` | Local user home (not synced by IT) |

### Deploy via `SHADER_HEALTH_STUDIO_CONFIG`

Set the environment variable to an **absolute path** (local or UNC/network) before Maya or `mayapy` starts:

```powershell
# Windows — facility launcher or user profile
$env:SHADER_HEALTH_STUDIO_CONFIG = "\\pipeline\config\shader_health\shader_health_studio.json"
```

```bash
# Linux / macOS
export SHADER_HEALTH_STUDIO_CONFIG="/pipeline/config/shader_health/shader_health_studio.json"
```

Discovery precedence (same in the Maya panel and headless CLI):

1. `SHADER_HEALTH_STUDIO_CONFIG` when the file exists
2. `~/.shader_health/shader_health_studio.json`
3. `~/shader_health_studio.json`

Headless CLI also accepts `--studio-config <path>`, which takes priority over env and default paths.

Validate that a workstation picked up the rollout:

```bash
python -c "from shader_health.studio_config import discover_studio_config_path; print(discover_studio_config_path())"
```

In Maya Script Editor after launch:

```python
from shader_health.studio_config import StudioConfig

print(StudioConfig.default().config_path)
print(StudioConfig.default().studio_name)
```

### Minimal rollout template (schema 2.0)

```json
{
  "schema_version": "2.0",
  "studio_name": "Example Studio",
  "pipeline": {
    "require_tx_derivatives": true,
    "waiver_defaults": {
      "default_approved_by": "pipeline_td",
      "default_expiry_days": 30,
      "allow_critical_waivers": false
    },
    "manifest_gate_defaults": {
      "max_new_changes": 0,
      "max_fingerprint_changes": 0,
      "block_on_new_textures": true
    },
    "pinned_workflow_profile_ids": ["publish_strict", "deadline_critical"],
    "pinned_asset_class_profile_ids": []
  },
  "studio_environment": {
    "texture_root": "\\\\farm\\textures",
    "asset_root": "\\\\farm\\assets",
    "cache_root": "\\\\farm\\cache",
    "render_root": "\\\\farm\\render",
    "variable_aliases": {
      "STUDIO_TEXTURE_ROOT": "\\\\farm\\textures"
    }
  },
  "connectors": {
    "deadline": {
      "enabled": true,
      "api_url": "http://deadline-web:8081",
      "profile_id": "deadline_critical"
    }
  },
  "bug_report": {
    "enabled": false,
    "relay_url": "",
    "api_key": ""
  }
}
```

Expand `connectors` for Telegram, Discord, Slack, Ftrack, ShotGrid, and Cerebro as needed. See [ADR 0007](adr/0007-settings-and-connectors-architecture.md) for the full schema and secret-field policy.

### Version control and secrets

| Rule | Detail |
| --- | --- |
| Do not commit | `shader_health_studio.json` with connector tokens, relay API keys, or internal URLs |
| Do commit | Sanitized templates (`.example.json`) and facility deployment runbooks |
| Prefer | Network share + `SHADER_HEALTH_STUDIO_CONFIG`; restrict write access to pipeline TD / IT |
| User JSON | `user.json` holds theme and local `extra_rule_paths` only — never connector secrets |

Legacy **schema 1.0** files (`pipeline.require_tx_derivatives`, `connectors.deadline`) still load. Saving from the Settings screen rewrites **2.0** with default sections for `studio_environment`, `waiver_defaults`, and related fields.

### How studio config relates to custom rules

| Mechanism | What it controls |
| --- | --- |
| `shader_health_studio.json` → `pipeline` | Require `.tx`, waiver defaults, manifest gate defaults, optional pinned profile lists |
| `shader_health_studio.json` → `studio_environment` | `${STUDIO_*_ROOT}` path substitution during validation |
| `--extra-rules` / user `extra_rule_paths` | Additional rule JSON layered on packaged rules (below) |
| Custom profile JSON | Per-step `rule_overrides` (below) |

Studio policy cannot be overridden by user preferences. Custom rules and profiles stack on top at validation time.

## What studios typically customize

| Need | Mechanism |
| --- | --- |
| Add show/facility rules | Extra rule file or folder via `--extra-rules` / `extra_rule_paths` |
| Tune severity and blocking per pipeline step | Custom profile JSON with `rule_overrides` |
| Replace packaged rule packs entirely | `--rule-root` pointing at a studio mirror of `src/shader_health/rules/` |
| Keep base rules upstream | Leave packaged `common/`, `vray/`, `arnold/` untouched; layer extras on top |

The validation pipeline always loads rules in this order:

1. `common/`
2. Renderer packs for the active snapshot renderer (`vray`, `arnold`, …)
3. Sorted `extra_rule_paths`
4. Profile overrides from `--profile` or packaged `--profile-id`

Later rule files replace earlier rules with the same `id`.

## Packaged rule pack layout

The reference layout lives under [`src/shader_health/rules/`](../src/shader_health/rules/):

```text
rules/
├── common/           # renderer-agnostic checks
├── vray/             # V-Ray policy packs
├── arnold/           # Arnold policy packs
└── profiles/         # packaged profile overrides
    ├── artist_relaxed.json
    ├── publish_strict.json
    ├── deadline_critical.json
    ├── supervisor_full.json
    └── ci_headless.json
```

Studio mirrors often copy this skeleton into a facility config repo:

```text
/show/config/shader_health/
├── common/
├── vray/
├── arnold/
├── studio/           # show-only rules
└── profiles/
    └── show_publish_strict.json
```

Validate studio rule JSON before rollout:

```bash
python tools/validate_rules.py examples/studio/rules
```

Profile overrides are validated against the loaded rule stack in unit tests and when `tools/validate_rules.py` validates the packaged rule root (it checks packaged `profiles/` entries against packaged rules). For studio profiles, load the same rule stack production uses and call `validate_profile_overrides()` — see [`tests/unit/test_studio_overrides_example.py`](../tests/unit/test_studio_overrides_example.py).

Fixture examples for valid/invalid rule JSON live under [`tests/fixtures/rules/`](../tests/fixtures/rules/).

## Extra rules (`--extra-rules` / `extra_rule_paths`)

### Headless CLI

Pass one or more rule files or folders after the packaged rule root is resolved:

```bash
mayapy -m shader_health validate scene.ma \
  --profile examples/studio/profiles/show_publish_strict.json \
  --extra-rules examples/studio/rules \
  --report report.json
```

`--extra-rules` accepts:

- a single rule JSON file (`{"rules": [...]}` or one rule object)
- a folder searched recursively for `*.json`

### Python API

[`run_validation()`](../src/shader_health/maya/validation_pipeline.py) exposes the same hook:

```python
from pathlib import Path

from shader_health.maya.validation_pipeline import run_validation

run = run_validation(
    snapshot,
    profile_path=Path("examples/studio/profiles/show_publish_strict.json"),
    extra_rule_paths=(Path("examples/studio/rules"),),
    scan_scope="scene",
)
```

### Maya UI pipeline

The dockable panel loads packaged profiles from the dropdown and uses the default packaged rule root. It does **not** expose an extra-rules picker in v0.2.

Studios that need custom rules inside Maya can call the shared pipeline directly from a facility bootstrap script:

```python
from pathlib import Path

from shader_health.maya.validation_pipeline import run_validation
from shader_health.maya.scanner import scan_scene

SHOW_RULES = Path("/show/config/shader_health/studio")
SHOW_PROFILE = Path("/show/config/shader_health/profiles/show_publish_strict.json")

snapshot = scan_scene()
run = run_validation(
    snapshot,
    profile_path=SHOW_PROFILE,
    extra_rule_paths=(SHOW_RULES,),
)
```

Wire that into a custom menu item, publish hook, or extended `userSetup.py` bootstrap. Renderer-specific checks still belong in renderer adapters and renderer rule packs per [ADR 0002](adr/0002-renderer-adapter-boundary.md).

## Custom profile JSON

Profiles never redefine rules. They override packaged or studio rule behavior through `rule_overrides`.

Allowed override fields per rule id:

| Field | Effect |
| --- | --- |
| `enabled` | Turn a rule on or off for this profile |
| `severity` | Change reported severity |
| `block_publish` | Publish gate flag on failed results |
| `block_deadline` | Farm/Deadline gate flag on failed results |
| `waiver_allowed` | Whether waivers may suppress the rule |
| `auto_fix_allowed` | Whether fix planning may include the rule |

### Packaged profile id vs custom profile path

| Entrypoint | Packaged id | Custom JSON path |
| --- | --- | --- |
| CLI | `--profile-id publish_strict` | `--profile /show/config/.../show_publish_strict.json` |
| `run_validation()` | `profile_id="publish_strict"` | `profile_path=Path("...")` |

When `--profile` / `profile_path` is supplied, `--profile-id` is ignored.

## Worked example (repo `examples/studio/`)

This repository ships a minimal studio overlay used in docs and unit tests.

### 1. Studio rule pack

[`examples/studio/rules/show_path_policy.json`](../examples/studio/rules/show_path_policy.json) adds:

- rule id: `studio.texture.path.no_user_home`
- check: `path_policy` with `disallow: ["user_home"]`
- default policy: warning-only (`block_publish: false`)

### 2. Show profile overrides

[`examples/studio/profiles/show_publish_strict.json`](../examples/studio/profiles/show_publish_strict.json):

- disables `common.texture.version.latest` for publish (`enabled: false`)
- strengthens `common.texture.path.local_drive` blocking
- enables the studio rule as **critical** with `block_publish: true`

### 3. Run the example headlessly

```bash
python -m shader_health validate \
  tests/fixtures/snapshots/texture_freshness_outdated.json \
  --input-kind snapshot \
  --profile examples/studio/profiles/show_publish_strict.json \
  --extra-rules examples/studio/rules \
  --report /tmp/show_publish_strict_report.json
```

The snapshot fixture keeps the example deterministic without Maya. Swap the input for a `.ma` scene and run through `mayapy` in production.

### 4. Expected override behavior

After loading the example stack:

- `common.texture.version.latest` is not evaluated (`enabled: false`)
- `studio.texture.path.no_user_home` inherits studio severity/block flags from the profile
- `common.texture.path.local_drive` keeps its base rule definition but uses stricter `block_publish` / `block_deadline` from the profile

## Profile validation and unknown rule ids

`tools/validate_rules.py` loads the packaged rule stack and verifies that every `rule_overrides` key exists in the loaded rule set. Unknown ids fail validation:

```text
profile 'show_publish_strict' references unknown rule(s): missing.rule.id
```

When you validate a studio profile, include the same `--extra-rules` folders (or custom `--rule-root`) that production will use so override keys for studio rule ids are recognized.

`apply_profile_overrides()` only mutates rules that are present in the loaded stack. Overrides for renderer rules that are not loaded in the current session are ignored rather than failing at runtime.

## Recommended studio workflow

1. Author or copy base rule packs using [RULE_AUTHORING.md](RULE_AUTHORING.md).
2. Place show-only rules in a dedicated folder (for example `studio/` or `show_xyz/`).
3. Create profile JSON per pipeline step: publish, daily review, farm preflight.
4. Validate JSON with `python tools/validate_rules.py`.
5. Wire headless gates through [`publish_submit_preflight.md`](integrations/publish_submit_preflight.md) or [`deadline_submit_preflight.md`](integrations/deadline_submit_preflight.md).
6. Keep renderer-specific material semantics inside renderer adapters and renderer packs per [ADR 0002](adr/0002-renderer-adapter-boundary.md).

## Related docs

- [MAYA_INSTALL.md](MAYA_INSTALL.md) — loading the tool inside Maya and `SHADER_HEALTH_STUDIO_CONFIG` in launchers
- [adr/0007-settings-and-connectors-architecture.md](adr/0007-settings-and-connectors-architecture.md) — studio vs user config split
- [RULE_AUTHORING.md](RULE_AUTHORING.md) — authoring individual rules and profile override syntax
- [integrations/publish_submit_preflight.md](integrations/publish_submit_preflight.md) — publish gate using `--profile`
- [integrations/deadline_submit_preflight.md](integrations/deadline_submit_preflight.md) — farm gate using `--profile`

## Automated checks

The worked example is covered by:

```bash
python -m pytest tests/unit/test_studio_overrides_example.py -v
```
