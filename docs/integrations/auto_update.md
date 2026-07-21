# Auto-update (Check for Updates)

**Product:** [Maya Pipeline Inspector](../USER_GUIDE.md) (`maya-pipeline-inspector`)  
**Audience:** Pipeline TD / maintainer liaison  
**Related:** [MAYA_INSTALL.md](../MAYA_INSTALL.md) · [STUDIO_OVERRIDES.md](../STUDIO_OVERRIDES.md) · [ADR 0007](../adr/0007-settings-and-connectors-architecture.md)

Pipeline Inspector can check [GitHub Releases](https://github.com/armasonix/maya-pipeline-inspector/releases) for a newer version, download a release package to a local staging directory, install it with rollback on failure, and show a manual Maya restart checklist.

The flow is **GUI-first**: Technical Artists and TDs start it from the panel header **Check for Updates** button. Download and install always run inside the wizard — there is no silent auto-install.

See [ADR 0007](../adr/0007-settings-and-connectors-architecture.md) for settings architecture and security notes.

## End-to-end flow

```text
Panel header → Check for Updates
  -> ui/update_wizard.py (5-step progress dialog)
  -> integrations/update/github_releases.py   (query + semver compare)
  -> integrations/update/download.py          (download .zip to staging)
  -> integrations/update/install.py           (backup, merge payload, rollback)
  -> restart checklist (manual — Maya is not restarted by the plugin)
```

Wizard steps shown in the dialog:

1. Query GitHub Releases for the latest version
2. Compare installed version with the release tag
3. Download release package to staging
4. Install update and preserve `pipeline_inspector_studio.json` and `user.json`
5. Show manual Maya restart checklist

Default release source: `armasonix/maya-pipeline-inspector` (`integrations/update/config.py`).

## Module path vs pip install path

In-app update behavior depends on **how Pipeline Inspector is installed**. The installer merges `maya_module/` and `src/` into the live install root — it does **not** run `pip install`.

| Install method | Typical layout | In-app **Check for Updates** install | Recommended update path |
| --- | --- | --- | --- |
| **A — `MAYA_MODULE_PATH` (recommended)** | Repo checkout: `{root}/maya_module/` + `{root}/src/` | **Supported** when `{root}` is the running plugin install root | Use **Check for Updates** in the panel, then follow the restart checklist below |
| **B — Editable `pip` install** | Package in Maya's `site-packages`; no sibling `maya_module/` at repo root | **Not supported** by the wizard (install root cannot be resolved to `maya_module/` + `src/`) | Upgrade with `mayapy -m pip install -U maya-pipeline-inspector` (or reinstall from a release tag), then restart Maya |
| **Legacy `PYTHONPATH` to `src/` only** | `src/pipeline_inspector` on path; module file optional | **Not supported** | Switch to Option A or B, or manually sync a full repo checkout |

### Option A — module path (supported)

This matches [MAYA_INSTALL.md — Option A](../MAYA_INSTALL.md) (`MAYA_MODULE_PATH` repo checkout).

```powershell
$env:MAYA_MODULE_PATH = "D:\tools\maya-pipeline-inspector\maya_module"
```

Requirements for in-app install:

- The running session loaded the plugin from a directory tree that contains both `maya_module/` and `src/` (standard repository layout).
- The GitHub release asset is a `.zip` whose payload includes those two directories (see [Release package layout](#release-package-layout)).
- The workstation can reach `api.github.com` and `github.com` (HTTPS).

After a successful wizard install, **`pipeline_inspector_studio.json` and `user.json` are preserved** (see [Preserved config files](#preserved-config-files)). Other files under `maya_module/` and `src/` are replaced from the release package.

### Option B — pip install (manual update)

This matches [MAYA_INSTALL.md — Option B](../MAYA_INSTALL.md) (editable `pip` install).

Use **Check for Updates** only to **see** whether a newer release exists. When an update is available, upgrade with Maya's Python, for example:

```powershell
& "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" -m pip install -U maya-pipeline-inspector
```

Or reinstall from a tagged checkout:

```powershell
& "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" -m pip install -U "D:\tools\maya-pipeline-inspector"
```

Then follow the [Maya restart checklist](#maya-restart-checklist-after-update) below. Studio and user JSON files under `~/.pipeline_inspector/` are not modified by `pip` and do not need restoration.

## Studio and user settings

**Studio policy** (`pipeline_inspector_studio.json`):

```json
{
  "updates": {
    "allow_check": true,
    "pinned_version": ""
  }
}
```

| Field | Purpose |
| --- | --- |
| `allow_check` | When `false`, the wizard stops immediately — studio policy disables in-app update checks |
| `pinned_version` | When set (e.g. `"0.5.0"`), download/install is skipped if the latest GitHub tag is **newer** than the pinned version (facility lock-down) |

**User preference** (`~/.pipeline_inspector/user.json`):

```json
{
  "updates": {
    "check_on_startup": false
  }
}
```

`check_on_startup` triggers a **check-only** query when the panel opens (no download or install). If a newer release is available, the Validate tab status line shows a short message; use **Check for Updates** to open the full progress wizard and install.

## Building release packages

Maintainers build the auto-update zip from the repository root. The archive must include **native `.mll` plug-ins** so Technical Artists receive a complete module-path update from **Check for Updates** without manual rebuild steps.

```powershell
.\tools\build_release_assets.ps1
```

This script:

1. Builds `pipeline_inspector.mll` for each installed Maya year (2024 / 2025 / 2026 when present)
2. Produces `dist/maya-pipeline-inspector-{version}.zip` with `maya_module/`, `src/`, and the built `.mll` files

Zip-only packaging without native binaries (not suitable for Technical Artist auto-update):

```powershell
python tools/build_release_package.py
```

### GitHub Actions release workflow

Pushing a `v*` tag runs [`.github/workflows/release.yml`](../../.github/workflows/release.yml) on the **Windows self-hosted `maya` runner**:

1. Builds native plug-ins for installed Maya years via `tools/build_release_assets.ps1`
2. Packages `dist/maya-pipeline-inspector-{version}.zip` with `maya_module/`, `src/`, and `.mll` payloads
3. Attaches that single zip to the GitHub Release for the tag

The update wizard downloads **one zip**; `install.py` merges `maya_module/` (including year-specific `.mll` binaries and the Plug-in Manager copy) and `src/` into the live install root.

### Release zip layout

```text
maya_module/
  pipeline_inspector.mod
  scripts/
  plug-ins/
    pipeline_inspector.mll
    2024/pipeline_inspector.mll
    2025/pipeline_inspector.mll
  shelves/
src/
  pipeline_inspector/
    ...
```

Single top-level folder wrappers (e.g. `maya-pipeline-inspector/maya_module/...`) are accepted.

## Local staging, backup, and rollback

| Path | Purpose |
| --- | --- |
| `~/.pipeline_inspector/updates/staging/{tag}/` | Downloaded release `.zip` from GitHub |
| `~/.pipeline_inspector/updates/backups/{tag}/` | Pre-install copy of `maya_module/` and `src/` for rollback |

On install failure after backup, the client restores the previous `maya_module/` and `src/` trees and re-applies preserved config snapshots. The wizard shows an error on the install step and does **not** advance to the restart checklist.

## Preserved config files

These files are snapshotted before install and restored after a successful install or rollback:

- `pipeline_inspector_studio.json` — discovered via `PIPELINE_INSPECTOR_STUDIO_CONFIG`, `~/.pipeline_inspector/`, or home directory
- `user.json` — discovered via `PIPELINE_INSPECTOR_USER_CONFIG` or `~/.pipeline_inspector/user.json`

They are **not** part of the `maya_module/` / `src/` merge and are never deleted by the update installer.

## Maya restart checklist after update

Maya **must be restarted manually** after an update. The plugin does not quit or relaunch Maya.

Use this checklist after a **successful** module-path install or after a **manual pip** upgrade:

1. **Save work** — save open scenes and note any unsaved Script Editor tabs you need.
2. **Close Pipeline Inspector** — close the dockable panel (optional but avoids stale UI state).
3. **Close Maya** — exit the application completely so plug-ins and `import pipeline_inspector` reload from disk.
4. **Verify install (TD, optional)** — for module-path installs, confirm `{install_root}/src/pipeline_inspector/version.py` or the panel header version matches the expected release tag.
5. **Relaunch Maya** — start the same Maya version Technical Artists use in production.
6. **Confirm entrypoints** — open **Window → Pipeline Inspector** (or the **PipelineInspector** shelf) and open the panel.
7. **Smoke validate** — run **Validate Scene** on a policy demo scene (for example `examples/vray_policy/vray_policy_scene.ma` or `examples/arnold_policy/arnold_policy_scene.ma`, with the matching renderer loaded) and confirm the panel loads studio/user settings.

If anything looks wrong after restart, TDs can restore from `~/.pipeline_inspector/updates/backups/{tag}/` (module-path installs) or reinstall the previous release / `pip` version.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Wizard says studio policy disables checks | `updates.allow_check: false` | TD sets `allow_check: true` in studio config or uses manual deploy |
| Update available but install skipped (pinned) | `updates.pinned_version` blocks newer tags | TD clears pin or bumps pin after qualification |
| Install failed; files restored | Bad zip, disk error, or permission issue | Read install-step message; fix permissions; retry or deploy manually from release |
| Could not query GitHub Releases | Offline machine or proxy blocking GitHub | Use manual download from Releases page; TD deploys zip |
| Latest release has no install package | Release missing `maya-pipeline-inspector-<version>.zip` asset | Maintainer runs `python tools/build_release_package.py` and attaches zip via release workflow or `gh release upload` |
| Check works but install does nothing useful | **pip-only** or `src`-only layout | Use [pip upgrade](#option-b--pip-install-manual-update) or switch to module-path checkout |
| Panel shows old version after restart | Maya still running during copy, or wrong install root | Close Maya fully; confirm `MAYA_MODULE_PATH` points at updated `maya_module/` |
| Studio settings reverted | Unrelated edit to config file | Installer preserves JSON; restore from backup if file was edited outside the wizard |

## Related docs

- [MAYA_INSTALL.md](../MAYA_INSTALL.md) — module path, pip install, studio config rollout
- [STUDIO_OVERRIDES.md](../STUDIO_OVERRIDES.md) — studio JSON policy
- [USER_GUIDE.md](../USER_GUIDE.md) — daily panel workflow
