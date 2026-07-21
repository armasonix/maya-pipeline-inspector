# Maya install guide

**Product:** Maya Pipeline Inspector (`maya-pipeline-inspector`)  
**Related:** [USER_GUIDE.md](USER_GUIDE.md) · [STUDIO_OVERRIDES.md](STUDIO_OVERRIDES.md) · [ARCHITECTURE.md](ARCHITECTURE.md)

This guide documents how to load **Maya Pipeline Inspector** inside Autodesk Maya using the packaged `maya_module/` layout, and how to use an editable `pip` install as an alternative.

The module path is intended for studio deployment from a cloned or packaged repo. The `pip` path is convenient for TD workstations and for environments where `MAYA_MODULE_PATH` is not used.

## What gets installed

Regardless of install method, the UI entrypoints are the same:

| Entrypoint | Name | Behavior |
| --- | --- | --- |
| Main menu | `Pipeline Inspector` | Items: **Open Pipeline Inspector**, **Pipeline Inspector Farm Check**, **Readiness Check**, **Close Pipeline Inspector** |
| Shelf tab | `PipelineInspector` | Buttons: **Pipeline Inspector** (open panel), **Pipeline Inspector Farm Check** (Farm tab + preflight), **Readiness Check** (Readiness tab) |
| Python API | `pipeline_inspector.maya.commands` | `install_ui()`, `show_ui()`, `show_farm_check_ui()`, `show_readiness_check_ui()`, `close_ui()`, validation and export commands |

On module startup, [`maya_module/scripts/userSetup.py`](../maya_module/scripts/userSetup.py) defers UI installation and runs **dual-install detection** ([ADR 0006](adr/0006-native-mll-plugin-strategy.md)):

1. Year-specific native `.mll` at `plug-ins/{mayaYear}/` (absolute path load)
2. Top-level native `.mll` at `plug-ins/pipeline_inspector.mll` (Plug-in Manager copy)
3. Python plug-in `plug-ins/pipeline_inspector.py`
4. Direct `pipeline_inspector_bootstrap.install_ui()` when plug-in load fails

## Supported Maya versions (best-effort)

Maintainer-tested versions in this repository:

| Maya version | Status | Notes |
| --- | --- | --- |
| 2024 | Tested | Policy demos [`examples/vray_policy/vray_policy_scene.ma`](../examples/vray_policy/vray_policy_scene.ma) and [`examples/arnold_policy/arnold_policy_scene.ma`](../examples/arnold_policy/arnold_policy_scene.ma) |
| 2025 | Tested | Scanner and command unit tests target Maya 2025 APIs |
| 2026 | Best effort | Not regularly CI-tested; report issues if panel or `mayapy` integration differs |
| 2023 and earlier | Not tested | May work with PySide2-based Maya builds, but is outside the current support matrix |

