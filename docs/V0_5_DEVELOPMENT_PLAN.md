# v0.5 Development Plan — Studio Settings Hub, Connectors, Rule Authoring

**Status:** **v0.5.0 shipped** (2026-07-12)  
**Baseline release:** [CHANGELOG.md](../CHANGELOG.md) — `[0.4.0]`  
**Release playbook:** [V0_5_RELEASE.md](V0_5_RELEASE.md)

**GitHub tracking:** issues [#147–#198](https://github.com/armasonix/maya-pipeline-inspector/issues) (plan ids #113–#164).

---

## Milestones

| Milestone | Plan issues | Theme |
|-----------|-------------|-------|
| M29 Settings architecture | #113–#118 | ADR 0007, schema 2.0, connector registry, headless studio config |
| M30 Settings UI | #119–#124 | Basic / Advanced tabs, themes, dirty banner, unit tests |
| M31 Studio Environment | #125–#130 | Path substitution, Studio tab, deploy docs, integration tests |
| M32 Header & update shell | #131–#134 | Docs button, Check for Updates shell, progress dialog |
| M33 Notifications | #135–#140 | Telegram, Discord, Slack, dispatcher |
| M34 Task trackers | #141–#146 | Ftrack, ShotGrid, Cerebro, Send to Tracker |
| M35 Bug report | #147–#151 | Relay client, payload schema, server spec |
| M36 Auto-update | #152–#155 | GitHub Releases client, wizard, rollback install |
| M37 Rule authoring | #156–#162 | Rule browser, wizard, incident-to-rule, `rules validate` |
| M38 Studio docs | #163 | STUDIO_OVERRIDES refresh for v0.5 |
| M41 Release | #164 | Version 0.5.0, CHANGELOG, tag, GitHub Release |

---

## Issue checklist

Work in order. One issue = one commit on `dev`.

| Plan | GitHub | Title |
|------|--------|-------|
| #113 | #147 | ADR 0007 Settings and Connectors architecture |
| #114 | #148 | Studio config schema 2.0 migration |
| #115 | #149 | Connector registry and Deadline refactor |
| #116 | #150 | Settings tab model expansion |
| #117 | #151 | Save and load split for studio vs user config |
| #118 | #152 | Headless studio config support |
| #119 | #153 | Basic settings tab UI and persistence |
| #120 | #154 | Classic and Dark UI themes |
| #121 | #155 | Advanced settings tab UI |
| #122 | #156 | Wire user preferences into pipeline and UI defaults |
| #123 | #157 | Settings dirty state and status banner |
| #124 | #158 | Basic and Advanced settings unit tests |
| #125 | #159 | StudioEnvironmentSettings model and path substitution |
| #126 | #160 | Studio Environment settings tab UI |
| #127 | #161 | Wire studio paths into normalize_path and enrichment |
| #128 | #162 | Studio tab policy fields expansion |
| #129 | #163 | Studio config deploy documentation |
| #130 | #164 | Studio path substitution integration tests |
| #131 | #165 | Documentation header button placeholder |
| #132 | #166 | Check for Updates button and modal shell |
| #133 | #167 | Update progress dialog widget |
| #134 | #168 | Header layout tests and tooltips |
| #135 | #169 | Telegram connector package and settings UI |
| #136 | #170 | Telegram notification wiring |
| #137 | #171 | Discord connector package and settings UI |
| #138 | #172 | Discord notification wiring |
| #139 | #173 | Slack connector with channel routing |
| #140 | #174 | Notification dispatcher service |
| #141 | #175 | Task tracker connector base and publish DTO |
| #142 | #176 | Ftrack connector client and settings UI |
| #143 | #177 | ShotGrid connector client and settings UI |
| #144 | #178 | Cerebro connector client and settings UI |
| #145 | #179 | Reports tab Send to Tracker action |
| #146 | #180 | Slack thread context from tracker metadata |
| #147 | #181 | Bug Report settings tab UI |
| #148 | #182 | Bug report relay client and payload schema |
| #149 | #183 | Bug report spam and abuse controls |
| #150 | #184 | Bug report relay server specification |
| #151 | #185 | Bug report maintainer email notification contract |
| #152 | #186 | GitHub Releases update client |
| #153 | #187 | Update wizard UI full flow |
| #154 | #188 | Safe update install with rollback |
| #155 | #189 | Auto-update documentation |
| #156 | #190 | Rule browser and safe field editor MVP |
| #157 | #191 | New rule wizard from template |
| #158 | #192 | Rule editor entry from Settings Advanced |
| #159 | #193 | Create rule draft from issue details |
| #160 | #194 | Export incident rule draft to studio extra_rules |
| #161 | #195 | Incident-to-rule workflow documentation |
| #162 | #196 | pipeline_inspector rules validate CLI subcommand |
| #163 | #197 | Studio overrides docs for v0.5 settings and connectors |
| #164 | #198 | Prepare v0.5.0 public release |

Acceptance criteria: each GitHub issue body.
