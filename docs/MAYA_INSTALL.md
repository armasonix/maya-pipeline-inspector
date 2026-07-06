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

On module startup, [`maya_module/scripts/userSetup.py`](../maya_module/scripts/userSetup.py) defers a call to [`shader_health_inspector_bootstrap.install_ui()`](../maya_module/scripts/shader_health_inspector_bootstrap.py), which installs the menu and shelf for the current Maya session.

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
+ shader_health_inspector 0.1 .
PYTHONPATH +:= ../src
scripts: scripts
shelves: shelves
```

- `PYTHONPATH +:= ../src` adds the repository `src/` folder so `import shader_health` resolves without a separate `pip` install.
- `scripts: scripts` puts `maya_module/scripts/` on Maya's script path so `userSetup.py` runs at startup.
- `shelves: shelves` publishes the optional MEL shelf helper in `maya_module/shelves/`.

### 4. Startup behavior

At Maya launch:

1. Maya executes `maya_module/scripts/userSetup.py`.
2. `userSetup.py` registers `shader_health_inspector_bootstrap.install_ui()` with `cmds.evalDeferred(...)`.
3. After UI initialization, `install_ui()` creates the **Shader Health** menu and **ShaderHealth** shelf button.
4. If installation fails, Maya prints a warning: `Shader Health Inspector UI install failed: ...`.

The bootstrap module also ensures the repository `src/` directory is on `sys.path` before importing `shader_health`, even if the `.mod` path is customized.

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

To remove only the current session menu/shelf:

```python
from shader_health.maya.commands import uninstall_menu, uninstall_shelf

uninstall_menu()
uninstall_shelf()
```

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

### Optional GitHub Actions workflow (maintainers)

The repository ships a manual workflow at [`.github/workflows/maya-integration.yml`](../.github/workflows/maya-integration.yml). It is triggered by **workflow_dispatch only** and does not run on every pull request.

1. Configure a self-hosted runner with Autodesk Maya installed.
2. Add repository secret `MAYA_PY` with the absolute path to `mayapy`.
3. In GitHub: **Actions → Maya integration → Run workflow**.
4. Optionally pass workflow input `mayapy_path` to override the secret for one run.

When `MAYA_PY` is unset or the path is missing, the workflow exits successfully and prints a skip notice. Default CI in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) stays Maya-free.

Local Windows example:

```powershell
$env:MAYA_PY = "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe"
& $env:MAYA_PY -m pip install -e ".[dev]"
& $env:MAYA_PY -m pytest tests/integration -v
```