Pipeline Inspector is **under active development**. Even on supported Maya versions, expect occasional panel regressions, incomplete Settings flows, and connector setup friction. See [USER_GUIDE — Known limitations & gaps](USER_GUIDE.md#known-limitations--gaps).

The UI loads Qt through PySide2 or PySide6 depending on what the active Maya build provides.

Renderer plugins (V-Ray, Arnold) are optional for opening the panel, but renderer-specific rules need the corresponding plugin loaded in the session being validated.

## Option A — `MAYA_MODULE_PATH` (recommended for repo checkout)

### 1. Clone or sync the repository

```bash
git clone https://github.com/armasonix/maya-pipeline-inspector.git
cd maya-pipeline-inspector
```

### 2. Point Maya at the module folder

Add the `maya_module` directory to `MAYA_MODULE_PATH` before launching Maya.

Windows (PowerShell, current session):

```powershell
$env:MAYA_MODULE_PATH = "D:\tools\maya-pipeline-inspector\maya_module"
& "C:\Program Files\Autodesk\Maya2025\bin\maya.exe"
```

Linux/macOS (bash, current session):

```bash
export MAYA_MODULE_PATH="/tools/maya-pipeline-inspector/maya_module"
maya
```

For a persistent studio setup, set `MAYA_MODULE_PATH` in the facility launcher, shell profile, or render wrangler environment the same way you manage other Maya modules. Roll out `pipeline_inspector_studio.json` the same way via `PIPELINE_INSPECTOR_STUDIO_CONFIG` (see [Studio config rollout](#studio-config-rollout-pipeline_inspector_studiojson) below).

### 3. What the module file does

[`maya_module/pipeline_inspector.mod`](../maya_module/pipeline_inspector.mod):

```text
+ pipeline_inspector 0.4 .
PYTHONPATH +:= ../src
scripts: scripts
shelves: shelves
plug-ins: plug-ins
```

- `plug-ins: plug-ins` exposes both the Python fallback (`pipeline_inspector.py`) and any built native binaries (`pipeline_inspector.mll`, plus year folders `2024/`, `2025/`, `2026/`).

- `PYTHONPATH +:= ../src` adds the repository `src/` folder so `import pipeline_inspector` resolves without a separate `pip` install.
- `scripts: scripts` puts `maya_module/scripts/` on Maya's script path so `userSetup.py` runs at startup.
- `shelves: shelves` publishes the optional MEL shelf helper in `maya_module/shelves/`.

### 4. Dual install detection and startup behavior

[`pipeline_inspector_bootstrap.py`](../maya_module/scripts/pipeline_inspector_bootstrap.py) resolves the active Maya year from `cmds.about(version=True)` and picks the first available delivery path:

| Priority | `detect_install_mode` | File | Notes |
| --- | --- | --- | --- |
| 1 | `native_year` | `plug-ins/{year}/pipeline_inspector.mll` | Preferred when built for the running Maya year; loaded by **absolute path** (Maya does not search plug-in subfolders by relative name). |
| 2 | `native_manager` | `plug-ins/pipeline_inspector.mll` | Top-level copy created by `tools/build_native_plugin.ps1` so Plug-in Manager can browse the native binary. |
| 3 | `python` | `plug-ins/pipeline_inspector.py` | Default for source checkouts without a local native build. |
| 4 | `module_only` | _(no plug-in file)_ | `userSetup.py` calls `install_ui()` directly. |

At Maya launch:

1. Maya executes `maya_module/scripts/userSetup.py`.
2. `userSetup.py` defers `_install_pipeline_inspector_ui()`.
3. If `pipeline_inspector` is already loaded, startup exits early.
4. Otherwise `userSetup.py` tries each path from `plugin_load_candidates()` in order.
5. When a plug-in loads, `initializePlugin` defers `pipeline_inspector_bootstrap.install_ui()`.
6. If every plug-in load fails, `userSetup.py` falls back to `install_ui()` directly.
7. After UI initialization, `install_ui()` creates the **Pipeline Inspector** menu and **PipelineInspector** shelf buttons.
8. If installation fails, Maya prints a warning: `Pipeline Inspector UI install failed: ...`.

Troubleshooting in Script Editor:

```python
import pipeline_inspector_bootstrap as bootstrap
from maya import cmds

print(bootstrap.describe_dual_install(
    bootstrap.resolve_maya_year(lambda: cmds.about(version=True))
))
print(cmds.pluginInfo("pipeline_inspector", q=True, path=True))
```

Expected native load: `plugin_path` ends with `.mll` under `plug-ins/2024/` (or the top-level manager copy).

The bootstrap module also ensures the repository `src/` directory is on `sys.path` before importing `pipeline_inspector`, even if the `.mod` path is customized.

## Plug-in Manager: dual install (native `.mll` + Python fallback)

| Delivery | File | When used |
| --- | --- | --- |
| Native year build | `plug-ins/{year}/pipeline_inspector.mll` | Built for the running Maya year; highest priority at startup |
| Native manager copy | `plug-ins/pipeline_inspector.mll` | Same binary copied to plug-ins root for Plug-in Manager browsing |
| Python fallback | `plug-ins/pipeline_inspector.py` | Source checkout or machines without a devkit build |
| Module-only fallback | `pipeline_inspector_bootstrap.install_ui()` | All plug-in loads failed |

Do **not** load both `.mll` and `.py` at the same time — they register the same plug-in name (`pipeline_inspector`). `userSetup.py` loads the first successful candidate only.

The native `.mll` is a **thin C++ bootstrap** only — it calls the same `pipeline_inspector_bootstrap` Python module as the `.py` plug-in. Validation and UI logic are unchanged. Build requirements and per-year matrix: [ADR 0006](adr/0006-native-mll-plugin-strategy.md).

### Build the native plug-in (optional)

CMake scaffold lives in [`native/`](../native/README.md). From the repo root (Windows example):

```powershell
.\tools\build_native_plugin.ps1 -MayaVersion 2025
```

This installs `pipeline_inspector.mll` to `maya_module/plug-ins/{year}/` and copies it to `maya_module/plug-ins/pipeline_inspector.mll` for Plug-in Manager.

## Plug-in Manager workflow

| Path | Plug-in Manager | Module `userSetup` |
| --- | --- | --- |
| Dual install (recommended) | Lists `.mll` and `.py` at plug-ins root; year binaries under `2024/` etc. are loaded by absolute path | Detects year → native → `.py` → bootstrap |
| Module-only (backward compatible) | Plug-in not loaded | Direct `install_ui()` fallback |

1. Ensure `MAYA_MODULE_PATH` points at `maya_module/` (see Option A above).
2. Open **Settings → Plug-in Manager**.
3. Enable **Loaded** for `pipeline_inspector` (native `.mll` under `plug-ins/{year}/` when built, or `pipeline_inspector.py` fallback).
4. Confirm the **Pipeline Inspector** menu and **PipelineInspector** shelf appear.
5. Unload the plugin to remove menu, shelf, and panel without restarting Maya.

### `autoLoad` studio policy

- **Manual load (default):** leave `autoLoad` off so TDs control when Pipeline Inspector UI appears.
- **Auto load:** enable `autoLoad` in Plug-in Manager or rely on `userSetup.py`, which calls `cmds.loadPlugin(..., quiet=True)` when your facility wants the panel available in every interactive session.
- **Farm / `mayapy`:** headless validation does **not** require plugin load; use `mayapy -m pipeline_inspector ...` instead.

### 5. Verify in Maya

After Maya finishes loading:

```python
from maya import cmds

print(cmds.menu("pipelineInspectorMenu", q=True, exists=True))      # expect True
print(cmds.shelfButton("pipelineInspectorShelfButton", q=True, exists=True))  # expect True
print(cmds.shelfButton("pipelineInspectorFarmCheckShelfButton", q=True, exists=True))  # expect True

from pipeline_inspector.maya.commands import show_ui
show_ui()
```

Then open a **policy demo scene** (load the matching renderer) and run **Validate Scene**:

- `examples/vray_policy/vray_policy_scene.ma` (V-Ray)
- `examples/arnold_policy/arnold_policy_scene.ma` (Arnold)

See [`examples/vray_policy/README.md`](../examples/vray_policy/README.md) and [`examples/arnold_policy/README.md`](../examples/arnold_policy/README.md).

## Option B — Editable `pip` install (TD / workstation alternative)

Use this when you prefer installing the package into Maya's Python environment instead of relying on `MAYA_MODULE_PATH`.

### 1. Install into Maya's Python

Windows example with Maya 2025:

```powershell
& "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" -m pip install --upgrade pip
& "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" -m pip install -e "D:\tools\maya-pipeline-inspector"
```

Use the `mayapy` executable that matches the Maya version Technical Artists launch.

### 2. Install UI entrypoints for the session

In Maya's Script Editor:

```python
from pipeline_inspector.maya.commands import install_ui, show_ui

install_ui()
show_ui()
```

To load the UI automatically, wrap the same calls in a studio `userSetup.py` or shelf button.

### 3. Headless validation with `mayapy`

```bash
mayapy -m pipeline_inspector validate scene.ma --profile-id publish_strict --report report.json
```

Scene validation requires `mayapy`; regular system Python can validate snapshot JSON inputs only.

## Studio config rollout (`pipeline_inspector_studio.json`)

Pipeline TDs deploy one JSON file for studio-wide policy: pipeline toggles, network path roots, connector credentials, bug-report relay URL, and waiver/manifest defaults. Per-machine user preferences stay in `~/.pipeline_inspector/user.json` (see [ADR 0007](adr/0007-settings-and-connectors-architecture.md)).

### Discovery order

The Maya panel and headless CLI (`validate`, `manifest`, `gate`) resolve the same file:

| Priority | Source |
| --- | --- |
| 1 | `PIPELINE_INSPECTOR_STUDIO_CONFIG` environment variable (absolute path to a JSON file) |
| 2 | `~/.pipeline_inspector/pipeline_inspector_studio.json` |
| 3 | `~/pipeline_inspector_studio.json` |

Headless CLI also accepts `--studio-config /path/to/pipeline_inspector_studio.json`, which overrides env and default discovery.

### Recommended facility rollout

1. Place `pipeline_inspector_studio.json` on a network share (for example `\\pipeline\config\pipeline_inspector\pipeline_inspector_studio.json`).
2. Set `PIPELINE_INSPECTOR_STUDIO_CONFIG` in the facility Maya launcher, farm wrangler environment, and Deadline worker setup so interactive and headless sessions load the same file.
3. Keep files with connector tokens and relay API keys out of git — see [STUDIO_OVERRIDES.md](STUDIO_OVERRIDES.md).

Windows launcher (PowerShell):

```powershell
$env:PIPELINE_INSPECTOR_STUDIO_CONFIG = "\\pipeline\config\pipeline_inspector\pipeline_inspector_studio.json"
& "C:\Program Files\Autodesk\Maya2025\bin\maya.exe"
```

Linux/macOS:

```bash
export PIPELINE_INSPECTOR_STUDIO_CONFIG="/pipeline/config/pipeline_inspector/pipeline_inspector_studio.json"
maya
```

Headless validation with the same studio policy:

```bash
export PIPELINE_INSPECTOR_STUDIO_CONFIG="/pipeline/config/pipeline_inspector/pipeline_inspector_studio.json"
mayapy -m pipeline_inspector validate scene.ma --profile-id publish_strict --report report.json
```

Or pass the path explicitly:

```bash
mayapy -m pipeline_inspector validate scene.ma \
  --studio-config /pipeline/config/pipeline_inspector/pipeline_inspector_studio.json \
  --profile-id publish_strict \
  --report report.json
```

### Edit in the Maya Settings screen

TDs with write access to the deployed file can use **Settings → Studio** / **Studio Environment** / **Connectors** and **Save Studio Config**. The status banner shows which path is loaded. First save without discovery prompts for a target path.

Schema **2.0** sections include `studio_name`, `pipeline`, `studio_environment`, `connectors`, and `bug_report`, plus optional `ui` and `updates`. Legacy **1.0** files load with defaults for missing sections and migrate to **2.0** on save.

Full rollout templates, secret handling, and how studio policy relates to custom rule packs: [STUDIO_OVERRIDES.md](STUDIO_OVERRIDES.md).

## Optional MEL shelf helper

[`maya_module/shelves/shelf_PipelineInspector.mel`](../maya_module/shelves/shelf_PipelineInspector.mel) defines two shelf buttons:

- **Pipeline Inspector** — opens the dockable panel
- **Pipeline Inspector Farm Check** — opens the **Farm** tab and runs `deadline_critical` preflight

The open-panel button calls:

```python
import pipeline_inspector_bootstrap
pipeline_inspector_bootstrap.show()
```

Studios that already manage shelves through MEL can use this file directly. The default startup path still uses the Python `install_shelf()` helper from `userSetup.py`.

## Manual PYTHONPATH (legacy fallback)

If you cannot use `MAYA_MODULE_PATH` or `pip`, add the repository `src/` directory to `PYTHONPATH`, then run `install_ui()` manually:

```python
import sys
sys.path.insert(0, r"D:\tools\maya-pipeline-inspector\src")

from pipeline_inspector.maya.commands import install_ui, show_ui
install_ui()
show_ui()
```

Prefer **Option A** or **Option B** for repeatable studio rollout.

## In-app updates (Check for Updates)

When the plugin is installed via **Option A** (`MAYA_MODULE_PATH` + full repo checkout), Technical Artists and TDs can use the panel header **Check for Updates** button to download a GitHub Release and install it with config preservation and rollback.

**Option B (`pip`)** and legacy `PYTHONPATH`-only layouts are not updated in-place by the wizard — use `mayapy -m pip install -U` and restart Maya instead.

Full flow, studio policy fields, staging paths, and the **Maya restart checklist**: [`docs/integrations/auto_update.md`](integrations/auto_update.md).

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `No module named 'pipeline_inspector'` | Package not on Maya `PYTHONPATH` | Use `MAYA_MODULE_PATH`, editable `pip` install, or bootstrap/`src` path |
| `Pipeline Inspector UI install failed` on startup | Import error before UI wiring | Open Script Editor traceback; confirm `src/` exists relative to `maya_module/` |
| Menu exists but panel does not open | Qt import issue in the active Maya build | Confirm Maya version is in the support matrix; test `show_ui()` in Script Editor |
| Validation returns empty renderer rules | Renderer plugin not loaded | Load V-Ray or Arnold before validating renderer-specific scenes |
| `scene validation requires Autodesk Maya / mayapy` in CLI | Running scene validation outside Maya | Use `mayapy -m pipeline_inspector ...` |

## Uninstall / disable

For the module path:

1. Remove the repo path from `MAYA_MODULE_PATH`.
2. Restart Maya.

For a `pip` install:

```bash
mayapy -m pip uninstall maya-pipeline-inspector
```

To remove only the current session menu/shelf/panel:

```python
from pipeline_inspector.maya.commands import uninstall_ui

uninstall_ui()
```

When using Plug-in Manager, unloading `pipeline_inspector` runs the same cleanup via `uninitializePlugin`.

## Related docs

- [`USER_GUIDE.md`](USER_GUIDE.md) — Technical Artist and TD workflow inside the panel
- [`STUDIO_OVERRIDES.md`](STUDIO_OVERRIDES.md) — rolling `pipeline_inspector_studio.json` and custom rule packs
- [`adr/0007-settings-and-connectors-architecture.md`](adr/0007-settings-and-connectors-architecture.md) — studio vs user config split
- [`integrations/publish_submit_preflight.md`](integrations/publish_submit_preflight.md) — publish gate example
- [`integrations/deadline_submit_preflight.md`](integrations/deadline_submit_preflight.md) — Deadline 10 on-prem integration guide (v0.4)
- [`integrations/auto_update.md`](integrations/auto_update.md) — Check for Updates wizard, module vs pip paths, restart checklist (v0.5)

## Automated checks

Bootstrap behavior is covered by unit tests:

```bash
python -m pytest tests/unit/test_maya_module_bootstrap.py -v
```

Integration tests can run under system Python (default public CI) or through `mayapy` when Maya is available:

```bash
mayapy -m pip install -e ".[dev]"
mayapy -m pytest tests/integration -v
```

When validating v0.3 manifest automation locally, also run:

```bash
# Policy demo (manual / portfolio); legacy headless.ma still works for CI fixtures
DEMO_SCENE="examples/vray_policy/vray_policy_scene.ma"
OUT_MANIFEST="/tmp/pipeline_inspector_manifest_smoke.json"
GATE_REPORT="/tmp/pipeline_inspector_gate_smoke.json"

mayapy -m pipeline_inspector manifest "$DEMO_SCENE" \
  --out "$OUT_MANIFEST" \
  --profile-id publish_strict

mayapy -m pipeline_inspector gate "$DEMO_SCENE" "$OUT_MANIFEST" \
  --profile-id publish_strict \
  --out "$GATE_REPORT"
```

### Optional GitHub Actions workflow (maintainers)

Real Maya integration runs on a **self-hosted runner** labeled `self-hosted` and `maya`. The workflow is [`.github/workflows/maya-integration.yml`](../.github/workflows/maya-integration.yml).

| Trigger | When it runs |
|---------|----------------|
| `workflow_dispatch` | Manual run from **Actions → Maya integration** |
| `schedule` | Weekly (Monday 06:00 UTC) on the default branch |
| `pull_request` | Same-repo PRs only, when paths under `src/pipeline_inspector/maya/`, `maya_module/`, `tests/integration/`, or related examples change |

**Fork pull requests are skipped** — untrusted code must not execute on a studio self-hosted runner.

#### Runner setup

1. Register a self-hosted runner with labels **`self-hosted`** and **`maya`**. **Git Bash / pwsh are not required** — the workflow uses **Windows PowerShell** and `cmd` for the resolve step.
2. Install Autodesk Maya on that machine.
3. Configure **one** of these so the workflow can find `mayapy`:
   - Repository secret **`MAYA_PY`** (recommended) — absolute path, e.g. `C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe`
   - Repository variable **`MAYA_PY`**
   - Runner environment variable **`MAYA_PY`**
   - Workflow dispatch input **`mayapy_path`** (one-off override)
   - `mayapy` on `PATH`

4. In GitHub: **Actions → Maya integration → Run workflow** (optional `mayapy_path` input).

**Failure behavior:** when the job runs on the self-hosted runner, a missing or invalid `mayapy` path **fails the job** (exit code 1). There is no silent skip that reports success without Maya.

**Public forks / no runner:** if no runner matches `[self-hosted, maya]`, the workflow stays queued until timeout. Fork PRs never schedule this job.

#### Smoke steps (v0.4)

Demo scene for integration smoke: [`examples/vray_policy/vray_policy_scene.ma`](../examples/vray_policy/vray_policy_scene.ma) (load V-Ray) or [`examples/arnold_policy/arnold_policy_scene.ma`](../examples/arnold_policy/arnold_policy_scene.ma) (load Arnold).

After `pytest tests/integration`:

1. `pipeline_inspector validate` (publish_strict) — report written; exit codes 0–2 accepted
2. `pipeline_inspector manifest` — schema **1.1**
3. `pipeline_inspector gate` — baseline = freshly exported manifest (no regression expected)
4. `examples/deadline/submit_preflight.py` — `deadline_critical` profile dry-run; exit codes 0–2 accepted

Default CI in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) stays Maya-free.

#### Local Windows example

```powershell
$env:MAYA_PY = "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe"
$SCENE = "examples\vray_policy\vray_policy_scene.ma"
& $env:MAYA_PY -m pip install -e ".[dev]"
& $env:MAYA_PY -m pytest tests/integration -v
& $env:MAYA_PY -m pipeline_inspector validate $SCENE --input-kind scene --profile-id publish_strict --report "$env:TEMP\validate_smoke.json"
& $env:MAYA_PY examples\deadline\submit_preflight.py $SCENE `
  --report "$env:TEMP\deadline_preflight_smoke.json" `
  --profile "src\pipeline_inspector\rules\profiles\deadline_critical.json" `
  --repo-root (Get-Location) `
  --mayapy $env:MAYA_PY
```

See also [`docs/CLI_TESTING.md`](CLI_TESTING.md).
