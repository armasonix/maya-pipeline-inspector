# Maya install guide

This guide documents how to load **Maya Shader Health Inspector** inside Autodesk Maya using the packaged `maya_module/` layout, and how to use an editable `pip` install as an alternative.

The module path is intended for studio deployment from a cloned or packaged repo. The `pip` path is convenient for TD workstations and for environments where `MAYA_MODULE_PATH` is not used.

## What gets installed

Regardless of install method, the UI entrypoints are the same:

| Entrypoint | Name | Behavior |
| --- | --- | --- |
| Main menu | `Shader Health` | Items: **Open Shader Health Inspector**, **Close Shader Health Inspector** |
| Shelf tab | `ShaderHealth` | Button: **Shader Health** — opens the dockable panel |
| Python API | `shader_health.maya.commands` | `install_ui()`, `show_ui()`, `close_ui()`, validation and export commands |

On module startup, [`maya_module/scripts/userSetup.py`](../maya_module/scripts/userSetup.py) defers UI installation. **v0.3** tries `cmds.loadPlugin("shader_health_inspector.py")` first, then falls back to [`shader_health_inspector_bootstrap.install_ui()`](../maya_module/scripts/shader_health_inspector_bootstrap.py). **v0.4** ([ADR 0006](adr/0006-native-mll-plugin-strategy.md)) adds a preferred native `.mll` per Maya year (`plug-ins/2024/`, `2025/`, `2026/`) when prebuilt binaries are present; the `.py` plug-in remains the fallback for source checkouts and machines without a devkit build.

## Supported Maya versions (best-effort)

Maintainer-tested versions in this repository:

| Maya version | Status | Notes |
| --- | --- | --- |
| 2024 | Tested | Demo scene [`examples/broken_scene/shader_health_demo_broken.ma`](../examples/broken_scene/shader_health_demo_broken.ma) is saved in Maya 2024 |
| 2025 | Tested | Scanner and command unit tests target Maya 2025 APIs |
| 2026 | Best effort | Not regularly CI-tested; report issues if panel or `mayapy` integration differs |
| 2023 and earlier | Not tested | May work with PySide2-based Maya builds, but is outside the current support matrix |

The UI loads Qt through PySide2 or PySide6 depending on what the active Maya build provides.

Renderer plugins (V-Ray, Arnold) are optional for opening the panel, but renderer-specific rules need the corresponding plugin loaded in the session being validated.

## Option A — `MAYA_MODULE_PATH` (recommended for repo checkout)

### 1. Clone or sync the repository

```bash
git clone https://github.com/armasonix/maya-shader-health-inspector.git
cd maya-shader-health-inspector
```

### 2. Point Maya at the module folder

Add the `maya_module` directory to `MAYA_MODULE_PATH` before launching Maya.

Windows (PowerShell, current session):

```powershell
$env:MAYA_MODULE_PATH = "D:\tools\maya-shader-health-inspector\maya_module"
& "C:\Program Files\Autodesk\Maya2025\bin\maya.exe"
```

Linux/macOS (bash, current session):

```bash
export MAYA_MODULE_PATH="/tools/maya-shader-health-inspector/maya_module"
maya
```

For a persistent studio setup, set `MAYA_MODULE_PATH` in the facility launcher, shell profile, or render wrangler environment the same way you manage other Maya modules.

### 3. What the module file does

[`maya_module/shader_health_inspector.mod`](../maya_module/shader_health_inspector.mod):

```text
+ shader_health_inspector 0.3 .
PYTHONPATH +:= ../src
scripts: scripts
shelves: shelves
plug-ins: plug-ins
```

- `PYTHONPATH +:= ../src` adds the repository `src/` folder so `import shader_health` resolves without a separate `pip` install.
- `scripts: scripts` puts `maya_module/scripts/` on Maya's script path so `userSetup.py` runs at startup.
- `shelves: shelves` publishes the optional MEL shelf helper in `maya_module/shelves/`.
- `plug-ins: plug-ins` registers the Python plugin for **Settings → Plug-in Manager** (v0.3+).

### 4. Startup behavior

At Maya launch:

1. Maya executes `maya_module/scripts/userSetup.py`.
2. `userSetup.py` defers `_install_shader_health_ui()`.
3. **v0.4 target:** deferred hook tries `plug-ins/{mayaYear}/shader_health_inspector.mll` when present.
4. Otherwise tries `cmds.loadPlugin("shader_health_inspector.py", quiet=True)`.
5. When a plug-in loads, `initializePlugin` defers `shader_health_inspector_bootstrap.install_ui()`.
6. If plug-in load fails, `userSetup.py` falls back to calling `install_ui()` directly.
7. After UI initialization, `install_ui()` creates the **Shader Health** menu and **ShaderHealth** shelf button.
8. If installation fails, Maya prints a warning: `Shader Health Inspector UI install failed: ...`.

