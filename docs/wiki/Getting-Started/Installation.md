# Installation

Pipeline Inspector supports two primary install paths. Choose based on who maintains the deployment.

## Option A — `MAYA_MODULE_PATH` (recommended for studios)

Best for **Technical Artists** and facilities that want **in-app Check for Updates**.

```powershell
# Windows example
$env:MAYA_MODULE_PATH = "D:\tools\maya-pipeline-inspector\maya_module"
```

Layout: repository root with sibling `maya_module/` and `src/`. Native `.mll` plug-ins load per Maya year with Python fallback.

**Full guide:** [`MAYA_INSTALL.md` — Option A](../../MAYA_INSTALL.md)

| Pros | Cons |
| --- | --- |
| In-app update + rollback | Requires shared checkout or release zip deploy |
| Matches release zip contract | TD must manage `MAYA_MODULE_PATH` |

## Option B — Editable `pip` install (TD workstations)

```powershell
& "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" -m pip install -e "D:\tools\maya-pipeline-inspector"
```

Then call `install_ui()` from Script Editor or rely on module bootstrap.

**Full guide:** [`MAYA_INSTALL.md` — Option B](../../MAYA_INSTALL.md)

| Pros | Cons |
| --- | --- |
| Familiar Python workflow | No in-app update install |
| Good for rule development | Manual `pip install -U` on upgrade |

## Native plug-in (optional)

Year-specific `pipeline_inspector.mll` improves Plug-in Manager integration. Build locally:

```powershell
.\tools\build_native_plugin.ps1 -MayaVersion 2025
```

Strategy: [ADR 0006 — Native `.mll` plug-in strategy](../../adr/0006-native-mll-plugin-strategy.md)

## Studio config discovery

Set once for all artists:

```powershell
$env:PIPELINE_INSPECTOR_STUDIO_CONFIG = "\\pipeline\config\pipeline_inspector_studio.json"
```

→ [Studio config](../Administration/Studio-Config)

## Verify install

1. Launch Maya → **Window → Pipeline Inspector** (or shelf button).
2. Open panel header — version should match release (e.g. **v0.6.0**).
3. Run **Validate Scene** on a demo scene.

→ [Demo scenes](Demo-Scenes) · [Quick start](Quick-Start-5-Minutes)
