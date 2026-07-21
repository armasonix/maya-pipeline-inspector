# User Guide

**Product:** Maya Pipeline Inspector (`maya-pipeline-inspector`)  
**Status:** v0.5.0 shipped (2026-07-12) · v0.6 in development on `dev`  
**Related:** [MAYA_INSTALL.md](MAYA_INSTALL.md) · [ARCHITECTURE.md](ARCHITECTURE.md) · [STUDIO_OVERRIDES.md](STUDIO_OVERRIDES.md) · [CONTRIBUTING.md](../CONTRIBUTING.md) · [CHANGELOG.md](../CHANGELOG.md)

Maya Pipeline Inspector is an **open-source** production-oriented material and scene QA tool for Autodesk Maya (MIT, [GitHub](https://github.com/armasonix/maya-pipeline-inspector)). It helps Technical Artists, Shader TDs, Pipeline TDs, and render supervisors detect material and geometry problems before publish or render farm submission. To contribute rules, adapters, or integrations, see [CONTRIBUTING.md](../CONTRIBUTING.md), [`COMMUNITY.md`](../COMMUNITY.md), and the [README community section](../README.md#open-source--community).

> **Honest scope:** the project is **actively developed** and **far from feature-complete**. Many integrations are MVP-quality, Maya coverage is limited to tested versions, and headless paths do not mirror every panel behavior. Read [Known limitations & gaps](#known-limitations--gaps) before betting a facility rollout on it.

## GUI-first workflow

Pipeline Inspector is built for daily use **inside the Maya dockable panel**. Pipeline TDs can automate the same checks headlessly, but Technical Artists and Shader TDs should not need a terminal or JSON export for routine validate → triage → fix → revalidate work.

Product principles ([ADR 0005](adr/0005-gui-first-product-philosophy.md)):

1. **Panel first** — Open **Window → Pipeline Inspector** (or the shelf button). For farm preflight, use **Pipeline Inspector → Pipeline Inspector Farm Check** or the **Pipeline Inspector Farm Check** shelf button.
2. **Fast paths** — Target three clicks or fewer from an open panel to an actionable result (for example: open panel → **Validate Scene** → double-click an issue to select the node).
3. **Clear blocking state** — After validation, the summary shows health score, severity counts, and whether the scene **blocks publish** or **blocks Deadline** without opening a report file.
4. **Low-friction fixes** — Safe auto-fixes use the Fixes tab queue; high-risk or referenced edits still require explicit confirmation per studio policy.
5. **Same results everywhere** — The panel, `pipeline_inspector validate`, and Deadline preflight share one validation pipeline, so GUI and headless reports stay aligned.
6. **Check for Updates** — Use the panel header button to compare against GitHub Releases. Module-path installs can download and install in-app; pip installs should use `mayapy -m pip install -U` (see [auto_update.md](integrations/auto_update.md)).

UX friction and Wave 1 backlog: [MAYA_UX_AUDIT_v0.4.md](MAYA_UX_AUDIT_v0.4.md).

Headless CLI, manifest gates, and farm preflight remain available for publish hooks and render wranglers — see [CLI_TESTING.md](CLI_TESTING.md) and [integrations/deadline_submit_preflight.md](integrations/deadline_submit_preflight.md). v0.4 adds a **Farm** tab for Deadline 10 on-prem preflight and submit from the panel.

## What the Tool Checks

v0.3 adds manifest schema 1.1, manifest regression gates, headless apply-fixes, texture resolution budgets by asset class, and plugin dual install. v0.2 adds expanded safe fixes, renderer policy packs, manifest diff, waiver manager, and pipeline integration docs. v0.1 MVP validates:

- missing texture files;
- local or unsafe texture paths;
- stale texture versions (filesystem sibling scan only; see [Texture version freshness](#texture-version-freshness));
- broken UDIM tile sets;
- wrong color space on data maps;
- risky displacement setups;
- expensive shader graphs;
- duplicate or orphan material networks;
- geometry polycount over asset-class budgets (v0.6);
- accidental duplicate meshes with identical topology (v0.6);
- basic renderer compatibility;
- Deadline preflight safety.

## Shader farm cost score

During validation, Pipeline Inspector profiles each material subgraph and stores complexity metadata on `MaterialSnapshot.complexity_metadata`:

| Field | Meaning |
| --- | --- |
| `expensive_node_count` | Count of nodes flagged as high render cost. |
| `expensive_node_types` | Per node-type totals for expensive nodes (for example `VRayBlendMtl`, `aiLayerShader`). |
| `farm_cost_score` | Weighted sum of adapter cost weights across the material graph. |
| `farm_cost_hint` | Cost band: `low` (<8), `medium` (<16), `high` (<28), `critical` (28+). |

Expensive nodes come from renderer adapter lists in `adapters/base.py` (V-Ray blend/SSS/layered nodes, Arnold layer/mix/OSL nodes, common `layeredTexture`) plus any node whose adapter weight is **1.5 or higher**. Rules `common.shader_complexity.expensive_nodes.max` and `common.shader_complexity.farm_cost_score.max` compare these metrics against profile budgets. `deadline_critical` and `publish_strict` tighten the thresholds for farm submission and publish gates.

The score is a relative complexity estimate for triage, not a measured render time. Use it to spot layered shaders worth simplifying before farm submission.

## Texture version freshness

Rule `common.texture.version.latest` compares the `v###` token in a texture filename against the highest numeric sibling found in the same folder on disk (for example `albedo_v001.<UDIM>.exr` vs `albedo_v003.<UDIM>.exr` in the same directory).

**v0.2 limitation:** version detection is filesystem-based only. Pipeline Inspector does not query a publish database, asset management system, or shot-level version registry. If the latest approved texture lives on another path, branch, or storage tier, the rule may report a false pass or false fail.

The check is skipped when the filename has no `v###` version token or when the scanner cannot resolve version metadata from the path.

## Texture resolution budgets

Rules `common.texture.resolution.{hero,prop,background}.max` compare `max_dimension` (longest image edge in pixels) on texture file dependencies. The rules are **disabled by default**; enable one tier per asset using packaged profiles:

| Profile | Max longest edge |
|---|---|
| `asset_class_hero` | 4096px |
| `asset_class_prop` | 2048px |
| `asset_class_background` | 1024px |

During Maya scan, snapshot enrichment probes PNG/JPEG/WebP headers to populate `max_dimension` without a Pillow dependency. When metadata is unavailable, the rule is skipped rather than failed.

Headless example:

```bash
python -m pipeline_inspector validate scene.ma --profile-id asset_class_hero --report report.json
```

Shader manifests (schema 1.1) include `max_dimension` per texture entry for diff review.

## Main User Roles

### Technical Artist

Main needs:

- validate current scene or selected assets;
- see clear red/yellow/green status;
- jump to broken nodes;
- understand why an issue matters;
- apply low-risk fixes safely;
- avoid rejected publishes or failed farm submissions.

### Shader TD

Main needs:

- enforce material rules;
- inspect shader networks;
- author or tune rule packs;
- validate renderer-specific material behavior;
- keep shader libraries clean.

### Pipeline TD

Main needs:

- run validation headlessly;
- generate deterministic JSON reports;
- integrate with publish tools;
- integrate with Deadline submit flow;
- maintain project/show-specific profiles.

### Render Supervisor

Main needs:

- know if an asset or shot is safe for farm submission;
- review blocking issues;
- approve waivers if policy allows;
- inspect material health trends and reports.

## Expected Maya UI Workflow

```text
1. Open Maya scene.
2. Open Maya Pipeline Inspector panel.
3. Select profile: `artist_relaxed`, `publish_strict`, `deadline_critical`, `supervisor_full`, or `ci_headless`.
4. Click Validate Scene or Validate Selection.
5. Review health score and blocking status.
6. Filter issues by severity, owner, blocking status, or auto-fix availability.
7. Select an issue.
8. Read what failed and why it matters.
9. Use Select Node, Open in Hypershade, Copy Path, or Reveal File.
10. Apply safe fixes if available.
11. Revalidate.
12. Export JSON/HTML report if needed.
```

## Maya UI Layout

The dockable panel uses six tabs. Each tab shows the panel title and version at the top.

```text
+--------------------------------------------------------------------------------+
| Maya Pipeline Inspector  v0.5.0+                                               |
| [Validate] [Waivers] [Fixes] [Reports] [Readiness] [Farm]                    |
+--------------------------------------------------------------------------------+
| Validate tab (default)                                                         |
| Health: 78/100   Critical: 2   Error: 5   Warning: 17   Info: 8                |
| Publish Block: YES   Deadline Block: YES                                         |
| Workflow: [Publish Strict]   Asset class: [None | Hero | Prop | Background]    |
| [Validate Scene] [Validate Selection]                                          |
| Severity [All]  Owner [All]  View [All issues]  Sort [severity]                 |
| Issues table ...                                                               |
| Issue Details + [Select Node] [Hypershade] [Copy Path] [Reveal File]           |
+--------------------------------------------------------------------------------+
| Waivers tab: status, waiver table, [Make Waive] [Refresh] [Revoke Selected]     |
| Fixes tab: checkbox column + fix queue table, [Fix Selected] [Apply Safe Fixes]  |
|            [Export Fix Plan]                                                   |
| Reports tab: compact export buttons for JSON/HTML/manifest/diff/compare          |
| Readiness tab: machine checks, [Run Machine Readiness], escalation actions       |
| Farm tab: Deadline connection, scene readiness, eligibility, last report/job id |
|           [Refresh Connection] [Run Farm Preflight] [Submit to Farm]          |
+--------------------------------------------------------------------------------+
```

Menu and shelf shortcuts (see [MAYA_INSTALL.md](MAYA_INSTALL.md)):

- **Pipeline Inspector** — open panel (Validate tab)
- **Pipeline Inspector Farm Check** — open Farm tab and run preflight
- **Readiness Check** — open Readiness tab (v0.6)

### Validation profiles (Workflow + Asset class)

**Workflow** profiles control role and publish/deadline blocking policy:

| Profile | Typical use |
|---|---|
| `artist_relaxed` | Daily lookdev with fewer complexity warnings |
| `publish_strict` | Publish gate — blocking issues stop submission |
| `deadline_critical` | Farm submit preflight |
| `supervisor_full` | Full review with batch risky-fix confirmation |

**Asset class** is an optional overlay for texture resolution budgets:

| Profile | Max longest edge |
|---|---|
| None | No resolution tier (rules stay disabled) |
| `asset_class_hero` | 4096px |
| `asset_class_prop` | 2048px |
| `asset_class_background` | 1024px |

When an asset class is selected, its resolution and geometry rule overrides are merged onto the active workflow profile. Pipeline-only profiles such as `ci_headless` are headless-only and do not appear in the Maya UI dropdown.

## Machine Readiness (v0.6)

The **Readiness** tab evaluates whether the current workstation meets studio prerequisites before publish or farm work:

| Check category | Examples |
| --- | --- |
| Maya plugins | V-Ray, Arnold, studio custom plug-ins |
| Mapped drives | Texture / asset roots |
| Environment variables | `SHOW_ROOT`, pipeline tokens |
| Network paths | UNC roots from `studio_environment` |
| Installed software | Required DCC or utility versions |

Pipeline TDs configure checks in `pipeline_inspector_studio.json` under `readiness.checks`. Technical Artists click **Run Machine Readiness**; failed checks show actionable detail. When connectors are enabled, the tab can escalate a summary to sysadmin or support.

Open the tab from the panel or via menu/shelf **Readiness Check**. Architecture detail: [ARCHITECTURE.md](ARCHITECTURE.md#machine-readiness).

## Roles and permissions (v0.6)

Pipeline Inspector resolves an effective role (Technical Artist, Technical Support, Pipeline TD, Admin) and gates risky actions:

| Action | Required capability |
| --- | --- |
| Apply high-risk fixes | `apply_risky_fixes` |
| Submit to Farm | `submit_farm` |
| Save studio config / edit connectors | `edit_studio_settings`, `edit_connectors` |
| Add extra rule paths | `manage_rules` |

Technical Artists set **Assigned role** in Settings → Basic unless studio policy locks it. Studio overrides: [STUDIO_OVERRIDES.md](STUDIO_OVERRIDES.md#governance-and-role-assignment-v06) · [ADR 0008](adr/0008-role-based-governance-foundation.md).

## Health Score

The health score is a quick summary of scene or selection quality.

Example:

```text
Health: 76 / 100
Critical: 1
Error: 2
Warning: 14
Info: 8
Publish Block: YES
Deadline Block: YES
Auto-fixable: 9
Waived: 2
```

A high score does not mean the scene is visually final. It means the scene has fewer detected technical material risks according to the selected profile.

## Severity Meaning

| Severity | Meaning |
|---|---|
| Info | Useful cleanup or visibility. Usually not blocking. |
| Warning | Should be reviewed. Usually not blocking. |
| Error | Should be fixed before publish. May block depending on profile. |
| Critical | High production risk. Usually blocks publish or Deadline. |

## Blocking Status

The tool separates severity from block policy.

A rule may be critical but only block publish. Another rule may be an error in UI but block Deadline in strict farm-preflight profile.

Important block flags:

- `block_publish`
- `block_deadline`

## Profiles

Profiles control strictness and runtime behavior.

Packaged MVP profiles (under `src/pipeline_inspector/rules/profiles/`):

| Profile | Purpose |
|---|---|
| `artist_relaxed` | Interactive lookdev checks with fewer blocks. |
| `publish_strict` | Asset publish checks. Blocks serious issues. |
| `deadline_critical` | Fast farm submission preflight. Critical-only where possible. |
| `supervisor_full` | Full audit mode with all rules visible. |
| `ci_headless` | Deterministic validation for automated checks. Same rule profile in UI and CLI; selecting it in Maya does not spawn a separate headless process. |
| `asset_class_hero` | Hero asset publish gate with 4096px texture resolution budget. |
| `asset_class_prop` | Prop asset publish gate with 2048px texture resolution budget. |
| `asset_class_background` | Background asset checks with 1024px texture resolution budget. |

The Maya UI and headless CLI both call the same validation pipeline (`run_validation`). Choosing `ci_headless` in the panel only changes which rules/overrides are applied to the current scene scan.

## Renderer Rule Packs

Packaged renderer-specific rules live under `src/pipeline_inspector/rules/vray/` and `src/pipeline_inspector/rules/arnold/`.

Current v0.1 renderer checks are info-level audits such as:

- untextured V-Ray / Arnold materials;
- displacement-linked materials that should be reviewed before publish.

These rules load when the snapshot renderer is `vray` or `arnold`.

## Issue Details

Every issue should explain:

- what failed;
- why it matters;
- current value;
- expected value;
- affected material/node/plug;
- owner;
- rule ID;
- graph trace;
- block flags;
- auto-fix availability.

Example:

```text
Issue: Roughness texture is color-managed as ACEScg.
Why: Roughness is scalar data. Color transforms can change numeric values and alter reflection response.
Current: ACEScg
Expected: Raw
Owner: Shader TD
Rule: common.texture.colorspace.data_raw
Auto-fix: available
```

## Safe Auto-Fix Workflow

Use the **checkboxes** in the Selected column to choose fixes. **Apply Safe Fixes** runs only non-blocked low-risk `set_attr` fixes. **Apply Selected Fixes** runs checked medium/high fixes (with confirmation when required).

### Local development paths (no studio `$ASSET_ROOT` yet)

When textures use absolute paths such as `D:/Workspace/.../examples/broken_scene/textures/...`, the `normalize_path` fix rewrites them relative to the detected project root (folder containing `src/pipeline_inspector/`) as `${ASSET_ROOT}/examples/broken_scene/...`.

Paths outside the project (for example `C:/Users/.../Documents/local_only_texture.exr`) normalize to `${ASSET_ROOT}/textures/<filename>`. Copy or relink the file into your project textures folder after apply if needed.

For a local-only workflow:

1. Validate and review the **After** column — it must show a real `${ASSET_ROOT}/...` path, not the placeholder `path policy compliant`.
2. Apply the normalize fix, then manually set Maya project/`ASSET_ROOT` resolver or replace `${ASSET_ROOT}` with your checkout path in file nodes.
3. Missing texture paths (`DOES_NOT_EXIST_...`) cannot be auto-fixed — create the file or relink manually.

Studio pipelines should configure `${ASSET_ROOT}` / `${TEXTURE_ROOT}` in rule packs and profiles per [`STUDIO_OVERRIDES.md`](STUDIO_OVERRIDES.md).

Auto-fix is never silent.

Expected flow:

```text
1. Select issue with available fix.
2. Review before/after values.
3. Review risk level.
4. Confirm fix.
5. Tool applies fix inside Maya undo chunk.
6. Revalidate.
```

Low-risk example:

```text
file_roughness.colorSpace: ACEScg -> Raw
```

High-risk fixes require explicit confirmation before apply. The fix queue shows how many risky fixes are pending and how many are selected. Click **Select** on each row you want to apply, then use **Apply Selected Fixes**. Cancel on a confirmation dialog leaves the scene unchanged; confirm applies fixes inside a Maya undo chunk.

Issue Details also shows **Reference safety** (referenced/locked node and whether fixes are blocked). See [`MAYA_V02_MANUAL_CHECKLIST.md`](MAYA_V02_MANUAL_CHECKLIST.md) for Maya verification sessions (demo, reference, renderer).

- **Strict profiles** (`artist_relaxed`, `publish_strict`, `deadline_critical`, …): one confirmation dialog per risky fix.
- **`supervisor_full`**: a single batch confirmation for all selected risky fixes.

## Reference Safety

Referenced nodes can be fixed **in the current scene** as Maya reference edits when the node is not locked. Locked nodes remain blocked.

The dockable panel shows **Reference safety** in Issue Details. Referenced fixes show **Blocked = NO** unless the node is locked or the fix is otherwise unplannable (for example an invalid normalize path). You do not need to open the reference file separately for typical attribute and path fixes.

If an issue is inside a referenced asset, the tool should:

- report the problem;
- show the reference path;
- apply safe fixes in-place when Maya allows reference edits;
- block only locked nodes or policy-blocked fixes;
- allow waiver only if profile policy permits it.

## Waivers

Waivers are controlled exceptions for known issues.

The dockable panel includes a **Waiver Manager** section that lists waivers from the scene sidecar (`*.pipeline_inspector_waivers.json`), shows rule id, target, approver, expiry, and whether each entry is active or expired. Expired waivers are labeled as ignored on validate. Use **Revoke Selected** to remove a waiver and revalidate.

Expected behavior (implemented via waiver sidecar beside the scene file):

- waiver must include reason;
- waiver must include approver;
- waiver should expire;
- waived issues remain visible in reports;
- critical farm-blocking issues are waiver-disabled by default unless profile allows it.

Example:

```text
Rule: common.texture.resolution.hero.max
Reason: Hero close-up approved by supervisor.
Approved by: supervisor_name
Expires: 2026-07-30
```

## Reports

Implemented report outputs:

- JSON report for automation;
- HTML report for human review;
- Shader Manifest for asset state tracking;
- manifest diff report for change review.

JSON reports are intended for pipeline systems. HTML reports are self-contained, modern summary pages for supervisors and TD review (health score, blocking status, severity groups, and issue tables with horizontal scroll for long rule IDs).

### Compare to Approved Manifest (v0.3)

Export a shader manifest beside the scene (`{scene}_pipeline_inspector_manifest.json`), then open the **Reports** tab or use **Compare to Approved Manifest** to diff against that sidecar without a file picker. If the sidecar is missing, the action falls back to the baseline manifest file picker (same as **Export Manifest Diff**). Use **Make Waive** on the **Waivers** tab for the selected issue from the Validate tab.

## Headless Usage

```bash
python -m pipeline_inspector validate scene.ma --profile-id publish_strict --report report.json
python -m pipeline_inspector manifest scene.ma --out shader_manifest.json
python -m pipeline_inspector validate snapshot.json --input-kind snapshot --profile-id ci_headless --report report.json
python -m pipeline_inspector validate scene.ma --waiver-sidecar scene.pipeline_inspector_waivers.json --report report.json
```

The headless CLI uses the same validation pipeline as the Maya UI (`prepare_snapshot_for_validation`, profile loading, waivers, enrichment, fix planning).

## Publish Preflight

Publish tools can gate asset commits with the `publish_strict` profile (or a studio copy) via [`examples/publish/submit_preflight.py`](../examples/publish/submit_preflight.py). See [`docs/integrations/publish_submit_preflight.md`](integrations/publish_submit_preflight.md) for exit codes and integration snippets.

Expected behavior:

```text
1. Technical Artist triggers publish.
2. Publish tool runs Pipeline Inspector validation with `publish_strict` profile.
3. If block_publish is false, publish continues.
4. If block_publish is true, publish stops and shows summary.
5. JSON report is saved for review.
```

## Deadline Submit Preflight

Deadline preflight should run validation before render submission.

**Full studio guide:** [integrations/deadline_submit_preflight.md](integrations/deadline_submit_preflight.md) — Web Service setup, pool/group routing, headless automation, and deployment checklist.

### Farm Submit

Technical Artist workflow for Deadline 10 on-prem validation from Maya (v0.4):

| Step | Where | Action |
| --- | --- | --- |
| 1 | Menu or shelf | **Pipeline Inspector Farm Check** — opens **Farm** tab and runs `deadline_critical` preflight in one click |
| 2 | Farm tab | Confirm **Status: Online** (green lamp). If **Offline**, ask TD to verify Web Service URL / `PIPELINE_INSPECTOR_DEADLINE_API_URL` |
| 3 | Farm tab | Review eligibility after preflight — blocked scenes show reasons (unsaved file, missing renderer plug-in, `block_deadline` issues) |
| 4 | Validate / Fixes tabs | Fix farm-blocking issues, then re-run **Pipeline Inspector Farm Check** or **Run Farm Preflight** |
| 5 | Farm tab | When eligibility is **allow**, click **Submit to Farm** to queue a CommandScript utility job |
| 6 | Farm tab | Note **Last farm report** and **Last Deadline job id** for supervisor / wrangler follow-up |

Headless / pipeline submit hooks use the same eligibility gate and profiles — see the [Deadline integration guide](integrations/deadline_submit_preflight.md#headless-automation).

Expected behavior:
1. Technical Artist submits render (or clicks **Submit to Farm** in the panel).
2. Submit tool runs Pipeline Inspector validation with `deadline_critical` profile.
3. If `block_deadline` is false, submission continues.
4. If `block_deadline` is true, submission stops and shows summary.
5. JSON report is saved for review.

## Best Practices for Users

- Validate before publish, not after render failure.
- Fix critical issues before sending to farm.
- Do not waive missing textures or unsafe local paths unless policy explicitly allows it.
- Use selection validation while working on a single asset.
- Use full scene validation before publish or submission.
- Export reports for supervisor review when issues are complex.

## Current Development Status

Maya Pipeline Inspector is **not production-complete**. It solves a narrow but important problem — early material and scene QA inside Maya — while many surrounding pipeline concerns (asset versioning, shot tracking, render scheduling, cross-DCC validation) are only partially addressed or still on the roadmap.

**Shipped:** **v0.5.0** (2026-07-12) — settings hub, notifications, trackers, rule authoring MVP, auto-update (module path), bug-report relay.

**In active development on `dev`:** **v0.6** — geometry QA rules, Machine Readiness tab, role governance foundation ([ADR 0008](adr/0008-role-based-governance-foundation.md)), Deadline farm analytics CLI. These areas are **functional but still being refined**; behavior and configuration may change before the next release tag.

Public CI runs pure Python tests without launching Maya. Optional `mayapy` integration is documented in [MAYA_INSTALL.md](MAYA_INSTALL.md) and [CLI_TESTING.md](CLI_TESTING.md), but **most contributors never run it in CI** — treat Maya-specific bugs as expected until reported.

## Known limitations & gaps

Use this section when deciding whether Pipeline Inspector fits your facility **today**, not on the roadmap slide.

### Product scope

- **Maya-first.** Other DCCs are out of scope. USD/MaterialX inspection is listed as a future adapter; do not assume cross-DCC parity.
- **QA assistant, not a publish system.** The tool validates and reports; your publish tool, tracker, and farm scheduler still own submission, versioning, and scheduling.
- **Beta quality.** Panel layout, Settings tabs, compact UI, and connector error messages are still being improved release to release.

### Maya platform

| Topic | Limitation |
| --- | --- |
| Supported Maya | **2024–2025** tested; **2026** best-effort; **2023−** not tested ([MAYA_INSTALL.md](MAYA_INSTALL.md)) |
| Native plugin | Compiled `.mll` binaries are **not in the git repo** — build locally ([ADR 0006](adr/0006-native-mll-plugin-strategy.md)) or use release attachments; Python plug-in fallback always available |
| Maya in CI | Default GitHub Actions jobs **do not launch Maya**; integration smoke is optional on self-hosted runners |
| Renderer plugins | V-Ray / Arnold rules require the matching plug-in **loaded in the session** being validated |

### Validation engine

- **Heuristic scoring.** Health score and farm cost score summarize rule outcomes; they are **not** measured render time or farm dollar cost.
- **Texture versions.** Version freshness compares **filesystem siblings only** — no query against a publish database, Perforce/ShotGrid version, or texture library API ([Texture version freshness](#texture-version-freshness)).
- **Semantic mapping.** Renderer adapter slot mapping can be **incomplete** on exotic node graphs ([ADR 0002](adr/0002-renderer-adapter-boundary.md)).
- **Geometry (v0.6).** Polycount and duplicate-mesh checks depend on scan scope and budget; large scenes may **truncate** duplicate scans with evidence flagged in the report.
- **False results.** Any rule can false-pass or false-fail on studio-specific setups. Waivers exist, but someone must curate them.

### Panel vs headless

| Surface | Loads studio config | Loads user.json | Notes |
| --- | :---: | :---: | --- |
| Maya panel | ✓ | ✓ | Primary, most complete experience |
| CLI (`validate`, `gate`, …) | ✓ (`--studio-config` or env) | ✗ | Uses default user prefs; **role/governance may differ** from a Technical Artist's panel session |
| Readiness tab | ✓ | ✓ | **Maya session only** — no headless readiness CLI parity |
| Connectors (notify / tracker) | ✓ | partial | Require live network, credentials, and studio JSON rollout |

### Roles and governance (v0.6)

- Capability gates are a **foundation**, not full studio IAM.
- **User-assigned role** in Settings → Basic is **self-reported** unless `governance.enforced_role` locks it.
- Tracker role mapping uses **`PIPELINE_INSPECTOR_TRACKER_ROLE`** env + JSON map — not automatic session discovery from every tracker client.
- Denied actions show a reason string; there is **no audit log export** for compliance review yet.

### Connectors and integrations

- **Notifications** (Telegram, Discord, Slack): webhook/token setup, `notify_on` tuning, and report links are studio responsibilities; delivery failures may be silent except in debug logs.
- **Trackers:** Ftrack and ShotGrid support Markdown notes and optional HTML attachments; **Cerebro has no HTML upload API** — path is echoed in the note only ([tracker_publish.md](integrations/tracker_publish.md)).
- **Deadline:** **On-prem Deadline 10** Web Service only in current docs; AWS Deadline Cloud is a separate integration surface. Farm tab **Submit to Farm** queues a **validation utility job**, not a beauty render pass.
- **Bug report relay:** Requires a reachable HTTPS endpoint. The **public default** notifies upstream maintainers; a **studio private relay** is for facilities that **develop or fork the plugin locally** and need **in-house R&D** alerted about plugin defects (crashes, panel bugs, validation regressions) — not scene or asset issues. See [bug_report_relay.md](integrations/bug_report_relay.md#why-a-studio-private-relay).
- **Auto-update:** **Module-path installs only** — `pip` / `site-packages` installs must upgrade manually ([auto_update.md](integrations/auto_update.md)).

### Rule authoring and policy

- Rule browser / new rule wizard covers **MVP templates**; complex checks need JSON by hand ([RULE_AUTHORING.md](RULE_AUTHORING.md)).
- Session rule overrides from the Rule Editor **do not persist** across Maya restarts.
- Studio `extra_rules_folder` deployment is manual unless your pipeline syncs it.

### Safe fixes and scene mutation

- Auto-fix covers **only rules that define a fix** and pass safety/reference checks.
- Referenced and locked nodes are blocked by default; **reference edits** need explicit confirmation.
- High-risk fixes require capability + confirmation; studios still need policy for what Technical Artists may change.
- Undo chunks help, but **always validate again** after apply — fixes can miss edge cases.

### What we are still building

Non-exhaustive backlog visible on `dev` and in [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md):

- Deeper tracker-driven role resolution and publish routing
- Additional renderer adapters (RenderMan, Redshift, USD/MaterialX)
- Stronger headless parity for user prefs and readiness
- Richer rule editor and audit trails
- Broader Maya version CI coverage

If you hit a gap, file an issue on GitHub with scene/profile steps — production feedback drives priority.

See also:

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [integrations/deadline_submit_preflight.md](integrations/deadline_submit_preflight.md)
- [integrations/deadline_farm_analytics.md](integrations/deadline_farm_analytics.md)
- [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)
- [RULE_AUTHORING.md](RULE_AUTHORING.md)
