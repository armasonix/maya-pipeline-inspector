# v0.6 Development Plan — Geometry QA, Readiness, Governance & Farm Intelligence

**Status:** **v0.6.0 shipped** (2026-07-21)  
**Baseline release:** [CHANGELOG.md](../CHANGELOG.md) — `[0.5.0]`  
**Release playbook:** [V0_6_RELEASE.md](V0_6_RELEASE.md)

**GitHub tracking:** issues [#211–#232](https://github.com/armasonix/maya-pipeline-inspector/issues) (plan ids #165–#186).

---

## Milestones

| Milestone | Plan issues | Theme |
|-----------|-------------|-------|
| M42 Rebrand & platform hygiene | #165–#170 | Public MIT branding, community paths, platform cleanup |
| M43 Release packaging & relay | #171–#174 | GitHub Release zip contract, public bug-report relay |
| M44–M45 UI & geometry snapshot | #175–#178 | ShapeSnapshot enrichment, panel polish, naming |
| M46 Geometry budget checks | #179–#180 | Polycount and duplicate-mesh rules, asset-class budgets |
| M47 Readiness & shader performance | #181–#182 | Machine Readiness tab, probe engine |
| M48 Governance & supervisor routing | #183–#184 | ADR 0008/0009, PermissionResolver, routing UI |
| M49 Trackers & notifications | #181–#182 | Tracker role discovery, supervisor report dispatch |
| M50 Deadline farm intelligence | #183–#184 | `farm-analytics` CLI, HTML export, history JSONL |
| M51 Examples & documentation | (M51 PR) | Policy demo scenes, docs/community overhaul |
| M52 Release readiness | #186 | Version 0.6.0, CHANGELOG, tag, GitHub Release |

---

## Issue checklist

Work in order. One issue = one commit on `dev`.

| Plan | GitHub | Title |
|------|--------|-------|
| #165 | #211 | Rebrand repository to Maya Pipeline Inspector |
| #166 | #212 | MIT license and public community posture |
| #167 | #213 | Platform hygiene and CI baseline refresh |
| #168 | #214 | Release packaging zip asset contract |
| #169 | #215 | Public bug-report relay documentation |
| #170 | #216 | Native plugin version sync at release |
| #171 | #217 | Geometry snapshot model and scanner enrichment |
| #172 | #218 | Panel header and Validate tab layout polish |
| #173 | #219 | Geometry polycount rule and asset-class budgets |
| #174 | #220 | Duplicate geometry rule and scan budget |
| #175 | #221 | Machine Readiness probe engine |
| #176 | #222 | Readiness tab UI and Maya hooks |
| #177 | #223 | ADR 0008 role governance foundation |
| #178 | #224 | PermissionResolver capability gates |
| #179 | #225 | ADR 0009 supervisor routing by role |
| #180 | #226 | Governance and supervisor routing Settings UI |
| #181 | #227 | Ftrack and Cerebro role discovery |
| #182 | #228 | Validation and readiness supervisor notifications |
| #183 | #229 | Deadline farm analytics CLI |
| #184 | #230 | Farm analytics HTML export and history JSONL |
| #185 | #231 | Final debug instrumentation cleanup |
| #186 | #232 | Prepare v0.6.0 public release |

Acceptance criteria: each GitHub issue body.