The bootstrap module also ensures the repository `src/` directory is on `sys.path` before importing `shader_health`, even if the `.mod` path is customized.

## Plug-in Manager: Python fallback and native `.mll` (ADR 0006)

| Delivery | File | When used |
| --- | --- | --- |
| Native bootstrap (v0.4+, preferred) | `plug-ins/{year}/shader_health_inspector.mll` | Prebuilt binary matching the running Maya year (2024 / 2025 / 2026) |
| Python fallback (v0.3+) | `plug-ins/shader_health_inspector.py` | Source checkout, unsupported OS, or no `.mll` for this year |
| Module-only fallback | `shader_health_inspector_bootstrap.install_ui()` | Plug-in load failed; backward-compatible path |

The native `.mll` is a **thin C++ bootstrap** only — it calls the same `shader_health_inspector_bootstrap` Python module as the `.py` plug-in. Validation and UI logic are unchanged. Build requirements and per-year matrix: [ADR 0006](adr/0006-native-mll-plugin-strategy.md). CMake scaffolding lands in issues #096–#097.

Until release binaries are attached, developers use the `.py` plug-in path documented below.

## Plug-in Manager vs module-only (v0.3 dual install)

| Path | Plug-in Manager | Module `userSetup` |
| --- | --- | --- |
| Dual install (recommended v0.3+) | Load/unload `shader_health_inspector` | Tries `loadPlugin` on startup |
| Module-only (backward compatible) | Plugin not loaded | Direct `install_ui()` fallback |

### Plug-in Manager workflow

1. Ensure `MAYA_MODULE_PATH` points at `maya_module/` (see Option A above).
2. Open **Settings → Plug-in Manager**.
3. Enable **Loaded** for `shader_health_inspector.py` (vendor: Shader Health Inspector).
4. Confirm the **Shader Health** menu and **ShaderHealth** shelf appear.
5. Unload the plugin to remove menu, shelf, and panel without restarting Maya.

### `autoLoad` studio policy

- **Manual load (default):** leave `autoLoad` off so TDs control when Shader Health UI appears.
- **Auto load:** enable `autoLoad` in Plug-in Manager or rely on `userSetup.py`, which calls `cmds.loadPlugin(..., quiet=True)` when your facility wants the panel available in every interactive session.
- **Farm / `mayapy`:** headless validation does **not** require plugin load; use `mayapy -m shader_health ...` instead.

### 5. Verify in Maya

After Maya finishes loading:

```python
from maya import cmds

print(cmds.menu("shaderHealthInspectorMenu", q=True, exists=True))      # expect True
print(cmds.shelfButton("shaderHealthInspectorShelfButton", q=True, exists=True))  # expect True

from shader_health.maya.commands import show_ui
show_ui()
```

Then open the demo scene and run **Validate Scene**:

`examples/broken_scene/shader_health_demo_broken.ma`

## Option B — Editable `pip` install (TD / workstation alternative)

Use this when you prefer installing the package into Maya's Python environment instead of relying on `MAYA_MODULE_PATH`.

### 1. Install into Maya's Python

Windows example with Maya 2025:

```powershell
& "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" -m pip install --upgrade pip
& "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" -m pip install -e "D:\tools\maya-shader-health-inspector"
```

Use the `mayapy` executable that matches the Maya version artists launch.

### 2. Install UI entrypoints for the session

In Maya's Script Editor:

```python
from shader_health.maya.commands import install_ui, show_ui

install_ui()
show_ui()
```

To load the UI automatically, wrap the same calls in a studio `userSetup.py` or shelf button.

### 3. Headless validation with `mayapy`

```bash
mayapy -m shader_health validate scene.ma --profile-id publish_strict --report report.json
```

Scene validation requires `mayapy`; regular system Python can validate snapshot JSON inputs only.

## Optional MEL shelf helper

[`maya_module/shelves/shelf_ShaderHealth.mel`](../maya_module/shelves/shelf_ShaderHealth.mel) defines a shelf button that calls:

```python
import shader_health_inspector_bootstrap
shader_health_inspector_bootstrap.show()
```

Studios that already manage shelves through MEL can use this file directly. The default startup path still uses the Python `install_shelf()` helper from `userSetup.py`.

## Manual PYTHONPATH (legacy fallback)

