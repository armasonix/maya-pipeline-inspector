# User Guide

Maya Shader Health Inspector is a production-oriented material QA tool for Autodesk Maya. It is designed to help artists, Shader TDs, Pipeline TDs, and render supervisors detect material problems before publish or render farm submission.

Status: v0.1 MVP. The dockable Maya UI, headless CLI, packaged profiles, waiver sidecars, and report export are implemented. See the demo scene under `examples/broken_scene/`.

Install in Maya: [`docs/MAYA_INSTALL.md`](MAYA_INSTALL.md) (`MAYA_MODULE_PATH`, editable `pip`, menu/shelf bootstrap).

Studio rule packs and profile overrides: [`docs/STUDIO_OVERRIDES.md`](STUDIO_OVERRIDES.md).

## What the Tool Checks

The v0.1 MVP validates:

- missing texture files;
- local or unsafe texture paths;
- stale texture versions (filesystem sibling scan only; see [Texture version freshness](#texture-version-freshness));
- broken UDIM tile sets;
- wrong color space on data maps;
- risky displacement setups;
- expensive shader graphs;
- duplicate or orphan material networks;
- basic renderer compatibility;
- Deadline preflight safety.

## Texture version freshness

Rule `common.texture.version.latest` compares the `v###` token in a texture filename against the highest numeric sibling found in the same folder on disk (for example `albedo_v001.<UDIM>.exr` vs `albedo_v003.<UDIM>.exr` in the same directory).

**v0.2 limitation:** version detection is filesystem-based only. Shader Health Inspector does not query a publish database, asset management system, or shot-level version registry. If the latest approved texture lives on another path, branch, or storage tier, the rule may report a false pass or false fail.

The check is skipped when the filename has no `v###` version token or when the scanner cannot resolve version metadata from the path.

## Main User Roles

### Artist / Lookdev Artist

Main needs:

- validate current scene or selected assets;
- see clear red/yellow/green status;
- jump to broken nodes;
- understand why an issue matters;
- apply low-risk fixes safely;
- avoid rejected publishes or failed farm submissions.

### Shader TD / Technical Artist

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
2. Open Maya Shader Health Inspector panel.
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

```text
+--------------------------------------------------------------------------------+
| Maya Shader Health Inspector                                                    |
| Health: 78/100   Critical: 2   Error: 5   Warning: 17   Deadline Block: YES     |
| Profile: publish_strict                                                         |
| [Validate Scene] [Validate Selection]                                           |
+--------------------------------------------------------------------------------+
| Sort: [severity]  Severity: [All severities]  Owner: [All owners]               |
| View: [All issues | Blocking only | Auto-fixable]                               |
+--------------------------------------------------------------------------------+
| Sev | Material | Node | Issue | Owner | Rule                                    |
+--------------------------------------------------------------------------------+
| Details                                                                        |
| What: Roughness texture is color-managed as ACEScg.                             |
| Why: Roughness is scalar data; color transforms alter numeric values.           |
| Current: ACEScg                                                                 |
| Expected: Raw                                                                   |
| Trace: file_roughness.outAlpha -> material.roughness                           |
| [Select Node] [Open in Hypershade] [Copy Path] [Reveal File] [Waive]          |
+--------------------------------------------------------------------------------+
| Fix Queue: preview safe fixes, apply selected or all safe fixes                 |
| Export: JSON / HTML / Shader Manifest                                           |
+--------------------------------------------------------------------------------+
```

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

A high score does not mean the scene is artistically correct. It means the scene has fewer detected technical material risks according to the selected profile.

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

Packaged MVP profiles (under `src/shader_health/rules/profiles/`):

| Profile | Purpose |
|---|---|
| `artist_relaxed` | Interactive lookdev checks with fewer blocks. |
| `publish_strict` | Asset publish checks. Blocks serious issues. |
| `deadline_critical` | Fast farm submission preflight. Critical-only where possible. |
| `supervisor_full` | Full audit mode with all rules visible. |
| `ci_headless` | Deterministic validation for automated checks. Same rule profile in UI and CLI; selecting it in Maya does not spawn a separate headless process. |

The Maya UI and headless CLI both call the same validation pipeline (`run_validation`). Choosing `ci_headless` in the panel only changes which rules/overrides are applied to the current scene scan.

## Renderer Rule Packs

Packaged renderer-specific rules live under `src/shader_health/rules/vray/` and `src/shader_health/rules/arnold/`.

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

High-risk fixes should require explicit confirmation or supervisor approval depending on profile.

## Reference Safety

Referenced and locked nodes should not be modified by default.

If an issue is inside a referenced asset, the tool should:

- report the problem;
- show the reference path;
- block unsafe auto-fix by default;
- suggest opening/fixing the source asset file;
- allow waiver only if profile policy permits it.

## Waivers

Waivers are controlled exceptions for known issues.

The dockable panel includes a **Waiver Manager** section that lists waivers from the scene sidecar (`*.shader_health_waivers.json`), shows rule id, target, approver, expiry, and whether each entry is active or expired. Expired waivers are labeled as ignored on validate. Use **Revoke Selected** to remove a waiver and revalidate.

Expected behavior (implemented via waiver sidecar beside the scene file):

- waiver must include reason;
- waiver must include approver;
- waiver should expire;
- waived issues remain visible in reports;
- critical farm-blocking issues are waiver-disabled by default unless profile allows it.

Example:

```text
Rule: common.texture.resolution.max
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

## Headless Usage

```bash
python -m shader_health validate scene.ma --profile-id publish_strict --report report.json
python -m shader_health validate snapshot.json --input-kind snapshot --profile-id ci_headless --report report.json
python -m shader_health validate scene.ma --waiver-sidecar scene.shader_health_waivers.json --report report.json
```

The headless CLI uses the same validation pipeline as the Maya UI (`prepare_snapshot_for_validation`, profile loading, waivers, enrichment, fix planning).

## Publish Preflight

Publish tools can gate asset commits with the `publish_strict` profile (or a studio copy) via [`examples/publish/submit_preflight.py`](../examples/publish/submit_preflight.py). See [`docs/integrations/publish_submit_preflight.md`](integrations/publish_submit_preflight.md) for exit codes and integration snippets.

Expected behavior:

```text
1. Artist triggers publish.
2. Publish tool runs shader health validation with publish_strict profile.
3. If block_publish is false, publish continues.
4. If block_publish is true, publish stops and shows summary.
5. JSON report is saved for review.
```

## Deadline Submit Preflight

Deadline preflight should run validation before render submission.

Expected behavior:
1. Artist submits render.
2. Submit tool runs shader health validation with deadline_critical profile.
3. If block_deadline is false, submission continues.
4. If block_deadline is true, submission stops and shows summary.
5. JSON report is saved for review.
```

## Best Practices for Users

- Validate before publish, not after render failure.
- Fix critical issues before sending to farm.
- Do not waive missing textures or unsafe local paths unless policy explicitly allows it.
- Use selection validation while working on a single asset.
- Use full scene validation before publish or submission.
- Export reports for supervisor review when issues are complex.

## Current Development Status

v0.1 MVP is implemented: core rule engine, Maya scanner, snapshot enrichment, dockable UI, headless CLI, packaged profiles, waiver sidecars, JSON/HTML reports, shader manifest export, and safe-fix queue. Public CI runs pure Python tests; optional `mayapy` integration is documented in [`MAYA_INSTALL.md`](MAYA_INSTALL.md).

See also:

- `docs/MAYA_INSTALL.md`
- `docs/DEVELOPMENT_PLAN.md`
- `docs/ARCHITECTURE.md`
- `docs/RULE_AUTHORING.md`
