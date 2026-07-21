# FAQ & troubleshooting

## General

### Is Pipeline Inspector production-ready?

**v0.6.0 is a public MIT release** with broad test coverage, but many integrations are **MVP-quality**. Read [known limitations](#known-limitations) before facility rollout.

### Which Maya versions are supported?

Maintainer-tested: **2024, 2025**. **2026** best effort. **2023−** not tested. → [`MAYA_INSTALL.md`](../../MAYA_INSTALL.md)

### Does it replace our publish tool?

No. It **feeds** publish/farm decisions with validation, manifests, and reports — not a full AMS/publish stack.

---

## Installation

### Panel does not appear

| Check | Action |
| --- | --- |
| `MAYA_MODULE_PATH` | Points to `maya_module/` with `pipeline_inspector.mod` |
| Script Editor errors | Import traceback on startup |
| Conflicting install | Dual pip + module path — see [ADR 0006](../../adr/0006-native-mll-plugin-strategy.md) |

### Native plug-in missing

Python fallback still loads UI. Build `.mll` locally or use release zip with binaries.

→ [Installation](../Getting-Started/Installation)

---

## Validation

### False positive missing texture

- UDIM naming — verify tile pattern
- Sequence resolved path — check `file` node frame pattern
- Studio root token not expanded — configure `studio_environment`

### Texture freshness wrong

Rule uses **filesystem siblings only** — not publish database version.

### Health score vs blocking

Health is heuristic. Trust **Publish Block** / **Deadline Block** for gates.

---

## Updates

### Check for Updates does not install

Only **module-path** installs (sibling `maya_module/` + `src/`). Pip installs: manual `pip install -U`.

→ [Updates & releases](../Administration/Updates-and-Releases)

### Version unchanged after update

Quit Maya fully; verify install root matches `MAYA_MODULE_PATH`.

---

## Farm & Deadline

### Submit disabled

Role may lack `submit_farm` — [Governance](../Administration/Governance).

### Web Service connection failed

Check `connectors.deadline` URL, firewall, Deadline repository path.

→ [`deadline_submit_preflight.md`](../../integrations/deadline_submit_preflight.md)

---

## Known limitations

From [`USER_GUIDE.md`](../../USER_GUIDE.md#known-limitations--gaps):

| Area | Limitation |
| --- | --- |
| Texture freshness | Filesystem only |
| Farm cost score | Heuristic, not render time |
| Rule wizard | MVP templates — advanced JSON manual |
| Roles | Self-reported unless enforced |
| Readiness | No headless CLI |
| AWS Deadline Cloud | Not integrated |
| User prefs in CLI | Studio config only |

Full matrix: [Capability matrix](../Reference/Capability-Matrix)

---

## Get help

- [GitHub Issues](https://github.com/armasonix/maya-pipeline-inspector/issues)
- Panel **Bug Report** → [`bug_report_relay.md`](../../integrations/bug_report_relay.md)
- [GitHub Discussions](https://github.com/armasonix/maya-pipeline-inspector/discussions)
