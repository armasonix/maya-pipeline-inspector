# Updates & releases

## Versioning

Public releases: [GitHub Releases](https://github.com/armasonix/maya-pipeline-inspector/releases) tagged `v*`. Current: **v0.6.0**.

Changelog: [`CHANGELOG.md`](../../CHANGELOG.md)

## Auto-update (module-path installs)

Panel header **Check for Updates**:

1. Compare semver with GitHub Releases API.
2. Download `maya-pipeline-inspector-<version>.zip`.
3. Merge `maya_module/` + `src/` with config preservation + rollback.

Requires **`MAYA_MODULE_PATH`** install root with sibling `maya_module/` and `src/`.

Full spec: [`auto_update.md`](../../integrations/auto_update.md)

## Pip installs

Editable or site-packages install: wizard is **check-only** — upgrade with:

```powershell
mayapy -m pip install -U maya-pipeline-inspector
```

→ [`MAYA_INSTALL.md`](../../MAYA_INSTALL.md)

## Release artifacts

| Asset | Consumer |
| --- | --- |
| `maya-pipeline-inspector-<ver>.zip` | Module-path auto-update |
| Source tag | Git checkout deploy |
| Optional native `.mll` | Inside zip — built on release runner |

Maintainer playbook: [`V0_6_RELEASE.md`](../../V0_6_RELEASE.md)

## Pinning updates

Studio lock-down:

```json
"updates": { "pinned_version": "0.6.0" }
```

## After update checklist

1. Save work.
2. Complete wizard install.
3. **Quit Maya fully**.
4. Relaunch — verify panel header version.
