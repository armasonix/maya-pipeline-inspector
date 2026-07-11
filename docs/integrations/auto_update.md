# Auto-update (Check for Updates)

Shader Health Inspector can check [GitHub Releases](https://github.com/armasonix/maya-shader-health-inspector/releases) for a newer version, download a release package to a local staging directory, install it with rollback on failure, and show a manual Maya restart checklist.

The flow is **GUI-first**: artists and TDs start it from the panel header **Check for Updates** button. Download and install always run inside the wizard — there is no silent auto-install.

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
4. Install update and preserve `shader_health_studio.json` and `user.json`
5. Show manual Maya restart checklist

Default release source: `armasonix/maya-shader-health-inspector` (`integrations/update/config.py`).

## Module path vs pip install path

In-app update behavior depends on **how Shader Health Inspector is installed**. The installer merges `maya_module/` and `src/` into the live install root — it does **not** run `pip install`.

| Install method | Typical layout | In-app **Check for Updates** install | Recommended update path |
| --- | --- | --- | --- |
| **A — `MAYA_MODULE_PATH` (recommended)** | Repo checkout: `{root}/maya_module/` + `{root}/src/` | **Supported** when `{root}` is the running plugin install root | Use **Check for Updates** in the panel, then follow the restart checklist below |
| **B — Editable `pip` install** | Package in Maya's `site-packages`; no sibling `maya_module/` at repo root | **Not supported** by the wizard (install root cannot be resolved to `maya_module/` + `src/`) | Upgrade with `mayapy -m pip install -U maya-shader-health-inspector` (or reinstall from a release tag), then restart Maya |
| **Legacy `PYTHONPATH` to `src/` only** | `src/shader_health` on path; module file optional | **Not supported** | Switch to Option A or B, or manually sync a full repo checkout |

### Option A — module path (supported)

This matches [MAYA_INSTALL.md — Option A](../MAYA_INSTALL.md) (`MAYA_MODULE_PATH` repo checkout).

```powershell
$env:MAYA_MODULE_PATH = "D:\tools\maya-shader-health-inspector\maya_module"
```

Requirements for in-app install:

- The running session loaded the plugin from a directory tree that contains both `maya_module/` and `src/` (standard repository layout).
- The GitHub release asset is a `.zip` whose payload includes those two directories (see [Release package layout](#release-package-layout)).
- The workstation can reach `api.github.com` and `github.com` (HTTPS).

After a successful wizard install, **`shader_health_studio.json` and `user.json` are preserved** (see [Preserved config files](#preserved-config-files)). Other files under `maya_module/` and `src/` are replaced from the release package.

### Option B — pip install (manual update)

This matches [MAYA_INSTALL.md — Option B](../MAYA_INSTALL.md) (editable `pip` install).

Use **Check for Updates** only to **see** whether a newer release exists. When an update is available, upgrade with Maya's Python, for example:

```powershell
& "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" -m pip install -U maya-shader-health-inspector
```

Or reinstall from a tagged checkout:

```powershell
& "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" -m pip install -U "D:\tools\maya-shader-health-inspector"
```

Then follow the [Maya restart checklist](#maya-restart-checklist-after-update) below. Studio and user JSON files under `~/.shader_health/` are not modified by `pip` and do not need restoration.

## Studio and user settings

**Studio policy** (`shader_health_studio.json`):

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

**User preference** (`~/.shader_health/user.json`):

```json
{
  "updates": {
    "check_on_startup": false
  }
}
```

`check_on_startup` is stored for future silent **check-only** behavior. Download and install always require opening **Check for Updates** and confirming the wizard (GUI-first clarity per ADR 0007).

## Local staging, backup, and rollback

| Path | Purpose |
| --- | --- |
| `~/.shader_health/updates/staging/{tag}/` | Downloaded release `.zip` from GitHub |
| `~/.shader_health/updates/backups/{tag}/` | Pre-install copy of `maya_module/` and `src/` for rollback |

On install failure after backup, the client restores the previous `maya_module/` and `src/` trees and re-applies preserved config snapshots. The wizard shows an error on the install step and does **not** advance to the restart checklist.

## Preserved config files

These files are snapshotted before install and restored after a successful install or rollback:

- `shader_health_studio.json` — discovered via `SHADER_HEALTH_STUDIO_CONFIG`, `~/.shader_health/`, or home directory
- `user.json` — discovered via `SHADER_HEALTH_USER_CONFIG` or `~/.shader_health/user.json`

They are **not** part of the `maya_module/` / `src/` merge and are never deleted by the update installer.

## Release package layout

The wizard prefers a GitHub release asset named like `maya-shader-health-inspector-{version}.zip`. The archive must unpack to a tree containing:

```text
maya_module/
  shader_health_inspector.mod
  scripts/
  plug-ins/
  shelves/
src/
  shader_health/
    ...
```

Single top-level folder wrappers (e.g. `maya-shader-health-inspector/maya_module/...`) are accepted.

## Maya restart checklist after update

Maya **must be restarted manually** after an update. The plugin does not quit or relaunch Maya.

Use this checklist after a **successful** module-path install or after a **manual pip** upgrade:

1. **Save work** — save open scenes and note any unsaved Script Editor tabs you need.
2. **Close Shader Health Inspector** — close the dockable panel (optional but avoids stale UI state).
3. **Close Maya** — exit the application completely so plug-ins and `import shader_health` reload from disk.
4. **Verify install (TD, optional)** — for module-path installs, confirm `{install_root}/src/shader_health/version.py` or the panel header version matches the expected release tag.
5. **Relaunch Maya** — start the same Maya version artists use in production.
6. **Confirm entrypoints** — open **Window → Shader Health** (or the **ShaderHealth** shelf) and open the panel.
7. **Smoke validate** — run **Validate Scene** on a known test scene (for example `examples/broken_scene/shader_health_demo_broken.ma`) and confirm the panel loads studio/user settings.

If anything looks wrong after restart, TDs can restore from `~/.shader_health/updates/backups/{tag}/` (module-path installs) or reinstall the previous release / `pip` version.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Wizard says studio policy disables checks | `updates.allow_check: false` | TD sets `allow_check: true` in studio config or uses manual deploy |
| Update available but install skipped (pinned) | `updates.pinned_version` blocks newer tags | TD clears pin or bumps pin after qualification |
| Install failed; files restored | Bad zip, disk error, or permission issue | Read install-step message; fix permissions; retry or deploy manually from release |
| Could not query GitHub Releases | Offline machine or proxy blocking GitHub | Use manual download from Releases page; TD deploys zip |
| Check works but install does nothing useful | **pip-only** or `src`-only layout | Use [pip upgrade](#option-b--pip-install-manual-update) or switch to module-path checkout |
| Panel shows old version after restart | Maya still running during copy, or wrong install root | Close Maya fully; confirm `MAYA_MODULE_PATH` points at updated `maya_module/` |
| Studio settings reverted | Unrelated edit to config file | Installer preserves JSON; restore from backup if file was edited outside the wizard |

## Related docs

- [MAYA_INSTALL.md](../MAYA_INSTALL.md) — module path, pip install, studio config rollout
- [STUDIO_OVERRIDES.md](../STUDIO_OVERRIDES.md) — studio JSON policy
- [USER_GUIDE.md](../USER_GUIDE.md) — daily panel workflow