If you cannot use `MAYA_MODULE_PATH` or `pip`, add the repository `src/` directory to `PYTHONPATH`, then run `install_ui()` manually:

```python
import sys
sys.path.insert(0, r"D:\tools\maya-shader-health-inspector\src")

from shader_health.maya.commands import install_ui, show_ui
install_ui()
show_ui()
```

Prefer **Option A** or **Option B** for repeatable studio rollout.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `No module named 'shader_health'` | Package not on Maya `PYTHONPATH` | Use `MAYA_MODULE_PATH`, editable `pip` install, or bootstrap/`src` path |
| `Shader Health Inspector UI install failed` on startup | Import error before UI wiring | Open Script Editor traceback; confirm `src/` exists relative to `maya_module/` |
| Menu exists but panel does not open | Qt import issue in the active Maya build | Confirm Maya version is in the support matrix; test `show_ui()` in Script Editor |
| Validation returns empty renderer rules | Renderer plugin not loaded | Load V-Ray or Arnold before validating renderer-specific scenes |
| `scene validation requires Autodesk Maya / mayapy` in CLI | Running scene validation outside Maya | Use `mayapy -m shader_health ...` |

## Uninstall / disable

For the module path:

1. Remove the repo path from `MAYA_MODULE_PATH`.
2. Restart Maya.

For a `pip` install:

```bash
mayapy -m pip uninstall maya-shader-health-inspector
```

To remove only the current session menu/shelf/panel:

```python
from shader_health.maya.commands import uninstall_ui

uninstall_ui()
```

When using Plug-in Manager, unloading `shader_health_inspector` runs the same cleanup via `uninitializePlugin`.

## Related docs

- [`USER_GUIDE.md`](USER_GUIDE.md) — artist and TD workflow inside the panel
- [`integrations/publish_submit_preflight.md`](integrations/publish_submit_preflight.md) — publish gate example
- [`integrations/deadline_submit_preflight.md`](integrations/deadline_submit_preflight.md) — farm submit gate example

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
DEMO_SCENE="examples/broken_scene/shader_health_demo_broken.ma"
OUT_MANIFEST="/tmp/shader_health_manifest_smoke.json"
GATE_REPORT="/tmp/shader_health_gate_smoke.json"

mayapy -m shader_health manifest "$DEMO_SCENE" \
  --out "$OUT_MANIFEST" \
  --profile-id publish_strict

mayapy -m shader_health gate "$DEMO_SCENE" "$OUT_MANIFEST" \
  --profile-id publish_strict \
  --out "$GATE_REPORT"
```

### Optional GitHub Actions workflow (maintainers)

Real Maya integration runs on a **self-hosted runner** labeled `self-hosted` and `maya`. The workflow is [`.github/workflows/maya-integration.yml`](../.github/workflows/maya-integration.yml).

| Trigger | When it runs |
|---------|----------------|
| `workflow_dispatch` | Manual run from **Actions → Maya integration** |
| `schedule` | Weekly (Monday 06:00 UTC) on the default branch |
| `pull_request` | Same-repo PRs only, when paths under `src/shader_health/maya/`, `maya_module/`, `tests/integration/`, or related examples change |

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

Demo scene: [`examples/broken_scene/shader_health_demo_broken_headless.ma`](../examples/broken_scene/shader_health_demo_broken_headless.ma)

After `pytest tests/integration`:

1. `shader_health validate` (publish_strict) — report written; exit codes 0–2 accepted
2. `shader_health manifest` — schema **1.1**
3. `shader_health gate` — baseline = freshly exported manifest (no regression expected)
4. `examples/deadline/submit_preflight.py` — `deadline_critical` profile dry-run; exit codes 0–2 accepted

Default CI in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) stays Maya-free.

#### Local Windows example

```powershell
$env:MAYA_PY = "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe"
$SCENE = "examples\broken_scene\shader_health_demo_broken_headless.ma"
& $env:MAYA_PY -m pip install -e ".[dev]"
& $env:MAYA_PY -m pytest tests/integration -v
& $env:MAYA_PY -m shader_health validate $SCENE --input-kind scene --profile-id publish_strict --report "$env:TEMP\validate_smoke.json"
& $env:MAYA_PY examples\deadline\submit_preflight.py $SCENE `
  --report "$env:TEMP\deadline_preflight_smoke.json" `
  --profile "src\shader_health\rules\profiles\deadline_critical.json" `
  --repo-root (Get-Location) `
  --mayapy $env:MAYA_PY
```

See also [`docs/CLI_TESTING.md`](CLI_TESTING.md).
