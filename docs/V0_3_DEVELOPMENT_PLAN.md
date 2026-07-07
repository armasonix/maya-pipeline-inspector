# v0.3 Development Plan — Pipeline Automation & Manifest Depth

**Status:** **v0.3.0 shipped** (2026-07-07)  
**Baseline release:** [CHANGELOG.md](../CHANGELOG.md) — `[0.2.0]`  
**Workflow:** [V0_3_WORKFLOW.md](V0_3_WORKFLOW.md) — one issue, one commit on `dev`

**GitHub tracking:** issues [#91–#110](https://github.com/armasonix/maya-shader-health-inspector/issues) (plan ids #071–#090).

---

## Milestones

| Milestone | Plan issues | Theme |
|-----------|-------------|-------|
| M15 Plugin | #071–#072 | Python MPx plugin, dual install, MAYA_INSTALL docs |
| M16 Fingerprint | #073–#076 | Graph fingerprint, manifest schema 1.1, diff regression |
| M17 Gates | #077–#079 | `manifest_diff_policy`, `shader_health gate`, publish preflight |
| M18 Apply | #080–#083 | ADR 0004, headless `apply-fixes` |
| M19 Resolution | #084–#086 | Texture dimension metadata, resolution budgets |
| M20 Polish | #087–#089 | Approved manifest UI shortcut, `shader_health manifest`, CI smoke |
| M21 Release | #090 | Version 0.3.0, CHANGELOG, tag, GitHub Release |

---

## Issue checklist

Work in order. One issue = one commit on `dev`.

| Plan | GitHub | Title |
|------|--------|-------|
| #071 | #91 | Python MPx plugin stub and dual install |
| #072 | #92 | Document autoLoad plugin studio policy |
| #073 | #93 | Material graph fingerprint algorithm |
| #074 | #94 | Extend build_shader_manifest |
| #075 | #95 | Manifest schema 1.1 migration note |
| #076 | #96 | Manifest diff fingerprint regression hints |
| #077 | #97 | Profile manifest_diff_policy overrides |
| #078 | #98 | CLI gate and validate --baseline-manifest |
| #079 | #99 | Publish preflight manifest gate |
| #080 | #101 | ADR 0004 headless apply-fixes policy |
| #081 | #104 | shader_health apply-fixes subcommand |
| #082 | #107 | apply-fixes policy flags |
| #083 | #100 | fix_audit integration and exit codes |
| #084 | #103 | Texture resolution metadata enrichment |
| #085 | #106 | Texture resolution rules and asset class profiles |
| #086 | #109 | Texture resolution docs and tests |
| #087 | #102 | UI Compare to approved manifest shortcut |
| #088 | #105 | Headless shader_health manifest CLI |
| #089 | #108 | Maya CI manifest gate smoke |
| #090 | #110 | Prepare v0.3.0 public release |

Acceptance criteria: each GitHub issue body.
